import json
import requests
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
import asyncio
import aiohttp
from urllib.parse import urljoin

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
except ImportError:
    SentenceTransformer = None
    faiss = None
    np = None

# N8N integration using requests
logging.info("N8N integration configured to use requests API.")

from django.utils import timezone
from django.conf import settings

from .base import BaseAIService
from .config import AIConfig
from .exceptions import PredictionError, ExternalServiceError, ConfigurationError

logger = logging.getLogger(__name__)

class RAGN8NIntegrationService(BaseAIService):
    """
    AI Service untuk RAG (Retrieval-Augmented Generation) + N8N Integration.
    Mengotomatisasi workflow recruitment dengan kombinasi AI retrieval dan N8N automation.
    """
    
    def __init__(self):
        config = AIConfig.get_config('rag_n8n')
        super().__init__(config['MODEL_NAME'], '1.0')
        self.config = config
        
        # N8N Configuration
        self.n8n_base_url = config.get('N8N_BASE_URL', 'http://localhost:5678')
        self.n8n_api_key = config.get('N8N_API_KEY', '')
        self.n8n_webhook_url = config.get('N8N_WEBHOOK_URL', '')
        
        # Initialize N8N configuration
        self.n8n_headers = {
            'Content-Type': 'application/json',
            'X-N8N-API-KEY': self.n8n_api_key
        } if self.n8n_api_key else {'Content-Type': 'application/json'}
        
        # RAG Components
        self.embedding_model = None
        self.vector_index = None
        self.knowledge_base = []
        
        # Workflow Templates
        self.workflow_templates = {
            'candidate_screening': {
                'name': 'Candidate Screening Workflow',
                'description': 'Automated candidate screening and evaluation',
                'steps': ['resume_parsing', 'skill_matching', 'initial_scoring', 'notification']
            },
            'interview_scheduling': {
                'name': 'Interview Scheduling Workflow', 
                'description': 'Automated interview scheduling and coordination',
                'steps': ['availability_check', 'calendar_booking', 'notification_send', 'reminder_setup']
            },
            'onboarding_process': {
                'name': 'Employee Onboarding Workflow',
                'description': 'Automated new employee onboarding process',
                'steps': ['document_collection', 'account_creation', 'training_assignment', 'welcome_package']
            },
            'performance_review': {
                'name': 'Performance Review Workflow',
                'description': 'Automated performance review and feedback collection',
                'steps': ['review_initiation', 'feedback_collection', 'report_generation', 'meeting_scheduling']
            }
        }
        
        # Recruitment Knowledge Base
        self.recruitment_knowledge = [
            {
                'id': 'skill_requirements',
                'content': 'Technical skills required for software engineering positions include programming languages (Python, Java, JavaScript), frameworks (Django, React, Angular), databases (PostgreSQL, MongoDB), and version control (Git).',
                'category': 'technical_skills',
                'tags': ['programming', 'technical', 'requirements']
            },
            {
                'id': 'soft_skills',
                'content': 'Important soft skills for team collaboration include communication, problem-solving, teamwork, adaptability, time management, and leadership potential.',
                'category': 'soft_skills', 
                'tags': ['communication', 'teamwork', 'leadership']
            },
            {
                'id': 'interview_questions',
                'content': 'Standard interview questions should cover technical competency, problem-solving approach, past experience, cultural fit, and career goals.',
                'category': 'interview_process',
                'tags': ['interview', 'questions', 'evaluation']
            },
            {
                'id': 'evaluation_criteria',
                'content': 'Candidate evaluation should consider technical skills (40%), experience relevance (30%), cultural fit (20%), and growth potential (10%).',
                'category': 'evaluation',
                'tags': ['scoring', 'criteria', 'assessment']
            }
        ]
    
    def load_model(self) -> None:
        """
        Load RAG components dan initialize N8N connection.
        """
        try:
            # Load embedding model for RAG
            if SentenceTransformer is not None:
                model_name = self.config.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
                logger.info(f"Loading embedding model: {model_name}")
                self.embedding_model = SentenceTransformer(model_name)
                
                # Initialize vector index
                self._initialize_vector_index()
            else:
                logger.warning("SentenceTransformer not available, using fallback methods")
            
            # Test N8N connection
            self._test_n8n_connection()
            
            self.is_loaded = True
            logger.info("RAG + N8N Integration service loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load RAG + N8N service: {str(e)}")
            self.is_loaded = True  # Continue with limited functionality
    
    def _initialize_vector_index(self) -> None:
        """
        Initialize FAISS vector index untuk RAG.
        """
        try:
            if faiss is None or np is None:
                logger.warning("FAISS or NumPy not available, skipping vector index")
                return
            
            # Create embeddings untuk knowledge base
            if self.embedding_model and self.recruitment_knowledge:
                texts = [item['content'] for item in self.recruitment_knowledge]
                embeddings = self.embedding_model.encode(texts)
                
                # Create FAISS index
                dimension = embeddings.shape[1]
                self.vector_index = faiss.IndexFlatIP(dimension)  # Inner Product for similarity
                
                # Normalize embeddings untuk cosine similarity
                faiss.normalize_L2(embeddings)
                self.vector_index.add(embeddings.astype('float32'))
                
                logger.info(f"Vector index initialized with {len(texts)} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector index: {str(e)}")
    
    def _test_n8n_connection(self) -> bool:
        """
        Test connection ke N8N instance.
        """
        try:
            if not self.n8n_base_url:
                logger.warning("N8N base URL not configured")
                return False
            
            # Test basic connectivity
            health_url = urljoin(self.n8n_base_url, '/healthz')
            headers = {}
            
            if self.n8n_api_key:
                headers['Authorization'] = f'Bearer {self.n8n_api_key}'
            
            response = requests.get(health_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                logger.info("N8N connection successful")
                return True
            else:
                logger.warning(f"N8N connection failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"N8N connection test failed: {str(e)}")
            return False
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data untuk RAG + N8N processing.
        """
        if not isinstance(input_data, dict):
            return False
        
        # Check for required fields
        if 'action' not in input_data:
            return False
        
        valid_actions = [
            'query_knowledge', 'trigger_workflow', 'candidate_screening',
            'schedule_interview', 'start_onboarding', 'performance_review'
        ]
        
        if input_data['action'] not in valid_actions:
            return False
        
        return True
    
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process RAG + N8N requests berdasarkan action type.
        """
        try:
            action = input_data['action']
            
            if action == 'query_knowledge':
                return self._query_knowledge_base(input_data)
            elif action == 'trigger_workflow':
                return self._trigger_n8n_workflow(input_data)
            elif action == 'candidate_screening':
                return self._automated_candidate_screening(input_data)
            elif action == 'schedule_interview':
                return self._automated_interview_scheduling(input_data)
            elif action == 'start_onboarding':
                return self._automated_onboarding(input_data)
            elif action == 'performance_review':
                return self._automated_performance_review(input_data)
            else:
                raise ValueError(f"Unknown action: {action}")
                
        except Exception as e:
            raise PredictionError(f"RAG + N8N processing failed: {str(e)}", self.model_name, input_data)
    
    def _query_knowledge_base(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query knowledge base menggunakan RAG untuk mendapatkan informasi relevan.
        """
        try:
            query = input_data.get('query', '')
            top_k = input_data.get('top_k', 3)
            
            if not query:
                return {'error': 'Query is required'}
            
            # RAG-based retrieval
            if self.embedding_model and self.vector_index:
                relevant_docs = self._retrieve_relevant_documents(query, top_k)
            else:
                # Fallback to keyword-based search
                relevant_docs = self._keyword_based_search(query, top_k)
            
            # Generate response berdasarkan retrieved documents
            response = self._generate_rag_response(query, relevant_docs)
            
            return {
                'query': query,
                'response': response,
                'relevant_documents': relevant_docs,
                'method': 'rag' if self.embedding_model else 'keyword_search'
            }
            
        except Exception as e:
            logger.error(f"Knowledge base query failed: {str(e)}")
            return {'error': str(e)}
    
    def _retrieve_relevant_documents(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents menggunakan vector similarity.
        """
        try:
            if not self.embedding_model or not self.vector_index:
                return self._keyword_based_search(query, top_k)
            
            # Encode query
            query_embedding = self.embedding_model.encode([query])
            faiss.normalize_L2(query_embedding)
            
            # Search similar documents
            scores, indices = self.vector_index.search(query_embedding.astype('float32'), top_k)
            
            # Prepare results
            relevant_docs = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.recruitment_knowledge):
                    doc = self.recruitment_knowledge[idx].copy()
                    doc['similarity_score'] = float(score)
                    doc['rank'] = i + 1
                    relevant_docs.append(doc)
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Vector retrieval failed: {str(e)}")
            return self._keyword_based_search(query, top_k)
    
    def _keyword_based_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Fallback keyword-based search.
        """
        try:
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            # Score documents berdasarkan keyword matches
            scored_docs = []
            
            for doc in self.recruitment_knowledge:
                content_words = set(doc['content'].lower().split())
                tag_words = set(' '.join(doc.get('tags', [])).lower().split())
                
                # Calculate match score
                content_matches = len(query_words.intersection(content_words))
                tag_matches = len(query_words.intersection(tag_words)) * 2  # Weight tags higher
                
                total_score = content_matches + tag_matches
                
                if total_score > 0:
                    doc_copy = doc.copy()
                    doc_copy['similarity_score'] = total_score
                    scored_docs.append(doc_copy)
            
            # Sort by score dan return top_k
            scored_docs.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Add rank
            for i, doc in enumerate(scored_docs[:top_k]):
                doc['rank'] = i + 1
            
            return scored_docs[:top_k]
            
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return []
    
    def _generate_rag_response(self, query: str, relevant_docs: List[Dict[str, Any]]) -> str:
        """
        Generate response berdasarkan retrieved documents.
        """
        try:
            if not relevant_docs:
                return "I couldn't find relevant information for your query. Please try rephrasing or contact HR for assistance."
            
            # Combine information dari relevant documents
            context_parts = []
            
            for doc in relevant_docs:
                context_parts.append(f"• {doc['content']}")
            
            context = "\n".join(context_parts)
            
            # Generate structured response
            response = f"Based on the available information:\n\n{context}\n\n"
            
            # Add recommendations berdasarkan query type
            if any(word in query.lower() for word in ['skill', 'requirement', 'technical']):
                response += "For specific technical requirements, please consult with the technical team lead or review the detailed job description."
            elif any(word in query.lower() for word in ['interview', 'question']):
                response += "Remember to customize interview questions based on the specific role and candidate background."
            elif any(word in query.lower() for word in ['evaluation', 'scoring']):
                response += "Ensure all evaluations are documented and follow company guidelines for fair assessment."
            
            return response
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return "An error occurred while generating the response. Please try again."
    
    def _trigger_n8n_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Trigger N8N workflow dengan data yang diberikan.
        """
        try:
            workflow_name = input_data.get('workflow_name', '')
            workflow_data = input_data.get('data', {})
            
            if not workflow_name:
                return {'error': 'Workflow name is required'}
            
            # Prepare webhook payload
            payload = {
                'workflow': workflow_name,
                'data': workflow_data,
                'timestamp': datetime.now().isoformat(),
                'source': 'horilla_ai_service'
            }
            
            # Send to N8N webhook
            if self.n8n_webhook_url:
                response = self._send_n8n_webhook(payload)
                return {
                    'workflow_triggered': True,
                    'workflow_name': workflow_name,
                    'n8n_response': response,
                    'payload': payload
                }
            else:
                # Simulate workflow execution
                return self._simulate_workflow_execution(workflow_name, workflow_data)
                
        except Exception as e:
            logger.error(f"N8N workflow trigger failed: {str(e)}")
            return {'error': str(e)}
    
    def _send_n8n_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send data ke N8N webhook.
        """
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            if self.n8n_api_key:
                headers['Authorization'] = f'Bearer {self.n8n_api_key}'
            
            response = requests.post(
                self.n8n_webhook_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'response_data': response.json() if response.content else {},
                    'execution_id': response.headers.get('X-Execution-Id', 'unknown')
                }
            else:
                return {
                    'status': 'error',
                    'status_code': response.status_code,
                    'error_message': response.text
                }
                
        except Exception as e:
            logger.error(f"N8N webhook failed: {str(e)}")
            return {
                'status': 'error',
                'error_message': str(e)
            }
    
    def _simulate_workflow_execution(self, workflow_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate workflow execution ketika N8N tidak tersedia.
        """
        try:
            if workflow_name in self.workflow_templates:
                template = self.workflow_templates[workflow_name]
                
                # Simulate step execution
                executed_steps = []
                for step in template['steps']:
                    executed_steps.append({
                        'step': step,
                        'status': 'completed',
                        'timestamp': datetime.now().isoformat(),
                        'duration_ms': 100  # Simulated duration
                    })
                
                return {
                    'workflow_triggered': True,
                    'workflow_name': workflow_name,
                    'simulation': True,
                    'executed_steps': executed_steps,
                    'total_duration_ms': len(executed_steps) * 100,
                    'status': 'completed'
                }
            else:
                return {
                    'error': f'Unknown workflow template: {workflow_name}',
                    'available_workflows': list(self.workflow_templates.keys())
                }
                
        except Exception as e:
            logger.error(f"Workflow simulation failed: {str(e)}")
            return {'error': str(e)}
    
    def _automated_candidate_screening(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automated candidate screening menggunakan RAG + N8N.
        """
        try:
            candidate_data = input_data.get('candidate', {})
            position = input_data.get('position', '')
            
            # Step 1: Extract dan analyze resume
            resume_analysis = self._analyze_resume(candidate_data)
            
            # Step 2: Match skills dengan job requirements
            skill_match = self._match_skills_with_position(resume_analysis, position)
            
            # Step 3: Calculate initial score
            initial_score = self._calculate_candidate_score(resume_analysis, skill_match)
            
            # Step 4: Trigger N8N workflow untuk further processing
            workflow_data = {
                'candidate_id': candidate_data.get('id', ''),
                'resume_analysis': resume_analysis,
                'skill_match': skill_match,
                'initial_score': initial_score,
                'position': position
            }
            
            n8n_result = self._trigger_n8n_workflow({
                'workflow_name': 'candidate_screening',
                'data': workflow_data
            })
            
            return {
                'candidate_id': candidate_data.get('id', ''),
                'screening_result': {
                    'resume_analysis': resume_analysis,
                    'skill_match': skill_match,
                    'initial_score': initial_score,
                    'recommendation': self._get_screening_recommendation(initial_score)
                },
                'workflow_execution': n8n_result
            }
            
        except Exception as e:
            logger.error(f"Candidate screening failed: {str(e)}")
            return {'error': str(e)}
    
    def _analyze_resume(self, candidate_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze resume content untuk extract key information.
        """
        try:
            resume_text = candidate_data.get('resume_text', '')
            
            # Extract skills (simplified)
            technical_skills = self._extract_technical_skills(resume_text)
            soft_skills = self._extract_soft_skills(resume_text)
            
            # Extract experience
            experience_years = self._extract_experience_years(resume_text)
            
            # Extract education
            education = self._extract_education(resume_text)
            
            return {
                'technical_skills': technical_skills,
                'soft_skills': soft_skills,
                'experience_years': experience_years,
                'education': education,
                'resume_quality_score': self._assess_resume_quality(resume_text)
            }
            
        except Exception as e:
            logger.error(f"Resume analysis failed: {str(e)}")
            return {'error': str(e)}
    
    def _extract_technical_skills(self, resume_text: str) -> List[str]:
        """
        Extract technical skills dari resume text.
        """
        technical_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'django',
            'flask', 'nodejs', 'express', 'postgresql', 'mysql', 'mongodb',
            'redis', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'git',
            'jenkins', 'ci/cd', 'agile', 'scrum', 'rest', 'api', 'microservices'
        ]
        
        resume_lower = resume_text.lower()
        found_skills = [skill for skill in technical_keywords if skill in resume_lower]
        
        return found_skills
    
    def _extract_soft_skills(self, resume_text: str) -> List[str]:
        """
        Extract soft skills dari resume text.
        """
        soft_skill_keywords = [
            'leadership', 'communication', 'teamwork', 'problem solving',
            'analytical', 'creative', 'adaptable', 'organized', 'detail oriented'
        ]
        
        resume_lower = resume_text.lower()
        found_skills = [skill for skill in soft_skill_keywords if skill in resume_lower]
        
        return found_skills
    
    def _extract_experience_years(self, resume_text: str) -> int:
        """
        Extract years of experience dari resume text.
        """
        import re
        
        # Look for patterns like "5 years", "3+ years", etc.
        patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
            r'(\d+)\+?\s*years?\s*in',
            r'experience\s*:?\s*(\d+)\+?\s*years?'
        ]
        
        years = []
        for pattern in patterns:
            matches = re.findall(pattern, resume_text.lower())
            years.extend([int(match) for match in matches])
        
        return max(years) if years else 0
    
    def _extract_education(self, resume_text: str) -> List[str]:
        """
        Extract education information dari resume text.
        """
        education_keywords = [
            'bachelor', 'master', 'phd', 'diploma', 'degree',
            'computer science', 'software engineering', 'information technology'
        ]
        
        resume_lower = resume_text.lower()
        found_education = [edu for edu in education_keywords if edu in resume_lower]
        
        return found_education
    
    def _assess_resume_quality(self, resume_text: str) -> float:
        """
        Assess overall quality dari resume.
        """
        score = 0.0
        
        # Length check
        if 500 <= len(resume_text) <= 3000:
            score += 0.2
        
        # Structure indicators
        structure_keywords = ['experience', 'education', 'skills', 'projects']
        structure_score = sum(1 for keyword in structure_keywords if keyword in resume_text.lower())
        score += (structure_score / len(structure_keywords)) * 0.3
        
        # Contact information
        import re
        if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', resume_text):
            score += 0.2
        
        # Professional language
        professional_words = ['responsible', 'managed', 'developed', 'implemented', 'achieved']
        professional_score = sum(1 for word in professional_words if word in resume_text.lower())
        score += min(0.3, professional_score * 0.1)
        
        return min(1.0, score)
    
    def _match_skills_with_position(self, resume_analysis: Dict[str, Any], position: str) -> Dict[str, Any]:
        """
        Match candidate skills dengan position requirements.
        """
        # Simplified position requirements mapping
        position_requirements = {
            'software engineer': {
                'required_skills': ['python', 'javascript', 'git', 'api'],
                'preferred_skills': ['react', 'django', 'postgresql', 'docker'],
                'min_experience': 2
            },
            'senior developer': {
                'required_skills': ['python', 'javascript', 'git', 'api', 'leadership'],
                'preferred_skills': ['microservices', 'aws', 'ci/cd', 'mentoring'],
                'min_experience': 5
            },
            'data scientist': {
                'required_skills': ['python', 'sql', 'machine learning', 'statistics'],
                'preferred_skills': ['tensorflow', 'pytorch', 'aws', 'big data'],
                'min_experience': 3
            }
        }
        
        position_lower = position.lower()
        requirements = position_requirements.get(position_lower, {
            'required_skills': [],
            'preferred_skills': [],
            'min_experience': 0
        })
        
        candidate_skills = resume_analysis.get('technical_skills', [])
        candidate_experience = resume_analysis.get('experience_years', 0)
        
        # Calculate skill matches
        required_matches = len(set(candidate_skills).intersection(set(requirements['required_skills'])))
        preferred_matches = len(set(candidate_skills).intersection(set(requirements['preferred_skills'])))
        
        # Calculate match percentages
        required_percentage = (required_matches / len(requirements['required_skills'])) * 100 if requirements['required_skills'] else 100
        preferred_percentage = (preferred_matches / len(requirements['preferred_skills'])) * 100 if requirements['preferred_skills'] else 0
        
        # Experience match
        experience_match = candidate_experience >= requirements['min_experience']
        
        return {
            'required_skill_matches': required_matches,
            'required_skill_percentage': round(required_percentage, 2),
            'preferred_skill_matches': preferred_matches,
            'preferred_skill_percentage': round(preferred_percentage, 2),
            'experience_match': experience_match,
            'experience_gap': max(0, requirements['min_experience'] - candidate_experience)
        }
    
    def _calculate_candidate_score(self, resume_analysis: Dict[str, Any], skill_match: Dict[str, Any]) -> float:
        """
        Calculate overall candidate score.
        """
        score = 0.0
        
        # Resume quality (20%)
        score += resume_analysis.get('resume_quality_score', 0) * 0.2
        
        # Required skills (40%)
        score += (skill_match.get('required_skill_percentage', 0) / 100) * 0.4
        
        # Preferred skills (20%)
        score += (skill_match.get('preferred_skill_percentage', 0) / 100) * 0.2
        
        # Experience (20%)
        if skill_match.get('experience_match', False):
            score += 0.2
        else:
            # Partial credit berdasarkan experience gap
            gap = skill_match.get('experience_gap', 0)
            if gap <= 1:
                score += 0.15
            elif gap <= 2:
                score += 0.1
        
        return min(1.0, score)
    
    def _get_screening_recommendation(self, score: float) -> str:
        """
        Get recommendation berdasarkan candidate score.
        """
        if score >= 0.8:
            return 'Highly Recommended - Proceed to technical interview'
        elif score >= 0.6:
            return 'Recommended - Schedule phone screening'
        elif score >= 0.4:
            return 'Consider - Review manually before decision'
        else:
            return 'Not Recommended - Skills gap too significant'
    
    def _automated_interview_scheduling(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automated interview scheduling menggunakan N8N workflow.
        """
        try:
            candidate_id = input_data.get('candidate_id', '')
            interviewer_ids = input_data.get('interviewer_ids', [])
            preferred_dates = input_data.get('preferred_dates', [])
            
            workflow_data = {
                'candidate_id': candidate_id,
                'interviewer_ids': interviewer_ids,
                'preferred_dates': preferred_dates,
                'interview_type': input_data.get('interview_type', 'technical'),
                'duration_minutes': input_data.get('duration_minutes', 60)
            }
            
            # Trigger N8N workflow
            result = self._trigger_n8n_workflow({
                'workflow_name': 'interview_scheduling',
                'data': workflow_data
            })
            
            return {
                'scheduling_initiated': True,
                'candidate_id': candidate_id,
                'workflow_result': result
            }
            
        except Exception as e:
            logger.error(f"Interview scheduling failed: {str(e)}")
            return {'error': str(e)}
    
    def _automated_onboarding(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automated employee onboarding process.
        """
        try:
            employee_id = input_data.get('employee_id', '')
            department = input_data.get('department', '')
            position = input_data.get('position', '')
            start_date = input_data.get('start_date', '')
            
            workflow_data = {
                'employee_id': employee_id,
                'department': department,
                'position': position,
                'start_date': start_date,
                'onboarding_checklist': self._generate_onboarding_checklist(department, position)
            }
            
            # Trigger N8N workflow
            result = self._trigger_n8n_workflow({
                'workflow_name': 'onboarding_process',
                'data': workflow_data
            })
            
            return {
                'onboarding_initiated': True,
                'employee_id': employee_id,
                'checklist': workflow_data['onboarding_checklist'],
                'workflow_result': result
            }
            
        except Exception as e:
            logger.error(f"Onboarding automation failed: {str(e)}")
            return {'error': str(e)}
    
    def _generate_onboarding_checklist(self, department: str, position: str) -> List[Dict[str, Any]]:
        """
        Generate onboarding checklist berdasarkan department dan position.
        """
        base_checklist = [
            {'task': 'Complete HR documentation', 'priority': 'high', 'estimated_hours': 2},
            {'task': 'IT equipment setup', 'priority': 'high', 'estimated_hours': 1},
            {'task': 'Office tour and introductions', 'priority': 'medium', 'estimated_hours': 1},
            {'task': 'Company policies briefing', 'priority': 'high', 'estimated_hours': 1}
        ]
        
        # Add department-specific tasks
        if 'engineering' in department.lower() or 'developer' in position.lower():
            base_checklist.extend([
                {'task': 'Development environment setup', 'priority': 'high', 'estimated_hours': 4},
                {'task': 'Code repository access', 'priority': 'high', 'estimated_hours': 0.5},
                {'task': 'Technical architecture overview', 'priority': 'medium', 'estimated_hours': 2}
            ])
        
        if 'manager' in position.lower() or 'lead' in position.lower():
            base_checklist.extend([
                {'task': 'Team introduction meetings', 'priority': 'high', 'estimated_hours': 3},
                {'task': 'Management tools training', 'priority': 'medium', 'estimated_hours': 2}
            ])
        
        return base_checklist
    
    def _automated_performance_review(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automated performance review process.
        """
        try:
            employee_id = input_data.get('employee_id', '')
            review_period = input_data.get('review_period', '')
            reviewers = input_data.get('reviewers', [])
            
            workflow_data = {
                'employee_id': employee_id,
                'review_period': review_period,
                'reviewers': reviewers,
                'review_template': self._generate_review_template(),
                'deadline': input_data.get('deadline', '')
            }
            
            # Trigger N8N workflow
            result = self._trigger_n8n_workflow({
                'workflow_name': 'performance_review',
                'data': workflow_data
            })
            
            return {
                'review_initiated': True,
                'employee_id': employee_id,
                'review_template': workflow_data['review_template'],
                'workflow_result': result
            }
            
        except Exception as e:
            logger.error(f"Performance review automation failed: {str(e)}")
            return {'error': str(e)}
    
    def _generate_review_template(self) -> Dict[str, Any]:
        """
        Generate performance review template.
        """
        return {
            'sections': [
                {
                    'name': 'Goal Achievement',
                    'weight': 0.3,
                    'questions': [
                        'How well did the employee achieve their set goals?',
                        'What were the key accomplishments during this period?'
                    ]
                },
                {
                    'name': 'Technical Skills',
                    'weight': 0.25,
                    'questions': [
                        'How would you rate the employee\'s technical competency?',
                        'What technical areas need improvement?'
                    ]
                },
                {
                    'name': 'Collaboration',
                    'weight': 0.25,
                    'questions': [
                        'How effectively does the employee work with team members?',
                        'How do they contribute to team dynamics?'
                    ]
                },
                {
                    'name': 'Growth & Development',
                    'weight': 0.2,
                    'questions': [
                        'What learning and development activities has the employee engaged in?',
                        'What are their career development goals?'
                    ]
                }
            ],
            'rating_scale': {
                '5': 'Exceeds Expectations',
                '4': 'Meets Expectations',
                '3': 'Partially Meets Expectations',
                '2': 'Below Expectations',
                '1': 'Significantly Below Expectations'
            }
        }
    
    def get_available_workflows(self) -> Dict[str, Any]:
        """
        Get list of available workflow templates.
        """
        return {
            'workflow_templates': self.workflow_templates,
            'n8n_connected': self._test_n8n_connection(),
            'rag_enabled': self.embedding_model is not None
        }
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed information tentang RAG + N8N service.
        """
        info = super().get_model_info()
        
        info.update({
            'rag_enabled': self.embedding_model is not None,
            'vector_index_size': len(self.recruitment_knowledge),
            'n8n_configured': bool(self.n8n_base_url),
            'n8n_connected': self._test_n8n_connection(),
            'available_workflows': list(self.workflow_templates.keys()),
            'supported_actions': [
                'query_knowledge', 'trigger_workflow', 'candidate_screening',
                'schedule_interview', 'start_onboarding', 'performance_review'
            ]
        })
        
        return info