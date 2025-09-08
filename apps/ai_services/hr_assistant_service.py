"""HR Assistant Service

Service utama untuk AI Assistant HR yang mengintegrasikan:
- Knowledge Management (RAG)
- HR Data Processing
- Natural Language Understanding
- Response Generation
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date

from django.contrib.auth.models import User
from django.db.models import Q

# from .knowledge_ai_service import KnowledgeAIService  # Commented out for now
from .hr_assistant_architecture import HRAssistantOrchestrator
from employee.models import Employee

logger = logging.getLogger(__name__)


class HRAssistantService:
    """Main HR Assistant Service yang menggabungkan RAG dan HR data processing"""
    
    def __init__(self):
        # self.knowledge_service = KnowledgeAIService()  # Commented out - service not available
        self.knowledge_service = None  # Placeholder for future implementation
        self.hr_orchestrator = HRAssistantOrchestrator()
        
        # Intent classification keywords
        self.intent_keywords = {
            'knowledge': [
                'kebijakan', 'policy', 'prosedur', 'procedure', 'panduan', 'guide',
                'aturan', 'rule', 'regulasi', 'regulation', 'sop', 'standar',
                'bagaimana cara', 'how to', 'apa itu', 'what is', 'jelaskan', 'explain'
            ],
            'data_query': [
                'berapa', 'how much', 'how many', 'kapan', 'when', 'siapa', 'who',
                'dimana', 'where', 'status', 'saldo', 'balance', 'riwayat', 'history',
                'daftar', 'list', 'tampilkan', 'show', 'lihat', 'view'
            ],
            'action': [
                'buat', 'create', 'ajukan', 'submit', 'kirim', 'send', 'update',
                'ubah', 'change', 'hapus', 'delete', 'batalkan', 'cancel'
            ],
            'greeting': [
                'halo', 'hello', 'hi', 'hai', 'selamat', 'good morning', 'good afternoon',
                'good evening', 'apa kabar', 'how are you', 'terima kasih', 'thank you'
            ]
        }
    
    def process_query(self, query: str, user: User, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user query dan return response"""
        try:
            # Get employee info from user
            employee = self._get_employee_from_user(user)
            employee_id = employee.id if employee else None
            
            # Classify intent
            intent = self._classify_intent(query)
            
            # Process based on intent
            if intent == 'greeting':
                return self._handle_greeting(query, employee)
            
            elif intent == 'knowledge':
                return self._handle_knowledge_query(query, employee_id)
            
            elif intent == 'data_query':
                return self._handle_data_query(query, employee_id)
            
            elif intent == 'action':
                return self._handle_action_request(query, employee_id)
            
            else:
                # Hybrid approach: try both knowledge and data query
                return self._handle_hybrid_query(query, employee_id)
        
        except Exception as e:
            logger.error(f"Error processing HR query: {str(e)}")
            return {
                'success': False,
                'error': 'Terjadi kesalahan dalam memproses pertanyaan Anda.',
                'response': 'Maaf, saya mengalami kesulitan memproses pertanyaan Anda. Silakan coba lagi atau hubungi administrator.'
            }
    
    def _get_employee_from_user(self, user: User) -> Optional[Employee]:
        """Get employee object from user"""
        try:
            return Employee.objects.get(email=user.email)
        except Employee.DoesNotExist:
            return None
    
    def _classify_intent(self, query: str) -> str:
        """Classify user intent based on query content"""
        query_lower = query.lower()
        
        # Count matches for each intent
        intent_scores = {}
        for intent, keywords in self.intent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            if score > 0:
                intent_scores[intent] = score
        
        # Return intent with highest score
        if intent_scores:
            return max(intent_scores, key=intent_scores.get)
        
        return 'unknown'
    
    def _handle_greeting(self, query: str, employee: Optional[Employee]) -> Dict[str, Any]:
        """Handle greeting queries"""
        query_lower = query.lower()
        
        if employee:
            name = employee.employee_first_name or 'Karyawan'
            
            if any(greeting in query_lower for greeting in ['halo', 'hello', 'hi', 'hai']):
                response = f"Halo {name}! Saya adalah asisten HR Anda. Saya dapat membantu Anda dengan informasi karyawan, cuti, kinerja, gaji, dan kebijakan perusahaan. Ada yang bisa saya bantu?"
            
            elif any(greeting in query_lower for greeting in ['selamat pagi', 'good morning']):
                response = f"Selamat pagi {name}! Semoga hari Anda menyenangkan. Ada yang bisa saya bantu terkait HR hari ini?"
            
            elif any(greeting in query_lower for greeting in ['selamat siang', 'good afternoon']):
                response = f"Selamat siang {name}! Ada yang bisa saya bantu terkait HR?"
            
            elif any(greeting in query_lower for greeting in ['selamat sore', 'good evening']):
                response = f"Selamat sore {name}! Ada yang bisa saya bantu sebelum hari berakhir?"
            
            elif any(thanks in query_lower for thanks in ['terima kasih', 'thank you']):
                response = f"Sama-sama {name}! Senang bisa membantu Anda. Jangan ragu untuk bertanya kapan saja."
            
            else:
                response = f"Halo {name}! Saya siap membantu Anda dengan berbagai kebutuhan HR. Silakan tanyakan apa saja!"
        else:
            response = "Halo! Saya adalah asisten HR. Saya dapat membantu Anda dengan informasi HR, kebijakan perusahaan, dan berbagai layanan HR lainnya. Ada yang bisa saya bantu?"
        
        return {
            'success': True,
            'intent': 'greeting',
            'response': response,
            'data': None
        }
    
    def _handle_knowledge_query(self, query: str, employee_id: Optional[int]) -> Dict[str, Any]:
        """Handle knowledge-based queries using RAG"""
        try:
            # Check if knowledge service is available
            if self.knowledge_service is None:
                return {
                    'success': False,
                    'intent': 'knowledge',
                    'response': 'Knowledge service is currently not available. Please contact HR for policy and procedure questions.',
                    'sources': [],
                    'data': None
                }
            
            # Use knowledge service for policy/procedure questions
            knowledge_response = self.knowledge_service.get_response(query)
            
            if knowledge_response.get('success'):
                return {
                    'success': True,
                    'intent': 'knowledge',
                    'response': knowledge_response['response'],
                    'sources': knowledge_response.get('sources', []),
                    'data': knowledge_response.get('context')
                }
            else:
                return {
                    'success': False,
                    'intent': 'knowledge',
                    'response': 'Maaf, saya tidak dapat menemukan informasi yang relevan untuk pertanyaan Anda. Silakan coba dengan kata kunci yang berbeda atau hubungi tim HR.',
                    'error': knowledge_response.get('error')
                }
        
        except Exception as e:
            logger.error(f"Error in knowledge query: {str(e)}")
            return {
                'success': False,
                'intent': 'knowledge',
                'response': 'Terjadi kesalahan dalam mencari informasi. Silakan coba lagi.',
                'error': str(e)
            }
    
    def _handle_data_query(self, query: str, employee_id: Optional[int]) -> Dict[str, Any]:
        """Handle data queries using HR orchestrator"""
        try:
            # Use HR orchestrator for data queries
            hr_response = self.hr_orchestrator.process_hr_query(query, employee_id)
            
            if hr_response.get('success'):
                # Generate natural language response from structured data
                natural_response = self._generate_natural_response(query, hr_response)
                
                return {
                    'success': True,
                    'intent': 'data_query',
                    'response': natural_response,
                    'data': hr_response.get('data'),
                    'structured_data': hr_response
                }
            else:
                return {
                    'success': False,
                    'intent': 'data_query',
                    'response': hr_response.get('error', 'Tidak dapat memproses permintaan data Anda.'),
                    'error': hr_response.get('error')
                }
        
        except Exception as e:
            logger.error(f"Error in data query: {str(e)}")
            return {
                'success': False,
                'intent': 'data_query',
                'response': 'Terjadi kesalahan dalam mengambil data. Silakan coba lagi.',
                'error': str(e)
            }
    
    def _handle_action_request(self, query: str, employee_id: Optional[int]) -> Dict[str, Any]:
        """Handle action requests (create, update, delete)"""
        # For now, return guidance message as actions require additional implementation
        return {
            'success': True,
            'intent': 'action',
            'response': 'Untuk melakukan tindakan seperti mengajukan cuti, mengupdate profil, atau membuat permintaan, silakan gunakan menu yang tersedia di sistem atau hubungi tim HR untuk bantuan.',
            'data': {
                'suggested_actions': [
                    'Gunakan menu Cuti untuk mengajukan cuti',
                    'Gunakan menu Profil untuk mengupdate informasi pribadi',
                    'Hubungi HR untuk permintaan khusus'
                ]
            }
        }
    
    def _handle_hybrid_query(self, query: str, employee_id: Optional[int]) -> Dict[str, Any]:
        """Handle queries that might need both knowledge and data"""
        try:
            # Try data query first
            data_response = self.hr_orchestrator.process_hr_query(query, employee_id)
            
            if data_response.get('success') and data_response.get('data'):
                # If we got data, generate natural response
                natural_response = self._generate_natural_response(query, data_response)
                
                return {
                    'success': True,
                    'intent': 'hybrid',
                    'response': natural_response,
                    'data': data_response.get('data'),
                    'structured_data': data_response
                }
            
            # If no data found, try knowledge base
            if self.knowledge_service is None:
                return {
                    'success': False,
                    'intent': 'hybrid',
                    'response': 'No relevant HR data found and knowledge service is not available.',
                    'data': None,
                    'structured_data': data_response
                }
            
            knowledge_response = self.knowledge_service.get_response(query)
            
            if knowledge_response.get('success'):
                return {
                    'success': True,
                    'intent': 'hybrid',
                    'response': knowledge_response['response'],
                    'sources': knowledge_response.get('sources', []),
                    'data': knowledge_response.get('context')
                }
            
            # If both fail, return helpful message
            return {
                'success': False,
                'intent': 'hybrid',
                'response': 'Maaf, saya tidak dapat menemukan informasi yang relevan untuk pertanyaan Anda. Silakan coba dengan kata kunci yang lebih spesifik atau hubungi tim HR untuk bantuan.',
                'suggestions': [
                    'Coba gunakan kata kunci yang lebih spesifik',
                    'Tanyakan tentang profil, cuti, kinerja, atau gaji',
                    'Hubungi tim HR untuk bantuan lebih lanjut'
                ]
            }
        
        except Exception as e:
            logger.error(f"Error in hybrid query: {str(e)}")
            return {
                'success': False,
                'intent': 'hybrid',
                'response': 'Terjadi kesalahan dalam memproses pertanyaan Anda. Silakan coba lagi.',
                'error': str(e)
            }
    
    def _generate_natural_response(self, query: str, hr_response: Dict[str, Any]) -> str:
        """Generate natural language response from structured HR data"""
        try:
            data = hr_response.get('data', {})
            query_lower = query.lower()
            
            # Employee profile responses
            if 'personal_info' in data or 'work_info' in data:
                return self._format_employee_profile_response(data)
            
            # Leave balance responses
            elif 'leave_balances' in data:
                return self._format_leave_balance_response(data)
            
            # Leave history responses
            elif 'leave_history' in data:
                return self._format_leave_history_response(data)
            
            # Payslip responses
            elif 'payslips' in data:
                return self._format_payslip_response(data)
            
            # Contract responses
            elif 'contract' in data:
                return self._format_contract_response(data)
            
            # Performance responses
            elif 'objectives' in data:
                return self._format_objectives_response(data)
            
            # General summary responses
            elif any(key in data for key in ['employee_summary', 'leave_summary', 'performance_summary', 'payroll_summary']):
                return self._format_general_summary_response(data)
            
            # Default response
            else:
                return "Berikut adalah informasi yang Anda minta. Jika Anda memerlukan detail lebih lanjut, silakan tanyakan."
        
        except Exception as e:
            logger.error(f"Error generating natural response: {str(e)}")
            return "Informasi telah ditemukan, namun terjadi kesalahan dalam memformat respons. Silakan coba lagi."
    
    def _format_employee_profile_response(self, data: Dict[str, Any]) -> str:
        """Format employee profile response"""
        if 'personal_info' in data and 'work_info' in data:
            personal = data['personal_info']
            work = data['work_info']
            
            response = f"Berikut adalah profil Anda:\n\n"
            response += f"**Informasi Pribadi:**\n"
            response += f"• Nama: {personal['name']}\n"
            response += f"• Email: {personal['email']}\n"
            if personal.get('phone'):
                response += f"• Telepon: {personal['phone']}\n"
            
            response += f"\n**Informasi Pekerjaan:**\n"
            response += f"• ID Karyawan: {work['employee_id']}\n"
            if work.get('department'):
                response += f"• Departemen: {work['department']}\n"
            if work.get('position'):
                response += f"• Posisi: {work['position']}\n"
            if work.get('manager'):
                response += f"• Manajer: {work['manager']}\n"
            if work.get('join_date'):
                response += f"• Tanggal Bergabung: {work['join_date']}\n"
            
            return response
        
        return "Informasi profil Anda telah ditemukan."
    
    def _format_leave_balance_response(self, data: Dict[str, Any]) -> str:
        """Format leave balance response"""
        balances = data.get('leave_balances', [])
        
        if not balances:
            return "Tidak ada informasi saldo cuti yang tersedia."
        
        response = "Berikut adalah saldo cuti Anda:\n\n"
        
        for balance in balances:
            response += f"**{balance['leave_type']}:**\n"
            response += f"• Saldo tersedia: {balance['available_days']} hari\n"
            if balance.get('carryforward_days', 0) > 0:
                response += f"• Saldo carry forward: {balance['carryforward_days']} hari\n"
            response += f"• Total: {balance['total_days']} hari\n\n"
        
        return response
    
    def _format_leave_history_response(self, data: Dict[str, Any]) -> str:
        """Format leave history response"""
        history = data.get('leave_history', [])
        
        if not history:
            return "Tidak ada riwayat cuti yang ditemukan."
        
        response = "Berikut adalah riwayat cuti Anda (10 terakhir):\n\n"
        
        for leave in history:
            response += f"**{leave['leave_type']}** ({leave['start_date']} - {leave['end_date']})\n"
            response += f"• Durasi: {leave['requested_days']} hari\n"
            response += f"• Status: {leave['status']}\n"
            if leave.get('description'):
                response += f"• Keterangan: {leave['description']}\n"
            response += "\n"
        
        return response
    
    def _format_payslip_response(self, data: Dict[str, Any]) -> str:
        """Format payslip response"""
        payslips = data.get('payslips', [])
        
        if not payslips:
            return "Tidak ada slip gaji yang ditemukan."
        
        response = "Berikut adalah slip gaji Anda (6 bulan terakhir):\n\n"
        
        for payslip in payslips:
            response += f"**Periode: {payslip['period']}**\n"
            response += f"• Gaji Pokok: Rp {payslip['basic_pay']:,.0f}\n"
            response += f"• Gaji Kotor: Rp {payslip['gross_pay']:,.0f}\n"
            response += f"• Potongan: Rp {payslip['deduction']:,.0f}\n"
            response += f"• Gaji Bersih: Rp {payslip['net_pay']:,.0f}\n"
            response += f"• Status: {payslip['status']}\n\n"
        
        return response
    
    def _format_contract_response(self, data: Dict[str, Any]) -> str:
        """Format contract response"""
        contract = data.get('contract', {})
        
        if not contract:
            return "Informasi kontrak tidak ditemukan."
        
        response = "Berikut adalah informasi kontrak Anda:\n\n"
        response += f"• Nama Kontrak: {contract['contract_name']}\n"
        response += f"• Periode: {contract['start_date']} - {contract.get('end_date', 'Tidak terbatas')}\n"
        response += f"• Gaji Pokok: Rp {contract['basic_salary']:,.0f} ({contract['wage_type']})\n"
        response += f"• Frekuensi Pembayaran: {contract['pay_frequency']}\n"
        
        if contract.get('department'):
            response += f"• Departemen: {contract['department']}\n"
        if contract.get('job_position'):
            response += f"• Posisi: {contract['job_position']}\n"
        
        response += f"• Masa Notice: {contract['notice_period']} hari\n"
        response += f"• Status: {contract['status']}\n"
        
        return response
    
    def _format_objectives_response(self, data: Dict[str, Any]) -> str:
        """Format objectives response"""
        objectives = data.get('objectives', [])
        
        if not objectives:
            return "Tidak ada objektif yang ditemukan."
        
        response = "Berikut adalah objektif Anda:\n\n"
        
        for obj in objectives:
            response += f"**{obj['title']}**\n"
            if obj.get('description'):
                response += f"• Deskripsi: {obj['description']}\n"
            response += f"• Status: {obj['status']}\n"
            response += f"• Progress: {obj['progress']}%\n"
            response += f"• Periode: {obj['start_date']} - {obj['end_date']}\n\n"
        
        return response
    
    def _format_general_summary_response(self, data: Dict[str, Any]) -> str:
        """Format general summary response"""
        response = "Berikut adalah ringkasan informasi HR Anda:\n\n"
        
        # Employee summary
        if 'employee_summary' in data:
            emp_data = data['employee_summary']
            response += f"**Informasi Karyawan:**\n"
            if 'name' in emp_data:
                response += f"• Nama: {emp_data['name']}\n"
            if 'department' in emp_data:
                response += f"• Departemen: {emp_data['department']}\n"
            response += "\n"
        
        # Leave summary
        if 'leave_summary' in data:
            leave_data = data['leave_summary']
            response += f"**Ringkasan Cuti:**\n"
            if 'pending_requests' in leave_data:
                response += f"• Permintaan pending: {leave_data['pending_requests']}\n"
            response += "\n"
        
        # Performance summary
        if 'performance_summary' in data:
            perf_data = data['performance_summary']
            response += f"**Ringkasan Kinerja:**\n"
            if 'completion_rate' in perf_data:
                response += f"• Tingkat penyelesaian objektif: {perf_data['completion_rate']:.1f}%\n"
            response += "\n"
        
        # Payroll summary
        if 'payroll_summary' in data:
            payroll_data = data['payroll_summary']
            response += f"**Ringkasan Gaji:**\n"
            if 'latest_payslip' in payroll_data:
                latest = payroll_data['latest_payslip']
                if latest.get('net_pay'):
                    response += f"• Gaji bersih terakhir: Rp {latest['net_pay']:,.0f}\n"
                if latest.get('period'):
                    response += f"• Periode: {latest['period']}\n"
        
        return response
    
    def get_hr_insights(self, user: User) -> Dict[str, Any]:
        """Get HR insights for user"""
        try:
            employee = self._get_employee_from_user(user)
            employee_id = employee.id if employee else None
            
            insights = self.hr_orchestrator.get_hr_insights(employee_id)
            
            if insights.get('success'):
                # Generate natural language insights
                natural_insights = self._format_insights_response(insights['data'])
                
                return {
                    'success': True,
                    'response': natural_insights,
                    'data': insights['data']
                }
            else:
                return {
                    'success': False,
                    'response': 'Tidak dapat mengambil insights HR saat ini.',
                    'error': insights.get('error')
                }
        
        except Exception as e:
            logger.error(f"Error getting HR insights: {str(e)}")
            return {
                'success': False,
                'response': 'Terjadi kesalahan dalam mengambil insights.',
                'error': str(e)
            }
    
    def _format_insights_response(self, data: Dict[str, Any]) -> str:
        """Format insights response"""
        insights = data.get('insights', [])
        
        if not insights:
            return "Tidak ada insights khusus saat ini. Semua terlihat baik!"
        
        response = "Berikut adalah insights HR untuk Anda:\n\n"
        
        for insight in insights:
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(insight.get('priority', 'low'), '🔵')
            
            response += f"{priority_emoji} **{insight['type'].title()}:** {insight['message']}\n\n"
        
        return response