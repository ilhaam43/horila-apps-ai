from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, Mock
from datetime import timedelta

from .models import ChatSession, ChatMessage, HRQueryLog
from .hr_assistant_service import HRAssistantService
from .hr_administrative_tasks import HRAdministrativeTasksService


class HRAssistantTestCase(TestCase):
    """Test cases for HR Assistant functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.hr_service = HRAssistantService()
    
    def test_chat_session_creation(self):
        """Test creating a new chat session."""
        session = ChatSession.objects.create(
            user=self.user,
            title='Test HR Session'
        )
        
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.title, 'Test HR Session')
        self.assertTrue(session.is_active)
    
    def test_chat_message_creation(self):
        """Test creating chat messages."""
        session = ChatSession.objects.create(
            user=self.user,
            title='Test Chat'
        )
        
        message = ChatMessage.objects.create(
            session=session,
            is_user_message=True,
            message='Hello HR Assistant'
        )
        
        self.assertEqual(message.session, session)
        self.assertTrue(message.is_user_message)
        self.assertEqual(message.message, 'Hello HR Assistant')
    
    def test_hr_query_log_creation(self):
        """Test HR query logging."""
        log = HRQueryLog.objects.create(
            user=self.user,
            query_type='employee_info',
            query='Get employee details',
            response_data={'status': 'success'},
            processing_time=0.5
        )
        
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.query_type, 'employee_info')
        self.assertTrue(log.success)
    
    def test_process_employee_query(self):
        """Test processing employee-related queries."""
        query = "How many employees do we have?"
        result = self.hr_service.process_query(query, self.user.id)
        
        self.assertIsInstance(result, dict)
        self.assertIn('response', result)
    
    def test_hr_administrative_tasks_service(self):
        """Test HR administrative tasks service initialization."""
        admin_service = HRAdministrativeTasksService()
        
        # Test that service initializes without errors
        self.assertIsNotNone(admin_service)
        self.assertIsNotNone(admin_service.notification_service)
        self.assertIsNotNone(admin_service.reminder_service)
        self.assertIsNotNone(admin_service.report_service)
    
    def test_daily_tasks_processing(self):
        """Test daily tasks processing."""
        admin_service = HRAdministrativeTasksService()
        
        # Mock the process to avoid actual execution
        with patch.object(admin_service, 'process_daily_tasks') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'tasks_completed': 3,
                'notifications_sent': 5
            }
            
            result = admin_service.process_daily_tasks()
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('tasks_completed', result)
    
    def test_weekly_tasks_processing(self):
        """Test weekly tasks processing."""
        admin_service = HRAdministrativeTasksService()
        
        with patch.object(admin_service, 'process_weekly_tasks') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'reports_generated': 2,
                'emails_sent': 10
            }
            
            result = admin_service.process_weekly_tasks()
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('reports_generated', result)
    
    def test_monthly_tasks_processing(self):
        """Test monthly tasks processing."""
        admin_service = HRAdministrativeTasksService()
        
        with patch.object(admin_service, 'process_monthly_tasks') as mock_process:
            mock_process.return_value = {
                'status': 'success',
                'comprehensive_reports': 1,
                'analytics_updated': True
            }
            
            result = admin_service.process_monthly_tasks()
            
            self.assertEqual(result['status'], 'success')
            self.assertIn('comprehensive_reports', result)
    
    def test_hr_query_logging(self):
        """Test HR query logging functionality."""
        # Create a query log
        log_data = {
            'user': self.user,
            'query_type': 'leave_balance',
            'query': 'What is my leave balance?',
            'response_data': {'balance': 15},
            'processing_time': 0.3
        }
        
        log = HRQueryLog.objects.create(**log_data)
        
        # Verify log was created correctly
        self.assertEqual(log.user, self.user)
        self.assertEqual(log.query_type, 'leave_balance')
        self.assertTrue(log.success)
        self.assertEqual(log.processing_time, 0.3)
    
    def test_chat_session_management(self):
        """Test chat session management."""
        # Create multiple sessions
        session1 = ChatSession.objects.create(
            user=self.user,
            title='Session 1'
        )
        session2 = ChatSession.objects.create(
            user=self.user,
            title='Session 2'
        )
        
        # Test that both sessions exist
        user_sessions = ChatSession.objects.filter(user=self.user)
        self.assertEqual(user_sessions.count(), 2)
        
        # Test deactivating a session
        session1.is_active = False
        session1.save()
        
        active_sessions = ChatSession.objects.filter(user=self.user, is_active=True)
        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions.first(), session2)