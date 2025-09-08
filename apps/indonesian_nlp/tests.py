import json
import time
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.urls import reverse
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from celery import current_app
from celery.result import AsyncResult

from .models import (
    NLPConfiguration, NLPModel, TextAnalysisJob,
    SentimentAnalysisResult, NamedEntityResult, TextClassificationResult,
    ModelUsageStatistics
)
from .client import IndonesianNLPClient
from .utils import (
    IndonesianTextProcessor, ModelPerformanceTracker,
    TextAnalysisValidator, CacheManager, BatchProcessor,
    get_text_language, calculate_text_similarity, extract_text_features
)
from .tasks import (
    process_text_analysis_job, load_nlp_model, unload_nlp_model,
    test_nlp_model, batch_process_texts
)
from .serializers import (
    NLPModelSerializer, TextAnalysisJobSerializer,
    QuickAnalysisSerializer, BatchAnalysisSerializer
)


class NLPConfigurationTestCase(TestCase):
    """Test NLP Configuration model"""
    
    def setUp(self):
        self.config = NLPConfiguration.objects.create(
            name="Test Configuration",
            is_active=True,
            max_concurrent_jobs=5,
            job_timeout=300,
            max_text_length=10000,
            enable_detailed_logging=True
        )
    
    def test_configuration_creation(self):
        """Test configuration creation"""
        self.assertEqual(self.config.name, "Test Configuration")
        self.assertTrue(self.config.is_active)
        self.assertEqual(self.config.max_concurrent_jobs, 5)
    
    def test_get_active_config(self):
        """Test getting active configuration"""
        active_config = NLPConfiguration.get_active_config()
        self.assertEqual(active_config, self.config)
    
    def test_configuration_validation(self):
        """Test configuration validation"""
        from django.core.exceptions import ValidationError
        # Test invalid max_concurrent_jobs
        config = NLPConfiguration(
            name="Invalid Config",
            max_concurrent_jobs=0
        )
        with self.assertRaises(ValidationError):
            config.full_clean()


class NLPModelTestCase(TestCase):
    """Test NLP Model"""
    
    def setUp(self):
        self.model = NLPModel.objects.create(
            name="test-sentiment-model",
            model_type="sentiment",
            framework="nltk",
            model_path="vader_lexicon",
            is_active=True,
            description="Test sentiment analysis model"
        )
    
    def test_model_creation(self):
        """Test model creation"""
        self.assertEqual(self.model.name, "test-sentiment-model")
        self.assertEqual(self.model.model_type, "sentiment")
        self.assertEqual(self.model.framework, "nltk")
        self.assertTrue(self.model.is_active)
        self.assertFalse(self.model.is_loaded)
    
    def test_model_str_representation(self):
        """Test model string representation"""
        expected = "test-sentiment-model (sentiment)"
        self.assertEqual(str(self.model), expected)
    
    def test_model_update_last_used(self):
        """Test updating last used timestamp"""
        # Set initial last_used time
        initial_time = timezone.now()
        self.model.last_used = initial_time
        self.model.save()
        
        time.sleep(0.1)
        # Update last_used by setting is_loaded to True (triggers save logic)
        self.model.is_loaded = True
        self.model.save()
        self.assertGreater(self.model.last_used, initial_time)


class TextAnalysisJobTestCase(TestCase):
    """Test Text Analysis Job"""
    
    def setUp(self):
        self.model = NLPModel.objects.create(
            name="test-model",
            model_type="sentiment",
            framework="nltk",
            model_path="vader_lexicon",
            is_active=True
        )
        
        self.job = TextAnalysisJob.objects.create(
            model=self.model,
            input_text="Saya sangat senang dengan layanan ini.",
            analysis_type="sentiment",
            priority="medium"
        )
    
    def test_job_creation(self):
        """Test job creation"""
        self.assertEqual(self.job.model, self.model)
        self.assertEqual(self.job.status, "pending")
        self.assertEqual(self.job.priority, "medium")
        self.assertIsNotNone(self.job.job_id)
    
    def test_job_str_representation(self):
        """Test job string representation"""
        expected = f"Job {self.job.job_id} - sentiment (pending)"
        self.assertEqual(str(self.job), expected)
    
    def test_job_duration_calculation(self):
        """Test job duration calculation"""
        self.job.started_at = timezone.now()
        self.job.completed_at = self.job.started_at + timezone.timedelta(seconds=5)
        duration = self.job.duration
        self.assertEqual(duration, 5.0)


class IndonesianTextProcessorTestCase(TestCase):
    """Test Indonesian Text Processor"""
    
    def setUp(self):
        self.processor = IndonesianTextProcessor()
    
    def test_clean_text(self):
        """Test text cleaning"""
        dirty_text = "  Halo   dunia!  \n\n  "
        cleaned = self.processor.clean_text(dirty_text)
        self.assertEqual(cleaned, "Halo dunia!")
    
    def test_normalize_slang(self):
        """Test slang normalization"""
        slang_text = "gw udah ga bisa dateng"
        normalized = self.processor.normalize_slang(slang_text)
        self.assertEqual(normalized, "saya sudah tidak bisa dateng")
    
    def test_tokenize_words(self):
        """Test word tokenization"""
        text = "Saya suka makan nasi."
        words = self.processor.tokenize_words(text)
        expected = ["saya", "suka", "makan", "nasi"]
        self.assertEqual(words, expected)
    
    def test_tokenize_sentences(self):
        """Test sentence tokenization"""
        text = "Halo! Apa kabar? Saya baik-baik saja."
        sentences = self.processor.tokenize_sentences(text)
        expected = ["Halo", "Apa kabar", "Saya baik-baik saja"]
        self.assertEqual(sentences, expected)
    
    def test_extract_keywords(self):
        """Test keyword extraction"""
        text = "Saya sangat suka makan nasi goreng. Nasi goreng adalah makanan favorit saya."
        keywords = self.processor.extract_keywords(text, top_k=3)
        self.assertIsInstance(keywords, list)
        self.assertGreater(len(keywords), 0)
        # Check that 'nasi' and 'goreng' are in top keywords
        keyword_words = [kw[0] for kw in keywords]
        self.assertIn('nasi', keyword_words)
    
    def test_calculate_readability(self):
        """Test readability calculation"""
        text = "Ini adalah teks sederhana. Mudah dibaca."
        readability = self.processor.calculate_readability(text)
        
        self.assertIn('score', readability)
        self.assertIn('level', readability)
        self.assertIn('num_sentences', readability)
        self.assertIn('num_words', readability)
        self.assertGreater(readability['score'], 0)


class TextAnalysisValidatorTestCase(TestCase):
    """Test Text Analysis Validator"""
    
    def test_validate_text_input_valid(self):
        """Test valid text input"""
        text = "Ini adalah teks yang valid."
        validated = TextAnalysisValidator.validate_text_input(text)
        self.assertEqual(validated, text)
    
    def test_validate_text_input_empty(self):
        """Test empty text input"""
        with self.assertRaises(Exception):
            TextAnalysisValidator.validate_text_input("")
    
    def test_validate_text_input_too_long(self):
        """Test text input too long"""
        long_text = "a" * 10001
        with self.assertRaises(Exception):
            TextAnalysisValidator.validate_text_input(long_text)
    
    def test_validate_model_parameters(self):
        """Test model parameters validation"""
        params = {
            'confidence_threshold': 0.8,
            'max_length': 512,
            'return_emotions': True
        }
        validated = TextAnalysisValidator.validate_model_parameters(params, 'sentiment')
        
        self.assertEqual(validated['confidence_threshold'], 0.8)
        self.assertEqual(validated['max_length'], 512)
        self.assertTrue(validated['return_emotions'])
    
    def test_validate_analysis_result_sentiment(self):
        """Test sentiment analysis result validation"""
        result = {
            'sentiment': 'positive',
            'confidence': 0.85,
            'positive_score': 0.85,
            'negative_score': 0.15
        }
        is_valid = TextAnalysisValidator.validate_analysis_result(result, 'sentiment')
        self.assertTrue(is_valid)
    
    def test_validate_analysis_result_ner(self):
        """Test NER result validation"""
        result = {
            'entities': [
                {
                    'text': 'Jakarta',
                    'label': 'LOCATION',
                    'start': 0,
                    'end': 7,
                    'confidence': 0.9
                }
            ]
        }
        is_valid = TextAnalysisValidator.validate_analysis_result(result, 'ner')
        self.assertTrue(is_valid)


class CacheManagerTestCase(TestCase):
    """Test Cache Manager"""
    
    def setUp(self):
        self.cache_manager = CacheManager()
        cache.clear()  # Clear cache before each test
    
    def test_generate_cache_key(self):
        """Test cache key generation"""
        text = "Test text"
        model_name = "test-model"
        parameters = {'confidence_threshold': 0.8}
        
        key = self.cache_manager.generate_cache_key(text, model_name, parameters)
        self.assertIsInstance(key, str)
        self.assertTrue(key.startswith('nlp_analysis:'))
    
    def test_cache_and_retrieve_result(self):
        """Test caching and retrieving results"""
        text = "Test text"
        model_name = "test-model"
        result = {'sentiment': 'positive', 'confidence': 0.8}
        
        # Cache result
        self.cache_manager.cache_result(text, model_name, result)
        
        # Retrieve result
        cached_result = self.cache_manager.get_cached_result(text, model_name)
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result['result'], result)
    
    def test_cache_miss(self):
        """Test cache miss"""
        result = self.cache_manager.get_cached_result("nonexistent", "model")
        self.assertIsNone(result)


class BatchProcessorTestCase(TestCase):
    """Test Batch Processor"""
    
    def setUp(self):
        self.batch_processor = BatchProcessor(batch_size=3)
    
    def test_create_batches(self):
        """Test batch creation"""
        texts = ["text1", "text2", "text3", "text4", "text5"]
        batches = self.batch_processor.create_batches(texts)
        
        self.assertEqual(len(batches), 2)
        self.assertEqual(len(batches[0]), 3)
        self.assertEqual(len(batches[1]), 2)
    
    def test_estimate_processing_time(self):
        """Test processing time estimation"""
        estimated_time = self.batch_processor.estimate_processing_time(10, 0.5)
        self.assertGreater(estimated_time, 0)
    
    def test_validate_batch_request(self):
        """Test batch request validation"""
        valid_texts = ["text1", "text2", "text3"]
        # Should not raise exception
        self.batch_processor.validate_batch_request(valid_texts)
        
        # Test empty list
        with self.assertRaises(Exception):
            self.batch_processor.validate_batch_request([])


class UtilityFunctionsTestCase(TestCase):
    """Test utility functions"""
    
    def test_get_text_language(self):
        """Test language detection"""
        indonesian_text = "Saya suka makan nasi dan minum air."
        english_text = "I like to eat rice and drink water."
        
        self.assertEqual(get_text_language(indonesian_text), 'indonesian')
        self.assertEqual(get_text_language(english_text), 'other')
    
    def test_calculate_text_similarity(self):
        """Test text similarity calculation"""
        text1 = "Saya suka makan nasi"
        text2 = "Saya suka minum air"
        text3 = "Dia tidak suka olahraga"
        
        similarity_12 = calculate_text_similarity(text1, text2)
        similarity_13 = calculate_text_similarity(text1, text3)
        
        self.assertGreater(similarity_12, similarity_13)
        self.assertGreaterEqual(similarity_12, 0)
        self.assertLessEqual(similarity_12, 1)
    
    def test_extract_text_features(self):
        """Test text feature extraction"""
        text = "Saya sangat senang dengan layanan ini! Terima kasih."
        features = extract_text_features(text)
        
        required_features = [
            'char_count', 'word_count', 'sentence_count',
            'avg_word_length', 'readability_score', 'language'
        ]
        
        for feature in required_features:
            self.assertIn(feature, features)
        
        self.assertGreater(features['char_count'], 0)
        self.assertGreater(features['word_count'], 0)
        self.assertEqual(features['language'], 'indonesian')


class IndonesianNLPClientTestCase(TestCase):
    """Test Indonesian NLP Client"""
    
    def setUp(self):
        self.client = IndonesianNLPClient()
        self.model = NLPModel.objects.create(
            name="test-model",
            model_type="sentiment",
            framework="transformers",
            model_path="/path/to/model",
            is_active=True
        )
    
    @patch('indonesian_nlp.client.HAS_TRANSFORMERS', True)
    @patch('indonesian_nlp.client.torch.cuda.is_available', return_value=False)
    @patch('indonesian_nlp.client.IndonesianNLPClient._load_transformers_model')
    def test_load_model_transformers(self, mock_load_transformers, mock_cuda):
        """Test loading Transformers model"""
        mock_load_transformers.return_value = {
            'classifier': MagicMock(),
            'tokenizer': MagicMock(),
            'model': MagicMock()
        }
        
        result = self.client.load_model("test-model")
        
        self.assertTrue(result)
        self.assertIn("test-model", self.client.loaded_models)
        mock_load_transformers.assert_called_once()
    
    def test_get_available_frameworks(self):
        """Test getting available frameworks"""
        frameworks = self.client.get_available_frameworks()
        self.assertIsInstance(frameworks, list)
        # At least one framework should be available
        self.assertGreater(len(frameworks), 0)
    
    def test_preprocess_text(self):
        """Test text preprocessing"""
        text = "  Halo dunia!  \n\n  "
        processed = self.client.preprocess_text(text)
        self.assertEqual(processed.strip(), "Halo dunia!")


class APITestCase(APITestCase):
    """Test REST API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.model = NLPModel.objects.create(
            name="test-api-model",
            model_type="sentiment",
            framework="nltk",
            model_path="vader_lexicon",
            is_active=True
        )
    
    def test_model_list_api(self):
        """Test model list API"""
        url = reverse('indonesian_nlp:model-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_model_detail_api(self):
        """Test model detail API"""
        url = reverse('indonesian_nlp:model-detail', kwargs={'pk': self.model.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.model.name)
    
    def test_quick_analysis_api(self):
        """Test quick analysis API"""
        url = reverse('indonesian_nlp:quick-analysis')
        data = {
            'text': 'Saya sangat senang dengan layanan ini.',
            'analysis_type': 'sentiment',
            'model_name': self.model.name
        }
        
        with patch.object(IndonesianNLPClient, 'analyze_sentiment') as mock_analyze:
            mock_analyze.return_value = {
                'sentiment': 'positive',
                'confidence': 0.85
            }
            
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('result', response.data)
    
    def test_batch_analysis_api(self):
        """Test batch analysis API"""
        url = reverse('indonesian_nlp:batch-analysis')
        data = {
            'texts': [
                'Saya senang',
                'Saya sedih',
                'Saya biasa saja'
            ],
            'analysis_type': 'sentiment',
            'model_name': self.model.name
        }
        
        response = self.client.post(url, data, format='json')
        # This might return 202 (accepted) for async processing
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_202_ACCEPTED])
    
    def test_job_list_api(self):
        """Test job list API"""
        # Create a test job
        job = TextAnalysisJob.objects.create(
            model=self.model,
            input_text="Test text",
            analysis_type="sentiment"
        )
        
        url = reverse('indonesian_nlp:job-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
    
    def test_unauthorized_access(self):
        """Test unauthorized access"""
        # Create a new client without authentication
        unauthenticated_client = APIClient()
        
        url = reverse('indonesian_nlp:model-list')
        response = unauthenticated_client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class SerializerTestCase(TestCase):
    """Test serializers"""
    
    def setUp(self):
        self.model = NLPModel.objects.create(
            name="test-serializer-model",
            model_type="sentiment",
            framework="nltk",
            model_path="vader_lexicon",
            is_active=True
        )
    
    def test_nlp_model_serializer(self):
        """Test NLP model serializer"""
        serializer = NLPModelSerializer(self.model)
        data = serializer.data
        
        self.assertEqual(data['name'], self.model.name)
        self.assertEqual(data['model_type'], self.model.model_type)
        self.assertEqual(data['framework'], self.model.framework)
    
    def test_quick_analysis_serializer(self):
        """Test quick analysis serializer"""
        data = {
            'text': 'Saya senang',
            'analysis_type': 'sentiment',
            'model_name': self.model.name
        }
        
        serializer = QuickAnalysisSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_batch_analysis_serializer(self):
        """Test batch analysis serializer"""
        data = {
            'texts': ['Text 1', 'Text 2'],
            'analysis_type': 'sentiment',
            'model_name': self.model.name
        }
        
        serializer = BatchAnalysisSerializer(data=data)
        self.assertTrue(serializer.is_valid())
    
    def test_invalid_serializer_data(self):
        """Test invalid serializer data"""
        data = {
            'text': '',  # Empty text
            'analysis_type': 'invalid_type',
            'model_name': 'nonexistent_model'
        }
        
        serializer = QuickAnalysisSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('text', serializer.errors)


class CeleryTaskTestCase(TransactionTestCase):
    """Test Celery tasks"""
    
    def setUp(self):
        self.model = NLPModel.objects.create(
            name="test-task-model",
            model_type="sentiment",
            framework="nltk",
            model_path="vader_lexicon",
            is_active=True
        )
        
        self.job = TextAnalysisJob.objects.create(
            model=self.model,
            input_text="Saya sangat senang dengan layanan ini.",
            analysis_type="sentiment"
        )
    
    @patch.object(IndonesianNLPClient, 'analyze_sentiment')
    def test_process_text_analysis_job_task(self, mock_analyze):
        """Test text analysis job processing task"""
        mock_analyze.return_value = {
            'sentiment': 'positive',
            'confidence': 0.85,
            'positive_score': 0.85,
            'negative_score': 0.15
        }
        
        result = process_text_analysis_job(self.job.id)
        
        self.assertEqual(result['status'], 'completed')
        self.assertIn('result', result)
        
        # Check job was updated
        self.job.refresh_from_db()
        self.assertEqual(self.job.status, 'completed')
    
    @patch.object(IndonesianNLPClient, 'load_model')
    def test_load_nlp_model_task(self, mock_load):
        """Test model loading task"""
        mock_load.return_value = {
            'status': 'loaded',
            'memory_usage': 512.0
        }
        
        result = load_nlp_model(self.model.name)
        
        self.assertEqual(result['status'], 'loaded')
        self.assertIn('load_time', result)
    
    @patch.object(IndonesianNLPClient, 'unload_model')
    def test_unload_nlp_model_task(self, mock_unload):
        """Test model unloading task"""
        mock_unload.return_value = True
        
        # Set model as loaded first
        self.model.is_loaded = True
        self.model.save()
        
        result = unload_nlp_model(self.model.name)
        
        self.assertEqual(result['status'], 'unloaded')
    
    @patch.object(IndonesianNLPClient, 'analyze_sentiment')
    def test_batch_process_texts_task(self, mock_analyze):
        """Test batch text processing task"""
        mock_analyze.return_value = {
            'sentiment': 'positive',
            'confidence': 0.8
        }
        
        texts = ['Text 1', 'Text 2', 'Text 3']
        result = batch_process_texts(texts, 'sentiment', self.model.name)
        
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['total_texts'], 3)
        self.assertIn('results', result)


class IntegrationTestCase(TransactionTestCase):
    """Integration tests"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.config = NLPConfiguration.objects.create(
            name="Integration Test Config",
            is_active=True,
            max_concurrent_jobs=3,
            enable_caching=True
        )
        
        self.model = NLPModel.objects.create(
            name="integration-test-model",
            model_type="sentiment",
            framework="nltk",
            model_path="vader_lexicon",
            is_active=True
        )
    
    def test_end_to_end_analysis_workflow(self):
        """Test complete analysis workflow"""
        # Create job
        job = TextAnalysisJob.objects.create(
            model=self.model,
            input_text="Saya sangat puas dengan pelayanan yang diberikan.",
            analysis_type="sentiment",
            priority="high"
        )
        
        self.assertEqual(job.status, 'pending')
        
        # Mock the analysis
        with patch.object(IndonesianNLPClient, 'analyze_sentiment') as mock_analyze:
            mock_analyze.return_value = {
                'sentiment': 'positive',
                'confidence': 0.92,
                'positive_score': 0.92,
                'negative_score': 0.08,
                'neutral_score': 0.0
            }
            
            # Process job
            result = process_text_analysis_job(job.id)
            
            self.assertEqual(result['status'], 'completed')
            
            # Check job was updated
            job.refresh_from_db()
            self.assertEqual(job.status, 'completed')
            self.assertIsNotNone(job.result)
            self.assertGreater(job.confidence_score, 0)
            
            # Check detailed result was created
            sentiment_result = SentimentAnalysisResult.objects.filter(job=job).first()
            self.assertIsNotNone(sentiment_result)
            self.assertEqual(sentiment_result.sentiment, 'positive')
    
    def test_model_performance_tracking(self):
        """Test model performance tracking"""
        tracker = ModelPerformanceTracker()
        
        # Record some predictions
        for i in range(5):
            tracker.record_prediction(
                model_name=self.model.name,
                processing_time=0.5 + i * 0.1,
                confidence=0.8 + i * 0.02,
                success=True
            )
        
        # Get stats
        stats = tracker.get_model_stats(self.model.name)
        
        self.assertEqual(stats['total_predictions'], 5)
        self.assertEqual(stats['success_rate'], 1.0)
        self.assertGreater(stats['avg_processing_time'], 0)
        self.assertGreater(stats['avg_confidence'], 0)
    
    def test_caching_functionality(self):
        """Test caching functionality"""
        cache_manager = CacheManager()
        
        text = "Test caching dengan teks ini"
        model_name = self.model.name
        result = {'sentiment': 'neutral', 'confidence': 0.7}
        
        # Cache result
        cache_manager.cache_result(text, model_name, result)
        
        # Retrieve from cache
        cached_result = cache_manager.get_cached_result(text, model_name)
        
        self.assertIsNotNone(cached_result)
        self.assertEqual(cached_result['result'], result)
        self.assertIn('cached_at', cached_result)
    
    def tearDown(self):
        """Clean up after tests"""
        cache.clear()


class PerformanceTestCase(TestCase):
    """Performance tests"""
    
    def test_text_processing_performance(self):
        """Test text processing performance"""
        processor = IndonesianTextProcessor()
        
        # Test with various text sizes
        texts = [
            "Teks pendek.",
            "Teks sedang dengan beberapa kalimat. Ini kalimat kedua.",
            "Teks panjang " * 100 + "dengan banyak pengulangan kata."
        ]
        
        for text in texts:
            start_time = time.time()
            
            # Perform various operations
            cleaned = processor.clean_text(text)
            normalized = processor.normalize_slang(cleaned)
            words = processor.tokenize_words(normalized)
            keywords = processor.extract_keywords(text, top_k=5)
            readability = processor.calculate_readability(text)
            
            processing_time = time.time() - start_time
            
            # Performance assertions
            self.assertLess(processing_time, 1.0)  # Should complete within 1 second
            self.assertIsInstance(cleaned, str)
            self.assertIsInstance(words, list)
            self.assertIsInstance(keywords, list)
            self.assertIsInstance(readability, dict)
    
    def test_batch_processing_performance(self):
        """Test batch processing performance"""
        batch_processor = BatchProcessor(batch_size=10)
        
        # Create test texts
        texts = [f"Teks nomor {i} untuk pengujian batch processing." for i in range(50)]
        
        start_time = time.time()
        batches = batch_processor.create_batches(texts)
        processing_time = time.time() - start_time
        
        self.assertLess(processing_time, 0.1)  # Should be very fast
        self.assertEqual(len(batches), 5)  # 50 texts / 10 batch_size = 5 batches


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            },
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'rest_framework',
                'indonesian_nlp',
            ],
            SECRET_KEY='test-secret-key',
            USE_TZ=True,
        )
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["indonesian_nlp"])