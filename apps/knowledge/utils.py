import os
import re
import json
import uuid
import mimetypes
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from celery import shared_task
import PyPDF2
import docx
import openpyxl
from bs4 import BeautifulSoup
import requests
from textstat import flesch_reading_ease, flesch_kincaid_grade
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import PorterStemmer
import logging

logger = logging.getLogger(__name__)

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')


class DocumentProcessor:
    """Document processing utilities"""
    
    def __init__(self):
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words('english'))
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text content from various file formats"""
        try:
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.pdf':
                return self._extract_from_pdf(file_path)
            elif file_extension in ['.doc', '.docx']:
                return self._extract_from_docx(file_path)
            elif file_extension in ['.xls', '.xlsx']:
                return self._extract_from_excel(file_path)
            elif file_extension == '.txt':
                return self._extract_from_txt(file_path)
            elif file_extension == '.html':
                return self._extract_from_html(file_path)
            else:
                logger.warning(f"Unsupported file format: {file_extension}")
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {str(e)}")
            return ""
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e:
            logger.error(f"Error reading PDF: {str(e)}")
        return text
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text
        except Exception as e:
            logger.error(f"Error reading DOCX: {str(e)}")
            return ""
    
    def _extract_from_excel(self, file_path: str) -> str:
        """Extract text from Excel file"""
        try:
            workbook = openpyxl.load_workbook(file_path)
            text = ""
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows(values_only=True):
                    row_text = " ".join([str(cell) for cell in row if cell is not None])
                    text += row_text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error reading Excel: {str(e)}")
            return ""
    
    def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error reading TXT: {str(e)}")
            return ""
    
    def _extract_from_html(self, file_path: str) -> str:
        """Extract text from HTML file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                soup = BeautifulSoup(file.read(), 'html.parser')
                return soup.get_text()
        except Exception as e:
            logger.error(f"Error reading HTML: {str(e)}")
            return ""
    
    def preprocess_text(self, text: str) -> str:
        """Preprocess text for analysis"""
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and digits
        text = re.sub(r'[^a-zA-Z\s]', '', text)
        
        # Tokenize
        tokens = word_tokenize(text)
        
        # Remove stopwords and stem
        processed_tokens = [
            self.stemmer.stem(token) for token in tokens 
            if token not in self.stop_words and len(token) > 2
        ]
        
        return ' '.join(processed_tokens)
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords using TF-IDF"""
        try:
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            # Use TF-IDF to extract keywords
            vectorizer = TfidfVectorizer(max_features=max_keywords, ngram_range=(1, 2))
            tfidf_matrix = vectorizer.fit_transform([processed_text])
            
            # Get feature names (keywords)
            feature_names = vectorizer.get_feature_names_out()
            tfidf_scores = tfidf_matrix.toarray()[0]
            
            # Sort by TF-IDF score
            keyword_scores = list(zip(feature_names, tfidf_scores))
            keyword_scores.sort(key=lambda x: x[1], reverse=True)
            
            return [keyword for keyword, score in keyword_scores if score > 0]
        except Exception as e:
            logger.error(f"Error extracting keywords: {str(e)}")
            return []
    
    def calculate_readability(self, text: str) -> Dict[str, float]:
        """Calculate readability scores"""
        try:
            return {
                'flesch_reading_ease': flesch_reading_ease(text),
                'flesch_kincaid_grade': flesch_kincaid_grade(text)
            }
        except Exception as e:
            logger.error(f"Error calculating readability: {str(e)}")
            return {'flesch_reading_ease': 0, 'flesch_kincaid_grade': 0}
    
    def generate_summary(self, text: str, max_sentences: int = 3) -> str:
        """Generate extractive summary"""
        try:
            sentences = sent_tokenize(text)
            if len(sentences) <= max_sentences:
                return text
            
            # Use TF-IDF to score sentences
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform(sentences)
            
            # Calculate sentence scores
            sentence_scores = tfidf_matrix.sum(axis=1).A1
            
            # Get top sentences
            top_sentence_indices = sentence_scores.argsort()[-max_sentences:][::-1]
            top_sentence_indices.sort()
            
            summary_sentences = [sentences[i] for i in top_sentence_indices]
            return ' '.join(summary_sentences)
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return text[:500] + "..." if len(text) > 500 else text


class AIDocumentClassifier:
    """AI-powered document classifier"""
    
    def __init__(self):
        self.processor = DocumentProcessor()
        self.categories = {
            'policy': ['policy', 'procedure', 'guideline', 'rule', 'regulation'],
            'manual': ['manual', 'guide', 'instruction', 'tutorial', 'howto'],
            'template': ['template', 'form', 'format', 'sample', 'example'],
            'training': ['training', 'course', 'lesson', 'education', 'learning'],
            'presentation': ['presentation', 'slide', 'deck', 'meeting', 'conference'],
            'other': []
        }
    
    def classify_document(self, text: str, title: str = "") -> Dict[str, Any]:
        """Classify document based on content and title"""
        try:
            # Combine title and text for classification
            full_text = f"{title} {text}".lower()
            
            # Calculate scores for each category
            category_scores = {}
            for category, keywords in self.categories.items():
                if category == 'other':
                    continue
                
                score = sum(1 for keyword in keywords if keyword in full_text)
                category_scores[category] = score
            
            # Find best category
            if category_scores:
                best_category = max(category_scores, key=category_scores.get)
                confidence = category_scores[best_category] / len(self.categories[best_category])
            else:
                best_category = 'other'
                confidence = 0.0
            
            return {
                'category': best_category,
                'confidence': min(confidence, 1.0),
                'scores': category_scores
            }
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return {'category': 'other', 'confidence': 0.0, 'scores': {}}
    
    def suggest_tags(self, text: str, existing_tags: List[str] = None) -> List[str]:
        """Suggest tags based on document content"""
        try:
            keywords = self.processor.extract_keywords(text, max_keywords=20)
            
            # Filter and clean keywords
            suggested_tags = []
            for keyword in keywords:
                # Clean keyword
                clean_keyword = re.sub(r'[^a-zA-Z\s]', '', keyword).strip()
                if len(clean_keyword) > 2 and clean_keyword not in suggested_tags:
                    suggested_tags.append(clean_keyword)
            
            # Limit to top 10 suggestions
            return suggested_tags[:10]
        except Exception as e:
            logger.error(f"Error suggesting tags: {str(e)}")
            return []


class OllamaIntegration:
    """Integration with Ollama for local AI processing"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = getattr(settings, 'OLLAMA_MODEL', 'llama2')
    
    def is_available(self) -> bool:
        """Check if Ollama service is available"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    def generate_summary(self, text: str, max_length: int = 200) -> str:
        """Generate summary using Ollama"""
        if not self.is_available():
            # Fallback to extractive summary
            processor = DocumentProcessor()
            return processor.generate_summary(text)
        
        try:
            prompt = f"""Summarize the following text in {max_length} words or less:

{text[:2000]}  # Limit input text

Summary:"""
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return ""
        except Exception as e:
            logger.error(f"Error generating summary with Ollama: {str(e)}")
            return ""
    
    def classify_document(self, text: str, title: str = "") -> Dict[str, Any]:
        """Classify document using Ollama"""
        if not self.is_available():
            # Fallback to rule-based classification
            classifier = AIDocumentClassifier()
            return classifier.classify_document(text, title)
        
        try:
            prompt = f"""Classify the following document into one of these categories:
- policy: Policies, procedures, guidelines, rules
- manual: Manuals, guides, instructions, tutorials
- template: Templates, forms, formats, samples
- training: Training materials, courses, lessons
- presentation: Presentations, slides, meeting materials
- other: Any other type

Title: {title}
Content: {text[:1000]}

Classification (respond with just the category name):"""
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                category = result.get('response', '').strip().lower()
                
                # Validate category
                valid_categories = ['policy', 'manual', 'template', 'training', 'presentation', 'other']
                if category not in valid_categories:
                    category = 'other'
                
                return {
                    'category': category,
                    'confidence': 0.8,  # Assume high confidence for AI classification
                    'method': 'ollama'
                }
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return {'category': 'other', 'confidence': 0.0, 'method': 'fallback'}
        except Exception as e:
            logger.error(f"Error classifying with Ollama: {str(e)}")
            return {'category': 'other', 'confidence': 0.0, 'method': 'error'}


# Utility functions
def extract_text_from_file(file_path: str) -> str:
    """Extract text from file"""
    processor = DocumentProcessor()
    return processor.extract_text_from_file(file_path)


def generate_document_summary(text: str, use_ai: bool = True) -> str:
    """Generate document summary"""
    if use_ai:
        ollama = OllamaIntegration()
        summary = ollama.generate_summary(text)
        if summary:
            return summary
    
    # Fallback to extractive summary
    processor = DocumentProcessor()
    return processor.generate_summary(text)


def suggest_document_tags(text: str, title: str = "") -> List[str]:
    """Suggest tags for document"""
    classifier = AIDocumentClassifier()
    return classifier.suggest_tags(f"{title} {text}")


def classify_document_type(text: str, title: str = "", use_ai: bool = True) -> Dict[str, Any]:
    """Classify document type"""
    if use_ai:
        ollama = OllamaIntegration()
        result = ollama.classify_document(text, title)
        if result.get('confidence', 0) > 0:
            return result
    
    # Fallback to rule-based classification
    classifier = AIDocumentClassifier()
    return classifier.classify_document(text, title)


def calculate_document_similarity(doc1_text: str, doc2_text: str) -> float:
    """Calculate similarity between two documents"""
    try:
        processor = DocumentProcessor()
        
        # Preprocess texts
        processed_doc1 = processor.preprocess_text(doc1_text)
        processed_doc2 = processor.preprocess_text(doc2_text)
        
        # Calculate TF-IDF vectors
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform([processed_doc1, processed_doc2])
        
        # Calculate cosine similarity
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except Exception as e:
        logger.error(f"Error calculating similarity: {str(e)}")
        return 0.0


# Celery tasks
@shared_task
def process_document_with_ai(document_id: int, assistant_id: Optional[int] = None):
    """Process document with AI (Celery task)"""
    from .models import KnowledgeDocument, AIProcessingJob, AIAssistant
    
    try:
        document = KnowledgeDocument.objects.get(id=document_id)
        
        # Create processing job
        job = AIProcessingJob.objects.create(
            job_type='classify_document',
            document=document,
            assistant_id=assistant_id or 1,  # Default assistant
            status='processing',
            started_at=timezone.now()
        )
        
        # Extract text from file if available
        text_content = document.content
        if document.file:
            extracted_text = extract_text_from_file(document.file.path)
            text_content = f"{document.content}\n\n{extracted_text}"
        
        # Process with AI
        results = {}
        
        # Classification
        classification = classify_document_type(text_content, document.title)
        results['classification'] = classification
        
        # Keyword extraction
        processor = DocumentProcessor()
        keywords = processor.extract_keywords(text_content)
        results['keywords'] = keywords
        
        # Tag suggestions
        suggested_tags = suggest_document_tags(text_content, document.title)
        results['suggested_tags'] = suggested_tags
        
        # Summary generation
        summary = generate_document_summary(text_content)
        results['summary'] = summary
        
        # Readability analysis
        readability = processor.calculate_readability(text_content)
        results['readability'] = readability
        
        # Update document with AI results
        document.ai_confidence_score = classification.get('confidence', 0.0)
        document.ai_suggested_tags = suggested_tags
        document.ai_extracted_keywords = keywords
        
        # Auto-suggest document type if confidence is high
        if classification.get('confidence', 0) > 0.7:
            document.document_type = classification['category']
        
        document.save()
        
        # Update job status
        job.status = 'completed'
        job.output_data = results
        job.completed_at = timezone.now()
        job.save()
        
        logger.info(f"Successfully processed document {document_id} with AI")
        return results
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        
        # Update job status
        if 'job' in locals():
            job.status = 'failed'
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
        
        raise e


@shared_task
def batch_process_documents(document_ids: List[int]):
    """Batch process multiple documents"""
    results = []
    for doc_id in document_ids:
        try:
            result = process_document_with_ai.delay(doc_id)
            results.append({'document_id': doc_id, 'job_id': str(result.id)})
        except Exception as e:
            logger.error(f"Error starting processing for document {doc_id}: {str(e)}")
            results.append({'document_id': doc_id, 'error': str(e)})
    
    return results


@shared_task
def cleanup_old_ai_jobs():
    """Clean up old AI processing jobs"""
    from .models import AIProcessingJob
    
    # Delete jobs older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    deleted_count = AIProcessingJob.objects.filter(
        created_at__lt=cutoff_date
    ).delete()[0]
    
    logger.info(f"Cleaned up {deleted_count} old AI processing jobs")
    return deleted_count