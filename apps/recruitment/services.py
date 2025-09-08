from typing import Dict, List, Any, Optional
import json
import requests
import logging
from datetime import datetime
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from celery import shared_task
import chromadb
from chromadb.config import Settings as ChromaSettings

from knowledge.utils import OllamaIntegration, DocumentProcessor
from .models import Candidate, Recruitment, Stage
from indonesian_nlp.client import IndonesianNLPClient

logger = logging.getLogger(__name__)


class N8NClient:
    """Client for N8N workflow automation"""
    
    def __init__(self, base_url: str = None, auth_token: str = None):
        self.base_url = base_url or getattr(settings, 'N8N_BASE_URL', 'http://localhost:5678')
        self.auth_token = auth_token or getattr(settings, 'N8N_AUTH_TOKEN', None)
        self.session = requests.Session()
        
        if self.auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}',
                'Content-Type': 'application/json'
            })
    
    def is_available(self) -> bool:
        """Check if N8N service is available"""
        try:
            response = self.session.get(f"{self.base_url}/healthz", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"N8N service not available: {str(e)}")
            return False
    
    async def trigger_workflow(self, workflow_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Trigger N8N workflow with data"""
        try:
            url = f"{self.base_url}/webhook/{workflow_id}"
            response = self.session.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                return {
                    'status': 'success',
                    'execution_id': response.json().get('executionId'),
                    'data': response.json()
                }
            else:
                logger.error(f"N8N workflow trigger failed: {response.status_code} - {response.text}")
                return {
                    'status': 'error',
                    'message': f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            logger.error(f"Error triggering N8N workflow {workflow_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        try:
            url = f"{self.base_url}/api/v1/executions/{execution_id}"
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'status': 'error',
                    'message': f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            logger.error(f"Error getting workflow status {execution_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


class RecruitmentRAGService:
    """RAG (Retrieval-Augmented Generation) service for recruitment"""
    
    def __init__(self):
        self.chroma_client = chromadb.Client(ChromaSettings(
            persist_directory=getattr(settings, 'CHROMA_PERSIST_DIR', './chroma_db')
        ))
        self.ollama_service = OllamaIntegration()
        self.n8n_client = N8NClient()
        self.nlp_client = IndonesianNLPClient()
        self.doc_processor = DocumentProcessor()
        
        # Initialize collections
        self.resume_collection = self._get_or_create_collection('resumes')
        self.job_collection = self._get_or_create_collection('job_descriptions')
    
    def _get_or_create_collection(self, name: str):
        """Get or create ChromaDB collection"""
        try:
            return self.chroma_client.get_collection(name)
        except Exception:
            return self.chroma_client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
    
    async def analyze_resume(self, candidate_id: int, job_description: str = None) -> Dict[str, Any]:
        """Analyze candidate resume against job requirements"""
        try:
            candidate = Candidate.objects.get(id=candidate_id)
            
            # Extract resume text
            if candidate.resume:
                resume_text = self.doc_processor.extract_text_from_file(candidate.resume.path)
            else:
                resume_text = f"Name: {candidate.name}\nEmail: {candidate.email}\nMobile: {candidate.mobile}"
            
            # Get job description
            if not job_description and candidate.recruitment_id:
                job_description = candidate.recruitment_id.description or ""
            
            # Perform NLP analysis
            sentiment_result = await self._analyze_sentiment(resume_text)
            entities = await self._extract_entities(resume_text)
            keywords = self.doc_processor.extract_keywords(resume_text)
            
            # Calculate similarity score
            similarity_score = await self._calculate_similarity(resume_text, job_description)
            
            # Generate AI analysis
            analysis = await self._generate_analysis(resume_text, job_description, candidate)
            
            # Store in vector database
            await self._store_resume_embedding(candidate_id, resume_text)
            
            result = {
                'candidate_id': candidate_id,
                'similarity_score': similarity_score,
                'sentiment': sentiment_result,
                'entities': entities,
                'keywords': keywords,
                'analysis': analysis,
                'recommendation': self._get_recommendation(similarity_score, sentiment_result),
                'processed_at': timezone.now().isoformat()
            }
            
            # Cache result
            cache.set(f"resume_analysis_{candidate_id}", result, timeout=3600)
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing resume for candidate {candidate_id}: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze text sentiment using Indonesian NLP"""
        try:
            result = await self.nlp_client.analyze_sentiment(text)
            return result
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {str(e)}")
            return {'label': 'NEUTRAL', 'score': 0.5}
    
    async def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract named entities from text"""
        try:
            result = await self.nlp_client.extract_entities(text)
            return result
        except Exception as e:
            logger.warning(f"Entity extraction failed: {str(e)}")
            return []
    
    async def _calculate_similarity(self, resume_text: str, job_description: str) -> float:
        """Calculate similarity between resume and job description"""
        if not job_description:
            return 0.0
        
        try:
            # Use TF-IDF similarity as fallback
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform([resume_text, job_description])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
        except Exception as e:
            logger.warning(f"Similarity calculation failed: {str(e)}")
            return 0.0
    
    async def _generate_analysis(self, resume_text: str, job_description: str, candidate) -> str:
        """Generate AI-powered analysis"""
        if not self.ollama_service.is_available():
            return "AI analysis not available - Ollama service offline"
        
        try:
            prompt = f"""
            Analyze this candidate's resume against the job requirements:
            
            CANDIDATE INFORMATION:
            Name: {candidate.name}
            Email: {candidate.email}
            
            RESUME CONTENT:
            {resume_text[:2000]}  # Limit text length
            
            JOB DESCRIPTION:
            {job_description[:1000] if job_description else 'No job description provided'}
            
            Please provide a detailed analysis in Indonesian including:
            1. Kesesuaian keahlian (Skills match)
            2. Relevansi pengalaman (Experience relevance)
            3. Kualifikasi pendidikan (Education qualification)
            4. Kekuatan kandidat (Candidate strengths)
            5. Area yang perlu dikembangkan (Areas for improvement)
            6. Rekomendasi keputusan (Decision recommendation)
            
            Format response dalam bahasa Indonesia yang profesional.
            """
            
            analysis = await self.ollama_service.generate_summary(prompt, max_length=500)
            return analysis
            
        except Exception as e:
            logger.warning(f"AI analysis generation failed: {str(e)}")
            return "Analisis AI tidak tersedia saat ini. Silakan lakukan review manual."
    
    async def _store_resume_embedding(self, candidate_id: int, resume_text: str):
        """Store resume embedding in vector database"""
        try:
            # Generate embedding (simplified - in production use proper embedding model)
            embedding = self._generate_simple_embedding(resume_text)
            
            self.resume_collection.upsert(
                ids=[str(candidate_id)],
                documents=[resume_text[:1000]],  # Limit document size
                embeddings=[embedding],
                metadatas=[{
                    'candidate_id': candidate_id,
                    'created_at': timezone.now().isoformat()
                }]
            )
        except Exception as e:
            logger.warning(f"Failed to store resume embedding: {str(e)}")
    
    def _generate_simple_embedding(self, text: str) -> List[float]:
        """Generate simple embedding (placeholder for proper embedding model)"""
        # This is a simplified embedding - in production use proper models
        from sklearn.feature_extraction.text import TfidfVectorizer
        import numpy as np
        
        try:
            vectorizer = TfidfVectorizer(max_features=384, stop_words='english')
            tfidf_matrix = vectorizer.fit_transform([text])
            embedding = tfidf_matrix.toarray()[0].tolist()
            
            # Pad or truncate to fixed size
            if len(embedding) < 384:
                embedding.extend([0.0] * (384 - len(embedding)))
            else:
                embedding = embedding[:384]
                
            return embedding
        except Exception:
            # Return zero vector as fallback
            return [0.0] * 384
    
    def _get_recommendation(self, similarity_score: float, sentiment_result: Dict) -> str:
        """Get hiring recommendation based on analysis"""
        sentiment_score = sentiment_result.get('score', 0.5)
        
        if similarity_score >= 0.8 and sentiment_score >= 0.7:
            return "HIGHLY_RECOMMENDED"
        elif similarity_score >= 0.6 and sentiment_score >= 0.6:
            return "RECOMMENDED"
        elif similarity_score >= 0.4:
            return "REVIEW_REQUIRED"
        else:
            return "NOT_RECOMMENDED"
    
    async def trigger_recruitment_workflow(self, candidate_id: int, workflow_type: str) -> Dict[str, Any]:
        """Trigger N8N recruitment workflow"""
        try:
            candidate = Candidate.objects.get(id=candidate_id)
            
            # Get analysis data
            analysis_data = cache.get(f"resume_analysis_{candidate_id}")
            if not analysis_data:
                analysis_data = await self.analyze_resume(candidate_id)
            
            # Prepare workflow data
            workflow_data = {
                'candidate': {
                    'id': candidate.id,
                    'name': candidate.name,
                    'email': candidate.email,
                    'mobile': candidate.mobile,
                    'stage': candidate.stage_id.stage if candidate.stage_id else None
                },
                'recruitment': {
                    'id': candidate.recruitment_id.id if candidate.recruitment_id else None,
                    'title': candidate.recruitment_id.title if candidate.recruitment_id else None
                },
                'analysis': analysis_data,
                'workflow_type': workflow_type,
                'timestamp': timezone.now().isoformat()
            }
            
            # Trigger appropriate workflow
            workflow_id = self._get_workflow_id(workflow_type)
            result = await self.n8n_client.trigger_workflow(workflow_id, workflow_data)
            
            return result
            
        except Exception as e:
            logger.error(f"Error triggering recruitment workflow: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _get_workflow_id(self, workflow_type: str) -> str:
        """Get N8N workflow ID based on type"""
        workflow_mapping = {
            'resume_screening': 'resume-screening-workflow',
            'interview_scheduling': 'interview-scheduling-workflow',
            'candidate_notification': 'candidate-notification-workflow',
            'hiring_decision': 'hiring-decision-workflow',
            'onboarding_trigger': 'onboarding-trigger-workflow'
        }
        
        return workflow_mapping.get(workflow_type, 'default-recruitment-workflow')
    
    def find_similar_candidates(self, job_description: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find candidates similar to job requirements"""
        try:
            # Generate job description embedding
            job_embedding = self._generate_simple_embedding(job_description)
            
            # Query similar resumes
            results = self.resume_collection.query(
                query_embeddings=[job_embedding],
                n_results=limit
            )
            
            similar_candidates = []
            for i, candidate_id in enumerate(results['ids'][0]):
                try:
                    candidate = Candidate.objects.get(id=int(candidate_id))
                    similar_candidates.append({
                        'candidate': {
                            'id': candidate.id,
                            'name': candidate.name,
                            'email': candidate.email,
                            'stage': candidate.stage_id.stage if candidate.stage_id else None
                        },
                        'similarity_score': results['distances'][0][i] if results['distances'] else 0.0,
                        'document': results['documents'][0][i] if results['documents'] else ""
                    })
                except Candidate.DoesNotExist:
                    continue
            
            return similar_candidates
            
        except Exception as e:
            logger.error(f"Error finding similar candidates: {str(e)}")
            return []


# Celery tasks for async processing
@shared_task
def process_candidate_analysis(candidate_id: int):
    """Async task to process candidate analysis"""
    try:
        rag_service = RecruitmentRAGService()
        result = rag_service.analyze_resume(candidate_id)
        
        # Store result in database or cache
        cache.set(f"resume_analysis_{candidate_id}", result, timeout=86400)  # 24 hours
        
        return result
    except Exception as e:
        logger.error(f"Error in candidate analysis task: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def trigger_recruitment_workflow_task(candidate_id: int, workflow_type: str):
    """Async task to trigger recruitment workflow"""
    try:
        rag_service = RecruitmentRAGService()
        result = rag_service.trigger_recruitment_workflow(candidate_id, workflow_type)
        return result
    except Exception as e:
        logger.error(f"Error in workflow trigger task: {str(e)}")
        return {'status': 'error', 'message': str(e)}


@shared_task
def batch_analyze_candidates(candidate_ids: List[int]):
    """Batch process multiple candidates"""
    results = []
    rag_service = RecruitmentRAGService()
    
    for candidate_id in candidate_ids:
        try:
            result = rag_service.analyze_resume(candidate_id)
            results.append(result)
        except Exception as e:
            logger.error(f"Error analyzing candidate {candidate_id}: {str(e)}")
            results.append({
                'candidate_id': candidate_id,
                'status': 'error',
                'message': str(e)
            })
    
    return results