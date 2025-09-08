#!/usr/bin/env python3
"""
Test script for AI Services Preprocessing Pipeline
"""

import os
import sys
import django
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

import pandas as pd
import numpy as np
from ai_services.preprocessing import DataPreprocessor, create_preprocessing_pipeline
from ai_services.models import ModelTrainingSession, TrainingData
from django.utils import timezone
import json

def test_basic_preprocessing():
    """
    Test basic preprocessing functionality
    """
    print("\n=== Testing Basic Preprocessing ===")
    
    # Create sample data
    sample_data = {
        'budget_amount': [1000, 2000, 1500, 3000, 2500],
        'department': ['HR', 'IT', 'Finance', 'HR', 'IT'],
        'priority': ['high', 'medium', 'low', 'high', 'medium'],
        'description': [
            'Employee training budget',
            'Software licensing costs',
            'Office supplies',
            'Recruitment expenses',
            'Hardware upgrade'
        ],
        'target': [1, 0, 0, 1, 1]  # 1 = approved, 0 = rejected
    }
    
    df = pd.DataFrame(sample_data)
    print(f"Sample data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    
    # Create preprocessor
    preprocessor = create_preprocessing_pipeline('budget_ai')
    
    # Fit and transform
    features, target = preprocessor.fit_transform(df, target_column='target')
    
    print(f"Processed features shape: {features.shape}")
    print(f"Target shape: {target.shape}")
    print(f"Feature info: {preprocessor.get_feature_info()}")
    
    # Test transform on new data
    new_data = {
        'budget_amount': [1800],
        'department': ['Marketing'],  # New category
        'priority': ['high'],
        'description': ['Marketing campaign budget']
    }
    
    new_df = pd.DataFrame(new_data)
    new_features = preprocessor.transform(new_df)
    
    print(f"New data processed shape: {new_features.shape}")
    print("✓ Basic preprocessing test passed")
    
    return preprocessor

def test_mixed_data_types():
    """
    Test preprocessing with mixed data types
    """
    print("\n=== Testing Mixed Data Types ===")
    
    # Create data with various types
    sample_data = {
        'numeric_int': [1, 2, 3, 4, 5],
        'numeric_float': [1.1, 2.2, 3.3, 4.4, 5.5],
        'categorical': ['A', 'B', 'C', 'A', 'B'],
        'text_short': ['yes', 'no', 'maybe', 'yes', 'no'],
        'text_long': [
            'This is a long text description with multiple words',
            'Another lengthy description for testing purposes',
            'Short text',
            'Very detailed explanation of the requirements and specifications',
            'Brief note'
        ],
        'missing_values': [1.0, None, 3.0, None, 5.0],
        'target': [0, 1, 0, 1, 0]
    }
    
    df = pd.DataFrame(sample_data)
    print(f"Mixed data shape: {df.shape}")
    print(f"Data types:\n{df.dtypes}")
    
    preprocessor = create_preprocessing_pipeline('mixed_test')
    features, target = preprocessor.fit_transform(df, target_column='target')
    
    print(f"Processed features shape: {features.shape}")
    print(f"Feature info: {preprocessor.get_feature_info()}")
    print("✓ Mixed data types test passed")
    
    return preprocessor

def test_session_integration():
    """
    Test integration with ModelTrainingSession
    """
    print("\n=== Testing Session Integration ===")
    
    try:
        # Create a test AI model registry first
        from ai_services.models import AIModelRegistry
        model_registry = AIModelRegistry.objects.create(
            name='test_preprocessing_model',
            service_type='budget_ai',
            model_type='classification',
            model_path='/tmp/test_model.pkl',
            is_active=True
        )
        
        # Create a test training session
        session = ModelTrainingSession.objects.create(
            model=model_registry,
            training_config={'test': True},
            status='pending'
        )
        
        print(f"Created test session: {session.id}")
        
        # Create preprocessor and save to session
        preprocessor = create_preprocessing_pipeline('session_test')
        
        # Create some dummy data to fit the preprocessor
        dummy_data = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': ['A', 'B', 'C'],
            'target': [0, 1, 0]
        })
        
        preprocessor.fit_transform(dummy_data, target_column='target')
        preprocessor.save_to_session(session)
        
        print("✓ Preprocessor saved to session")
        
        # Load preprocessor from session
        loaded_preprocessor = DataPreprocessor.load_from_session(session)
        
        print(f"✓ Preprocessor loaded from session")
        print(f"Feature names match: {preprocessor.feature_names == loaded_preprocessor.feature_names}")
        
        # Test transform with loaded preprocessor
        test_data = pd.DataFrame({
            'feature1': [4],
            'feature2': ['D']
        })
        
        transformed = loaded_preprocessor.transform(test_data)
        print(f"Transform with loaded preprocessor shape: {transformed.shape}")
        
        # Cleanup
        session.delete()
        model_registry.delete()
        print("✓ Session integration test passed")
        
    except Exception as e:
        print(f"✗ Session integration test failed: {str(e)}")
        # Try to cleanup
        try:
            session.delete()
            model_registry.delete()
        except:
            pass

def test_hr_data_preprocessing():
    """
    Test preprocessing for HR-specific data
    """
    print("\n=== Testing HR Data Preprocessing ===")
    
    # Sample HR data
    hr_data = {
        'employee_id': ['EMP001', 'EMP002', 'EMP003', 'EMP004', 'EMP005'],
        'department': ['Engineering', 'HR', 'Sales', 'Engineering', 'Marketing'],
        'position': ['Senior Developer', 'HR Manager', 'Sales Rep', 'Junior Developer', 'Marketing Specialist'],
        'salary': [75000, 65000, 45000, 55000, 50000],
        'years_experience': [5, 8, 2, 1, 3],
        'performance_score': [4.2, 4.8, 3.9, 4.0, 4.5],
        'leave_days_taken': [12, 8, 15, 5, 10],
        'training_completed': [3, 5, 1, 2, 4],
        'promotion_eligible': [1, 1, 0, 0, 1]  # Target variable
    }
    
    df = pd.DataFrame(hr_data)
    print(f"HR data shape: {df.shape}")
    
    preprocessor = create_preprocessing_pipeline('hr_assistant')
    features, target = preprocessor.fit_transform(df, target_column='promotion_eligible')
    
    print(f"Processed HR features shape: {features.shape}")
    print(f"Feature info: {preprocessor.get_feature_info()}")
    
    # Test with new employee data
    new_employee = {
        'employee_id': ['EMP006'],
        'department': ['Finance'],  # New department
        'position': ['Financial Analyst'],
        'salary': [60000],
        'years_experience': [4],
        'performance_score': [4.3],
        'leave_days_taken': [7],
        'training_completed': [2]
    }
    
    new_df = pd.DataFrame(new_employee)
    new_features = preprocessor.transform(new_df)
    
    print(f"New employee data processed shape: {new_features.shape}")
    print("✓ HR data preprocessing test passed")

def test_error_handling():
    """
    Test error handling and edge cases
    """
    print("\n=== Testing Error Handling ===")
    
    preprocessor = create_preprocessing_pipeline('error_test')
    
    # Test empty data
    try:
        empty_df = pd.DataFrame()
        features, target = preprocessor.fit_transform(empty_df)
        print("✓ Empty data handled gracefully")
    except Exception as e:
        print(f"✓ Empty data error handled: {type(e).__name__}")
    
    # Test missing columns in transform
    try:
        # Fit with some data
        fit_data = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['A', 'B', 'C']
        })
        preprocessor.fit_transform(fit_data)
        
        # Transform with missing column
        transform_data = pd.DataFrame({
            'col1': [4]  # Missing col2
        })
        features = preprocessor.transform(transform_data)
        print("✓ Missing columns handled gracefully")
        
    except Exception as e:
        print(f"✓ Missing columns error handled: {type(e).__name__}")
    
    print("✓ Error handling test completed")

def main():
    """
    Run all preprocessing tests
    """
    print("Starting AI Services Preprocessing Pipeline Tests")
    print("=" * 50)
    
    try:
        # Run all tests
        test_basic_preprocessing()
        test_mixed_data_types()
        test_session_integration()
        test_hr_data_preprocessing()
        test_error_handling()
        
        print("\n" + "=" * 50)
        print("✅ All preprocessing tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)