import os
import logging
import time
import uuid
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import json
import re

try:
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification,
        AutoModelForTokenClassification, pipeline
    )
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import spacy
    from spacy import displacy
    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False

try:
    import nltk
    from nltk.sentiment import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import PorterStemmer
    HAS_NLTK = True
except ImportError:
    HAS_NLTK = False

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

from .models import (
    NLPModel, TextAnalysisJob, SentimentAnalysisResult,
    NamedEntityResult, TextClassificationResult,
    ModelUsageStatistics, NLPConfiguration
)


logger = logging.getLogger(__name__)


class IndonesianNLPClient:
    """Main client for Indonesian NLP processing"""
    
    def __init__(self):
        self.loaded_models = {}
        self.model_cache = {}
        try:
            self.config = NLPConfiguration.get_active_config()
        except Exception as e:
            logger.warning(f"Could not load NLP configuration: {e}")
            self.config = None
        self._setup_nltk()
    
    def _setup_nltk(self):
        """Setup NLTK resources"""
        if not HAS_NLTK:
            return
        
        try:
            # Download required NLTK data
            nltk_data = [
                'punkt', 'stopwords', 'vader_lexicon',
                'averaged_perceptron_tagger', 'wordnet'
            ]
            
            for data in nltk_data:
                try:
                    nltk.data.find(f'tokenizers/{data}')
                except LookupError:
                    try:
                        nltk.download(data, quiet=True)
                    except Exception as e:
                        logger.warning(f"Failed to download NLTK data {data}: {e}")
        
        except Exception as e:
            logger.error(f"Error setting up NLTK: {e}")
    
    def load_model(self, model_name: str) -> bool:
        """Load a model into memory"""
        try:
            try:
                model_obj = NLPModel.objects.get(name=model_name, is_active=True)
            except Exception as e:
                logger.warning(f"Could not load model {model_name} from database: {e}")
                return False
            
            if model_name in self.loaded_models:
                logger.info(f"Model {model_name} already loaded")
                return True
            
            start_time = time.time()
            
            if model_obj.framework == 'transformers' and HAS_TRANSFORMERS:
                model_data = self._load_transformers_model(model_obj)
            elif model_obj.framework == 'spacy' and HAS_SPACY:
                model_data = self._load_spacy_model(model_obj)
            elif model_obj.framework == 'nltk' and HAS_NLTK:
                model_data = self._load_nltk_model(model_obj)
            else:
                raise ValueError(f"Unsupported framework: {model_obj.framework}")
            
            load_time = time.time() - start_time
            
            self.loaded_models[model_name] = {
                'model': model_data,
                'config': model_obj,
                'loaded_at': timezone.now(),
                'load_time': load_time
            }
            
            # Update model status
            model_obj.is_loaded = True
            model_obj.load_time = load_time
            model_obj.last_used = timezone.now()
            model_obj.save()
            
            logger.info(f"Model {model_name} loaded successfully in {load_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model {model_name}: {e}")
            return False
    
    def _load_transformers_model(self, model_obj: NLPModel) -> Dict:
        """Load Transformers model"""
        tokenizer = AutoTokenizer.from_pretrained(model_obj.model_path)
        
        if model_obj.model_type == 'sentiment':
            model = AutoModelForSequenceClassification.from_pretrained(model_obj.model_path)
            classifier = pipeline(
                "sentiment-analysis",
                model=model,
                tokenizer=tokenizer,
                device=0 if torch.cuda.is_available() else -1
            )
            return {'classifier': classifier, 'tokenizer': tokenizer, 'model': model}
        
        elif model_obj.model_type == 'ner':
            model = AutoModelForTokenClassification.from_pretrained(model_obj.model_path)
            ner = pipeline(
                "ner",
                model=model,
                tokenizer=tokenizer,
                aggregation_strategy="simple",
                device=0 if torch.cuda.is_available() else -1
            )
            return {'ner': ner, 'tokenizer': tokenizer, 'model': model}
        
        elif model_obj.model_type == 'classification':
            model = AutoModelForSequenceClassification.from_pretrained(model_obj.model_path)
            classifier = pipeline(
                "text-classification",
                model=model,
                tokenizer=tokenizer,
                device=0 if torch.cuda.is_available() else -1
            )
            return {'classifier': classifier, 'tokenizer': tokenizer, 'model': model}
        
        else:
            raise ValueError(f"Unsupported model type for transformers: {model_obj.model_type}")
    
    def _load_spacy_model(self, model_obj: NLPModel) -> Dict:
        """Load spaCy model"""
        nlp = spacy.load(model_obj.model_path)
        return {'nlp': nlp}
    
    def _load_nltk_model(self, model_obj: NLPModel) -> Dict:
        """Load NLTK-based model"""
        if model_obj.model_type == 'sentiment':
            analyzer = SentimentIntensityAnalyzer()
            return {'analyzer': analyzer}
        else:
            raise ValueError(f"Unsupported model type for NLTK: {model_obj.model_type}")
    
    def unload_model(self, model_name: str) -> bool:
        """Unload a model from memory"""
        try:
            if model_name in self.loaded_models:
                del self.loaded_models[model_name]
                
                # Update model status
                model_obj = NLPModel.objects.get(name=model_name)
                model_obj.is_loaded = False
                model_obj.save()
                
                logger.info(f"Model {model_name} unloaded")
                return True
            return False
        except Exception as e:
            logger.error(f"Error unloading model {model_name}: {e}")
            return False
    
    def analyze_sentiment(self, text: str, model_name: str = None) -> Dict:
        """Analyze sentiment of Indonesian text"""
        if not model_name:
            model_name = self._get_default_model('sentiment')
        
        if not self._ensure_model_loaded(model_name):
            raise ValueError(f"Failed to load model {model_name}")
        
        model_data = self.loaded_models[model_name]
        model_config = model_data['config']
        
        start_time = time.time()
        
        try:
            if model_config.framework == 'transformers':
                result = self._analyze_sentiment_transformers(text, model_data)
            elif model_config.framework == 'nltk':
                result = self._analyze_sentiment_nltk(text, model_data)
            else:
                raise ValueError(f"Unsupported framework for sentiment analysis: {model_config.framework}")
            
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time
            
            # Update usage statistics
            self._update_usage_stats(model_name, processing_time, True)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_usage_stats(model_name, processing_time, False)
            raise e
    
    def _analyze_sentiment_transformers(self, text: str, model_data: Dict) -> Dict:
        """Analyze sentiment using Transformers model"""
        classifier = model_data['classifier']
        results = classifier(text)
        
        # Convert to standard format
        result = results[0] if isinstance(results, list) else results
        
        sentiment_map = {
            'POSITIVE': 'positive',
            'NEGATIVE': 'negative',
            'NEUTRAL': 'neutral',
            'LABEL_0': 'negative',
            'LABEL_1': 'positive',
            'LABEL_2': 'neutral'
        }
        
        sentiment = sentiment_map.get(result['label'], result['label'].lower())
        confidence = result['score']
        
        return {
            'sentiment': sentiment,
            'confidence': confidence,
            'scores': {
                'positive': confidence if sentiment == 'positive' else 1 - confidence,
                'negative': confidence if sentiment == 'negative' else 1 - confidence,
                'neutral': confidence if sentiment == 'neutral' else 1 - confidence
            },
            'raw_result': result
        }
    
    def _analyze_sentiment_nltk(self, text: str, model_data: Dict) -> Dict:
        """Analyze sentiment using NLTK"""
        analyzer = model_data['analyzer']
        scores = analyzer.polarity_scores(text)
        
        # Determine overall sentiment
        if scores['compound'] >= 0.05:
            sentiment = 'positive'
        elif scores['compound'] <= -0.05:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'
        
        return {
            'sentiment': sentiment,
            'confidence': abs(scores['compound']),
            'scores': {
                'positive': scores['pos'],
                'negative': scores['neg'],
                'neutral': scores['neu']
            },
            'compound': scores['compound'],
            'raw_result': scores
        }
    
    def extract_entities(self, text: str, model_name: str = None) -> List[Dict]:
        """Extract named entities from Indonesian text"""
        if not model_name:
            model_name = self._get_default_model('ner')
        
        if not self._ensure_model_loaded(model_name):
            raise ValueError(f"Failed to load model {model_name}")
        
        model_data = self.loaded_models[model_name]
        model_config = model_data['config']
        
        start_time = time.time()
        
        try:
            if model_config.framework == 'transformers':
                entities = self._extract_entities_transformers(text, model_data)
            elif model_config.framework == 'spacy':
                entities = self._extract_entities_spacy(text, model_data)
            else:
                raise ValueError(f"Unsupported framework for NER: {model_config.framework}")
            
            processing_time = time.time() - start_time
            
            # Update usage statistics
            self._update_usage_stats(model_name, processing_time, True)
            
            return entities
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_usage_stats(model_name, processing_time, False)
            raise e
    
    def _extract_entities_transformers(self, text: str, model_data: Dict) -> List[Dict]:
        """Extract entities using Transformers NER model"""
        ner = model_data['ner']
        results = ner(text)
        
        entities = []
        for entity in results:
            entities.append({
                'text': entity['word'],
                'label': entity['entity_group'],
                'confidence': entity['score'],
                'start': entity['start'],
                'end': entity['end']
            })
        
        return entities
    
    def _extract_entities_spacy(self, text: str, model_data: Dict) -> List[Dict]:
        """Extract entities using spaCy model"""
        nlp = model_data['nlp']
        doc = nlp(text)
        
        entities = []
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_,
                'confidence': 1.0,  # spaCy doesn't provide confidence scores by default
                'start': ent.start_char,
                'end': ent.end_char
            })
        
        return entities
    
    def classify_text(self, text: str, model_name: str = None) -> Dict:
        """Classify Indonesian text"""
        if not model_name:
            model_name = self._get_default_model('classification')
        
        if not self._ensure_model_loaded(model_name):
            raise ValueError(f"Failed to load model {model_name}")
        
        model_data = self.loaded_models[model_name]
        model_config = model_data['config']
        
        start_time = time.time()
        
        try:
            if model_config.framework == 'transformers':
                result = self._classify_text_transformers(text, model_data)
            else:
                raise ValueError(f"Unsupported framework for classification: {model_config.framework}")
            
            processing_time = time.time() - start_time
            result['processing_time'] = processing_time
            
            # Update usage statistics
            self._update_usage_stats(model_name, processing_time, True)
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self._update_usage_stats(model_name, processing_time, False)
            raise e
    
    def _classify_text_transformers(self, text: str, model_data: Dict) -> Dict:
        """Classify text using Transformers model"""
        classifier = model_data['classifier']
        results = classifier(text)
        
        result = results[0] if isinstance(results, list) else results
        
        return {
            'predicted_class': result['label'],
            'confidence': result['score'],
            'raw_result': result
        }
    
    def preprocess_text(self, text: str, config: Dict = None) -> str:
        """Preprocess Indonesian text"""
        if not config:
            config = {
                'lowercase': False,
                'remove_punctuation': False,
                'remove_numbers': False,
                'remove_stopwords': False,
                'normalize_whitespace': True
            }
        
        processed_text = text
        
        # Normalize whitespace
        if config.get('normalize_whitespace', True):
            processed_text = re.sub(r'\s+', ' ', processed_text.strip())
        
        # Convert to lowercase
        if config.get('lowercase', True):
            processed_text = processed_text.lower()
        
        # Remove punctuation
        if config.get('remove_punctuation', True):
            processed_text = re.sub(r'[^\w\s]', '', processed_text)
        
        # Remove numbers
        if config.get('remove_numbers', False):
            processed_text = re.sub(r'\d+', '', processed_text)
        
        # Remove Indonesian stopwords
        if config.get('remove_stopwords', True) and HAS_NLTK:
            try:
                # Indonesian stopwords (basic list)
                indonesian_stopwords = {
                    'yang', 'dan', 'di', 'ke', 'dari', 'dalam', 'untuk', 'pada', 'dengan', 'adalah',
                    'ini', 'itu', 'atau', 'juga', 'akan', 'telah', 'sudah', 'dapat', 'bisa', 'ada',
                    'tidak', 'belum', 'masih', 'hanya', 'saja', 'lebih', 'sangat', 'paling', 'sekali',
                    'kami', 'kita', 'mereka', 'dia', 'ia', 'anda', 'saya', 'kamu', 'nya', 'mu', 'ku'
                }
                
                words = processed_text.split()
                words = [word for word in words if word not in indonesian_stopwords]
                processed_text = ' '.join(words)
            except Exception as e:
                logger.warning(f"Error removing stopwords: {e}")
        
        return processed_text
    
    def _ensure_model_loaded(self, model_name: str) -> bool:
        """Ensure model is loaded, load if necessary"""
        if model_name not in self.loaded_models:
            return self.load_model(model_name)
        return True
    
    def _get_default_model(self, model_type: str) -> str:
        """Get default model for a given type"""
        try:
            model = NLPModel.objects.filter(
                model_type=model_type,
                is_active=True
            ).first()
            
            if model:
                return model.name
            else:
                raise ValueError(f"No active model found for type: {model_type}")
        except Exception as e:
            logger.error(f"Error getting default model for {model_type}: {e}")
            raise e
    
    def _update_usage_stats(self, model_name: str, processing_time: float, success: bool):
        """Update model usage statistics"""
        try:
            model = NLPModel.objects.get(name=model_name)
            now = timezone.now()
            
            stats, created = ModelUsageStatistics.objects.get_or_create(
                model=model,
                date=now.date(),
                hour=now.hour,
                defaults={
                    'total_requests': 0,
                    'successful_requests': 0,
                    'failed_requests': 0,
                    'avg_processing_time': 0.0
                }
            )
            
            stats.total_requests += 1
            if success:
                stats.successful_requests += 1
            else:
                stats.failed_requests += 1
            
            # Update average processing time
            if stats.successful_requests > 0:
                total_time = stats.avg_processing_time * (stats.successful_requests - 1) + processing_time
                stats.avg_processing_time = total_time / stats.successful_requests
            
            # Update min/max processing times
            if stats.min_processing_time is None or processing_time < stats.min_processing_time:
                stats.min_processing_time = processing_time
            if stats.max_processing_time is None or processing_time > stats.max_processing_time:
                stats.max_processing_time = processing_time
            
            stats.save()
            
        except Exception as e:
            logger.error(f"Error updating usage stats: {e}")
    
    def get_model_info(self, model_name: str = None) -> Dict:
        """Get information about loaded models"""
        if model_name:
            if model_name in self.loaded_models:
                model_data = self.loaded_models[model_name]
                return {
                    'name': model_name,
                    'loaded': True,
                    'loaded_at': model_data['loaded_at'],
                    'load_time': model_data['load_time'],
                    'config': model_data['config']
                }
            else:
                return {'name': model_name, 'loaded': False}
        else:
            return {
                'loaded_models': list(self.loaded_models.keys()),
                'total_loaded': len(self.loaded_models)
            }
    
    def get_available_frameworks(self) -> List[str]:
        """Get list of available NLP frameworks"""
        frameworks = []
        if HAS_TRANSFORMERS:
            frameworks.append('transformers')
        if HAS_SPACY:
            frameworks.append('spacy')
        if HAS_NLTK:
            frameworks.append('nltk')
        return frameworks
    
    def cleanup_models(self):
        """Cleanup unused models based on configuration"""
        if not self.config:
            return
        
        try:
            timeout = self.config.model_unload_timeout
            cutoff_time = timezone.now() - timedelta(seconds=timeout)
            
            models_to_unload = []
            for model_name, model_data in self.loaded_models.items():
                if model_data['loaded_at'] < cutoff_time:
                    models_to_unload.append(model_name)
            
            for model_name in models_to_unload:
                self.unload_model(model_name)
                logger.info(f"Unloaded unused model: {model_name}")
                
        except Exception as e:
            logger.error(f"Error during model cleanup: {e}")


class JobManager:
    """Manager for text analysis jobs"""
    
    def __init__(self, nlp_client: IndonesianNLPClient):
        self.nlp_client = nlp_client
    
    def create_job(self, input_text: str, model_name: str, job_type: str, 
                   parameters: Dict = None, user=None) -> TextAnalysisJob:
        """Create a new analysis job"""
        try:
            model = NLPModel.objects.get(name=model_name, is_active=True)
            
            job = TextAnalysisJob.objects.create(
                job_id=str(uuid.uuid4()),
                input_text=input_text,
                model=model,
                parameters=parameters or {},
                created_by=user,
                status='pending'
            )
            
            logger.info(f"Created job {job.job_id} for model {model_name}")
            return job
            
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise e
    
    def process_job(self, job_id: str) -> bool:
        """Process a text analysis job"""
        try:
            job = TextAnalysisJob.objects.get(job_id=job_id)
            
            if job.status != 'pending':
                logger.warning(f"Job {job_id} is not in pending status")
                return False
            
            # Update job status
            job.status = 'processing'
            job.started_at = timezone.now()
            job.save()
            
            start_time = time.time()
            
            try:
                # Process based on model type
                if job.model.model_type == 'sentiment':
                    result = self.nlp_client.analyze_sentiment(
                        job.input_text, job.model.name
                    )
                    self._save_sentiment_result(job, result)
                
                elif job.model.model_type == 'ner':
                    entities = self.nlp_client.extract_entities(
                        job.input_text, job.model.name
                    )
                    self._save_ner_results(job, entities)
                
                elif job.model.model_type == 'classification':
                    result = self.nlp_client.classify_text(
                        job.input_text, job.model.name
                    )
                    self._save_classification_result(job, result)
                
                else:
                    raise ValueError(f"Unsupported model type: {job.model.model_type}")
                
                # Update job completion
                processing_time = time.time() - start_time
                job.status = 'completed'
                job.completed_at = timezone.now()
                job.processing_time = processing_time
                job.progress = 100
                job.save()
                
                logger.info(f"Job {job_id} completed successfully")
                return True
                
            except Exception as e:
                # Handle job failure
                job.status = 'failed'
                job.error_message = str(e)
                job.completed_at = timezone.now()
                job.retry_count += 1
                job.save()
                
                logger.error(f"Job {job_id} failed: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")
            return False
    
    def _save_sentiment_result(self, job: TextAnalysisJob, result: Dict):
        """Save sentiment analysis result"""
        SentimentAnalysisResult.objects.create(
            job=job,
            sentiment=result['sentiment'],
            confidence=result['confidence'],
            positive_score=result['scores']['positive'],
            negative_score=result['scores']['negative'],
            neutral_score=result['scores']['neutral']
        )
        
        job.result = result
        job.confidence_score = result['confidence']
        job.save()
    
    def _save_ner_results(self, job: TextAnalysisJob, entities: List[Dict]):
        """Save NER results"""
        for entity in entities:
            NamedEntityResult.objects.create(
                job=job,
                text=entity['text'],
                label=entity['label'],
                start_pos=entity['start'],
                end_pos=entity['end'],
                confidence=entity['confidence']
            )
        
        job.result = {'entities': entities, 'entity_count': len(entities)}
        job.confidence_score = sum(e['confidence'] for e in entities) / len(entities) if entities else 0
        job.save()
    
    def _save_classification_result(self, job: TextAnalysisJob, result: Dict):
        """Save classification result"""
        TextClassificationResult.objects.create(
            job=job,
            predicted_class=result['predicted_class'],
            confidence=result['confidence']
        )
        
        job.result = result
        job.confidence_score = result['confidence']
        job.save()
    
    def get_job_status(self, job_id: str) -> Dict:
        """Get job status and results"""
        try:
            job = TextAnalysisJob.objects.get(job_id=job_id)
            
            status_info = {
                'job_id': job.job_id,
                'status': job.status,
                'progress': job.progress,
                'created_at': job.created_at,
                'started_at': job.started_at,
                'completed_at': job.completed_at,
                'processing_time': job.processing_time,
                'error_message': job.error_message
            }
            
            if job.status == 'completed' and job.result:
                status_info['result'] = job.result
                status_info['confidence_score'] = job.confidence_score
            
            return status_info
            
        except TextAnalysisJob.DoesNotExist:
            return {'error': f'Job {job_id} not found'}
        except Exception as e:
            return {'error': str(e)}