import os
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
except ImportError:
    # Fallback jika libraries tidak tersedia
    SentenceTransformer = None
    np = None
    faiss = None

from django.core.files.storage import default_storage
from django.conf import settings
from django.db.models import Q

from .base import BaseAIService, NLPModelMixin
from .config import AIConfig
from .exceptions import PredictionError, ModelLoadError, ValidationError
from .performance_optimizer import (
    cache_prediction, 
    cache_search_results,
    monitor_ai_performance,
    optimize_ai_service
)

logger = logging.getLogger(__name__)

@optimize_ai_service
class KnowledgeAIService(BaseAIService, NLPModelMixin):
    """
    AI Service untuk Knowledge Management dengan RAG (Retrieval-Augmented Generation).
    Menyediakan AI Assistant untuk akses informasi yang efisien.
    """
    
    def __init__(self):
        config = AIConfig.get_config('knowledge')
        super().__init__(config['MODEL_NAME'], '1.0')
        self.config = config
        self.embedding_model = None
        self.vector_index = None
        self.knowledge_base = {}
        self.document_chunks = []
        self.chunk_metadata = []
        
    def load_model(self) -> None:
        """
        Load embedding model dan vector database untuk RAG.
        """
        try:
            if SentenceTransformer is None:
                logger.warning("sentence-transformers not available, using fallback")
                self.is_loaded = True
                return
            
            # Load embedding model
            embedding_model_name = self.config['EMBEDDING_MODEL']
            logger.info(f"Loading embedding model: {embedding_model_name}")
            
            self.embedding_model = SentenceTransformer(embedding_model_name)
            
            # Initialize vector index
            self._initialize_vector_index()
            
            # Load existing knowledge base
            self._load_knowledge_base()
            
            self.is_loaded = True
            logger.info("Knowledge AI model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load Knowledge AI model: {str(e)}")
            # Fallback mode
            self.is_loaded = True
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data untuk knowledge query.
        """
        if not isinstance(input_data, dict):
            return False
        
        # Check for query
        if 'query' not in input_data:
            return False
        
        if not isinstance(input_data['query'], str) or len(input_data['query'].strip()) == 0:
            return False
        
        # Validate query length
        if len(input_data['query']) > self.config.get('MAX_QUERY_LENGTH', 1000):
            return False
        
        return True
    
    @cache_search_results
    @monitor_ai_performance
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process knowledge query menggunakan RAG approach.
        """
        try:
            query = input_data['query'].strip()
            max_results = input_data.get('max_results', 5)
            include_context = input_data.get('include_context', True)
            
            # Preprocess query
            processed_query = self.preprocess_text(query)
            
            # Retrieve relevant documents
            relevant_docs = self._retrieve_documents(processed_query, max_results)
            
            # Generate response
            response = self._generate_response(processed_query, relevant_docs)
            
            # Extract keywords
            keywords = self.extract_keywords(processed_query)
            
            # Calculate confidence based on retrieval scores
            confidence = self._calculate_confidence(relevant_docs)
            
            result = {
                'response': response,
                'confidence_score': confidence,
                'relevant_documents': relevant_docs if include_context else [],
                'keywords': keywords,
                'query_processed': processed_query,
                'total_documents_searched': len(self.document_chunks)
            }
            
            return result
            
        except Exception as e:
            raise PredictionError(f"Knowledge query failed: {str(e)}", self.model_name, input_data)
    
    def _initialize_vector_index(self) -> None:
        """
        Initialize FAISS vector index untuk similarity search.
        """
        try:
            if faiss is None:
                logger.warning("FAISS not available, using fallback search")
                return
            
            # Get embedding dimension
            dimension = self.config.get('VECTOR_DIMENSION', 384)  # MiniLM dimension
            
            # Create FAISS index
            self.vector_index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            
            logger.info(f"Vector index initialized with dimension {dimension}")
            
        except Exception as e:
            logger.error(f"Vector index initialization failed: {str(e)}")
            self.vector_index = None
    
    def _load_knowledge_base(self) -> None:
        """
        Load knowledge base dari Django database dan file storage.
        """
        try:
            # First, load documents from Django database
            self._load_documents_from_database()
            
            # Then, load any additional documents from file storage
            knowledge_path = AIConfig.get_model_path(self.model_name)
            knowledge_file = os.path.join(knowledge_path, 'knowledge_base.json')
            
            if os.path.exists(knowledge_file):
                with open(knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    additional_chunks = data.get('document_chunks', [])
                    self.document_chunks.extend(additional_chunks)
                    
                    additional_metadata = data.get('chunk_metadata', [])
                    self.chunk_metadata.extend(additional_metadata)
                
                # Load vector embeddings if available
                embeddings_file = os.path.join(knowledge_path, 'embeddings.npy')
                if os.path.exists(embeddings_file) and self.vector_index is not None:
                    embeddings = np.load(embeddings_file)
                    self.vector_index.add(embeddings)
            
            # If no documents loaded, initialize with defaults
            if not self.document_chunks:
                logger.info("No documents found, initializing with defaults")
                self._initialize_default_knowledge()
            else:
                logger.info(f"Loaded {len(self.document_chunks)} document chunks")
                
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {str(e)}")
            self._initialize_default_knowledge()
    
    def _load_documents_from_database(self) -> None:
        """
        Load dokumen dari Django KnowledgeDocument model.
        """
        try:
            from knowledge.models import KnowledgeDocument
            
            # Get published documents
            documents = KnowledgeDocument.objects.filter(
                status='published'
            ).select_related('category')
            
            for doc in documents:
                # Split document into chunks if content is long
                content = doc.content or ''
                if len(content) > 1000:
                    chunks = self._split_text(content, 800, 100)
                    for i, chunk_content in enumerate(chunks):
                        chunk = {
                            'content': chunk_content,
                            'title': f"{doc.title} (Part {i+1})",
                            'category': doc.category.name if doc.category else 'general',
                            'source': 'database',
                            'document_id': doc.id,
                            'chunk_index': i,
                            'metadata': {
                                'document_type': doc.document_type,
                                'language': doc.language,
                                'created_at': doc.created_at.isoformat() if doc.created_at else None,
                                'keywords': doc.ai_extracted_keywords or ''
                            }
                        }
                        self.document_chunks.append(chunk)
                else:
                    # Small document, keep as single chunk
                    chunk = {
                        'content': content,
                        'title': doc.title,
                        'category': doc.category.name if doc.category else 'general',
                        'source': 'database',
                        'document_id': doc.id,
                        'chunk_index': 0,
                        'metadata': {
                            'document_type': doc.document_type,
                            'language': doc.language,
                            'created_at': doc.created_at.isoformat() if doc.created_at else None,
                            'keywords': doc.ai_extracted_keywords or ''
                        }
                    }
                    self.document_chunks.append(chunk)
            
            logger.info(f"Loaded {len(self.document_chunks)} chunks from {documents.count()} database documents")
            
        except Exception as e:
            logger.error(f"Failed to load documents from database: {str(e)}")
    
    def _initialize_default_knowledge(self) -> None:
        """
        Initialize dengan default knowledge base untuk HR system.
        """
        default_knowledge = {
            'hr_policies': {
                'leave_policy': 'Karyawan berhak atas cuti tahunan 12 hari kerja per tahun. Cuti dapat diambil setelah masa kerja minimal 6 bulan.',
                'attendance_policy': 'Jam kerja standar adalah 8 jam per hari, Senin-Jumat. Keterlambatan lebih dari 15 menit akan dicatat sebagai pelanggaran.',
                'performance_review': 'Evaluasi kinerja dilakukan setiap 6 bulan dengan menggunakan sistem KPI dan feedback 360 derajat.'
            },
            'procedures': {
                'recruitment': 'Proses rekrutmen meliputi: screening CV, tes tertulis, wawancara HR, wawancara user, dan medical check-up.',
                'onboarding': 'Proses onboarding baru berlangsung 2 minggu dengan orientasi perusahaan, training sistem, dan pengenalan tim.',
                'payroll': 'Penggajian dilakukan setiap tanggal 25 dengan sistem transfer bank. Slip gaji tersedia di sistem HR.',
                'budget_management': 'Anggaran departemen dikelola melalui sistem ERP dengan approval workflow. Setiap pengeluaran di atas Rp 1.000.000 memerlukan persetujuan manager.',
                'salary_structure': 'Struktur gaji terdiri dari gaji pokok, tunjangan jabatan, tunjangan transport, dan tunjangan makan. Review gaji dilakukan setiap tahun berdasarkan performance.'
            },
            'benefits': {
                'health_insurance': 'Asuransi kesehatan disediakan untuk karyawan dan keluarga (maksimal 3 orang) dengan coverage 100%.',
                'training_budget': 'Setiap karyawan mendapat budget training Rp 5.000.000 per tahun untuk pengembangan skill.',
                'bonus': 'Bonus tahunan diberikan berdasarkan performance dan pencapaian target perusahaan.',
                'allowances': 'Tunjangan meliputi: transport Rp 500.000/bulan, makan Rp 300.000/bulan, komunikasi Rp 200.000/bulan untuk level manager ke atas.'
            }
        }
        
        # Convert to document chunks
        for category, items in default_knowledge.items():
            for key, content in items.items():
                chunk = {
                    'content': content,
                    'title': f"{category.replace('_', ' ').title()}: {key.replace('_', ' ').title()}",
                    'category': category,
                    'source': 'default_knowledge',
                    'created_at': datetime.now().isoformat()
                }
                
                self.document_chunks.append(chunk)
                self.chunk_metadata.append({
                    'id': len(self.document_chunks) - 1,
                    'title': chunk['title'],
                    'category': category,
                    'source': 'default_knowledge'
                })
        
        # Generate embeddings for default knowledge
        if self.embedding_model is not None:
            self._generate_embeddings()
        
        logger.info(f"Initialized with {len(self.document_chunks)} default knowledge chunks")
    
    def _retrieve_documents(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents berdasarkan query.
        """
        try:
            if self.embedding_model is None or self.vector_index is None:
                # Fallback to keyword search
                return self._keyword_search(query, max_results)
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            
            # Search in vector index
            scores, indices = self.vector_index.search(query_embedding, min(max_results, len(self.document_chunks)))
            
            relevant_docs = []
            
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if idx < len(self.document_chunks):
                    doc = self.document_chunks[idx].copy()
                    doc['similarity_score'] = float(score)
                    doc['rank'] = i + 1
                    relevant_docs.append(doc)
            
            # Filter by similarity threshold
            threshold = self.config.get('SIMILARITY_THRESHOLD', 0.3)
            relevant_docs = [doc for doc in relevant_docs if doc['similarity_score'] >= threshold]
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"Document retrieval failed: {str(e)}")
            return self._keyword_search(query, max_results)
    
    def _keyword_search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Fallback keyword-based search.
        """
        try:
            query_words = set(query.lower().split())
            scored_docs = []
            
            for i, chunk in enumerate(self.document_chunks):
                content_words = set(chunk['content'].lower().split())
                title_words = set(chunk['title'].lower().split())
                
                # Calculate simple keyword overlap score
                content_score = len(query_words.intersection(content_words)) / len(query_words)
                title_score = len(query_words.intersection(title_words)) / len(query_words) * 2  # Title gets higher weight
                
                total_score = content_score + title_score
                
                if total_score > 0:
                    doc = chunk.copy()
                    doc['similarity_score'] = total_score
                    doc['rank'] = 0  # Will be set after sorting
                    scored_docs.append(doc)
            
            # Sort by score and assign ranks
            scored_docs.sort(key=lambda x: x['similarity_score'], reverse=True)
            for i, doc in enumerate(scored_docs[:max_results]):
                doc['rank'] = i + 1
            
            return scored_docs[:max_results]
            
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return []
    
    def _generate_response(self, query: str, relevant_docs: List[Dict[str, Any]]) -> str:
        """
        Generate response berdasarkan retrieved documents.
        """
        try:
            if not relevant_docs:
                return "Maaf, saya tidak menemukan informasi yang relevan untuk pertanyaan Anda. Silakan coba dengan kata kunci yang berbeda atau hubungi HR untuk bantuan lebih lanjut."
            
            # Combine relevant content
            context_parts = []
            for doc in relevant_docs[:3]:  # Use top 3 documents
                context_parts.append(f"• {doc['title']}: {doc['content']}")
            
            context = "\n".join(context_parts)
            
            # Simple response generation (in production, use LLM)
            response_parts = [
                "Berdasarkan informasi yang tersedia:",
                "",
                context
            ]
            
            # Add helpful suggestions
            if len(relevant_docs) > 3:
                response_parts.extend([
                    "",
                    f"Saya juga menemukan {len(relevant_docs) - 3} informasi terkait lainnya. Apakah Anda ingin informasi lebih detail?"
                ])
            
            return "\n".join(response_parts)
            
        except Exception as e:
            logger.error(f"Response generation failed: {str(e)}")
            return "Maaf, terjadi kesalahan saat memproses pertanyaan Anda. Silakan coba lagi."
    
    def _calculate_confidence(self, relevant_docs: List[Dict[str, Any]]) -> float:
        """
        Calculate confidence score berdasarkan retrieval quality.
        """
        try:
            if not relevant_docs:
                return 0.0
            
            # Base confidence on top document similarity and number of results
            top_score = relevant_docs[0].get('similarity_score', 0.0)
            num_docs = len(relevant_docs)
            
            # Normalize and combine factors
            score_factor = min(1.0, top_score * 2)  # Boost similarity score
            count_factor = min(1.0, num_docs / 3)   # More docs = higher confidence (up to 3)
            
            confidence = (score_factor * 0.7 + count_factor * 0.3)
            
            return round(confidence, 4)
            
        except Exception as e:
            logger.warning(f"Confidence calculation failed: {str(e)}")
            return 0.5  # Default moderate confidence
    
    def add_document(self, title: str, content: str, category: str = 'general', 
                    source: str = 'manual', metadata: Dict[str, Any] = None) -> bool:
        """
        Add new document ke knowledge base.
        """
        try:
            # Create document chunk
            chunk = {
                'content': content,
                'title': title,
                'category': category,
                'source': source,
                'created_at': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            # Add to chunks
            chunk_id = len(self.document_chunks)
            self.document_chunks.append(chunk)
            
            # Add metadata
            self.chunk_metadata.append({
                'id': chunk_id,
                'title': title,
                'category': category,
                'source': source
            })
            
            # Generate embedding if model available
            if self.embedding_model is not None and self.vector_index is not None:
                embedding = self.embedding_model.encode([content])
                self.vector_index.add(embedding)
            
            # Save updated knowledge base
            self._save_knowledge_base()
            
            logger.info(f"Added document: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document: {str(e)}")
            return False
    
    def add_documents_from_text(self, text: str, title: str = None, 
                              category: str = 'general', chunk_size: int = None) -> int:
        """
        Add documents dari text panjang dengan chunking.
        """
        try:
            chunk_size = chunk_size or self.config.get('CHUNK_SIZE', 500)
            chunk_overlap = self.config.get('CHUNK_OVERLAP', 50)
            
            # Split text into chunks
            chunks = self._split_text(text, chunk_size, chunk_overlap)
            
            added_count = 0
            base_title = title or "Document"
            
            for i, chunk_text in enumerate(chunks):
                chunk_title = f"{base_title} - Part {i+1}" if len(chunks) > 1 else base_title
                
                if self.add_document(
                    title=chunk_title,
                    content=chunk_text,
                    category=category,
                    source='text_import',
                    metadata={'chunk_index': i, 'total_chunks': len(chunks)}
                ):
                    added_count += 1
            
            return added_count
            
        except Exception as e:
            logger.error(f"Failed to add documents from text: {str(e)}")
            return 0
    
    def _split_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """
        Split text into overlapping chunks.
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            if chunk_text.strip():
                chunks.append(chunk_text)
            
            # Break if we've reached the end
            if i + chunk_size >= len(words):
                break
        
        return chunks
    
    def _generate_embeddings(self) -> None:
        """
        Generate embeddings untuk semua document chunks.
        """
        try:
            if self.embedding_model is None or not self.document_chunks:
                return
            
            # Extract content for embedding
            texts = [chunk['content'] for chunk in self.document_chunks]
            
            # Generate embeddings
            embeddings = self.embedding_model.encode(texts)
            
            # Add to vector index
            if self.vector_index is not None:
                self.vector_index.reset()  # Clear existing
                self.vector_index.add(embeddings)
            
            # Save embeddings
            knowledge_path = AIConfig.get_model_path(self.model_name)
            os.makedirs(knowledge_path, exist_ok=True)
            
            embeddings_file = os.path.join(knowledge_path, 'embeddings.npy')
            np.save(embeddings_file, embeddings)
            
            logger.info(f"Generated embeddings for {len(texts)} documents")
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
    
    def _save_knowledge_base(self) -> None:
        """
        Save knowledge base ke storage.
        """
        try:
            knowledge_path = AIConfig.get_model_path(self.model_name)
            os.makedirs(knowledge_path, exist_ok=True)
            
            # Save knowledge base data
            data = {
                'knowledge_base': self.knowledge_base,
                'document_chunks': self.document_chunks,
                'chunk_metadata': self.chunk_metadata,
                'updated_at': datetime.now().isoformat()
            }
            
            knowledge_file = os.path.join(knowledge_path, 'knowledge_base.json')
            with open(knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info("Knowledge base saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge base: {str(e)}")
    
    def search_documents(self, query: str, category: str = None, 
                        max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search documents dengan optional category filter.
        """
        try:
            # Get all relevant documents
            relevant_docs = self._retrieve_documents(query, max_results * 2)
            
            # Filter by category if specified
            if category:
                relevant_docs = [doc for doc in relevant_docs if doc.get('category') == category]
            
            return relevant_docs[:max_results]
            
        except Exception as e:
            logger.error(f"Document search failed: {str(e)}")
            return []
    
    def get_categories(self) -> List[str]:
        """
        Get list of available categories.
        """
        try:
            categories = set()
            for chunk in self.document_chunks:
                categories.add(chunk.get('category', 'general'))
            
            return sorted(list(categories))
            
        except Exception as e:
            logger.error(f"Failed to get categories: {str(e)}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.
        """
        try:
            categories = {}
            sources = {}
            
            for chunk in self.document_chunks:
                category = chunk.get('category', 'general')
                source = chunk.get('source', 'unknown')
                
                categories[category] = categories.get(category, 0) + 1
                sources[source] = sources.get(source, 0) + 1
            
            return {
                'total_documents': len(self.document_chunks),
                'categories': categories,
                'sources': sources,
                'has_embeddings': self.vector_index is not None and self.vector_index.ntotal > 0,
                'embedding_model': self.config.get('EMBEDDING_MODEL', 'Not loaded')
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {str(e)}")
            return {
                'total_documents': 0,
                'error': str(e)
            }
    
    def clear_knowledge_base(self) -> bool:
        """
        Clear semua knowledge base (use with caution).
        """
        try:
            self.document_chunks = []
            self.chunk_metadata = []
            self.knowledge_base = {}
            
            if self.vector_index is not None:
                self.vector_index.reset()
            
            self._save_knowledge_base()
            
            logger.info("Knowledge base cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear knowledge base: {str(e)}")
            return False