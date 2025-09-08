#!/usr/bin/env python3
"""
Health Check Script for system_test_deployment_1757295956_knowledge_search
"""

import json
import time
import sys
from pathlib import Path

def check_model_health():
    """Check if the deployed model is healthy"""
    try:
        # Import the serving class
        sys.path.append(str(Path(__file__).parent))
        from serve_model import System_Test_Model_1757295956_Knowledge_SearchServing
        
        # Initialize serving
        serving = System_Test_Model_1757295956_Knowledge_SearchServing()
        
        if not serving.is_loaded:
            return {
                'status': 'unhealthy',
                'error': 'Model not loaded',
                'timestamp': time.time()
            }
        
        # Test prediction with dummy data
        test_data = {
            'budget_prediction': {'amount': 1000, 'category': 'test'},
            'knowledge_search': {'query': 'test query'},
            'indonesian_nlp': {'text': 'test text'}
        }
        
        service_type = "knowledge_search"
        dummy_input = test_data.get(service_type, {})
        
        start_time = time.time()
        result = serving.predict(dummy_input)
        response_time = time.time() - start_time
        
        return {
            'status': 'healthy',
            'model_loaded': True,
            'response_time_ms': round(response_time * 1000, 2),
            'test_prediction': result,
            'timestamp': time.time()
        }
        
    except Exception as e:
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }

if __name__ == '__main__':
    health = check_model_health()
    print(json.dumps(health, indent=2))
    
    # Exit with error code if unhealthy
    if health['status'] != 'healthy':
        sys.exit(1)
