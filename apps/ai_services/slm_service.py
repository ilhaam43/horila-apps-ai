import logging
import time
from typing import Dict, Any, List, Optional
from transformers import (
    AutoTokenizer, AutoModelForCausalLM, AutoModelForSequenceClassification,
    pipeline, GPT2LMHeadModel, GPT2Tokenizer, T5ForConditionalGeneration, T5Tokenizer
)
import torch
from django.conf import settings
from django.core.cache import cache
import os

logger = logging.getLogger(__name__)

class SLMService:
    """
    Small Language Model Service - Alternatif ringan untuk Ollama
    Menggunakan HuggingFace Transformers dengan model-model kecil yang efisien
    """
    
    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.models = {}
        self.tokenizers = {}
        self.pipelines = {}
        
        # Configuration
        self.config = {
            'max_length': getattr(settings, 'SLM_MAX_LENGTH', 512),
            'temperature': getattr(settings, 'SLM_TEMPERATURE', 0.7),
            'top_p': getattr(settings, 'SLM_TOP_P', 0.9),
            'top_k': getattr(settings, 'SLM_TOP_K', 50),
            'do_sample': True,
            'pad_token_id': None,  # Will be set per model
            'cache_timeout': 3600  # 1 hour
        }
        
        # Available small models
        self.available_models = {
            'text_generation': {
                'gpt2-small': 'gpt2',  # 124M parameters
                'distilgpt2': 'distilgpt2',  # 82M parameters
                'gpt2-indonesian': 'cahya/gpt2-small-indonesian-522M',  # Indonesian GPT2
                't5-small': 't5-small',  # 60M parameters
                'flan-t5-small': 'google/flan-t5-small'  # 80M parameters
            },
            'question_answering': {
                'distilbert-qa': 'distilbert-base-cased-distilled-squad',
                'bert-small-qa': 'deepset/bert-small-cased-squad2',
                'indonesian-qa': 'indobenchmark/indobert-base-p1'
            },
            'summarization': {
                't5-small': 't5-small',
                'flan-t5-small': 'google/flan-t5-small',
                'indonesian-t5': 'Wikidepia/IndoT5-base'
            },
            'classification': {
                'distilbert': 'distilbert-base-uncased',
                'indonesian-bert': 'indobenchmark/indobert-base-p1'
            }
        }
        
        # Initialize default models
        self._initialize_default_models()
    
    def _initialize_default_models(self):
        """Initialize default small models for common tasks"""
        try:
            # Initialize text generation model (GPT2 small)
            self._load_model('gpt2', 'text_generation')
            
            # Initialize Indonesian text generation if available
            try:
                self._load_model('gpt2-indonesian', 'text_generation')
            except Exception as e:
                logger.warning(f"Indonesian GPT2 not available: {e}")
            
            # Initialize T5 for summarization and QA
            self._load_model('t5-small', 'summarization')
            
            logger.info("Default SLM models initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize default models: {e}")
    
    def _load_model(self, model_key: str, task_type: str):
        """Load a specific model and tokenizer"""
        try:
            model_name = None
            
            # Find model name from available models
            for task, models in self.available_models.items():
                if model_key in models:
                    model_name = models[model_key]
                    break
            
            if not model_name:
                # If not found in available_models, use model_key as model_name directly
                model_name = model_key
            
            cache_key = f"slm_model_{model_key}"
            
            # Check if already loaded
            if model_key in self.models and model_key in self.tokenizers:
                logger.info(f"Model {model_key} already loaded")
                return
            
            logger.info(f"Loading model {model_name} for task {task_type}...")
            
            # Load tokenizer
            if 't5' in model_name.lower():
                tokenizer = T5Tokenizer.from_pretrained(model_name)
                model = T5ForConditionalGeneration.from_pretrained(model_name)
            elif 'gpt2' in model_name.lower():
                tokenizer = GPT2Tokenizer.from_pretrained(model_name)
                model = GPT2LMHeadModel.from_pretrained(model_name)
                # Set pad token for GPT2
                if tokenizer.pad_token is None:
                    tokenizer.pad_token = tokenizer.eos_token
            else:
                # Use Auto classes for other models
                tokenizer = AutoTokenizer.from_pretrained(model_name)
                if task_type == 'text_generation':
                    model = AutoModelForCausalLM.from_pretrained(model_name)
                else:
                    model = AutoModelForSequenceClassification.from_pretrained(model_name)
            
            # Move model to device
            model = model.to(self.device)
            model.eval()  # Set to evaluation mode
            
            # Store model and tokenizer
            self.models[model_key] = model
            self.tokenizers[model_key] = tokenizer
            
            logger.info(f"Successfully loaded model {model_name} as {model_key}")
            
        except Exception as e:
            logger.error(f"Failed to load model {model_key}: {e}")
            raise
            cached_model = cache.get(cache_key)
            
            if cached_model:
                self.models[model_key] = cached_model['model']
                self.tokenizers[model_key] = cached_model['tokenizer']
                logger.info(f"Loaded {model_key} from cache")
                return
            
        except Exception as e:
            logger.error(f"Failed to load model {model_key}: {e}")
            raise
    
    def generate_text(self, prompt: str, model_key: str = 'gpt2', max_length: int = None) -> Dict[str, Any]:
        """Generate text using small language model"""
        try:
            start_time = time.time()
            
            # Use default model if not specified
            if model_key not in self.models:
                if model_key == 'gpt2-indonesian' and 'gpt2-indonesian' not in self.models:
                    model_key = 'gpt2'  # Fallback to English GPT2
                else:
                    self._load_model(model_key, 'text_generation')
            
            model = self.models[model_key]
            tokenizer = self.tokenizers[model_key]
            
            # Set max length
            max_length = max_length or self.config['max_length']
            
            # Tokenize input
            inputs = tokenizer.encode(prompt, return_tensors='pt', truncation=True, max_length=max_length//2)
            inputs = inputs.to(self.device)
            
            # Generate
            with torch.no_grad():
                if 't5' in model_key.lower():
                    # T5 requires different generation approach
                    outputs = model.generate(
                        inputs,
                        max_length=max_length,
                        temperature=self.config['temperature'],
                        top_p=self.config['top_p'],
                        do_sample=self.config['do_sample'],
                        pad_token_id=tokenizer.pad_token_id,
                        eos_token_id=tokenizer.eos_token_id
                    )
                else:
                    # GPT2 and similar models
                    outputs = model.generate(
                        inputs,
                        max_length=max_length,
                        temperature=self.config['temperature'],
                        top_p=self.config['top_p'],
                        top_k=self.config['top_k'],
                        do_sample=self.config['do_sample'],
                        pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
                        eos_token_id=tokenizer.eos_token_id
                    )
            
            # Decode output
            generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # Remove input prompt from output for GPT2-style models
            if not 't5' in model_key.lower():
                generated_text = generated_text[len(prompt):].strip()
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'response': generated_text,
                'model_used': model_key,
                'processing_time': processing_time,
                'input_length': len(prompt),
                'output_length': len(generated_text)
            }
            
        except Exception as e:
            logger.error(f"Text generation failed: {e}")
            return {
                'success': False,
                'response': 'Maaf, terjadi kesalahan dalam menghasilkan teks.',
                'error': str(e),
                'model_used': model_key
            }
    
    def answer_question(self, question: str, context: str = None, model_key: str = 't5-small') -> Dict[str, Any]:
        """Answer questions using small models"""
        try:
            start_time = time.time()
            
            # Load QA pipeline if not exists
            pipeline_key = f"qa_{model_key}"
            if pipeline_key not in self.pipelines:
                model_name = self.available_models.get('question_answering', {}).get(model_key)
                if not model_name:
                    model_name = self.available_models.get('text_generation', {}).get(model_key, 't5-small')
                
                self.pipelines[pipeline_key] = pipeline(
                    "question-answering" if context else "text2text-generation",
                    model=model_name,
                    device=0 if self.device.type == 'cuda' else -1
                )
            
            qa_pipeline = self.pipelines[pipeline_key]
            
            if context:
                # Use context-based QA
                result = qa_pipeline(question=question, context=context)
                answer = result['answer']
                confidence = result.get('score', 0.8)
            else:
                # Use generative approach
                if 't5' in model_key:
                    prompt = f"question: {question}"
                else:
                    prompt = f"Q: {question}\nA:"
                
                result = qa_pipeline(prompt, max_length=200, temperature=0.7)
                if isinstance(result, list) and len(result) > 0:
                    answer = result[0].get('generated_text', '').replace(prompt, '').strip()
                else:
                    answer = str(result).strip()
                confidence = 0.7  # Default confidence for generative QA
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'answer': answer,
                'confidence': confidence,
                'model_used': model_key,
                'processing_time': processing_time,
                'has_context': bool(context)
            }
            
        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            return {
                'success': False,
                'answer': 'Maaf, saya tidak dapat menjawab pertanyaan tersebut saat ini.',
                'error': str(e),
                'model_used': model_key
            }
    
    def summarize_text(self, text: str, model_key: str = 't5-small', max_length: int = 150) -> Dict[str, Any]:
        """Summarize text using small models"""
        try:
            start_time = time.time()
            
            # Load summarization pipeline
            pipeline_key = f"summarization_{model_key}"
            if pipeline_key not in self.pipelines:
                model_name = self.available_models.get('summarization', {}).get(model_key, 't5-small')
                self.pipelines[pipeline_key] = pipeline(
                    "summarization",
                    model=model_name,
                    device=0 if self.device.type == 'cuda' else -1
                )
            
            summarizer = self.pipelines[pipeline_key]
            
            # Truncate text if too long
            max_input_length = 1000  # Adjust based on model capacity
            if len(text) > max_input_length:
                text = text[:max_input_length] + "..."
            
            result = summarizer(text, max_length=max_length, min_length=30, do_sample=False)
            summary = result[0]['summary_text'] if isinstance(result, list) else result['summary_text']
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'summary': summary,
                'model_used': model_key,
                'processing_time': processing_time,
                'input_length': len(text),
                'compression_ratio': len(summary) / len(text)
            }
            
        except Exception as e:
            logger.error(f"Text summarization failed: {e}")
            return {
                'success': False,
                'summary': 'Maaf, tidak dapat membuat ringkasan teks.',
                'error': str(e),
                'model_used': model_key
            }
    
    def get_available_models(self) -> Dict[str, List[str]]:
        """Get list of available models by task"""
        return {
            task: list(models.keys()) 
            for task, models in self.available_models.items()
        }
    
    def get_model_info(self, model_key: str) -> Dict[str, Any]:
        """Get information about a specific model"""
        model_info = {
            'model_key': model_key,
            'loaded': model_key in self.models,
            'device': str(self.device),
            'available_tasks': []
        }
        
        # Find which tasks this model supports
        for task, models in self.available_models.items():
            if model_key in models:
                model_info['available_tasks'].append(task)
                model_info['model_name'] = models[model_key]
        
        if model_key in self.models:
            model = self.models[model_key]
            model_info['parameters'] = sum(p.numel() for p in model.parameters())
            model_info['memory_usage'] = sum(p.numel() * p.element_size() for p in model.parameters()) / 1024 / 1024  # MB
        
        return model_info
    
    def clear_cache(self):
        """Clear model cache to free memory"""
        self.models.clear()
        self.tokenizers.clear()
        self.pipelines.clear()
        cache.delete_many([f"slm_model_{key}" for key in self.available_models])
        
        # Clear GPU cache if using CUDA
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        logger.info("SLM cache cleared")


# Global instance
slm_service = SLMService()