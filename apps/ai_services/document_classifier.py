import os
import json
import mimetypes
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
import hashlib
from pathlib import Path

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    from sentence_transformers import SentenceTransformer
    import torch
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.pipeline import Pipeline
    import joblib
except ImportError:
    # Fallback jika libraries tidak tersedia
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    pipeline = None
    torch = None
    np = None
    TfidfVectorizer = None
    MultinomialNB = None
    Pipeline = None
    joblib = None
    SentenceTransformer = None

try:
    import PyPDF2
    import docx
    from PIL import Image
    import pytesseract
except ImportError:
    PyPDF2 = None
    docx = None
    Image = None
    pytesseract = None

from django.utils import timezone
from django.core.files.storage import default_storage

from .base import BaseAIService
from .config import AIConfig
from .exceptions import PredictionError, ModelLoadError, ValidationError

logger = logging.getLogger(__name__)

class DocumentClassifierService(BaseAIService):
    """
    AI Service untuk Document Classification dengan akurasi tinggi.
    Mendukung berbagai format dokumen dan multiple classification approaches.
    """
    
    def __init__(self):
        config = AIConfig.get_config('document')
        super().__init__(config['MODEL_NAME'], '1.0')
        self.config = config
        
        # Classification models
        self.transformer_model = None
        self.transformer_tokenizer = None
        self.classification_pipeline = None
        self.embedding_model = None
        self.traditional_classifier = None
        
        # Document categories dengan detailed descriptions
        self.document_categories = {
            'resume_cv': {
                'name': 'Resume/CV',
                'description': 'Curriculum vitae, resume, or professional profile documents',
                'keywords': ['resume', 'cv', 'curriculum vitae', 'experience', 'education', 'skills', 'employment history'],
                'file_patterns': ['resume', 'cv', 'curriculum'],
                'confidence_threshold': 0.7
            },
            'job_description': {
                'name': 'Job Description',
                'description': 'Job postings, position descriptions, and role requirements',
                'keywords': ['job description', 'position', 'requirements', 'responsibilities', 'qualifications', 'salary', 'benefits'],
                'file_patterns': ['job', 'position', 'role', 'vacancy'],
                'confidence_threshold': 0.75
            },
            'contract': {
                'name': 'Contract/Agreement',
                'description': 'Employment contracts, agreements, and legal documents',
                'keywords': ['contract', 'agreement', 'terms', 'conditions', 'party', 'whereas', 'hereby', 'signature'],
                'file_patterns': ['contract', 'agreement', 'terms'],
                'confidence_threshold': 0.8
            },
            'policy_document': {
                'name': 'Policy Document',
                'description': 'Company policies, procedures, and guidelines',
                'keywords': ['policy', 'procedure', 'guideline', 'standard', 'protocol', 'compliance', 'regulation'],
                'file_patterns': ['policy', 'procedure', 'guideline'],
                'confidence_threshold': 0.7
            },
            'financial_document': {
                'name': 'Financial Document',
                'description': 'Invoices, receipts, financial reports, and accounting documents',
                'keywords': ['invoice', 'receipt', 'payment', 'amount', 'total', 'tax', 'financial', 'accounting', 'budget'],
                'file_patterns': ['invoice', 'receipt', 'financial', 'budget'],
                'confidence_threshold': 0.8
            },
            'training_material': {
                'name': 'Training Material',
                'description': 'Training documents, educational content, and learning materials',
                'keywords': ['training', 'course', 'module', 'lesson', 'learning', 'education', 'tutorial', 'workshop'],
                'file_patterns': ['training', 'course', 'tutorial'],
                'confidence_threshold': 0.7
            },
            'performance_review': {
                'name': 'Performance Review',
                'description': 'Performance evaluations, appraisals, and feedback documents',
                'keywords': ['performance', 'review', 'evaluation', 'appraisal', 'feedback', 'goals', 'rating', 'assessment'],
                'file_patterns': ['performance', 'review', 'evaluation'],
                'confidence_threshold': 0.75
            },
            'leave_request': {
                'name': 'Leave Request',
                'description': 'Leave applications, time-off requests, and absence forms',
                'keywords': ['leave', 'vacation', 'absence', 'time off', 'holiday', 'sick leave', 'request', 'application'],
                'file_patterns': ['leave', 'vacation', 'absence'],
                'confidence_threshold': 0.8
            },
            'certificate': {
                'name': 'Certificate/Credential',
                'description': 'Certificates, diplomas, licenses, and professional credentials',
                'keywords': ['certificate', 'diploma', 'license', 'certification', 'credential', 'award', 'achievement'],
                'file_patterns': ['certificate', 'diploma', 'license'],
                'confidence_threshold': 0.8
            },
            'other': {
                'name': 'Other/Miscellaneous',
                'description': 'Documents that do not fit into specific categories',
                'keywords': [],
                'file_patterns': [],
                'confidence_threshold': 0.5
            }
        }
        
        # Supported file formats
        self.supported_formats = {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.txt': 'text/plain',
            '.rtf': 'application/rtf',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.tiff': 'image/tiff',
            '.bmp': 'image/bmp'
        }
    
    def load_model(self) -> None:
        """
        Load document classification models.
        """
        try:
            # Load transformer-based model
            if AutoTokenizer is not None and AutoModelForSequenceClassification is not None:
                self._load_transformer_model()
            
            # Load embedding model
            if SentenceTransformer is not None:
                self._load_embedding_model()
            
            # Load or train traditional classifier
            self._load_traditional_classifier()
            
            self.is_loaded = True
            logger.info("Document classifier models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load document classifier: {str(e)}")
            self.is_loaded = True  # Continue with available methods
    
    def _load_transformer_model(self) -> None:
        """
        Load transformer-based classification model.
        """
        try:
            model_name = self.config.get('TRANSFORMER_MODEL', 'distilbert-base-uncased')
            logger.info(f"Loading transformer model: {model_name}")
            
            self.transformer_tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Try to load fine-tuned model, fallback to base model
            try:
                classifier_path = self.config.get('DOCUMENT_CLASSIFIER_PATH', model_name)
                self.transformer_model = AutoModelForSequenceClassification.from_pretrained(
                    classifier_path, num_labels=len(self.document_categories)
                )
            except:
                logger.info("Using base transformer model for document classification")
                self.transformer_model = AutoModelForSequenceClassification.from_pretrained(
                    model_name, num_labels=len(self.document_categories)
                )
            
            # Create classification pipeline
            if pipeline is not None:
                self.classification_pipeline = pipeline(
                    "text-classification",
                    model=self.transformer_model,
                    tokenizer=self.transformer_tokenizer,
                    return_all_scores=True
                )
            
            logger.info("Transformer model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load transformer model: {str(e)}")
    
    def _load_embedding_model(self) -> None:
        """
        Load embedding model untuk similarity-based classification.
        """
        try:
            embedding_model_name = self.config.get('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
            logger.info(f"Loading embedding model: {embedding_model_name}")
            
            self.embedding_model = SentenceTransformer(embedding_model_name)
            
            logger.info("Embedding model loaded successfully")
            
        except Exception as e:
            logger.warning(f"Failed to load embedding model: {str(e)}")
    
    def _load_traditional_classifier(self) -> None:
        """
        Load atau train traditional ML classifier sebagai fallback.
        """
        try:
            if TfidfVectorizer is None or MultinomialNB is None:
                logger.warning("Scikit-learn not available, skipping traditional classifier")
                return
            
            classifier_path = self.config.get('TRADITIONAL_CLASSIFIER_PATH', 'document_classifier.joblib')
            
            # Try to load existing classifier
            if os.path.exists(classifier_path) and joblib is not None:
                try:
                    self.traditional_classifier = joblib.load(classifier_path)
                    logger.info("Traditional classifier loaded from file")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load existing classifier: {str(e)}")
            
            # Train new classifier dengan synthetic data
            self._train_traditional_classifier()
            
        except Exception as e:
            logger.warning(f"Failed to setup traditional classifier: {str(e)}")
    
    def _train_traditional_classifier(self) -> None:
        """
        Train traditional classifier dengan synthetic training data.
        """
        try:
            # Generate synthetic training data berdasarkan keywords
            training_texts = []
            training_labels = []
            
            for category, config in self.document_categories.items():
                if category == 'other':
                    continue
                
                keywords = config['keywords']
                
                # Generate synthetic documents
                for i in range(10):  # 10 samples per category
                    # Create document dengan random combination of keywords
                    import random
                    selected_keywords = random.sample(keywords, min(len(keywords), random.randint(3, 6)))
                    synthetic_text = ' '.join(selected_keywords) + ' document content example'
                    
                    training_texts.append(synthetic_text)
                    training_labels.append(category)
            
            # Train classifier
            if training_texts:
                self.traditional_classifier = Pipeline([
                    ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
                    ('classifier', MultinomialNB())
                ])
                
                self.traditional_classifier.fit(training_texts, training_labels)
                
                # Save classifier
                if joblib is not None:
                    classifier_path = self.config.get('TRADITIONAL_CLASSIFIER_PATH', 'document_classifier.joblib')
                    joblib.dump(self.traditional_classifier, classifier_path)
                
                logger.info("Traditional classifier trained successfully")
            
        except Exception as e:
            logger.error(f"Failed to train traditional classifier: {str(e)}")
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data untuk document classification.
        """
        if not isinstance(input_data, dict):
            return False
        
        # Check for required fields
        if 'document' not in input_data:
            return False
        
        document = input_data['document']
        
        # Check if document has content or file path
        if 'content' not in document and 'file_path' not in document:
            return False
        
        # Validate file format if file_path provided
        if 'file_path' in document:
            file_path = document['file_path']
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext not in self.supported_formats:
                return False
        
        return True
    
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify document berdasarkan content dan metadata.
        """
        try:
            document = input_data['document']
            classification_methods = input_data.get('methods', ['all'])
            
            # Extract document content
            if 'content' in document:
                content = document['content']
                file_info = {'name': document.get('name', 'unknown'), 'size': len(content)}
            else:
                content, file_info = self._extract_document_content(document['file_path'])
            
            if not content:
                return {'error': 'Could not extract document content'}
            
            # Perform classification menggunakan multiple methods
            results = {
                'document_info': file_info,
                'content_preview': content[:200] + '...' if len(content) > 200 else content,
                'content_length': len(content),
                'word_count': len(content.split())
            }
            
            # Method 1: Transformer-based classification
            if ('all' in classification_methods or 'transformer' in classification_methods) and self.classification_pipeline:
                transformer_result = self._classify_with_transformer(content)
                results['transformer_classification'] = transformer_result
            
            # Method 2: Embedding-based classification
            if ('all' in classification_methods or 'embedding' in classification_methods) and self.embedding_model:
                embedding_result = self._classify_with_embeddings(content)
                results['embedding_classification'] = embedding_result
            
            # Method 3: Traditional ML classification
            if ('all' in classification_methods or 'traditional' in classification_methods) and self.traditional_classifier:
                traditional_result = self._classify_with_traditional_ml(content)
                results['traditional_classification'] = traditional_result
            
            # Method 4: Rule-based classification (always available)
            if 'all' in classification_methods or 'rule_based' in classification_methods:
                rule_based_result = self._classify_with_rules(content, file_info)
                results['rule_based_classification'] = rule_based_result
            
            # Ensemble classification (combine all methods)
            ensemble_result = self._ensemble_classification(results)
            results['final_classification'] = ensemble_result
            
            # Add confidence metrics
            results['classification_confidence'] = self._calculate_classification_confidence(results)
            
            return results
            
        except Exception as e:
            raise PredictionError(f"Document classification failed: {str(e)}", self.model_name, input_data)
    
    def _extract_document_content(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Extract text content dari berbagai format dokumen.
        """
        try:
            file_path = Path(file_path)
            file_ext = file_path.suffix.lower()
            
            file_info = {
                'name': file_path.name,
                'extension': file_ext,
                'size': file_path.stat().st_size if file_path.exists() else 0
            }
            
            content = ""
            
            if file_ext == '.pdf':
                content = self._extract_pdf_content(file_path)
            elif file_ext in ['.doc', '.docx']:
                content = self._extract_word_content(file_path)
            elif file_ext == '.txt':
                content = self._extract_text_content(file_path)
            elif file_ext in ['.jpg', '.jpeg', '.png', '.tiff', '.bmp']:
                content = self._extract_image_content(file_path)
            else:
                # Try to read as text
                content = self._extract_text_content(file_path)
            
            return content, file_info
            
        except Exception as e:
            logger.error(f"Content extraction failed: {str(e)}")
            return "", {'name': str(file_path), 'error': str(e)}
    
    def _extract_pdf_content(self, file_path: Path) -> str:
        """
        Extract text dari PDF files.
        """
        try:
            if PyPDF2 is None:
                raise ImportError("PyPDF2 not available")
            
            content = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            return ""
    
    def _extract_word_content(self, file_path: Path) -> str:
        """
        Extract text dari Word documents.
        """
        try:
            if docx is None:
                raise ImportError("python-docx not available")
            
            if file_path.suffix.lower() == '.docx':
                doc = docx.Document(file_path)
                content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
                return content
            else:
                # For .doc files, try to read as text (limited support)
                return self._extract_text_content(file_path)
                
        except Exception as e:
            logger.error(f"Word document extraction failed: {str(e)}")
            return ""
    
    def _extract_text_content(self, file_path: Path) -> str:
        """
        Extract text dari plain text files.
        """
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as file:
                        return file.read()
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, read as binary and decode with errors='ignore'
            with open(file_path, 'rb') as file:
                return file.read().decode('utf-8', errors='ignore')
                
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return ""
    
    def _extract_image_content(self, file_path: Path) -> str:
        """
        Extract text dari images menggunakan OCR.
        """
        try:
            if Image is None or pytesseract is None:
                logger.warning("PIL or pytesseract not available for OCR")
                return ""
            
            # Open image
            image = Image.open(file_path)
            
            # Perform OCR
            content = pytesseract.image_to_string(image)
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {str(e)}")
            return ""
    
    def _classify_with_transformer(self, content: str) -> Dict[str, Any]:
        """
        Classify document menggunakan transformer model.
        """
        try:
            # Truncate content if too long
            max_length = 512
            words = content.split()
            if len(words) > max_length:
                content = ' '.join(words[:max_length])
            
            # Get predictions
            results = self.classification_pipeline(content)
            
            # Process results
            predictions = {}
            for result in results[0]:  # First (and only) text result
                label = result['label']
                score = result['score']
                predictions[label] = score
            
            # Get top prediction
            top_category = max(predictions, key=predictions.get)
            confidence = predictions[top_category]
            
            return {
                'predicted_category': top_category,
                'confidence': round(confidence, 4),
                'all_scores': {k: round(v, 4) for k, v in predictions.items()},
                'method': 'transformer'
            }
            
        except Exception as e:
            logger.error(f"Transformer classification failed: {str(e)}")
            return {'error': str(e), 'method': 'transformer'}
    
    def _classify_with_embeddings(self, content: str) -> Dict[str, Any]:
        """
        Classify document menggunakan embedding similarity.
        """
        try:
            # Create embeddings untuk document content
            content_embedding = self.embedding_model.encode([content])
            
            # Create embeddings untuk category descriptions
            category_descriptions = []
            category_names = []
            
            for category, config in self.document_categories.items():
                if category != 'other':
                    description = config['description'] + ' ' + ' '.join(config['keywords'])
                    category_descriptions.append(description)
                    category_names.append(category)
            
            category_embeddings = self.embedding_model.encode(category_descriptions)
            
            # Calculate similarities
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(content_embedding, category_embeddings)[0]
            
            # Create predictions
            predictions = {}
            for i, category in enumerate(category_names):
                predictions[category] = similarities[i]
            
            # Add 'other' category dengan lower score
            predictions['other'] = max(0, 1 - max(similarities))
            
            # Get top prediction
            top_category = max(predictions, key=predictions.get)
            confidence = predictions[top_category]
            
            return {
                'predicted_category': top_category,
                'confidence': round(confidence, 4),
                'all_scores': {k: round(v, 4) for k, v in predictions.items()},
                'method': 'embedding_similarity'
            }
            
        except Exception as e:
            logger.error(f"Embedding classification failed: {str(e)}")
            return {'error': str(e), 'method': 'embedding_similarity'}
    
    def _classify_with_traditional_ml(self, content: str) -> Dict[str, Any]:
        """
        Classify document menggunakan traditional ML model.
        """
        try:
            # Get prediction
            prediction = self.traditional_classifier.predict([content])[0]
            
            # Get prediction probabilities
            try:
                probabilities = self.traditional_classifier.predict_proba([content])[0]
                classes = self.traditional_classifier.classes_
                
                predictions = {}
                for i, class_name in enumerate(classes):
                    predictions[class_name] = probabilities[i]
                
                confidence = predictions[prediction]
                
            except:
                # If probabilities not available
                predictions = {prediction: 1.0}
                confidence = 1.0
            
            return {
                'predicted_category': prediction,
                'confidence': round(confidence, 4),
                'all_scores': {k: round(v, 4) for k, v in predictions.items()},
                'method': 'traditional_ml'
            }
            
        except Exception as e:
            logger.error(f"Traditional ML classification failed: {str(e)}")
            return {'error': str(e), 'method': 'traditional_ml'}
    
    def _classify_with_rules(self, content: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify document menggunakan rule-based approach.
        """
        try:
            content_lower = content.lower()
            filename_lower = file_info.get('name', '').lower()
            
            category_scores = {}
            
            # Score berdasarkan keywords dalam content
            for category, config in self.document_categories.items():
                score = 0.0
                
                # Keyword matching dalam content
                for keyword in config['keywords']:
                    if keyword.lower() in content_lower:
                        score += 1.0
                
                # File pattern matching
                for pattern in config['file_patterns']:
                    if pattern.lower() in filename_lower:
                        score += 0.5
                
                # Normalize score
                max_possible_score = len(config['keywords']) + len(config['file_patterns']) * 0.5
                if max_possible_score > 0:
                    score = score / max_possible_score
                
                category_scores[category] = score
            
            # If no category has significant score, assign to 'other'
            max_score = max(category_scores.values()) if category_scores else 0
            if max_score < 0.1:
                category_scores['other'] = 0.8
            
            # Get top prediction
            top_category = max(category_scores, key=category_scores.get)
            confidence = category_scores[top_category]
            
            return {
                'predicted_category': top_category,
                'confidence': round(confidence, 4),
                'all_scores': {k: round(v, 4) for k, v in category_scores.items()},
                'method': 'rule_based'
            }
            
        except Exception as e:
            logger.error(f"Rule-based classification failed: {str(e)}")
            return {'error': str(e), 'method': 'rule_based'}
    
    def _ensemble_classification(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine predictions dari multiple methods untuk final classification.
        """
        try:
            # Collect predictions dari all methods
            method_predictions = {}
            method_weights = {
                'transformer_classification': 0.4,
                'embedding_classification': 0.3,
                'traditional_classification': 0.2,
                'rule_based_classification': 0.1
            }
            
            # Extract predictions
            for method_key, weight in method_weights.items():
                if method_key in results and 'error' not in results[method_key]:
                    method_predictions[method_key] = {
                        'prediction': results[method_key]['predicted_category'],
                        'confidence': results[method_key]['confidence'],
                        'weight': weight
                    }
            
            if not method_predictions:
                return {
                    'predicted_category': 'other',
                    'confidence': 0.0,
                    'method': 'ensemble',
                    'error': 'No valid predictions available'
                }
            
            # Calculate weighted scores untuk each category
            category_scores = {}
            
            for method_key, method_data in method_predictions.items():
                category = method_data['prediction']
                confidence = method_data['confidence']
                weight = method_data['weight']
                
                weighted_score = confidence * weight
                
                if category not in category_scores:
                    category_scores[category] = 0.0
                
                category_scores[category] += weighted_score
            
            # Normalize scores
            total_weight = sum(data['weight'] for data in method_predictions.values())
            for category in category_scores:
                category_scores[category] = category_scores[category] / total_weight
            
            # Get final prediction
            final_category = max(category_scores, key=category_scores.get)
            final_confidence = category_scores[final_category]
            
            # Check confidence threshold
            threshold = self.document_categories[final_category]['confidence_threshold']
            if final_confidence < threshold:
                final_category = 'other'
                final_confidence = category_scores.get('other', 0.5)
            
            return {
                'predicted_category': final_category,
                'confidence': round(final_confidence, 4),
                'all_scores': {k: round(v, 4) for k, v in category_scores.items()},
                'method': 'ensemble',
                'contributing_methods': list(method_predictions.keys()),
                'category_info': self.document_categories[final_category]
            }
            
        except Exception as e:
            logger.error(f"Ensemble classification failed: {str(e)}")
            return {
                'predicted_category': 'other',
                'confidence': 0.0,
                'method': 'ensemble',
                'error': str(e)
            }
    
    def _calculate_classification_confidence(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate overall confidence metrics untuk classification.
        """
        try:
            final_result = results.get('final_classification', {})
            
            # Count successful methods
            successful_methods = 0
            total_methods = 0
            
            method_keys = [
                'transformer_classification',
                'embedding_classification', 
                'traditional_classification',
                'rule_based_classification'
            ]
            
            for method_key in method_keys:
                total_methods += 1
                if method_key in results and 'error' not in results[method_key]:
                    successful_methods += 1
            
            # Calculate agreement score
            predictions = []
            for method_key in method_keys:
                if method_key in results and 'error' not in results[method_key]:
                    predictions.append(results[method_key]['predicted_category'])
            
            agreement_score = 0.0
            if predictions:
                most_common = max(set(predictions), key=predictions.count)
                agreement_score = predictions.count(most_common) / len(predictions)
            
            return {
                'overall_confidence': final_result.get('confidence', 0.0),
                'method_success_rate': successful_methods / total_methods,
                'prediction_agreement': round(agreement_score, 4),
                'successful_methods': successful_methods,
                'total_methods': total_methods,
                'reliability_score': round((final_result.get('confidence', 0.0) * agreement_score), 4)
            }
            
        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            return {
                'error': str(e)
            }
    
    def batch_classify_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Classify multiple documents dalam batch untuk efficiency.
        """
        try:
            results = []
            batch_size = self.config.get('BATCH_SIZE', 8)
            
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_results = []
                
                for doc in batch_docs:
                    try:
                        input_data = {'document': doc}
                        result = self.safe_predict(input_data, use_cache=True)
                        batch_results.append(result)
                    except Exception as e:
                        logger.error(f"Batch classification failed for document: {str(e)}")
                        batch_results.append({
                            'error': str(e),
                            'document_info': doc
                        })
                
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch document classification failed: {str(e)}")
            return [{'error': str(e)} for _ in documents]
    
    def get_supported_formats(self) -> Dict[str, Any]:
        """
        Get list of supported document formats.
        """
        return {
            'supported_extensions': list(self.supported_formats.keys()),
            'supported_mime_types': list(self.supported_formats.values()),
            'ocr_supported': Image is not None and pytesseract is not None,
            'pdf_supported': PyPDF2 is not None,
            'word_supported': docx is not None
        }
    
    def get_document_categories(self) -> Dict[str, Any]:
        """
        Get available document categories dengan descriptions.
        """
        return self.document_categories
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed information tentang document classifier.
        """
        info = super().get_model_info()
        
        info.update({
            'transformer_model_loaded': self.transformer_model is not None,
            'embedding_model_loaded': self.embedding_model is not None,
            'traditional_classifier_loaded': self.traditional_classifier is not None,
            'supported_formats': list(self.supported_formats.keys()),
            'document_categories': list(self.document_categories.keys()),
            'classification_methods': ['transformer', 'embedding', 'traditional', 'rule_based', 'ensemble'],
            'ocr_available': Image is not None and pytesseract is not None,
            'batch_processing_supported': True
        })
        
        return info