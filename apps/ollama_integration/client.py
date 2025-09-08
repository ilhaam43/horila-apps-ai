import requests
import json
import time
import logging
from typing import Dict, List, Optional, Any, Generator
from dataclasses import dataclass
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from queue import Queue, Empty

from .models import OllamaConfiguration, OllamaModel, OllamaProcessingJob, OllamaModelUsage


logger = logging.getLogger(__name__)


@dataclass
class OllamaResponse:
    """Ollama API response wrapper"""
    success: bool
    content: str
    model: str
    tokens_used: int = 0
    processing_time: float = 0.0
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class OllamaConnectionError(Exception):
    """Ollama connection error"""
    pass


class OllamaModelError(Exception):
    """Ollama model error"""
    pass


class OllamaClient:
    """Ollama API Client for local AI processing"""
    
    def __init__(self, config_name: str = 'default'):
        self.config = self._get_configuration(config_name)
        self.session = requests.Session()
        self.session.timeout = self.config.timeout
        self._setup_session()
        
        # Thread pool for concurrent requests
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_requests)
        
        # Request queue for rate limiting
        self.request_queue = Queue(maxsize=self.config.request_queue_size)
        self._queue_worker_running = False
        self._start_queue_worker()
    
    def _get_configuration(self, config_name: str) -> OllamaConfiguration:
        """Get Ollama configuration"""
        try:
            return OllamaConfiguration.objects.get(name=config_name, is_active=True)
        except OllamaConfiguration.DoesNotExist:
            # Create default configuration if it doesn't exist
            return OllamaConfiguration.objects.create(
                name='default',
                description='Default Ollama configuration',
                host='localhost',
                port=11434
            )
    
    def _setup_session(self):
        """Setup HTTP session with authentication and headers"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Horilla-Ollama-Client/1.0'
        }
        
        if self.config.api_key:
            headers['Authorization'] = f'Bearer {self.config.api_key}'
        
        self.session.headers.update(headers)
        
        if self.config.username and self.config.password:
            self.session.auth = (self.config.username, self.config.password)
    
    def _start_queue_worker(self):
        """Start background queue worker"""
        if not self._queue_worker_running:
            self._queue_worker_running = True
            threading.Thread(target=self._queue_worker, daemon=True).start()
    
    def _queue_worker(self):
        """Background worker to process request queue"""
        while self._queue_worker_running:
            try:
                request_func, args, kwargs, result_queue = self.request_queue.get(timeout=1)
                try:
                    result = request_func(*args, **kwargs)
                    result_queue.put(('success', result))
                except Exception as e:
                    result_queue.put(('error', e))
                finally:
                    self.request_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                logger.error(f"Queue worker error: {e}")
    
    def health_check(self) -> bool:
        """Check if Ollama server is healthy"""
        try:
            response = self.session.get(
                f"{self.config.effective_base_url}/api/tags",
                timeout=5
            )
            is_healthy = response.status_code == 200
            self.config.update_health_status(is_healthy)
            return is_healthy
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            self.config.update_health_status(False)
            return False
    
    def list_models(self) -> List[Dict]:
        """List available models on Ollama server"""
        try:
            response = self.session.get(f"{self.config.effective_base_url}/api/tags")
            response.raise_for_status()
            return response.json().get('models', [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            raise OllamaConnectionError(f"Failed to list models: {e}")
    
    def pull_model(self, model_name: str) -> bool:
        """Pull/download a model"""
        try:
            data = {'name': model_name}
            response = self.session.post(
                f"{self.config.effective_base_url}/api/pull",
                json=data,
                stream=True
            )
            response.raise_for_status()
            
            # Process streaming response
            for line in response.iter_lines():
                if line:
                    try:
                        status = json.loads(line)
                        if status.get('status') == 'success':
                            return True
                    except json.JSONDecodeError:
                        continue
            
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False
    
    def generate(self, 
                model_name: str, 
                prompt: str, 
                system_prompt: Optional[str] = None,
                temperature: float = 0.7,
                max_tokens: int = 2048,
                top_p: float = 0.9,
                top_k: int = 40,
                stream: bool = False,
                **kwargs) -> OllamaResponse:
        """Generate text using Ollama model"""
        
        start_time = time.time()
        
        try:
            # Prepare request data
            data = {
                'model': model_name,
                'prompt': prompt,
                'stream': stream,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens,
                    'top_p': top_p,
                    'top_k': top_k,
                    **kwargs
                }
            }
            
            if system_prompt:
                data['system'] = system_prompt
            
            # Make request with retries
            response = self._make_request_with_retry(
                'POST',
                f"{self.config.effective_base_url}/api/generate",
                json=data
            )
            
            processing_time = time.time() - start_time
            
            if stream:
                return self._handle_streaming_response(response, model_name, processing_time)
            else:
                return self._handle_single_response(response, model_name, processing_time)
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Generation failed for model {model_name}: {e}")
            return OllamaResponse(
                success=False,
                content="",
                model=model_name,
                processing_time=processing_time,
                error=str(e)
            )
    
    def chat(self, 
            model_name: str, 
            messages: List[Dict[str, str]],
            temperature: float = 0.7,
            max_tokens: int = 2048,
            stream: bool = False,
            **kwargs) -> OllamaResponse:
        """Chat with Ollama model using conversation format"""
        
        start_time = time.time()
        
        try:
            data = {
                'model': model_name,
                'messages': messages,
                'stream': stream,
                'options': {
                    'temperature': temperature,
                    'num_predict': max_tokens,
                    **kwargs
                }
            }
            
            response = self._make_request_with_retry(
                'POST',
                f"{self.config.effective_base_url}/api/chat",
                json=data
            )
            
            processing_time = time.time() - start_time
            
            if stream:
                return self._handle_streaming_response(response, model_name, processing_time)
            else:
                return self._handle_single_response(response, model_name, processing_time)
                
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Chat failed for model {model_name}: {e}")
            return OllamaResponse(
                success=False,
                content="",
                model=model_name,
                processing_time=processing_time,
                error=str(e)
            )
    
    def embed(self, model_name: str, text: str) -> OllamaResponse:
        """Generate embeddings for text"""
        start_time = time.time()
        
        try:
            data = {
                'model': model_name,
                'prompt': text
            }
            
            response = self._make_request_with_retry(
                'POST',
                f"{self.config.effective_base_url}/api/embeddings",
                json=data
            )
            
            processing_time = time.time() - start_time
            result = response.json()
            
            return OllamaResponse(
                success=True,
                content="",  # Embeddings don't have text content
                model=model_name,
                processing_time=processing_time,
                metadata={'embeddings': result.get('embedding', [])}
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Embedding failed for model {model_name}: {e}")
            return OllamaResponse(
                success=False,
                content="",
                model=model_name,
                processing_time=processing_time,
                error=str(e)
            )
    
    def _make_request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = self.session.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except Exception as e:
                last_exception = e
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay * (2 ** attempt))  # Exponential backoff
                    continue
                break
        
        raise last_exception
    
    def _handle_single_response(self, response: requests.Response, model_name: str, processing_time: float) -> OllamaResponse:
        """Handle single (non-streaming) response"""
        try:
            result = response.json()
            content = result.get('response', '')
            
            # Extract token usage if available
            tokens_used = 0
            if 'eval_count' in result:
                tokens_used = result['eval_count']
            
            return OllamaResponse(
                success=True,
                content=content,
                model=model_name,
                tokens_used=tokens_used,
                processing_time=processing_time,
                metadata={
                    'eval_count': result.get('eval_count', 0),
                    'eval_duration': result.get('eval_duration', 0),
                    'load_duration': result.get('load_duration', 0),
                    'prompt_eval_count': result.get('prompt_eval_count', 0),
                    'prompt_eval_duration': result.get('prompt_eval_duration', 0),
                }
            )
        except Exception as e:
            return OllamaResponse(
                success=False,
                content="",
                model=model_name,
                processing_time=processing_time,
                error=f"Failed to parse response: {e}"
            )
    
    def _handle_streaming_response(self, response: requests.Response, model_name: str, processing_time: float) -> Generator[OllamaResponse, None, None]:
        """Handle streaming response"""
        try:
            full_content = ""
            total_tokens = 0
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        content = chunk.get('response', '')
                        full_content += content
                        
                        if 'eval_count' in chunk:
                            total_tokens = chunk['eval_count']
                        
                        yield OllamaResponse(
                            success=True,
                            content=content,
                            model=model_name,
                            tokens_used=total_tokens,
                            processing_time=processing_time,
                            metadata=chunk
                        )
                        
                        if chunk.get('done', False):
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            yield OllamaResponse(
                success=False,
                content="",
                model=model_name,
                processing_time=processing_time,
                error=f"Streaming error: {e}"
            )
    
    def close(self):
        """Close client and cleanup resources"""
        self._queue_worker_running = False
        self.executor.shutdown(wait=True)
        self.session.close()


class OllamaModelManager:
    """Manager for Ollama models and processing jobs"""
    
    def __init__(self):
        self.client = OllamaClient()
    
    def get_best_model_for_task(self, task_type: str) -> Optional[OllamaModel]:
        """Get the best available model for a specific task"""
        models = OllamaModel.objects.filter(
            task_type=task_type,
            is_active=True
        ).order_by('-priority', '-success_rate', 'average_response_time')
        
        # Check if models are available on server
        available_models = self._get_available_models()
        
        for model in models:
            if model.effective_model_name in available_models:
                return model
        
        return None
    
    def _get_available_models(self) -> List[str]:
        """Get list of available models from server (cached)"""
        cache_key = 'ollama_available_models'
        models = cache.get(cache_key)
        
        if models is None:
            try:
                server_models = self.client.list_models()
                models = [model['name'] for model in server_models]
                cache.set(cache_key, models, 300)  # Cache for 5 minutes
            except Exception as e:
                logger.error(f"Failed to get available models: {e}")
                models = []
        
        return models
    
    def process_with_best_model(self, 
                               task_type: str, 
                               prompt: str, 
                               user,
                               system_prompt: Optional[str] = None,
                               **kwargs) -> OllamaResponse:
        """Process request with the best available model for the task"""
        
        model = self.get_best_model_for_task(task_type)
        if not model:
            return OllamaResponse(
                success=False,
                content="",
                model="none",
                error=f"No available model for task type: {task_type}"
            )
        
        # Use model's default parameters if not provided
        kwargs.setdefault('temperature', model.temperature)
        kwargs.setdefault('max_tokens', model.max_tokens)
        kwargs.setdefault('top_p', model.top_p)
        kwargs.setdefault('top_k', model.top_k)
        
        start_time = time.time()
        response = self.client.generate(
            model.effective_model_name,
            prompt,
            system_prompt=system_prompt,
            **kwargs
        )
        
        # Update model metrics
        processing_time = time.time() - start_time
        model.update_metrics(processing_time, response.success)
        
        # Record usage statistics
        if user:
            OllamaModelUsage.record_usage(
                model=model,
                user=user,
                tokens_used=response.tokens_used,
                processing_time=processing_time,
                success=response.success
            )
        
        return response
    
    def create_processing_job(self, 
                             model: OllamaModel,
                             task_type: str,
                             prompt: str,
                             user,
                             name: str = None,
                             priority: str = 'normal',
                             input_data: Dict = None,
                             system_prompt: str = None) -> OllamaProcessingJob:
        """Create a new processing job"""
        
        job_id = f"ollama_{int(time.time())}_{user.id}"
        
        job = OllamaProcessingJob.objects.create(
            job_id=job_id,
            name=name or f"{task_type.title()} Job",
            model=model,
            task_type=task_type,
            priority=priority,
            prompt=prompt,
            system_prompt=system_prompt or "",
            input_data=input_data or {},
            created_by=user
        )
        
        return job
    
    def process_job(self, job: OllamaProcessingJob) -> OllamaResponse:
        """Process a job"""
        job.start_processing()
        
        try:
            response = self.client.generate(
                job.model.effective_model_name,
                job.prompt,
                system_prompt=job.system_prompt if job.system_prompt else None,
                temperature=job.model.temperature,
                max_tokens=job.model.max_tokens,
                top_p=job.model.top_p,
                top_k=job.model.top_k
            )
            
            if response.success:
                job.complete_processing(
                    output_data={
                        'content': response.content,
                        'metadata': response.metadata or {}
                    },
                    tokens_used=response.tokens_used
                )
            else:
                job.fail_processing(response.error or "Unknown error")
            
            # Update model metrics
            job.model.update_metrics(response.processing_time, response.success)
            
            # Record usage
            OllamaModelUsage.record_usage(
                model=job.model,
                user=job.created_by,
                tokens_used=response.tokens_used,
                processing_time=response.processing_time,
                success=response.success
            )
            
            return response
            
        except Exception as e:
            job.fail_processing(str(e))
            logger.error(f"Job processing failed: {e}")
            return OllamaResponse(
                success=False,
                content="",
                model=job.model.effective_model_name,
                error=str(e)
            )
    
    def close(self):
        """Close manager and cleanup resources"""
        self.client.close()


# Global instance
_model_manager = None

def get_model_manager() -> OllamaModelManager:
    """Get global model manager instance"""
    global _model_manager
    if _model_manager is None:
        _model_manager = OllamaModelManager()
    return _model_manager