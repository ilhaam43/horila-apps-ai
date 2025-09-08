from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import connection
from unittest.mock import patch, MagicMock
import json
import time


class HealthCheckViewTests(TestCase):
    """Test cases for basic health check endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.health_url = '/health/'
    
    def test_health_check_endpoint_exists(self):
        """Test that health check endpoint is accessible"""
        response = self.client.get(self.health_url)
        self.assertEqual(response.status_code, 200)
    
    def test_health_check_response_format(self):
        """Test health check response format"""
        response = self.client.get(self.health_url)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = json.loads(response.content)
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertEqual(data['status'], 'healthy')
    
    def test_health_check_performance(self):
        """Test health check response time"""
        start_time = time.time()
        response = self.client.get(self.health_url)
        end_time = time.time()
        
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        self.assertLess(response_time, 100)  # Should respond within 100ms
        self.assertEqual(response.status_code, 200)


class ReadinessCheckViewTests(TestCase):
    """Test cases for readiness check endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.ready_url = '/health/ready/'
    
    def test_readiness_check_endpoint_exists(self):
        """Test that readiness check endpoint is accessible"""
        response = self.client.get(self.ready_url)
        self.assertEqual(response.status_code, 200)
    
    def test_readiness_check_database_connection(self):
        """Test readiness check includes database connectivity"""
        response = self.client.get(self.ready_url)
        data = json.loads(response.content)
        
        self.assertIn('database', data)
        self.assertEqual(data['database']['status'], 'connected')
    
    def test_readiness_check_cache_connection(self):
        """Test readiness check includes cache connectivity"""
        response = self.client.get(self.ready_url)
        data = json.loads(response.content)
        
        self.assertIn('cache', data)
        # Cache status should be either 'connected' or 'unavailable'
        self.assertIn(data['cache']['status'], ['connected', 'unavailable'])
    
    @patch('django.db.connection.cursor')
    def test_readiness_check_database_failure(self, mock_cursor):
        """Test readiness check handles database failures"""
        mock_cursor.side_effect = Exception("Database connection failed")
        
        response = self.client.get(self.ready_url)
        data = json.loads(response.content)
        
        self.assertIn('database', data)
        self.assertEqual(data['database']['status'], 'error')


class LivenessCheckViewTests(TestCase):
    """Test cases for liveness check endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.live_url = '/health/live/'
    
    def test_liveness_check_endpoint_exists(self):
        """Test that liveness check endpoint is accessible"""
        response = self.client.get(self.live_url)
        self.assertEqual(response.status_code, 200)
    
    def test_liveness_check_response_format(self):
        """Test liveness check response format"""
        response = self.client.get(self.live_url)
        data = json.loads(response.content)
        
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('uptime', data)
        self.assertEqual(data['status'], 'alive')


class DetailedHealthCheckViewTests(TestCase):
    """Test cases for detailed health check endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.detailed_url = '/health/detailed/'
    
    def test_detailed_health_check_endpoint_exists(self):
        """Test that detailed health check endpoint is accessible"""
        response = self.client.get(self.detailed_url)
        self.assertEqual(response.status_code, 200)
    
    def test_detailed_health_check_includes_system_metrics(self):
        """Test detailed health check includes system metrics"""
        response = self.client.get(self.detailed_url)
        data = json.loads(response.content)
        
        # Check for system metrics
        self.assertIn('system', data)
        system_data = data['system']
        
        self.assertIn('cpu_usage', system_data)
        self.assertIn('memory_usage', system_data)
        self.assertIn('disk_usage', system_data)
        
        # Validate metric ranges
        self.assertGreaterEqual(system_data['cpu_usage'], 0)
        self.assertLessEqual(system_data['cpu_usage'], 100)
        self.assertGreaterEqual(system_data['memory_usage'], 0)
        self.assertLessEqual(system_data['memory_usage'], 100)
    
    def test_detailed_health_check_includes_database_metrics(self):
        """Test detailed health check includes database metrics"""
        response = self.client.get(self.detailed_url)
        data = json.loads(response.content)
        
        self.assertIn('database', data)
        db_data = data['database']
        
        self.assertIn('status', db_data)
        self.assertIn('response_time_ms', db_data)
    
    def test_detailed_health_check_includes_cache_metrics(self):
        """Test detailed health check includes cache metrics"""
        response = self.client.get(self.detailed_url)
        data = json.loads(response.content)
        
        self.assertIn('cache', data)
        cache_data = data['cache']
        
        self.assertIn('status', cache_data)
        self.assertIn('response_time_ms', cache_data)
    
    @patch('subprocess.run')
    def test_detailed_health_check_external_services(self, mock_subprocess):
        """Test detailed health check includes external service checks"""
        # Mock successful external service responses
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = 'OK'
        mock_subprocess.return_value = mock_result
        
        response = self.client.get(self.detailed_url)
        data = json.loads(response.content)
        
        self.assertIn('external_services', data)
        external_data = data['external_services']
        
        # Check for expected external services
        expected_services = ['elasticsearch', 'ollama', 'n8n', 'chromadb']
        for service in expected_services:
            if service in external_data:
                self.assertIn('status', external_data[service])


class MetricsViewTests(TestCase):
    """Test cases for Prometheus metrics endpoint"""
    
    def setUp(self):
        self.client = Client()
        self.metrics_url = '/metrics/'
    
    def test_metrics_endpoint_exists(self):
        """Test that metrics endpoint is accessible"""
        response = self.client.get(self.metrics_url)
        self.assertEqual(response.status_code, 200)
    
    def test_metrics_content_type(self):
        """Test metrics endpoint returns correct content type"""
        response = self.client.get(self.metrics_url)
        self.assertEqual(response['Content-Type'], 'text/plain; charset=utf-8')
    
    def test_metrics_format(self):
        """Test metrics are in Prometheus format"""
        response = self.client.get(self.metrics_url)
        content = response.content.decode('utf-8')
        
        # Check for basic Prometheus metrics format
        self.assertIn('# HELP', content)
        self.assertIn('# TYPE', content)
        
        # Check for expected metrics
        expected_metrics = [
            'horilla_http_requests_total',
            'horilla_http_request_duration_seconds',
            'horilla_database_connections',
            'horilla_cache_operations_total'
        ]
        
        for metric in expected_metrics:
            self.assertIn(metric, content)


class MonitoringIntegrationTests(TestCase):
    """Integration tests for monitoring system"""
    
    def setUp(self):
        self.client = Client()
    
    def test_all_monitoring_endpoints_accessible(self):
        """Test all monitoring endpoints are accessible"""
        endpoints = [
            '/health/',
            '/health/ready/',
            '/health/live/',
            '/health/detailed/',
            '/metrics/'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 200)
    
    def test_monitoring_endpoints_performance(self):
        """Test monitoring endpoints respond quickly"""
        endpoints = [
            '/health/',
            '/health/ready/',
            '/health/live/'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                start_time = time.time()
                response = self.client.get(endpoint)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                self.assertLess(response_time, 500)  # Should respond within 500ms
                self.assertEqual(response.status_code, 200)
    
    def test_monitoring_endpoints_concurrent_access(self):
        """Test monitoring endpoints handle concurrent requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request(endpoint):
            try:
                response = self.client.get(endpoint)
                results.put((endpoint, response.status_code))
            except Exception as e:
                results.put((endpoint, str(e)))
        
        # Create multiple threads to test concurrent access
        threads = []
        endpoints = ['/health/', '/health/ready/', '/health/live/'] * 5
        
        for endpoint in endpoints:
            thread = threading.Thread(target=make_request, args=(endpoint,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        while not results.empty():
            endpoint, status = results.get()
            self.assertEqual(status, 200, f"Endpoint {endpoint} failed with status {status}")


class MonitoringSecurityTests(TestCase):
    """Security tests for monitoring endpoints"""
    
    def setUp(self):
        self.client = Client()
    
    def test_monitoring_endpoints_no_sensitive_data(self):
        """Test monitoring endpoints don't expose sensitive data"""
        endpoints = [
            '/health/',
            '/health/ready/',
            '/health/live/',
            '/health/detailed/',
            '/metrics/'
        ]
        
        sensitive_patterns = [
            'password',
            'secret',
            'key',
            'token',
            'credential'
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                content = response.content.decode('utf-8').lower()
                
                for pattern in sensitive_patterns:
                    self.assertNotIn(pattern, content, 
                                   f"Sensitive data '{pattern}' found in {endpoint}")
    
    def test_monitoring_endpoints_http_methods(self):
        """Test monitoring endpoints only accept GET requests"""
        endpoints = [
            '/health/',
            '/health/ready/',
            '/health/live/',
            '/health/detailed/',
            '/metrics/',
        ]
        
        methods = ['PUT', 'DELETE', 'PATCH', 'POST']
        
        for endpoint in endpoints:
            for method in methods:
                with self.subTest(endpoint=endpoint, method=method):
                    response = getattr(self.client, method.lower())(endpoint)
                    self.assertIn(response.status_code, [405, 404])  # Method not allowed or not found


class MonitoringUtilityTests(TestCase):
    """Test utility functions used in monitoring"""
    
    def test_system_metrics_collection(self):
        """Test system metrics collection functions"""
        from monitoring.views import DetailedHealthCheckView
        
        view = DetailedHealthCheckView()
        
        # Test CPU usage collection
        cpu_usage = view.get_cpu_usage()
        self.assertIsInstance(cpu_usage, (int, float))
        self.assertGreaterEqual(cpu_usage, 0)
        self.assertLessEqual(cpu_usage, 100)
        
        # Test memory usage collection
        memory_usage = view.get_memory_usage()
        self.assertIsInstance(memory_usage, (int, float))
        self.assertGreaterEqual(memory_usage, 0)
        self.assertLessEqual(memory_usage, 100)
        
        # Test disk usage collection
        disk_usage = view.get_disk_usage()
        self.assertIsInstance(disk_usage, (int, float))
        self.assertGreaterEqual(disk_usage, 0)
        self.assertLessEqual(disk_usage, 100)
    
    def test_database_health_check(self):
        """Test database health check function"""
        from monitoring.views import ReadinessCheckView
        
        view = ReadinessCheckView()
        db_status = view.check_database()
        
        self.assertIsInstance(db_status, dict)
        self.assertIn('status', db_status)
        self.assertIn('response_time_ms', db_status)
        
        # Database should be connected in test environment
        self.assertEqual(db_status['status'], 'connected')
    
    def test_cache_health_check(self):
        """Test cache health check function"""
        from monitoring.views import ReadinessCheckView
        
        view = ReadinessCheckView()
        cache_status = view.check_cache()
        
        self.assertIsInstance(cache_status, dict)
        self.assertIn('status', cache_status)
        self.assertIn('response_time_ms', cache_status)
        
        # Cache status should be either connected or unavailable
        self.assertIn(cache_status['status'], ['connected', 'unavailable'])


class MonitoringErrorHandlingTests(TestCase):
    """Test error handling in monitoring endpoints"""
    
    def setUp(self):
        self.client = Client()
    
    @patch('django.db.connection.cursor')
    def test_database_error_handling(self, mock_cursor):
        """Test handling of database errors"""
        mock_cursor.side_effect = Exception("Database error")
        
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 200)  # Should still return 200
        
        data = json.loads(response.content)
        self.assertEqual(data['database']['status'], 'error')
    
    @patch('django.core.cache.cache.get')
    def test_cache_error_handling(self, mock_cache_get):
        """Test handling of cache errors"""
        mock_cache_get.side_effect = Exception("Cache error")
        
        response = self.client.get('/health/ready/')
        self.assertEqual(response.status_code, 200)  # Should still return 200
        
        data = json.loads(response.content)
        self.assertEqual(data['cache']['status'], 'error')
    
    @patch('psutil.cpu_percent')
    def test_system_metrics_error_handling(self, mock_cpu_percent):
        """Test handling of system metrics errors"""
        mock_cpu_percent.side_effect = Exception("System error")
        
        response = self.client.get('/health/detailed/')
        self.assertEqual(response.status_code, 200)  # Should still return 200
        
        data = json.loads(response.content)
        # Should handle the error gracefully
        self.assertIn('system', data)