import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import requests
import json
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from .models import (
    KnowledgeDocument, ChatbotConversation, ChatbotMessage,
    DocumentCategory, DocumentTag
)
from ai_services.knowledge_ai import KnowledgeAIService
from helpdesk.models import FAQ

logger = logging.getLogger(__name__)


class ChatbotRAGService:
    """
    RAG (Retrieval-Augmented Generation) service untuk chatbot knowledge management.
    Mengintegrasikan pencarian dokumen dengan AI untuk memberikan jawaban yang akurat.
    """
    
    def __init__(self):
        self.knowledge_ai = None
        self.embedding_model = None
        self.ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.default_model = getattr(settings, 'OLLAMA_DEFAULT_MODEL', 'llama2')
        self.max_context_length = getattr(settings, 'CHATBOT_MAX_CONTEXT_LENGTH', 4000)
        self.similarity_threshold = getattr(settings, 'CHATBOT_SIMILARITY_THRESHOLD', 0.3)
        
        # Initialize services
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize AI services and embedding model"""
        try:
            # Initialize KnowledgeAI service
            self.knowledge_ai = KnowledgeAIService()
            
            # Initialize embedding model for semantic search
            try:
                self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Embedding model initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize embedding model: {e}")
                self.embedding_model = None
                
        except Exception as e:
            logger.error(f"Failed to initialize chatbot services: {e}")
    
    def retrieve_relevant_documents(self, query: str, user: User, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve dokumen yang relevan berdasarkan query menggunakan multiple strategies.
        """
        try:
            relevant_docs = []
            
            # Strategy 1: FAQ search - prioritize FAQ results
            faq_results = self._faq_search(query, user, max_results)
            relevant_docs.extend(faq_results)
            
            # Strategy 2: Semantic search using KnowledgeAI if available
            if self.knowledge_ai and len(relevant_docs) < max_results:
                try:
                    ai_results = self.knowledge_ai.search_documents(query, max_results=max_results - len(relevant_docs))
                    for doc_data in ai_results:
                        if 'document_id' in doc_data:
                            try:
                                doc = KnowledgeDocument.objects.get(
                                    id=doc_data['document_id'],
                                    status='published'
                                )
                                if self._user_can_access_document(user, doc):
                                    relevant_docs.append({
                                        'document': doc,
                                        'similarity_score': doc_data.get('similarity_score', 0.0),
                                        'snippet': doc_data.get('snippet', ''),
                                        'method': 'ai_semantic'
                                    })
                            except KnowledgeDocument.DoesNotExist:
                                continue
                except Exception as e:
                    logger.warning(f"AI search failed, falling back to traditional search: {e}")
            
            # Strategy 3: Traditional keyword search if needed
            if len(relevant_docs) < max_results:
                keyword_results = self._keyword_search(query, user, max_results - len(relevant_docs))
                
                # Avoid duplicates
                existing_doc_ids = {doc['document'].id for doc in relevant_docs if 'document' in doc}
                for doc_data in keyword_results:
                    if doc_data['document'].id not in existing_doc_ids:
                        relevant_docs.append(doc_data)
            
            # Strategy 4: Embedding-based search if available
            if self.embedding_model and len(relevant_docs) < max_results:
                embedding_results = self._embedding_search(query, user, max_results - len(relevant_docs))
                
                existing_doc_ids = {doc['document'].id for doc in relevant_docs if 'document' in doc}
                for doc_data in embedding_results:
                    if doc_data['document'].id not in existing_doc_ids:
                        relevant_docs.append(doc_data)
            
            # Sort by similarity score and return top results
            relevant_docs.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            return relevant_docs[:max_results]
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return []
    
    def _keyword_search(self, query: str, user: User, max_results: int) -> List[Dict[str, Any]]:
        """Traditional keyword-based search"""
        try:
            # Build search query
            search_terms = query.lower().split()
            q_objects = Q()
            
            for term in search_terms:
                q_objects |= (
                    Q(title__icontains=term) |
                    Q(description__icontains=term) |
                    Q(content__icontains=term) |
                    Q(ai_extracted_keywords__icontains=term)
                )
            
            # Get documents
            documents = KnowledgeDocument.objects.filter(
                q_objects,
                status='published'
            ).select_related('category', 'created_by')[:max_results * 2]
            
            results = []
            for doc in documents:
                if self._user_can_access_document(user, doc):
                    # Calculate simple relevance score
                    score = self._calculate_keyword_relevance(query, doc)
                    if score > 0:
                        results.append({
                            'document': doc,
                            'similarity_score': score,
                            'snippet': self._extract_snippet(query, doc),
                            'method': 'keyword'
                        })
            
            return sorted(results, key=lambda x: x['similarity_score'], reverse=True)[:max_results]
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _faq_search(self, query: str, user: User, max_results: int) -> List[Dict[str, Any]]:
        """Search in helpdesk FAQ"""
        try:
            # Build search query for FAQ
            search_terms = query.lower().split()
            q_objects = Q()
            
            for term in search_terms:
                q_objects |= (
                    Q(question__icontains=term) |
                    Q(answer__icontains=term)
                )
            
            # Get FAQ entries
            faqs = FAQ.objects.filter(
                q_objects,
                is_active=True
            ).select_related('category')[:max_results * 2]
            
            results = []
            for faq in faqs:
                # Calculate simple relevance score
                score = self._calculate_faq_relevance(query, faq)
                if score > 0:
                    results.append({
                        'faq': faq,
                        'similarity_score': score,
                        'snippet': faq.answer[:200] + '...' if len(faq.answer) > 200 else faq.answer,
                        'method': 'faq_search',
                        'type': 'faq'
                    })
            
            return sorted(results, key=lambda x: x['similarity_score'], reverse=True)[:max_results]
            
        except Exception as e:
            logger.error(f"FAQ search failed: {e}")
            return []
    
    def _calculate_faq_relevance(self, query: str, faq: FAQ) -> float:
        """Calculate keyword-based relevance score for FAQ"""
        try:
            query_terms = set(query.lower().split())
            if not query_terms:
                return 0.0
            
            # Text to search in
            searchable_text = f"{faq.question} {faq.answer}".lower()
            
            # Count matches
            matches = 0
            for term in query_terms:
                if term in searchable_text:
                    matches += searchable_text.count(term)
            
            # Normalize by query length
            return min(matches / len(query_terms), 1.0)
            
        except Exception as e:
            logger.error(f"FAQ relevance calculation failed: {e}")
            return 0.0
    
    def _embedding_search(self, query: str, user: User, max_results: int) -> List[Dict[str, Any]]:
        """Embedding-based semantic search"""
        try:
            if not self.embedding_model:
                return []
            
            # Get all accessible documents
            documents = KnowledgeDocument.objects.filter(
                status='published'
            ).select_related('category', 'created_by')
            
            # Filter by user access
            accessible_docs = [doc for doc in documents if self._user_can_access_document(user, doc)]
            
            if not accessible_docs:
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Generate document embeddings
            doc_texts = []
            for doc in accessible_docs:
                text = f"{doc.title} {doc.description} {doc.content[:500]}"
                doc_texts.append(text)
            
            if not doc_texts:
                return []
            
            doc_embeddings = self.embedding_model.encode(doc_texts)
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            
            # Create results
            results = []
            for i, (doc, similarity) in enumerate(zip(accessible_docs, similarities)):
                if similarity >= self.similarity_threshold:
                    results.append({
                        'document': doc,
                        'similarity_score': float(similarity),
                        'snippet': self._extract_snippet(query, doc),
                        'method': 'embedding'
                    })
            
            return sorted(results, key=lambda x: x['similarity_score'], reverse=True)[:max_results]
            
        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []
    
    def _user_can_access_document(self, user: User, document: KnowledgeDocument) -> bool:
        """Check if user can access the document"""
        try:
            # Public documents are accessible to all
            if document.visibility == 'public':
                return True
            
            # Department-only documents
            if document.visibility == 'department':
                if hasattr(user, 'employee') and user.employee.department == document.department:
                    return True
            
            # Restricted documents
            if document.visibility == 'restricted':
                if document.allowed_users.filter(id=user.id).exists():
                    return True
            
            # Document creator can always access
            if document.created_by == user:
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Access check failed: {e}")
            return False
    
    def _calculate_keyword_relevance(self, query: str, document: KnowledgeDocument) -> float:
        """Calculate keyword-based relevance score"""
        try:
            query_terms = set(query.lower().split())
            if not query_terms:
                return 0.0
            
            # Text to search in
            searchable_text = f"{document.title} {document.description} {document.content}".lower()
            
            # Count matches
            matches = 0
            for term in query_terms:
                if term in searchable_text:
                    matches += searchable_text.count(term)
            
            # Normalize by query length
            return min(matches / len(query_terms), 1.0)
            
        except Exception as e:
            logger.error(f"Relevance calculation failed: {e}")
            return 0.0
    
    def _extract_snippet(self, query: str, document: KnowledgeDocument, max_length: int = 200) -> str:
        """Extract relevant snippet from document"""
        try:
            query_terms = query.lower().split()
            content = document.content.lower()
            
            # Find first occurrence of any query term
            best_pos = len(content)
            for term in query_terms:
                pos = content.find(term)
                if pos != -1 and pos < best_pos:
                    best_pos = pos
            
            if best_pos == len(content):
                # No terms found, return beginning of content
                snippet = document.content[:max_length]
            else:
                # Extract around the found term
                start = max(0, best_pos - max_length // 2)
                end = min(len(document.content), start + max_length)
                snippet = document.content[start:end]
            
            return snippet.strip()
            
        except Exception as e:
            logger.error(f"Snippet extraction failed: {e}")
            return document.description[:max_length] if document.description else ""
    
    def generate_response(self, query: str, relevant_docs: List[Dict[str, Any]], 
                         conversation: ChatbotConversation) -> Dict[str, Any]:
        """Generate AI response using retrieved documents as context"""
        try:
            start_time = time.time()
            
            # Build context from relevant documents and FAQs
            context_parts = []
            referenced_docs = []
            referenced_faqs = []
            
            for doc_data in relevant_docs:
                if doc_data.get('type') == 'faq':
                    # Handle FAQ results
                    faq = doc_data['faq']
                    snippet = doc_data.get('snippet', '')
                    
                    context_part = f"FAQ: {faq.question}\n"
                    context_part += f"Answer: {faq.answer}\n"
                    context_part += f"Category: {faq.category.title}\n\n"
                    
                    context_parts.append(context_part)
                    referenced_faqs.append(faq)
                else:
                    # Handle document results
                    doc = doc_data['document']
                    snippet = doc_data.get('snippet', '')
                    
                    context_part = f"Document: {doc.title}\n"
                    if doc.description:
                        context_part += f"Description: {doc.description}\n"
                    if snippet:
                        context_part += f"Content: {snippet}\n"
                    context_part += f"Category: {doc.category.name}\n\n"
                    
                    context_parts.append(context_part)
                    referenced_docs.append(doc)
            
            # Limit context length
            context = "".join(context_parts)[:self.max_context_length]
            
            # Build prompt
            prompt = self._build_prompt(query, context, conversation)
            
            # Generate response using Ollama
            response_data = self._call_ollama(prompt)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'response': response_data.get('response', 'Maaf, saya tidak dapat memberikan jawaban saat ini.'),
                'confidence_score': response_data.get('confidence', 0.8),
                'processing_time': processing_time,
                'referenced_documents': referenced_docs,
                'referenced_faqs': referenced_faqs,
                'context_used': len(context),
                'model_used': response_data.get('model', self.default_model)
            }
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                'success': False,
                'response': 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda. Silakan coba lagi.',
                'error': str(e)
            }
    
    def _build_prompt(self, query: str, context: str, conversation: ChatbotConversation) -> str:
        """Build prompt for AI model"""
        # Get recent conversation history for context
        recent_messages = conversation.messages.filter(
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).order_by('created_at')[:10]
        
        conversation_history = ""
        for msg in recent_messages:
            role = "User" if msg.sender == 'user' else "Assistant"
            conversation_history += f"{role}: {msg.content}\n"
        
        prompt = f"""Anda adalah asisten AI untuk sistem HR Horilla yang membantu karyawan dengan pertanyaan seputar kebijakan dan prosedur perusahaan.

Informasi yang tersedia:
{context}

Riwayat percakapan:
{conversation_history}

Pertanyaan: {query}

PETUNJUK PENTING:
1. Berikan jawaban yang SPESIFIK dan LANGSUNG berdasarkan informasi FAQ atau dokumen yang tersedia
2. Jika ada FAQ yang relevan, gunakan jawaban dari FAQ tersebut sebagai dasar respons
3. Gunakan bahasa Indonesia yang jelas dan mudah dipahami
4. Berikan langkah-langkah konkret jika pertanyaan tentang cara melakukan sesuatu
5. Jika informasi tidak tersedia, katakan dengan jelas dan sarankan untuk menghubungi HR

Jawaban (dalam bahasa Indonesia yang jelas):"""
        
        return prompt
    
    def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API for response generation"""
        try:
            url = f"{self.ollama_base_url}/api/generate"
            payload = {
                "model": self.default_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 1000
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return {
                'response': result.get('response', ''),
                'model': result.get('model', self.default_model),
                'confidence': 0.8  # Default confidence
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama API call failed: {e}")
            # Fallback: Generate response based on FAQ context
            return self._generate_fallback_response(prompt)
        except Exception as e:
            logger.error(f"Unexpected error in Ollama call: {e}")
            return self._generate_fallback_response(prompt)
    
    def _generate_fallback_response(self, prompt: str) -> Dict[str, Any]:
        """Generate fallback response when Ollama is not available"""
        try:
            # Extract FAQ information from prompt
            if "FAQ:" in prompt:
                # Find the first FAQ in the context
                lines = prompt.split('\n')
                faq_answer = None
                for i, line in enumerate(lines):
                    if line.startswith("FAQ:"):
                        # Look for the answer in the next few lines
                        for j in range(i+1, min(i+4, len(lines))):
                            if lines[j].startswith("Answer:"):
                                faq_answer = lines[j].replace("Answer:", "").strip()
                                break
                        break
                
                if faq_answer:
                    return {
                        'response': f"Berdasarkan FAQ yang tersedia: {faq_answer}",
                        'model': 'faq_fallback',
                        'confidence': 0.7
                    }
            
            # Default fallback
            return {
                'response': 'Maaf, saya tidak dapat memberikan jawaban yang spesifik saat ini. Silakan hubungi tim HR untuk bantuan lebih lanjut.',
                'model': 'fallback',
                'confidence': 0.3
            }
            
        except Exception as e:
            logger.error(f"Fallback response generation failed: {e}")
            return {
                'response': 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda.',
                'model': 'error',
                'confidence': 0.1
            }
    
    def create_conversation(self, user: User, initial_query: str = None) -> ChatbotConversation:
        """Create new chatbot conversation"""
        try:
            conversation = ChatbotConversation.objects.create(
                user=user,
                title=initial_query[:50] + '...' if initial_query and len(initial_query) > 50 else initial_query or '',
                session_metadata={
                    'created_via': 'chatbot_service',
                    'initial_query': initial_query
                }
            )
            
            logger.info(f"Created new conversation {conversation.conversation_id} for user {user.username}")
            return conversation
            
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            raise
    
    def add_message(self, conversation: ChatbotConversation, sender: str, content: str, 
                   message_type: str = 'text', **kwargs) -> ChatbotMessage:
        """Add message to conversation"""
        try:
            message = ChatbotMessage.objects.create(
                conversation=conversation,
                sender=sender,
                message_type=message_type,
                content=content,
                **kwargs
            )
            
            # Update conversation last activity
            conversation.last_activity = timezone.now()
            conversation.save()
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise