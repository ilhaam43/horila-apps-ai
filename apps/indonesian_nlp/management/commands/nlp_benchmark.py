import os
import json
import time
import statistics
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from ...models import NLPModel, TextAnalysisJob, NLPConfiguration
from ...client import IndonesianNLPClient
from ...utils import IndonesianTextProcessor, ModelPerformanceTracker


class Command(BaseCommand):
    help = 'Benchmark and test Indonesian NLP module performance'
    
    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='Available actions')
        
        # Performance benchmark
        perf_parser = subparsers.add_parser('performance', help='Run performance benchmark')
        perf_parser.add_argument(
            '--model',
            type=str,
            help='Specific model to benchmark (default: all active models)'
        )
        perf_parser.add_argument(
            '--iterations',
            type=int,
            default=100,
            help='Number of test iterations (default: 100)'
        )
        perf_parser.add_argument(
            '--text-length',
            type=int,
            default=100,
            help='Length of test text in words (default: 100)'
        )
        perf_parser.add_argument(
            '--export',
            type=str,
            help='Export results to JSON file'
        )
        
        # Accuracy test
        accuracy_parser = subparsers.add_parser('accuracy', help='Test model accuracy')
        accuracy_parser.add_argument(
            '--test-data',
            type=str,
            required=True,
            help='Path to test dataset JSON file'
        )
        accuracy_parser.add_argument(
            '--model',
            type=str,
            help='Specific model to test (default: all active models)'
        )
        
        # Load test
        load_parser = subparsers.add_parser('load', help='Run load test')
        load_parser.add_argument(
            '--concurrent',
            type=int,
            default=10,
            help='Number of concurrent requests (default: 10)'
        )
        load_parser.add_argument(
            '--duration',
            type=int,
            default=60,
            help='Test duration in seconds (default: 60)'
        )
        load_parser.add_argument(
            '--ramp-up',
            type=int,
            default=10,
            help='Ramp-up time in seconds (default: 10)'
        )
        
        # Memory test
        memory_parser = subparsers.add_parser('memory', help='Test memory usage')
        memory_parser.add_argument(
            '--model',
            type=str,
            help='Specific model to test (default: all active models)'
        )
        memory_parser.add_argument(
            '--monitor-duration',
            type=int,
            default=300,
            help='Monitoring duration in seconds (default: 300)'
        )
        
        # Stress test
        stress_parser = subparsers.add_parser('stress', help='Run stress test')
        stress_parser.add_argument(
            '--max-concurrent',
            type=int,
            default=50,
            help='Maximum concurrent requests (default: 50)'
        )
        stress_parser.add_argument(
            '--step-size',
            type=int,
            default=5,
            help='Concurrent request step size (default: 5)'
        )
        
        # Text processing test
        text_parser = subparsers.add_parser('text-processing', help='Test text processing')
        text_parser.add_argument(
            '--sample-size',
            type=int,
            default=1000,
            help='Number of text samples to process (default: 1000)'
        )
    
    def handle(self, *args, **options):
        action = options.get('action')
        
        if not action:
            self.print_help('manage.py', 'nlp_benchmark')
            return
        
        try:
            if action == 'performance':
                self._run_performance_benchmark(options)
            elif action == 'accuracy':
                self._run_accuracy_test(options)
            elif action == 'load':
                self._run_load_test(options)
            elif action == 'memory':
                self._run_memory_test(options)
            elif action == 'stress':
                self._run_stress_test(options)
            elif action == 'text-processing':
                self._run_text_processing_test(options)
            else:
                raise CommandError(f"Unknown action: {action}")
                
        except Exception as e:
            raise CommandError(f"Benchmark failed: {str(e)}")
    
    def _run_performance_benchmark(self, options):
        """Run performance benchmark"""
        self.stdout.write(self.style.SUCCESS('Running Performance Benchmark'))
        self.stdout.write('=' * 50)
        
        model_name = options.get('model')
        iterations = options['iterations']
        text_length = options['text_length']
        export_file = options.get('export')
        
        # Get models to test
        if model_name:
            models = NLPModel.objects.filter(name=model_name, is_active=True)
            if not models.exists():
                raise CommandError(f"Model not found: {model_name}")
        else:
            models = NLPModel.objects.filter(is_active=True)
        
        if not models.exists():
            raise CommandError("No active models found")
        
        # Generate test text
        test_texts = self._generate_test_texts(iterations, text_length)
        
        results = {}
        client = IndonesianNLPClient()
        
        for model in models:
            self.stdout.write(f"\nTesting model: {model.name}")
            self.stdout.write('-' * 30)
            
            model_results = {
                'model_name': model.name,
                'model_type': model.model_type,
                'iterations': iterations,
                'text_length': text_length,
                'processing_times': [],
                'success_count': 0,
                'error_count': 0,
                'errors': []
            }
            
            # Load model if not loaded
            if not model.is_loaded:
                self.stdout.write("Loading model...")
                try:
                    client.load_model(model.name)
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Failed to load model: {str(e)}")
                    )
                    continue
            
            # Run benchmark
            for i, text in enumerate(test_texts):
                if (i + 1) % 10 == 0:
                    self.stdout.write(f"Progress: {i + 1}/{iterations}")
                
                start_time = time.time()
                
                try:
                    if model.model_type == 'sentiment':
                        result = client.analyze_sentiment(text, model.name)
                    elif model.model_type == 'ner':
                        result = client.extract_entities(text, model.name)
                    elif model.model_type == 'classification':
                        result = client.classify_text(text, model.name)
                    else:
                        # Generic analysis
                        result = client.analyze_text(text, model.name, 'sentiment')
                    
                    processing_time = time.time() - start_time
                    model_results['processing_times'].append(processing_time)
                    model_results['success_count'] += 1
                    
                except Exception as e:
                    processing_time = time.time() - start_time
                    model_results['processing_times'].append(processing_time)
                    model_results['error_count'] += 1
                    model_results['errors'].append(str(e))
            
            # Calculate statistics
            if model_results['processing_times']:
                times = model_results['processing_times']
                model_results['avg_time'] = statistics.mean(times)
                model_results['median_time'] = statistics.median(times)
                model_results['min_time'] = min(times)
                model_results['max_time'] = max(times)
                model_results['std_dev'] = statistics.stdev(times) if len(times) > 1 else 0
                model_results['throughput'] = iterations / sum(times)
            
            # Display results
            self.stdout.write(f"Success Rate: {model_results['success_count']}/{iterations}")
            self.stdout.write(f"Average Time: {model_results.get('avg_time', 0):.4f}s")
            self.stdout.write(f"Median Time: {model_results.get('median_time', 0):.4f}s")
            self.stdout.write(f"Throughput: {model_results.get('throughput', 0):.2f} req/s")
            
            if model_results['error_count'] > 0:
                self.stdout.write(
                    self.style.WARNING(f"Errors: {model_results['error_count']}")
                )
            
            results[model.name] = model_results
        
        # Export results if requested
        if export_file:
            benchmark_data = {
                'benchmark_type': 'performance',
                'timestamp': timezone.now().isoformat(),
                'parameters': {
                    'iterations': iterations,
                    'text_length': text_length
                },
                'results': results
            }
            
            with open(export_file, 'w') as f:
                json.dump(benchmark_data, f, indent=2, default=str)
            
            self.stdout.write(
                self.style.SUCCESS(f"\nResults exported to {export_file}")
            )
    
    def _run_accuracy_test(self, options):
        """Run accuracy test with labeled data"""
        self.stdout.write(self.style.SUCCESS('Running Accuracy Test'))
        self.stdout.write('=' * 50)
        
        test_data_file = options['test_data']
        model_name = options.get('model')
        
        # Load test data
        if not os.path.exists(test_data_file):
            raise CommandError(f"Test data file not found: {test_data_file}")
        
        with open(test_data_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        if not isinstance(test_data, list):
            raise CommandError("Test data must be a list of test cases")
        
        # Get models to test
        if model_name:
            models = NLPModel.objects.filter(name=model_name, is_active=True)
        else:
            models = NLPModel.objects.filter(is_active=True)
        
        client = IndonesianNLPClient()
        
        for model in models:
            self.stdout.write(f"\nTesting accuracy for: {model.name}")
            self.stdout.write('-' * 30)
            
            correct_predictions = 0
            total_predictions = 0
            
            for test_case in test_data:
                text = test_case.get('text')
                expected = test_case.get('expected')
                
                if not text or expected is None:
                    continue
                
                try:
                    if model.model_type == 'sentiment':
                        result = client.analyze_sentiment(text, model.name)
                        predicted = result.get('label', '').lower()
                        expected_label = expected.lower()
                        
                        if predicted == expected_label:
                            correct_predictions += 1
                    
                    elif model.model_type == 'ner':
                        result = client.extract_entities(text, model.name)
                        predicted_entities = set([
                            entity['text'].lower() 
                            for entity in result.get('entities', [])
                        ])
                        expected_entities = set([
                            entity.lower() for entity in expected
                        ])
                        
                        # Calculate F1 score for entities
                        if predicted_entities == expected_entities:
                            correct_predictions += 1
                    
                    elif model.model_type == 'classification':
                        result = client.classify_text(text, model.name)
                        predicted = result.get('label', '').lower()
                        expected_label = expected.lower()
                        
                        if predicted == expected_label:
                            correct_predictions += 1
                    
                    total_predictions += 1
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"Error processing test case: {str(e)}")
                    )
                    total_predictions += 1
            
            # Calculate accuracy
            if total_predictions > 0:
                accuracy = (correct_predictions / total_predictions) * 100
                self.stdout.write(
                    f"Accuracy: {accuracy:.2f}% ({correct_predictions}/{total_predictions})"
                )
            else:
                self.stdout.write("No valid test cases processed")
    
    def _run_load_test(self, options):
        """Run load test with concurrent requests"""
        self.stdout.write(self.style.SUCCESS('Running Load Test'))
        self.stdout.write('=' * 50)
        
        concurrent = options['concurrent']
        duration = options['duration']
        ramp_up = options['ramp_up']
        
        self.stdout.write(f"Concurrent users: {concurrent}")
        self.stdout.write(f"Test duration: {duration}s")
        self.stdout.write(f"Ramp-up time: {ramp_up}s")
        
        # This would require implementing concurrent request handling
        # For now, we'll simulate with sequential requests
        
        import threading
        import queue
        
        results_queue = queue.Queue()
        test_text = "Ini adalah teks uji untuk load testing sistem NLP bahasa Indonesia."
        
        def worker():
            client = IndonesianNLPClient()
            start_time = time.time()
            requests_made = 0
            errors = 0
            
            while time.time() - start_time < duration:
                try:
                    result = client.analyze_sentiment(test_text)
                    requests_made += 1
                except Exception:
                    errors += 1
                
                time.sleep(0.1)  # Small delay between requests
            
            results_queue.put({
                'requests': requests_made,
                'errors': errors,
                'duration': time.time() - start_time
            })
        
        # Start threads with ramp-up
        threads = []
        for i in range(concurrent):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
            
            if ramp_up > 0:
                time.sleep(ramp_up / concurrent)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        total_requests = 0
        total_errors = 0
        
        while not results_queue.empty():
            result = results_queue.get()
            total_requests += result['requests']
            total_errors += result['errors']
        
        # Display results
        self.stdout.write(f"\nLoad Test Results:")
        self.stdout.write(f"Total Requests: {total_requests}")
        self.stdout.write(f"Total Errors: {total_errors}")
        self.stdout.write(f"Success Rate: {((total_requests - total_errors) / total_requests * 100):.2f}%")
        self.stdout.write(f"Throughput: {total_requests / duration:.2f} req/s")
    
    def _run_memory_test(self, options):
        """Test memory usage during processing"""
        self.stdout.write(self.style.SUCCESS('Running Memory Test'))
        self.stdout.write('=' * 50)
        
        try:
            import psutil
        except ImportError:
            raise CommandError("psutil library required for memory testing")
        
        model_name = options.get('model')
        duration = options['monitor_duration']
        
        # Get models to test
        if model_name:
            models = NLPModel.objects.filter(name=model_name, is_active=True)
        else:
            models = NLPModel.objects.filter(is_active=True)
        
        client = IndonesianNLPClient()
        process = psutil.Process()
        
        for model in models:
            self.stdout.write(f"\nTesting memory usage for: {model.name}")
            self.stdout.write('-' * 30)
            
            # Record initial memory
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            self.stdout.write(f"Initial memory: {initial_memory:.2f} MB")
            
            # Load model
            try:
                client.load_model(model.name)
                loaded_memory = process.memory_info().rss / 1024 / 1024
                self.stdout.write(f"Memory after loading: {loaded_memory:.2f} MB")
                self.stdout.write(f"Model loading overhead: {loaded_memory - initial_memory:.2f} MB")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Failed to load model: {str(e)}")
                )
                continue
            
            # Monitor memory during processing
            memory_samples = []
            start_time = time.time()
            
            while time.time() - start_time < duration:
                try:
                    # Process some text
                    test_text = "Teks uji untuk monitoring penggunaan memori sistem NLP."
                    if model.model_type == 'sentiment':
                        client.analyze_sentiment(test_text, model.name)
                    elif model.model_type == 'ner':
                        client.extract_entities(test_text, model.name)
                    else:
                        client.classify_text(test_text, model.name)
                    
                    # Record memory usage
                    current_memory = process.memory_info().rss / 1024 / 1024
                    memory_samples.append(current_memory)
                    
                except Exception:
                    pass
                
                time.sleep(1)  # Sample every second
            
            # Calculate memory statistics
            if memory_samples:
                avg_memory = statistics.mean(memory_samples)
                max_memory = max(memory_samples)
                min_memory = min(memory_samples)
                
                self.stdout.write(f"Average memory during processing: {avg_memory:.2f} MB")
                self.stdout.write(f"Peak memory usage: {max_memory:.2f} MB")
                self.stdout.write(f"Memory range: {min_memory:.2f} - {max_memory:.2f} MB")
                self.stdout.write(f"Processing overhead: {max_memory - loaded_memory:.2f} MB")
    
    def _run_stress_test(self, options):
        """Run stress test with increasing load"""
        self.stdout.write(self.style.SUCCESS('Running Stress Test'))
        self.stdout.write('=' * 50)
        
        max_concurrent = options['max_concurrent']
        step_size = options['step_size']
        
        self.stdout.write(f"Maximum concurrent requests: {max_concurrent}")
        self.stdout.write(f"Step size: {step_size}")
        
        # This is a simplified stress test
        # In a real implementation, you'd use proper load testing tools
        
        for concurrent in range(step_size, max_concurrent + 1, step_size):
            self.stdout.write(f"\nTesting with {concurrent} concurrent requests...")
            
            # Run a short load test at this concurrency level
            start_time = time.time()
            success_count = 0
            error_count = 0
            
            # Simulate concurrent requests (simplified)
            client = IndonesianNLPClient()
            test_text = "Stress test untuk sistem NLP bahasa Indonesia."
            
            for i in range(concurrent):
                try:
                    result = client.analyze_sentiment(test_text)
                    success_count += 1
                except Exception:
                    error_count += 1
            
            duration = time.time() - start_time
            success_rate = (success_count / concurrent) * 100
            
            self.stdout.write(f"  Success rate: {success_rate:.2f}%")
            self.stdout.write(f"  Response time: {duration:.2f}s")
            
            # Stop if success rate drops below threshold
            if success_rate < 90:
                self.stdout.write(
                    self.style.WARNING(
                        f"Success rate dropped below 90% at {concurrent} concurrent requests"
                    )
                )
                break
    
    def _run_text_processing_test(self, options):
        """Test text processing utilities"""
        self.stdout.write(self.style.SUCCESS('Running Text Processing Test'))
        self.stdout.write('=' * 50)
        
        sample_size = options['sample_size']
        
        # Generate test texts
        test_texts = self._generate_indonesian_test_texts(sample_size)
        
        processor = IndonesianTextProcessor()
        
        # Test different processing functions
        processing_functions = [
            ('clean_text', processor.clean_text),
            ('normalize_slang', processor.normalize_slang),
            ('remove_stopwords', processor.remove_stopwords),
            ('stem_text', processor.stem_text),
            ('tokenize_words', processor.tokenize_words),
            ('tokenize_sentences', processor.tokenize_sentences)
        ]
        
        for func_name, func in processing_functions:
            self.stdout.write(f"\nTesting {func_name}...")
            
            start_time = time.time()
            success_count = 0
            error_count = 0
            
            for text in test_texts:
                try:
                    result = func(text)
                    success_count += 1
                except Exception:
                    error_count += 1
            
            duration = time.time() - start_time
            
            self.stdout.write(f"  Processed: {success_count}/{sample_size} texts")
            self.stdout.write(f"  Errors: {error_count}")
            self.stdout.write(f"  Time: {duration:.2f}s")
            self.stdout.write(f"  Throughput: {success_count / duration:.2f} texts/s")
    
    def _generate_test_texts(self, count, length):
        """Generate test texts for benchmarking"""
        base_words = [
            'saya', 'anda', 'dia', 'kami', 'mereka', 'ini', 'itu', 'yang', 'untuk',
            'dengan', 'dari', 'ke', 'di', 'pada', 'dalam', 'oleh', 'sebagai',
            'sangat', 'baik', 'buruk', 'senang', 'sedih', 'marah', 'takut',
            'Indonesia', 'Jakarta', 'Surabaya', 'Bandung', 'Medan', 'Makassar'
        ]
        
        texts = []
        for i in range(count):
            words = []
            for j in range(length):
                words.append(base_words[j % len(base_words)])
            texts.append(' '.join(words))
        
        return texts
    
    def _generate_indonesian_test_texts(self, count):
        """Generate Indonesian test texts"""
        sample_texts = [
            "Saya sangat senang dengan layanan ini.",
            "Produk ini tidak sesuai dengan harapan saya.",
            "Pelayanan customer service sangat memuaskan.",
            "Harga yang ditawarkan terlalu mahal.",
            "Kualitas produk sangat bagus dan berkualitas.",
            "Pengiriman barang terlambat dari jadwal.",
            "Tim support sangat responsif dan membantu.",
            "Website ini mudah digunakan dan user-friendly.",
            "Fitur-fitur yang disediakan sangat lengkap.",
            "Proses pembayaran rumit dan membingungkan."
        ]
        
        texts = []
        for i in range(count):
            texts.append(sample_texts[i % len(sample_texts)])
        
        return texts