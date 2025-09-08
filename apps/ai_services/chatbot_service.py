from typing import Dict, Any, Optional, List
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
import json
import logging
from datetime import datetime

from .hr_assistant_architecture import HRAssistantOrchestrator
from .models import ChatSession, ChatMessage

logger = logging.getLogger(__name__)

class ChatbotService:
    """
    Enhanced Chatbot Service untuk HR Assistant
    Mendukung query data HR real-time dengan integrasi ke sistem HR
    """
    
    def __init__(self):
        self.hr_orchestrator = HRAssistantOrchestrator()
        self.session_timeout = 3600  # 1 hour in seconds
    
    def process_message(self, user_id: int, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process incoming chat message and generate response
        """
        try:
            # Get or create chat session
            session = self._get_or_create_session(user_id, session_id)
            
            # Save user message
            user_message = self._save_message(
                session=session,
                message=message,
                is_user=True
            )
            
            # Process message with HR orchestrator
            hr_response = self.hr_orchestrator.process_query(
                query=message,
                user_id=user_id
            )
            
            # Generate chatbot response
            bot_response = self._generate_response(hr_response, message)
            
            # Save bot response
            bot_message = self._save_message(
                session=session,
                message=bot_response['message'],
                is_user=False,
                metadata=bot_response.get('metadata', {})
            )
            
            return {
                'success': True,
                'session_id': str(session.id),
                'response': bot_response,
                'message_id': str(bot_message.id),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                'success': False,
                'error': f'Maaf, terjadi kesalahan dalam memproses pesan Anda: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def _get_or_create_session(self, user_id: int, session_id: Optional[str] = None) -> 'ChatSession':
        """
        Get existing session or create new one
        """
        try:
            user = User.objects.get(id=user_id)
            
            if session_id:
                try:
                    session = ChatSession.objects.get(
                        id=session_id,
                        user=user,
                        is_active=True
                    )
                    # Check if session is still valid (not expired)
                    if self._is_session_valid(session):
                        return session
                except ChatSession.DoesNotExist:
                    pass
            
            # Create new session
            session = ChatSession.objects.create(
                user=user,
                title=f"HR Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                is_active=True
            )
            
            return session
            
        except User.DoesNotExist:
            raise ValueError(f"User with ID {user_id} not found")
    
    def _is_session_valid(self, session: 'ChatSession') -> bool:
        """
        Check if session is still valid (not expired)
        """
        time_diff = (datetime.now() - session.updated_at.replace(tzinfo=None)).total_seconds()
        return time_diff < self.session_timeout
    
    def _save_message(self, session: 'ChatSession', message: str, is_user: bool, metadata: Dict = None) -> 'ChatMessage':
        """
        Save message to database
        """
        return ChatMessage.objects.create(
            session=session,
            message=message,
            is_user_message=is_user,
            metadata=metadata or {}
        )
    
    def _generate_response(self, hr_response: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """
        Generate chatbot response based on HR orchestrator result
        """
        if not hr_response.get('success', False):
            return {
                'message': hr_response.get('error', 'Maaf, saya tidak dapat memproses permintaan Anda saat ini.'),
                'type': 'error',
                'metadata': {
                    'query_type': 'error',
                    'original_query': original_query
                }
            }
        
        data = hr_response.get('data', {})
        query_type = hr_response.get('query_type', 'general')
        
        # Format response based on query type
        if query_type == 'employee_data':
            return self._format_employee_response(data, original_query)
        elif query_type == 'leave_data':
            return self._format_leave_response(data, original_query)
        elif query_type == 'performance_data':
            return self._format_performance_response(data, original_query)
        elif query_type == 'payroll_data':
            return self._format_payroll_response(data, original_query)
        elif query_type == 'general_insights':
            return self._format_insights_response(data, original_query)
        else:
            return {
                'message': 'Informasi berhasil diambil.',
                'type': 'info',
                'data': data,
                'metadata': {
                    'query_type': query_type,
                    'original_query': original_query
                }
            }
    
    def _format_employee_response(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format employee data response
        """
        if 'profile' in data:
            profile = data['profile']
            message = f"📋 **Informasi Karyawan**\n\n"
            message += f"**Nama:** {profile.get('full_name', 'N/A')}\n"
            message += f"**Posisi:** {profile.get('job_position', 'N/A')}\n"
            message += f"**Departemen:** {profile.get('department', 'N/A')}\n"
            message += f"**Email:** {profile.get('email', 'N/A')}\n"
            
            if profile.get('phone'):
                message += f"**Telepon:** {profile['phone']}\n"
            if profile.get('employee_id'):
                message += f"**ID Karyawan:** {profile['employee_id']}\n"
        
        elif 'colleagues' in data:
            colleagues = data['colleagues']
            message = f"👥 **Rekan Kerja di Departemen**\n\n"
            for colleague in colleagues[:5]:  # Limit to 5
                message += f"• {colleague.get('name', 'N/A')} - {colleague.get('position', 'N/A')}\n"
        
        elif 'manager' in data:
            manager = data['manager']
            message = f"👨‍💼 **Informasi Manajer**\n\n"
            message += f"**Nama:** {manager.get('name', 'N/A')}\n"
            message += f"**Posisi:** {manager.get('position', 'N/A')}\n"
            message += f"**Email:** {manager.get('email', 'N/A')}\n"
        
        else:
            message = "Informasi karyawan berhasil diambil."
        
        return {
            'message': message,
            'type': 'employee_info',
            'data': data,
            'metadata': {
                'query_type': 'employee_data',
                'original_query': query
            }
        }
    
    def _format_leave_response(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format leave data response
        """
        if 'leave_balance' in data:
            balance = data['leave_balance']
            message = f"🏖️ **Saldo Cuti Anda**\n\n"
            for leave_type, info in balance.items():
                message += f"**{leave_type}:** {info.get('remaining', 0)} hari tersisa dari {info.get('allocated', 0)} hari\n"
        
        elif 'leave_history' in data:
            history = data['leave_history']
            message = f"📅 **Riwayat Cuti**\n\n"
            for leave in history[:5]:  # Limit to 5 recent
                status_emoji = "✅" if leave.get('status') == 'approved' else "⏳" if leave.get('status') == 'pending' else "❌"
                message += f"{status_emoji} {leave.get('leave_type', 'N/A')} - {leave.get('start_date', 'N/A')} s/d {leave.get('end_date', 'N/A')}\n"
        
        elif 'pending_requests' in data:
            pending = data['pending_requests']
            message = f"⏳ **Permintaan Cuti Tertunda**\n\n"
            if pending:
                for leave in pending:
                    message += f"• {leave.get('leave_type', 'N/A')} - {leave.get('start_date', 'N/A')} s/d {leave.get('end_date', 'N/A')}\n"
            else:
                message += "Tidak ada permintaan cuti yang tertunda."
        
        elif 'upcoming_holidays' in data:
            holidays = data['upcoming_holidays']
            message = f"🎉 **Hari Libur Mendatang**\n\n"
            for holiday in holidays[:5]:
                message += f"• {holiday.get('name', 'N/A')} - {holiday.get('date', 'N/A')}\n"
        
        else:
            message = "Informasi cuti berhasil diambil."
        
        return {
            'message': message,
            'type': 'leave_info',
            'data': data,
            'metadata': {
                'query_type': 'leave_data',
                'original_query': query
            }
        }
    
    def _format_performance_response(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format performance data response
        """
        if 'objectives' in data:
            objectives = data['objectives']
            message = f"🎯 **Objektif Kinerja**\n\n"
            for obj in objectives[:3]:  # Limit to 3
                progress = obj.get('progress', 0)
                status_emoji = "✅" if obj.get('status') == 'completed' else "🔄" if obj.get('status') == 'in_progress' else "⏸️"
                message += f"{status_emoji} {obj.get('title', 'N/A')} ({progress}% selesai)\n"
        
        elif 'key_results' in data:
            key_results = data['key_results']
            message = f"📊 **Key Results Terbaru**\n\n"
            for kr in key_results[:3]:
                progress = kr.get('progress_percentage', 0)
                message += f"• {kr.get('title', 'N/A')} - {progress}% tercapai\n"
        
        elif 'feedback' in data:
            feedback = data['feedback']
            message = f"💬 **Umpan Balik Kinerja**\n\n"
            for fb in feedback[:3]:
                message += f"• {fb.get('reviewer_name', 'N/A')}: {fb.get('rating', 'N/A')}/5\n"
                if fb.get('comments'):
                    message += f"  \"{fb['comments'][:100]}...\"\n"
        
        elif 'bonus_points' in data:
            points = data['bonus_points']
            message = f"⭐ **Poin Bonus**\n\n"
            total_points = sum(point.get('points', 0) for point in points)
            message += f"**Total Poin:** {total_points}\n\n"
            for point in points[:3]:
                message += f"• {point.get('reason', 'N/A')}: +{point.get('points', 0)} poin\n"
        
        elif 'performance_summary' in data:
            summary = data['performance_summary']
            message = f"📈 **Ringkasan Kinerja {summary.get('year', 'N/A')}**\n\n"
            
            obj_summary = summary.get('objectives_summary', {})
            message += f"**Objektif:** {obj_summary.get('completed', 0)}/{obj_summary.get('total', 0)} selesai\n"
            
            kr_summary = summary.get('key_results_summary', {})
            message += f"**Key Results:** {kr_summary.get('completed', 0)}/{kr_summary.get('total', 0)} tercapai\n"
            
            message += f"**Total Poin Bonus:** {summary.get('total_bonus_points', 0)}\n"
        
        else:
            message = "Informasi kinerja berhasil diambil."
        
        return {
            'message': message,
            'type': 'performance_info',
            'data': data,
            'metadata': {
                'query_type': 'performance_data',
                'original_query': query
            }
        }
    
    def _format_payroll_response(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format payroll data response
        """
        if 'payslips' in data:
            payslips = data['payslips']
            message = f"💰 **Slip Gaji Terbaru**\n\n"
            for slip in payslips[:3]:
                message += f"• {slip.get('period', 'N/A')}: Rp {slip.get('net_pay', 0):,.0f}\n"
        
        elif 'contract_info' in data:
            contract = data['contract_info']
            message = f"📄 **Informasi Kontrak**\n\n"
            message += f"**Tipe Kontrak:** {contract.get('contract_type', 'N/A')}\n"
            message += f"**Gaji Pokok:** Rp {contract.get('basic_salary', 0):,.0f}\n"
            message += f"**Mulai:** {contract.get('start_date', 'N/A')}\n"
            if contract.get('end_date'):
                message += f"**Berakhir:** {contract['end_date']}\n"
        
        elif 'salary_info' in data:
            salary = data['salary_info']
            message = f"💵 **Informasi Gaji**\n\n"
            message += f"**Gaji Pokok:** Rp {salary.get('basic_salary', 0):,.0f}\n"
            message += f"**Total Tunjangan:** Rp {salary.get('total_allowances', 0):,.0f}\n"
            message += f"**Total Potongan:** Rp {salary.get('total_deductions', 0):,.0f}\n"
            message += f"**Gaji Bersih:** Rp {salary.get('net_salary', 0):,.0f}\n"
        
        elif 'allowances' in data:
            allowances = data['allowances']
            message = f"💼 **Tunjangan**\n\n"
            for allowance in allowances:
                message += f"• {allowance.get('title', 'N/A')}: Rp {allowance.get('amount', 0):,.0f}\n"
        
        elif 'deductions' in data:
            deductions = data['deductions']
            message = f"📉 **Potongan**\n\n"
            for deduction in deductions:
                message += f"• {deduction.get('title', 'N/A')}: Rp {deduction.get('amount', 0):,.0f}\n"
        
        else:
            message = "Informasi penggajian berhasil diambil."
        
        return {
            'message': message,
            'type': 'payroll_info',
            'data': data,
            'metadata': {
                'query_type': 'payroll_data',
                'original_query': query
            }
        }
    
    def _format_insights_response(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """
        Format general insights response
        """
        message = f"📊 **Wawasan HR**\n\n"
        
        if 'summary' in data:
            summary = data['summary']
            message += f"**Ringkasan:** {summary}\n\n"
        
        if 'recommendations' in data:
            recommendations = data['recommendations']
            message += "**Rekomendasi:**\n"
            for rec in recommendations[:3]:
                message += f"• {rec}\n"
        
        if 'insights' in data:
            insights = data['insights']
            message += "\n**Wawasan:**\n"
            for insight in insights[:3]:
                message += f"• {insight}\n"
        
        return {
            'message': message,
            'type': 'insights',
            'data': data,
            'metadata': {
                'query_type': 'general_insights',
                'original_query': query
            }
        }
    
    def get_chat_history(self, session_id: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get chat history for a session
        """
        try:
            session = ChatSession.objects.get(id=session_id, is_active=True)
            messages = ChatMessage.objects.filter(
                session=session
            ).order_by('-created_at')[:limit]
            
            history = []
            for msg in reversed(messages):
                history.append({
                    'id': str(msg.id),
                    'message': msg.message,
                    'is_user': msg.is_user_message,
                    'timestamp': msg.created_at.isoformat(),
                    'metadata': msg.metadata
                })
            
            return {
                'success': True,
                'session_id': session_id,
                'messages': history,
                'total_messages': len(history)
            }
            
        except ChatSession.DoesNotExist:
            return {
                'success': False,
                'error': 'Session not found'
            }
        except Exception as e:
            logger.error(f"Error getting chat history: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def end_session(self, session_id: str) -> Dict[str, Any]:
        """
        End a chat session
        """
        try:
            session = ChatSession.objects.get(id=session_id, is_active=True)
            session.is_active = False
            session.save()
            
            return {
                'success': True,
                'message': 'Session ended successfully'
            }
            
        except ChatSession.DoesNotExist:
            return {
                'success': False,
                'error': 'Session not found'
            }
        except Exception as e:
            logger.error(f"Error ending session: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }