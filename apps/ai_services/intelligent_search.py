import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging
import hashlib
from collections import defaultdict
import math

try:
    from sentence_transformers import SentenceTransformer
    import faiss
    import numpy as np
except ImportError:
    SentenceTransformer = None
    faiss = None
    np = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import joblib
except ImportError:
    TfidfVectorizer = None
    cosine_similarity = None
    joblib = None

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import PorterStemmer
except ImportError:
    nltk = None
    stopwords = None
    word_tokenize = None
    PorterStemmer = None

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.apps import apps
from django.utils import timezone
from django.core.cache import cache

from .base import BaseAIService
from .config import AIConfig
from .exceptions import PredictionError, ModelLoadError, ValidationError

logger = logging.getLogger(__name__)

class IntelligentSearchService(BaseAIService):
    """
    AI Service untuk Intelligent Search dengan semantic understanding.
    Mendukung hybrid search (semantic + keyword), query expansion, dan contextual ranking.
    """
    
    def __init__(self):
        config = AIConfig.get_config('search')
        super().__init__(config['MODEL_NAME'], '1.0')
        self.config = config
        
        # Search models
        self.embedding_model = None
        self.vector_index = None
        self.tfidf_vectorizer = None
        self.stemmer = None
        
        # Search configuration
        self.max_results = config.get('MAX_RESULTS', 50)
        self.semantic_weight = config.get('SEMANTIC_WEIGHT', 0.7)
        self.keyword_weight = config.get('KEYWORD_WEIGHT', 0.3)
        self.min_similarity_threshold = config.get('MIN_SIMILARITY_THRESHOLD', 0.1)
        
        # Searchable models configuration
        self.searchable_models = {
            'employee': {
                'model': 'employee.Employee',
                'fields': ['employee_first_name', 'employee_last_name', 'email', 'phone', 'employee_work_info__job_position__job_position'],
                'display_fields': ['employee_first_name', 'employee_last_name', 'email', 'employee_work_info__department__department'],
                'weight': 1.0,
                'boost_fields': ['employee_first_name', 'employee_last_name']
            },
            'job_position': {
                'model': 'base.JobPosition',
                'fields': ['job_position', 'job_description'],
                'display_fields': ['job_position', 'department__department'],
                'weight': 0.8,
                'boost_fields': ['job_position']
            },
            'department': {
                'model': 'base.Department',
                'fields': ['department', 'hod__employee_first_name', 'hod__employee_last_name'],
                'display_fields': ['department', 'hod__employee_first_name'],
                'weight': 0.7,
                'boost_fields': ['department']
            },
            'leave_request': {
                'model': 'leave.LeaveRequest',
                'fields': ['employee__employee_first_name', 'employee__employee_last_name', 'leave_type__name', 'description'],
                'display_fields': ['employee__employee_first_name', 'leave_type__name', 'start_date'],
                'weight': 0.6,
                'boost_fields': ['leave_type__name']
            },
            'recruitment': {
                'model': 'recruitment.Recruitment',
                'fields': ['job_position__job_position', 'description', 'recruitment_managers__employee_first_name'],
                'display_fields': ['job_position__job_position', 'description', 'start_date'],
                'weight': 0.8,
                'boost_fields': ['job_position__job_position']
            },
            'candidate': {
                'model': 'recruitment.Candidate',
                'fields': ['name', 'email', 'mobile', 'job_position__job_position', 'stage__stage'],
                'display_fields': ['name', 'email', 'job_position__job_position'],
                'weight': 0.7,
                'boost_fields': ['name']
            },
            'budget_plan': {
                'model': 'budget.BudgetPlan',
                'fields': ['title', 'description', 'department__department', 'created_by__employee_first_name'],
                'display_fields': ['title', 'department__department', 'amount'],
                'weight': 0.6,
                'boost_fields': ['title']
            },
            'knowledge_article': {
                'model': 'knowledge.Article',
                'fields': ['title', 'content', 'tags', 'author__employee_first_name'],
                'display_fields': ['title', 'author__employee_first_name', 'created_at'],
                'weight': 0.9,
                'boost_fields': ['title', 'tags']
            }
        }
        
        # Query expansion patterns
        self.query_expansions = {
            'employee': ['staff', 'worker', 'personnel', 'team member'],
            'manager': ['supervisor', 'lead', 'head', 'director'],
            'salary': ['wage', 'compensation', 'pay', 'income'],
            'leave': ['vacation', 'time off', 'absence', 'holiday'],
            'recruitment': ['hiring', 'job posting', 'vacancy', 'position'],
            'training': ['course', 'workshop', 'learning', 'development'],
            'performance': ['evaluation', 'review', 'assessment', 'appraisal'],
            'budget': ['finance', 'cost', 'expense', 'funding']
        }
        
        # Search cache
        self.search_cache = {}
        self.cache_ttl = config.get('CACHE_TTL', 3600)  # 1 hour
        
        # Document embeddings storage
        self.document_embeddings = {}
        self.document_metadata = {}
    
    def load_model(self) -> None:
        """
        Load intelligent search models dan initialize search indices.
        """
        try:
            # Load embedding model
            if SentenceTransformer is not None:
                self._load_embedding_model()
            
            # Initialize TF-IDF vectorizer
            if TfidfVectorizer is not None:
                self._initialize_tfidf()
            
            # Initialize NLTK components
            if nltk is not None:
                self._initialize_nltk()
            
            # Build search indices
            self._build_search_indices()
            
            self.is_loaded = True
            logger.info("Intelligent search models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load intelligent search: {str(e)}")
            self.is_loaded = True  # Continue with available methods
    
    def _load_embedding_model(self) -> None:
        """
        Load sentence embedding model untuk semantic search.
        """
        try:
            model_name = self.config.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            logger.info(f"Loading embedding model: {model_name}")
            
            self.embedding_model = SentenceTransformer(model_name)
            
            # Initialize FAISS index
            if faiss is not None:
                embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
                self.vector_index = faiss.IndexFlatIP(embedding_dim)  # Inner product for cosine similarity
            
            logger.info("Embedding model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {str(e)}")
    
    def _initialize_tfidf(self) -> None:
        """
        Initialize TF-IDF vectorizer untuk keyword search.
        """
        try:
            self.tfidf_vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words='english',
                ngram_range=(1, 2),
                min_df=1,
                max_df=0.95
            )
            
            logger.info("TF-IDF vectorizer initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize TF-IDF: {str(e)}")
    
    def _initialize_nltk(self) -> None:
        """
        Initialize NLTK components untuk text processing.
        """
        try:
            # Download required NLTK data
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                nltk.download('punkt', quiet=True)
            
            try:
                nltk.data.find('corpora/stopwords')
            except LookupError:
                nltk.download('stopwords', quiet=True)
            
            # Initialize stemmer
            if PorterStemmer is not None:
                self.stemmer = PorterStemmer()
            
            logger.info("NLTK components initialized")
            
        except Exception as e:
            logger.warning(f"Failed to initialize NLTK: {str(e)}")
    
    def _build_search_indices(self) -> None:
        """
        Build search indices untuk all searchable models.
        """
        try:
            logger.info("Building search indices...")
            
            all_documents = []
            all_embeddings = []
            
            for model_key, model_config in self.searchable_models.items():
                try:
                    documents = self._extract_model_documents(model_key, model_config)
                    
                    if documents:
                        all_documents.extend(documents)
                        
                        # Generate embeddings jika embedding model available
                        if self.embedding_model is not None:
                            texts = [doc['searchable_text'] for doc in documents]
                            embeddings = self.embedding_model.encode(texts)
                            all_embeddings.extend(embeddings)
                    
                except Exception as e:
                    logger.warning(f"Failed to index model {model_key}: {str(e)}")
            
            # Store document metadata
            self.document_metadata = {i: doc for i, doc in enumerate(all_documents)}
            
            # Build FAISS index
            if all_embeddings and self.vector_index is not None:
                embeddings_array = np.array(all_embeddings).astype('float32')
                # Normalize embeddings untuk cosine similarity
                faiss.normalize_L2(embeddings_array)
                self.vector_index.add(embeddings_array)
                
                logger.info(f"FAISS index built with {len(all_embeddings)} documents")
            
            # Build TF-IDF index
            if all_documents and self.tfidf_vectorizer is not None:
                texts = [doc['searchable_text'] for doc in all_documents]
                self.tfidf_vectorizer.fit(texts)
                
                logger.info(f"TF-IDF index built with {len(texts)} documents")
            
            logger.info(f"Search indices built successfully with {len(all_documents)} total documents")
            
        except Exception as e:
            logger.error(f"Failed to build search indices: {str(e)}")
    
    def _extract_model_documents(self, model_key: str, model_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract searchable documents dari Django model.
        """
        try:
            # Get model class
            app_label, model_name = model_config['model'].split('.')
            model_class = apps.get_model(app_label, model_name)
            
            documents = []
            
            # Query all objects
            queryset = model_class.objects.all()
            
            # Add select_related untuk optimize queries
            if hasattr(model_class, '_meta'):
                related_fields = []
                for field_name in model_config['fields'] + model_config['display_fields']:
                    if '__' in field_name:
                        related_field = field_name.split('__')[0]
                        if related_field not in related_fields:
                            related_fields.append(related_field)
                
                if related_fields:
                    try:
                        queryset = queryset.select_related(*related_fields)
                    except:
                        pass  # Ignore if select_related fails
            
            # Limit queryset untuk performance
            max_docs = self.config.get('MAX_DOCUMENTS_PER_MODEL', 1000)
            queryset = queryset[:max_docs]
            
            for obj in queryset:
                try:
                    # Extract searchable text
                    searchable_text_parts = []
                    display_data = {}
                    
                    # Extract search fields
                    for field_name in model_config['fields']:
                        value = self._get_field_value(obj, field_name)
                        if value:
                            searchable_text_parts.append(str(value))
                    
                    # Extract display fields
                    for field_name in model_config['display_fields']:
                        value = self._get_field_value(obj, field_name)
                        if value:
                            display_data[field_name] = str(value)
                    
                    if searchable_text_parts:
                        searchable_text = ' '.join(searchable_text_parts)
                        
                        document = {
                            'id': obj.pk,
                            'model': model_key,
                            'model_class': model_config['model'],
                            'searchable_text': searchable_text,
                            'display_data': display_data,
                            'weight': model_config['weight'],
                            'boost_fields': model_config['boost_fields'],
                            'url': self._generate_object_url(model_key, obj),
                            'created_at': getattr(obj, 'created_at', None) or timezone.now()
                        }
                        
                        documents.append(document)
                
                except Exception as e:
                    logger.warning(f"Failed to extract document from {model_key} object {obj.pk}: {str(e)}")
            
            logger.info(f"Extracted {len(documents)} documents from {model_key}")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to extract documents from {model_key}: {str(e)}")
            return []
    
    def _get_field_value(self, obj: Any, field_path: str) -> Optional[str]:
        """
        Get field value dari object menggunakan dot notation.
        """
        try:
            current_obj = obj
            field_parts = field_path.split('__')
            
            for field_part in field_parts:
                if hasattr(current_obj, field_part):
                    current_obj = getattr(current_obj, field_part)
                    if current_obj is None:
                        return None
                else:
                    return None
            
            return str(current_obj) if current_obj is not None else None
            
        except Exception:
            return None
    
    def _generate_object_url(self, model_key: str, obj: Any) -> str:
        """
        Generate URL untuk object (placeholder implementation).
        """
        try:
            # This would be customized based on your URL patterns
            return f"/{model_key}/{obj.pk}/"
        except:
            return "#"
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data untuk intelligent search.
        """
        if not isinstance(input_data, dict):
            return False
        
        # Check for required query field
        if 'query' not in input_data or not input_data['query'].strip():
            return False
        
        return True
    
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform intelligent search dengan semantic understanding.
        """
        try:
            query = input_data['query'].strip()
            search_filters = input_data.get('filters', {})
            max_results = input_data.get('max_results', self.max_results)
            search_types = input_data.get('search_types', ['semantic', 'keyword'])
            
            # Check cache
            cache_key = self._generate_cache_key(query, search_filters, max_results, search_types)
            cached_result = self._get_cached_result(cache_key)
            if cached_result:
                return cached_result
            
            # Expand query
            expanded_query = self._expand_query(query)
            
            # Perform different types of search
            search_results = []
            
            # Semantic search
            if 'semantic' in search_types and self.embedding_model is not None:
                semantic_results = self._semantic_search(expanded_query, max_results)
                search_results.append({
                    'type': 'semantic',
                    'results': semantic_results,
                    'weight': self.semantic_weight
                })
            
            # Keyword search
            if 'keyword' in search_types:
                keyword_results = self._keyword_search(expanded_query, max_results)
                search_results.append({
                    'type': 'keyword',
                    'results': keyword_results,
                    'weight': self.keyword_weight
                })
            
            # Combine dan rank results
            final_results = self._combine_and_rank_results(search_results, search_filters, max_results)
            
            # Prepare response
            response = {
                'query': query,
                'expanded_query': expanded_query,
                'total_results': len(final_results),
                'results': final_results[:max_results],
                'search_metadata': {
                    'search_types_used': search_types,
                    'semantic_available': self.embedding_model is not None,
                    'keyword_available': self.tfidf_vectorizer is not None,
                    'total_indexed_documents': len(self.document_metadata),
                    'search_time': datetime.now().isoformat()
                },
                'suggestions': self._generate_search_suggestions(query, final_results)
            }
            
            # Cache result
            self._cache_result(cache_key, response)
            
            return response
            
        except Exception as e:
            raise PredictionError(f"Intelligent search failed: {str(e)}", self.model_name, input_data)
    
    def _expand_query(self, query: str) -> str:
        """
        Expand query dengan synonyms dan related terms.
        """
        try:
            expanded_terms = [query]
            query_lower = query.lower()
            
            # Add expansions berdasarkan predefined patterns
            for term, expansions in self.query_expansions.items():
                if term in query_lower:
                    expanded_terms.extend(expansions)
            
            # Add stemmed versions jika stemmer available
            if self.stemmer is not None and word_tokenize is not None:
                try:
                    tokens = word_tokenize(query_lower)
                    stemmed_tokens = [self.stemmer.stem(token) for token in tokens if token.isalpha()]
                    expanded_terms.extend(stemmed_tokens)
                except:
                    pass
            
            return ' '.join(set(expanded_terms))
            
        except Exception as e:
            logger.warning(f"Query expansion failed: {str(e)}")
            return query
    
    def _semantic_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Perform semantic search menggunakan embeddings.
        """
        try:
            if self.vector_index is None or self.vector_index.ntotal == 0:
                return []
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode([query])
            query_embedding = query_embedding.astype('float32')
            faiss.normalize_L2(query_embedding)
            
            # Search similar documents
            k = min(max_results * 2, self.vector_index.ntotal)  # Get more results untuk filtering
            similarities, indices = self.vector_index.search(query_embedding, k)
            
            results = []
            for i, (similarity, doc_idx) in enumerate(zip(similarities[0], indices[0])):
                if similarity < self.min_similarity_threshold:
                    continue
                
                if doc_idx in self.document_metadata:
                    doc = self.document_metadata[doc_idx].copy()
                    doc['similarity_score'] = float(similarity)
                    doc['rank'] = i + 1
                    doc['search_type'] = 'semantic'
                    results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            return []
    
    def _keyword_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Perform keyword search menggunakan TF-IDF.
        """
        try:
            if self.tfidf_vectorizer is None:
                return self._simple_keyword_search(query, max_results)
            
            # Transform query
            query_vector = self.tfidf_vectorizer.transform([query])
            
            # Get all document vectors
            all_texts = [doc['searchable_text'] for doc in self.document_metadata.values()]
            doc_vectors = self.tfidf_vectorizer.transform(all_texts)
            
            # Calculate similarities
            if cosine_similarity is not None:
                similarities = cosine_similarity(query_vector, doc_vectors).flatten()
            else:
                # Fallback to simple dot product
                similarities = (query_vector * doc_vectors.T).toarray().flatten()
            
            # Get top results
            top_indices = np.argsort(similarities)[::-1][:max_results * 2]
            
            results = []
            for i, doc_idx in enumerate(top_indices):
                similarity = similarities[doc_idx]
                
                if similarity < self.min_similarity_threshold:
                    continue
                
                if doc_idx in self.document_metadata:
                    doc = self.document_metadata[doc_idx].copy()
                    doc['similarity_score'] = float(similarity)
                    doc['rank'] = i + 1
                    doc['search_type'] = 'keyword'
                    results.append(doc)
            
            return results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {str(e)}")
            return self._simple_keyword_search(query, max_results)
    
    def _simple_keyword_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        """
        Simple keyword search sebagai fallback.
        """
        try:
            query_terms = query.lower().split()
            results = []
            
            for doc_idx, doc in self.document_metadata.items():
                text_lower = doc['searchable_text'].lower()
                
                # Count matching terms
                matches = sum(1 for term in query_terms if term in text_lower)
                
                if matches > 0:
                    # Simple scoring berdasarkan term frequency
                    score = matches / len(query_terms)
                    
                    # Boost score untuk boost fields
                    for boost_field in doc.get('boost_fields', []):
                        boost_text = ''
                        for field_name in doc['display_data']:
                            if boost_field in field_name:
                                boost_text += doc['display_data'][field_name].lower() + ' '
                        
                        boost_matches = sum(1 for term in query_terms if term in boost_text)
                        if boost_matches > 0:
                            score += boost_matches * 0.5
                    
                    doc_result = doc.copy()
                    doc_result['similarity_score'] = score
                    doc_result['search_type'] = 'simple_keyword'
                    results.append(doc_result)
            
            # Sort by score
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Add ranks
            for i, result in enumerate(results[:max_results]):
                result['rank'] = i + 1
            
            return results[:max_results]
            
        except Exception as e:
            logger.error(f"Simple keyword search failed: {str(e)}")
            return []
    
    def _combine_and_rank_results(self, search_results: List[Dict[str, Any]], 
                                 filters: Dict[str, Any], max_results: int) -> List[Dict[str, Any]]:
        """
        Combine results dari multiple search methods dan apply ranking.
        """
        try:
            # Collect all results dengan weighted scores
            combined_results = {}
            
            for search_result in search_results:
                search_type = search_result['type']
                weight = search_result['weight']
                results = search_result['results']
                
                for result in results:
                    doc_key = f"{result['model']}_{result['id']}"
                    
                    if doc_key not in combined_results:
                        combined_results[doc_key] = result.copy()
                        combined_results[doc_key]['combined_score'] = 0.0
                        combined_results[doc_key]['search_methods'] = []
                    
                    # Add weighted score
                    weighted_score = result['similarity_score'] * weight * result['weight']
                    combined_results[doc_key]['combined_score'] += weighted_score
                    combined_results[doc_key]['search_methods'].append(search_type)
            
            # Convert to list
            final_results = list(combined_results.values())
            
            # Apply filters
            if filters:
                final_results = self._apply_filters(final_results, filters)
            
            # Sort by combined score
            final_results.sort(key=lambda x: x['combined_score'], reverse=True)
            
            # Add final ranks
            for i, result in enumerate(final_results):
                result['final_rank'] = i + 1
            
            return final_results
            
        except Exception as e:
            logger.error(f"Result combination failed: {str(e)}")
            return []
    
    def _apply_filters(self, results: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Apply search filters ke results.
        """
        try:
            filtered_results = results
            
            # Model type filter
            if 'models' in filters and filters['models']:
                allowed_models = filters['models']
                filtered_results = [r for r in filtered_results if r['model'] in allowed_models]
            
            # Date range filter
            if 'date_from' in filters or 'date_to' in filters:
                date_from = filters.get('date_from')
                date_to = filters.get('date_to')
                
                if date_from:
                    date_from = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
                if date_to:
                    date_to = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
                
                def date_filter(result):
                    created_at = result.get('created_at')
                    if not created_at:
                        return True
                    
                    if isinstance(created_at, str):
                        created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    
                    if date_from and created_at < date_from:
                        return False
                    if date_to and created_at > date_to:
                        return False
                    
                    return True
                
                filtered_results = [r for r in filtered_results if date_filter(r)]
            
            # Minimum score filter
            if 'min_score' in filters:
                min_score = float(filters['min_score'])
                filtered_results = [r for r in filtered_results if r['combined_score'] >= min_score]
            
            return filtered_results
            
        except Exception as e:
            logger.error(f"Filter application failed: {str(e)}")
            return results
    
    def _generate_search_suggestions(self, query: str, results: List[Dict[str, Any]]) -> List[str]:
        """
        Generate search suggestions berdasarkan query dan results.
        """
        try:
            suggestions = []
            
            # Suggest related terms berdasarkan query expansions
            query_lower = query.lower()
            for term, expansions in self.query_expansions.items():
                if term in query_lower:
                    suggestions.extend([f"{query} {exp}" for exp in expansions[:2]])
            
            # Suggest berdasarkan popular terms dalam results
            if results:
                popular_terms = defaultdict(int)
                for result in results[:10]:  # Top 10 results
                    text = result['searchable_text'].lower()
                    words = re.findall(r'\b\w+\b', text)
                    for word in words:
                        if len(word) > 3 and word not in query_lower:
                            popular_terms[word] += 1
                
                # Add top popular terms
                top_terms = sorted(popular_terms.items(), key=lambda x: x[1], reverse=True)[:3]
                for term, _ in top_terms:
                    suggestions.append(f"{query} {term}")
            
            # Remove duplicates dan limit
            suggestions = list(set(suggestions))[:5]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Suggestion generation failed: {str(e)}")
            return []
    
    def _generate_cache_key(self, query: str, filters: Dict[str, Any], 
                           max_results: int, search_types: List[str]) -> str:
        """
        Generate cache key untuk search results.
        """
        try:
            cache_data = {
                'query': query,
                'filters': filters,
                'max_results': max_results,
                'search_types': sorted(search_types)
            }
            
            cache_string = json.dumps(cache_data, sort_keys=True)
            return hashlib.md5(cache_string.encode()).hexdigest()
            
        except Exception:
            return hashlib.md5(query.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached search result.
        """
        try:
            return cache.get(f"intelligent_search_{cache_key}")
        except Exception:
            return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """
        Cache search result.
        """
        try:
            cache.set(f"intelligent_search_{cache_key}", result, self.cache_ttl)
        except Exception as e:
            logger.warning(f"Failed to cache search result: {str(e)}")
    
    def rebuild_search_index(self) -> Dict[str, Any]:
        """
        Rebuild search index dengan fresh data.
        """
        try:
            logger.info("Rebuilding search index...")
            
            # Clear existing indices
            if self.vector_index is not None:
                self.vector_index.reset()
            
            self.document_metadata.clear()
            
            # Rebuild indices
            self._build_search_indices()
            
            # Clear cache
            try:
                cache.delete_many([key for key in cache._cache.keys() if key.startswith('intelligent_search_')])
            except:
                pass
            
            return {
                'status': 'success',
                'total_documents': len(self.document_metadata),
                'indexed_models': list(self.searchable_models.keys()),
                'rebuild_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Index rebuild failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_search_statistics(self) -> Dict[str, Any]:
        """
        Get search system statistics.
        """
        try:
            stats = {
                'total_indexed_documents': len(self.document_metadata),
                'indexed_models': {},
                'search_capabilities': {
                    'semantic_search': self.embedding_model is not None,
                    'keyword_search': self.tfidf_vectorizer is not None,
                    'query_expansion': True,
                    'result_caching': True
                },
                'configuration': {
                    'max_results': self.max_results,
                    'semantic_weight': self.semantic_weight,
                    'keyword_weight': self.keyword_weight,
                    'min_similarity_threshold': self.min_similarity_threshold,
                    'cache_ttl': self.cache_ttl
                }
            }
            
            # Count documents per model
            for doc in self.document_metadata.values():
                model = doc['model']
                if model not in stats['indexed_models']:
                    stats['indexed_models'][model] = 0
                stats['indexed_models'][model] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get search statistics: {str(e)}")
            return {'error': str(e)}
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed information tentang intelligent search service.
        """
        info = super().get_model_info()
        
        info.update({
            'embedding_model_loaded': self.embedding_model is not None,
            'vector_index_available': self.vector_index is not None,
            'tfidf_available': self.tfidf_vectorizer is not None,
            'nltk_available': nltk is not None,
            'searchable_models': list(self.searchable_models.keys()),
            'search_types': ['semantic', 'keyword', 'simple_keyword'],
            'query_expansion_available': True,
            'result_caching_enabled': True,
            'total_indexed_documents': len(self.document_metadata)
        })
        
        return info