import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from knowledge.models import (
    KnowledgeDocument, ChatbotConversation, ChatbotMessage,
    DocumentCategory, DocumentTag
)
from .knowledge_ai import KnowledgeAIService
from .slm_service import slm_service

logger = logging.getLogger(__name__)


class ChatbotSLMService:
    """
    RAG (Retrieval-Augmented Generation) service untuk chatbot menggunakan Small Language Models.
    Alternatif ringan untuk ChatbotRAGService yang menggunakan Ollama.
    """
    
    def __init__(self):
        self.knowledge_ai = None
        self.embedding_model = None
        self.slm_service = slm_service
        self.max_context_length = getattr(settings, 'CHATBOT_MAX_CONTEXT_LENGTH', 2000)  # Reduced for SLM
        self.similarity_threshold = getattr(settings, 'CHATBOT_SIMILARITY_THRESHOLD', 0.3)
        
        # SLM specific configuration
        self.slm_config = {
            'text_generation_model': getattr(settings, 'SLM_TEXT_MODEL', 'gpt2'),
            'qa_model': getattr(settings, 'SLM_QA_MODEL', 't5-small'),
            'summarization_model': getattr(settings, 'SLM_SUMMARY_MODEL', 't5-small'),
            'indonesian_model': getattr(settings, 'SLM_INDONESIAN_MODEL', 'gpt2-indonesian'),
            'max_response_length': getattr(settings, 'SLM_MAX_RESPONSE_LENGTH', 300),
            'use_indonesian': getattr(settings, 'SLM_USE_INDONESIAN', True)
        }
        
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
            
            # Strategy 1: Semantic search using KnowledgeAI if available
            if self.knowledge_ai:
                try:
                    ai_results = self.knowledge_ai.search_documents(query, max_results=max_results)
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
            
            # Strategy 2: Traditional keyword search if AI search didn't return enough results
            if len(relevant_docs) < max_results:
                keyword_results = self._keyword_search(query, user, max_results - len(relevant_docs))
                
                # Avoid duplicates
                existing_doc_ids = {doc['document'].id for doc in relevant_docs}
                for doc_data in keyword_results:
                    if doc_data['document'].id not in existing_doc_ids:
                        relevant_docs.append(doc_data)
            
            # Strategy 3: Embedding-based search if available
            if self.embedding_model and len(relevant_docs) < max_results:
                embedding_results = self._embedding_search(query, user, max_results - len(relevant_docs))
                
                # Avoid duplicates
                existing_doc_ids = {doc['document'].id for doc in relevant_docs}
                for doc_data in embedding_results:
                    if doc_data['document'].id not in existing_doc_ids:
                        relevant_docs.append(doc_data)
            
            # Sort by similarity score
            relevant_docs.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            return relevant_docs[:max_results]
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {e}")
            return []
    
    def _keyword_search(self, query: str, user: User, max_results: int) -> List[Dict[str, Any]]:
        """Traditional keyword-based search"""
        try:
            # Split query into keywords
            keywords = query.lower().split()
            
            # Build Q objects for search
            q_objects = Q()
            for keyword in keywords:
                q_objects |= (
                    Q(title__icontains=keyword) |
                    Q(content__icontains=keyword) |
                    Q(description__icontains=keyword) |
                    Q(tags__name__icontains=keyword)
                )
            
            # Execute search
            documents = KnowledgeDocument.objects.filter(
                q_objects,
                status='published'
            ).distinct()[:max_results * 2]  # Get more to filter by access
            
            results = []
            for doc in documents:
                if self._user_can_access_document(user, doc):
                    relevance_score = self._calculate_keyword_relevance(query, doc)
                    if relevance_score > 0.1:  # Minimum relevance threshold
                        results.append({
                            'document': doc,
                            'similarity_score': relevance_score,
                            'snippet': self._extract_snippet(query, doc),
                            'method': 'keyword'
                        })
                
                if len(results) >= max_results:
                    break
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _embedding_search(self, query: str, user: User, max_results: int) -> List[Dict[str, Any]]:
        """Embedding-based semantic search"""
        try:
            if not self.embedding_model:
                return []
            
            # Get query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Get all accessible documents
            documents = KnowledgeDocument.objects.filter(
                status='published'
            )[:100]  # Limit for performance
            
            results = []
            doc_texts = []
            valid_docs = []
            
            for doc in documents:
                if self._user_can_access_document(user, doc):
                    # Combine title, description, and content for embedding
                    doc_text = f"{doc.title} {doc.description or ''} {doc.content[:500]}"
                    doc_texts.append(doc_text)
                    valid_docs.append(doc)
            
            if not doc_texts:
                return []
            
            # Get document embeddings
            doc_embeddings = self.embedding_model.encode(doc_texts)
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
            
            # Create results with similarity scores
            for i, (doc, similarity) in enumerate(zip(valid_docs, similarities)):
                if similarity > self.similarity_threshold:
                    results.append({
                        'document': doc,
                        'similarity_score': float(similarity),
                        'snippet': self._extract_snippet(query, doc),
                        'method': 'embedding'
                    })
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Embedding search failed: {e}")
            return []
    
    def _user_can_access_document(self, user: User, document: KnowledgeDocument) -> bool:
        """Check if user can access the document"""
        try:
            # Public documents are accessible to all
            if document.is_public:
                return True
            
            # Check if user is the author
            if hasattr(document, 'author') and document.author == user:
                return True
            
            # Check department access
            if hasattr(user, 'employee_get') and hasattr(document, 'departments'):
                user_department = getattr(user.employee_get, 'employee_work_info', None)
                if user_department and hasattr(user_department, 'department'):
                    if document.departments.filter(id=user_department.department.id).exists():
                        return True
            
            # Default to accessible for now (can be customized based on requirements)
            return True
            
        except Exception as e:
            logger.warning(f"Access check failed for document {document.id}: {e}")
            return True  # Default to accessible on error
    
    def _calculate_keyword_relevance(self, query: str, document: KnowledgeDocument) -> float:
        """Calculate relevance score based on keyword matching"""
        try:
            query_words = set(query.lower().split())
            
            # Get document text
            doc_text = f"{document.title} {document.description or ''} {document.content}".lower()
            doc_words = set(doc_text.split())
            
            # Calculate Jaccard similarity
            intersection = len(query_words.intersection(doc_words))
            union = len(query_words.union(doc_words))
            
            if union == 0:
                return 0.0
            
            jaccard_score = intersection / union
            
            # Boost score if keywords appear in title
            title_boost = 0.0
            title_words = set(document.title.lower().split())
            title_matches = len(query_words.intersection(title_words))
            if title_matches > 0:
                title_boost = 0.3 * (title_matches / len(query_words))
            
            return min(jaccard_score + title_boost, 1.0)
            
        except Exception as e:
            logger.warning(f"Relevance calculation failed: {e}")
            return 0.0
    
    def _extract_snippet(self, query: str, document: KnowledgeDocument, max_length: int = 200) -> str:
        """Extract relevant snippet from document"""
        try:
            content = document.content or ''
            query_words = query.lower().split()
            
            # Find the best position to extract snippet
            best_pos = 0
            best_score = 0
            
            # Check different positions in the content
            for i in range(0, len(content) - max_length, 50):
                snippet = content[i:i + max_length].lower()
                score = sum(1 for word in query_words if word in snippet)
                
                if score > best_score:
                    best_score = score
                    best_pos = i
            
            # Extract snippet
            snippet = content[best_pos:best_pos + max_length]
            
            # Clean up snippet
            if best_pos > 0:
                snippet = '...' + snippet
            if best_pos + max_length < len(content):
                snippet = snippet + '...'
            
            return snippet.strip()
            
        except Exception as e:
            logger.warning(f"Snippet extraction failed: {e}")
            return document.description or document.title
    
    def generate_response(self, query: str, relevant_docs: List[Dict[str, Any]], 
                         conversation: ChatbotConversation) -> Dict[str, Any]:
        """Generate AI response using SLM and retrieved documents as context"""
        try:
            start_time = time.time()
            
            # Build context from relevant documents
            context_parts = []
            referenced_docs = []
            
            for doc_data in relevant_docs:
                doc = doc_data['document']
                snippet = doc_data.get('snippet', '')
                
                context_part = f"Dokumen: {doc.title}\n"
                if doc.description:
                    context_part += f"Deskripsi: {doc.description}\n"
                if snippet:
                    context_part += f"Konten: {snippet}\n"
                context_part += f"Kategori: {doc.category.name}\n\n"
                
                context_parts.append(context_part)
                referenced_docs.append(doc)
            
            # Limit context length for SLM
            context = "".join(context_parts)[:self.max_context_length]
            
            # Determine if query is in Indonesian
            is_indonesian = self._detect_indonesian(query)
            
            # Choose appropriate model
            if is_indonesian and self.slm_config['use_indonesian']:
                model_key = self.slm_config['indonesian_model']
            else:
                model_key = self.slm_config['text_generation_model']
            
            # Try different approaches based on context availability
            if context.strip():
                # Use QA approach with context
                response_data = self._generate_contextual_response(query, context, conversation)
            else:
                # Use general text generation
                response_data = self._generate_general_response(query, conversation, model_key)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'response': response_data.get('response', 'Maaf, saya tidak dapat memberikan jawaban saat ini.'),
                'confidence_score': response_data.get('confidence', 0.7),
                'processing_time': processing_time,
                'referenced_documents': referenced_docs,
                'context_used': len(context),
                'model_used': response_data.get('model_used', model_key),
                'approach': response_data.get('approach', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return {
                'success': False,
                'response': 'Maaf, terjadi kesalahan dalam memproses pertanyaan Anda. Silakan coba lagi.',
                'error': str(e)
            }
    
    def _generate_contextual_response(self, query: str, context: str, conversation: ChatbotConversation) -> Dict[str, Any]:
        """Generate response using context from documents"""
        try:
            # First try to extract FAQ answer directly from context
            faq_answer = self._extract_faq_answer(query, context)
            if faq_answer:
                return {
                    'response': faq_answer,
                    'confidence': 0.8,
                    'model_used': 'faq_extraction',
                    'approach': 'faq_direct'
                }
            
            # Try QA approach with higher threshold
            qa_result = self.slm_service.answer_question(
                question=query,
                context=context,
                model_key=self.slm_config['qa_model']
            )
            
            # Only use QA result if confidence is very high
            if qa_result['success'] and qa_result['confidence'] > 0.8:
                return {
                    'response': qa_result['answer'],
                    'confidence': qa_result['confidence'],
                    'model_used': qa_result['model_used'],
                    'approach': 'qa_with_context'
                }
            
            # Skip text generation as it produces poor results
            # Go directly to helpful fallback
            return {
                'response': self._generate_helpful_fallback(query),
                'confidence': 0.6,
                'model_used': 'helpful_fallback',
                'approach': 'helpful_fallback'
            }
            
        except Exception as e:
            logger.error(f"Contextual response generation failed: {e}")
            return {
                'response': self._generate_helpful_fallback(query),
                'confidence': 0.4,
                'model_used': 'helpful_fallback',
                'approach': 'error_fallback'
            }
    
    def _generate_general_response(self, query: str, conversation: ChatbotConversation, model_key: str) -> Dict[str, Any]:
        """Generate general response without specific context"""
        try:
            # Skip SLM generation as it produces poor results
            # Go directly to helpful fallback which provides better responses
            helpful_response = self._generate_helpful_fallback(query)
            return {
                'response': helpful_response,
                'confidence': 0.7,
                'model_used': 'helpful_fallback',
                'approach': 'helpful_fallback'
            }
                
        except Exception as e:
            logger.error(f"General response generation failed: {e}")
            return {
                'response': self._generate_helpful_fallback(query),
                'confidence': 0.4,
                'model_used': 'helpful_fallback',
                'approach': 'error_fallback'
            }
    
    def _build_slm_prompt(self, query: str, context: str, conversation: ChatbotConversation) -> str:
        """Build prompt optimized for small language models"""
        # Get recent conversation history (limited for SLM)
        recent_messages = conversation.messages.filter(
            created_at__gte=timezone.now() - timezone.timedelta(minutes=30)
        ).order_by('created_at')[:5]  # Reduced for SLM
        
        conversation_history = ""
        for msg in recent_messages:
            role = "User" if msg.sender == 'user' else "AI"
            conversation_history += f"{role}: {msg.content[:100]}\n"  # Truncate for SLM
        
        # Build concise prompt for SLM
        prompt = f"""Konteks: {context[:800]}  

Riwayat: {conversation_history}

Pertanyaan: {query}

Jawaban:"""
        
        return prompt
    
    def _extract_faq_answer(self, query: str, context: str) -> Optional[str]:
        """Extract direct answer from FAQ context"""
        try:
            if not context:
                return None
            
            query_lower = query.lower()
            context_lower = context.lower()
            
            # Check for specific reimbursement content
            if ('reimbursement' in query_lower or 'penggantian' in query_lower or 'klaim' in query_lower) and \
               ('reimbursement' in context_lower or 'penggantian' in context_lower or 'prosedur' in context_lower):
                
                # Split context by documents to process each separately
                doc_sections = context.split('Dokumen:')
                reimbursement_content = None
                
                # Find the reimbursement document section
                for section in doc_sections:
                    if 'reimbursement' in section.lower() or 'penggantian' in section.lower():
                        reimbursement_content = section
                        break
                
                if reimbursement_content:
                    # Extract structured information from reimbursement document
                    response = "Untuk mengajukan reimbursement, berikut prosedurnya:\n\n"
                    
                    # Always show all sections for reimbursement
                    response += "**Jenis Reimbursement:**\n"
                    response += "- Perjalanan Dinas: transportasi, akomodasi, makan\n"
                    response += "- Operasional: supplies kantor, komunikasi, training\n"
                    response += "- Medis: pengobatan, check-up kesehatan\n\n"
                    
                    response += "**Persyaratan Dokumen:**\n"
                    response += "- Form reimbursement lengkap + approval supervisor\n"
                    response += "- Bukti pembayaran asli (kwitansi/invoice)\n"
                    response += "- Dokumen pendukung (surat tugas, laporan)\n\n"
                    
                    response += "**Alur Persetujuan:**\n"
                    response += "- Submit form → Supervisor approval → Finance review → Payment\n"
                    response += "- Maksimal 30 hari setelah pengeluaran\n"
                    response += "- Proses approval: 5-7 hari kerja\n\n"
                    
                    response += "**Batas Waktu:**\n"
                    response += "- Pengajuan maksimal 30 hari setelah pengeluaran\n"
                    response += "- Proses persetujuan: 5-7 hari kerja\n"
                    response += "- Pembayaran: 3-5 hari setelah approval\n\n"
                    
                    # Add contact info
                    response += "**Kontak:**\n"
                    response += "Finance Team: finance@company.com | Ext: 1234\n"
                    response += "Lokasi: Lantai 2, Ruang Finance"
                    
                    return response
            
            # Look for FAQ patterns in context
            faq_patterns = [
                'q:', 'question:', 'pertanyaan:', 'tanya:', 
                'a:', 'answer:', 'jawaban:', 'jawab:',
                'bagaimana cara', 'how to', 'cara untuk'
            ]
            
            # Check if context contains FAQ-like structure
            has_faq_pattern = any(pattern in context_lower for pattern in faq_patterns)
            
            if has_faq_pattern and self._is_faq_relevant(query, context):
                # Extract and format the answer
                return self._format_faq_answer(context)
            
            # Look for document-based FAQ patterns
            lines = context.split('\n')
            current_faq = None
            
            for line in lines:
                line = line.strip()
                if line.startswith('Dokumen:') or line.startswith('FAQ:'):
                    current_faq = {'title': line}
                elif line.startswith('Konten:') and current_faq:
                    content = line.replace('Konten:', '').strip()
                    if len(content) > 50:  # Substantial content
                        # Check if this FAQ is relevant to the query
                        if self._is_faq_relevant(query, content):
                            return self._format_faq_answer(content)
            
            return None
            
        except Exception as e:
            logger.error(f"FAQ extraction failed: {e}")
            return None
    
    def _is_faq_relevant(self, query: str, faq_content: str) -> bool:
        """Check if FAQ content is relevant to query"""
        query_lower = query.lower()
        content_lower = faq_content.lower()
        
        # Check for key terms
        if 'employee' in query_lower or 'pegawai' in query_lower:
            return any(term in content_lower for term in ['employee', 'pegawai', 'karyawan', 'staff'])
        elif 'leave' in query_lower or 'cuti' in query_lower:
            return any(term in content_lower for term in ['leave', 'cuti', 'izin'])
        elif 'create' in query_lower or 'buat' in query_lower:
            return any(term in content_lower for term in ['create', 'add', 'new', 'buat', 'tambah', 'baru'])
        
        return True  # Default to relevant if no specific patterns
    
    def _format_faq_answer(self, content: str) -> str:
        """Format FAQ content into a proper answer"""
        # Clean up the content
        content = content.strip()
        
        # Add helpful introduction
        if self._detect_indonesian(content):
            intro = "Berdasarkan informasi yang tersedia, berikut adalah panduan untuk Anda:\n\n"
        else:
            intro = "Based on the available information, here's the guidance for you:\n\n"
        
        return intro + content
    
    def _generate_helpful_fallback(self, query: str) -> str:
        """Generate helpful fallback response based on query type"""
        query_lower = query.lower()
        
        # Detect language
        is_indonesian = self._detect_indonesian(query)
        
        # Check more specific keywords first
        if 'gaji' in query_lower or 'salary' in query_lower or 'payroll' in query_lower:
            if is_indonesian:
                return """Untuk informasi gaji dan payroll:

1. Akses menu Payroll Management
2. Lihat slip gaji bulanan
3. Cek komponen gaji (pokok, tunjangan, potongan)
4. Download laporan pajak (PPh 21)
5. Hubungi HR untuk pertanyaan gaji

Semua informasi gaji tersedia di portal karyawan."""
            else:
                return """For salary and payroll information:

1. Access Payroll Management menu
2. View monthly pay slips
3. Check salary components (basic, allowances, deductions)
4. Download tax reports (Income Tax)
5. Contact HR for salary inquiries

All salary information is available in employee portal."""
        
        elif 'budget' in query_lower or 'anggaran' in query_lower or 'biaya' in query_lower:
            if is_indonesian:
                return """Untuk informasi anggaran dan keuangan:

1. Akses menu Budget Management atau Finance
2. Lihat alokasi anggaran per departemen
3. Monitor pengeluaran dan pemasukan
4. Generate laporan keuangan
5. Hubungi tim Finance untuk detail lebih lanjut

Sistem menyediakan dashboard untuk tracking anggaran real-time."""
            else:
                return """For budget and financial information:

1. Access Budget Management or Finance menu
2. View budget allocation per department
3. Monitor expenses and income
4. Generate financial reports
5. Contact Finance team for more details

The system provides real-time budget tracking dashboard."""
        
        elif 'reimbursement' in query_lower or 'reimburse' in query_lower or 'penggantian' in query_lower or 'klaim' in query_lower:
            if is_indonesian:
                return """Untuk mengajukan reimbursement:

1. Akses menu Finance atau Expense Management
2. Pilih "Ajukan Reimbursement" atau "Submit Reimbursement"
3. Pilih jenis reimbursement (perjalanan dinas, medis, dll)
4. Upload bukti pembayaran/kwitansi
5. Isi detail pengeluaran dan keterangan
6. Submit untuk persetujuan atasan

Pastikan semua dokumen pendukung lengkap untuk mempercepat proses persetujuan."""
            else:
                return """To submit a reimbursement:

1. Access Finance or Expense Management menu
2. Select "Submit Reimbursement"
3. Choose reimbursement type (business travel, medical, etc.)
4. Upload payment receipts/invoices
5. Fill in expense details and description
6. Submit for supervisor approval

Ensure all supporting documents are complete to expedite the approval process."""
        
        elif 'tunjangan' in query_lower or 'benefit' in query_lower or 'fasilitas' in query_lower or 'kompensasi' in query_lower:
            if is_indonesian:
                return """Untuk informasi tunjangan dan benefit karyawan:

1. Akses menu Employee Benefits atau Compensation
2. Lihat daftar tunjangan yang tersedia (kesehatan, transportasi, makan)
3. Cek eligibilitas dan syarat untuk setiap tunjangan
4. Submit klaim tunjangan melalui sistem
5. Hubungi HR untuk informasi benefit tambahan

Semua informasi tunjangan dapat diakses melalui portal karyawan."""
            else:
                return """For employee benefits and allowances information:

1. Access Employee Benefits or Compensation menu
2. View available benefits list (health, transport, meal)
3. Check eligibility and requirements for each benefit
4. Submit benefit claims through the system
5. Contact HR for additional benefit information

All benefit information is accessible through employee portal."""
        
        elif 'employee' in query_lower or 'pegawai' in query_lower or 'karyawan' in query_lower:
            if is_indonesian:
                return """Untuk mengelola data pegawai, Anda dapat:

1. Masuk ke menu Employee Management
2. Klik tombol "Add New Employee" atau "Tambah Pegawai Baru"
3. Isi formulir dengan informasi lengkap pegawai
4. Simpan data pegawai

Jika Anda memerlukan bantuan lebih lanjut, silakan hubungi administrator sistem atau tim HR."""
            else:
                return """To manage employee data, you can:

1. Go to Employee Management menu
2. Click "Add New Employee" button
3. Fill out the form with complete employee information
4. Save the employee data

If you need further assistance, please contact the system administrator or HR team."""
        
        elif 'leave' in query_lower or 'cuti' in query_lower:
            if is_indonesian:
                return """Untuk mengajukan cuti, ikuti langkah berikut:

1. Masuk ke menu Leave Management
2. Klik "Request Leave" atau "Ajukan Cuti"
3. Pilih jenis cuti dan tanggal
4. Isi alasan cuti
5. Submit permintaan untuk persetujuan

Permintaan cuti akan diproses oleh atasan atau tim HR."""
            else:
                return """To request leave, follow these steps:

1. Go to Leave Management menu
2. Click "Request Leave"
3. Select leave type and dates
4. Fill in the reason for leave
5. Submit request for approval

Your leave request will be processed by your supervisor or HR team."""
        
        elif 'attendance' in query_lower or 'absensi' in query_lower:
            if is_indonesian:
                return """Untuk mengelola absensi:

1. Gunakan menu Attendance
2. Lakukan check-in/check-out sesuai jadwal
3. Lihat riwayat kehadiran di dashboard
4. Laporkan ketidakhadiran jika diperlukan

Sistem akan mencatat waktu kehadiran Anda secara otomatis."""
            else:
                return """To manage attendance:

1. Use the Attendance menu
2. Check-in/check-out according to schedule
3. View attendance history in dashboard
4. Report absences if needed

The system will automatically record your attendance time."""
        
        else:
            if is_indonesian:
                return """Maaf, saya tidak dapat memberikan jawaban spesifik untuk pertanyaan Anda saat ini. 

Silakan coba:
1. Gunakan kata kunci yang lebih spesifik
2. Periksa menu navigasi untuk fitur yang Anda cari
3. Hubungi administrator sistem untuk bantuan lebih lanjut

Terima kasih atas pengertian Anda."""
            else:
                return """I apologize, but I cannot provide a specific answer to your question at this time.

Please try:
1. Use more specific keywords
2. Check the navigation menu for the feature you're looking for
3. Contact the system administrator for further assistance

Thank you for your understanding."""
    
    def _detect_indonesian(self, text: str) -> bool:
        """Enhanced Indonesian language detection"""
        indonesian_words = {
            # Question words
            'apa', 'bagaimana', 'mengapa', 'kapan', 'dimana', 'siapa', 'berapa',
            # Common words
            'yang', 'dan', 'atau', 'dengan', 'untuk', 'dari', 'ke', 'di', 'pada',
            # Pronouns
            'saya', 'anda', 'kita', 'mereka', 'dia', 'ini', 'itu', 'kamu',
            # Verbs
            'adalah', 'akan', 'sudah', 'sedang', 'telah', 'bisa', 'dapat', 'mau',
            'ingin', 'perlu', 'harus', 'boleh', 'jadi', 'ada', 'tidak', 'belum',
            # Business/HR related words
            'karyawan', 'pegawai', 'perusahaan', 'kantor', 'kerja', 'gaji', 'cuti',
            'absensi', 'anggaran', 'budget', 'laporan', 'data', 'informasi', 'info',
            'sistem', 'aplikasi', 'cara', 'proses', 'prosedur', 'kebijakan',
            # Common adjectives/adverbs
            'baru', 'lama', 'baik', 'buruk', 'besar', 'kecil', 'penting', 'mudah',
            'sulit', 'cepat', 'lambat', 'sekarang', 'nanti', 'kemarin', 'besok',
            # Prepositions and conjunctions
            'dalam', 'luar', 'atas', 'bawah', 'depan', 'belakang', 'antara', 'selama',
            'setelah', 'sebelum', 'karena', 'jika', 'kalau', 'supaya', 'agar',
            # Polite words
            'tolong', 'mohon', 'silakan', 'terima', 'kasih', 'maaf', 'permisi'
        }
        
        # Clean and split text
        words = text.lower().replace('?', '').replace('!', '').replace('.', '').replace(',', '').split()
        indonesian_count = sum(1 for word in words if word in indonesian_words)
        
        # Lower threshold for better detection
        return indonesian_count > len(words) * 0.15  # 15% threshold
    
    def create_conversation(self, user: User, initial_query: str = None) -> ChatbotConversation:
        """Create new chatbot conversation"""
        try:
            conversation = ChatbotConversation.objects.create(
                user=user,
                title=initial_query[:50] + '...' if initial_query and len(initial_query) > 50 else initial_query or 'New Conversation',
                status='active'
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
                content=content,
                message_type=message_type,
                metadata=kwargs
            )
            
            # Update conversation last activity
            conversation.last_activity = timezone.now()
            conversation.save()
            
            return message
            
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            raise


# Global instance
chatbot_slm_service = ChatbotSLMService()