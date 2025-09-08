import re
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

try:
    from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
    import torch
    import numpy as np
except ImportError:
    # Fallback jika transformers tidak tersedia
    AutoTokenizer = None
    AutoModelForSequenceClassification = None
    pipeline = None
    torch = None
    np = None

from django.utils import timezone

from .base import BaseAIService, NLPModelMixin
from .config import AIConfig
from .exceptions import PredictionError, ModelLoadError, ValidationError

logger = logging.getLogger(__name__)

class IndonesianNLPService(BaseAIService, NLPModelMixin):
    """
    AI Service untuk Indonesian Natural Language Processing.
    Menyediakan sentiment analysis, NER, dan text classification untuk bahasa Indonesia.
    """
    
    def __init__(self):
        config = AIConfig.get_config('indonesian_nlp')
        super().__init__(config['MODEL_NAME'], '1.0')
        self.config = config
        self.sentiment_model = None
        self.sentiment_tokenizer = None
        self.ner_pipeline = None
        self.classification_pipeline = None
        
        # Indonesian stopwords
        self.indonesian_stopwords = {
            'yang', 'dan', 'di', 'ke', 'dari', 'dalam', 'untuk', 'pada', 'dengan', 'oleh',
            'adalah', 'ini', 'itu', 'akan', 'telah', 'sudah', 'dapat', 'bisa', 'harus',
            'tidak', 'juga', 'atau', 'tetapi', 'namun', 'karena', 'sebab', 'jika', 'kalau',
            'saya', 'anda', 'dia', 'mereka', 'kita', 'kami', 'kamu', 'ia', 'beliau',
            'ada', 'menjadi', 'membuat', 'memberikan', 'melakukan', 'menggunakan',
            'sangat', 'lebih', 'paling', 'cukup', 'agak', 'kurang', 'terlalu'
        }
        
        # Sentiment keywords untuk fallback
        self.positive_keywords = {
            'baik', 'bagus', 'hebat', 'luar biasa', 'sempurna', 'memuaskan', 'senang',
            'gembira', 'suka', 'cinta', 'terima kasih', 'mantap', 'keren', 'oke',
            'setuju', 'mendukung', 'positif', 'optimis', 'berhasil', 'sukses'
        }
        
        self.negative_keywords = {
            'buruk', 'jelek', 'tidak baik', 'mengecewakan', 'sedih', 'marah', 'kesal',
            'benci', 'tidak suka', 'gagal', 'salah', 'error', 'masalah', 'sulit',
            'tidak setuju', 'menolak', 'negatif', 'pesimis', 'kecewa', 'frustrasi'
        }
    
    def load_model(self) -> None:
        """
        Load Indonesian NLP models.
        """
        try:
            if AutoTokenizer is None or AutoModelForSequenceClassification is None:
                logger.warning("Transformers library not available, using fallback methods")
                self.is_loaded = True
                return
            
            # Load sentiment analysis model
            try:
                model_name = self.config.get('BERT_MODEL', 'indolem/indobert-base-uncased')
                logger.info(f"Loading Indonesian BERT model: {model_name}")
                
                self.sentiment_tokenizer = AutoTokenizer.from_pretrained(model_name)
                
                # Try to load fine-tuned sentiment model, fallback to base model
                try:
                    sentiment_model_path = self.config.get('SENTIMENT_MODEL', model_name)
                    self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(
                        sentiment_model_path, num_labels=3
                    )
                except:
                    logger.info("Using base model for sentiment analysis")
                    self.sentiment_model = AutoModelForSequenceClassification.from_pretrained(
                        model_name, num_labels=3
                    )
                
                # Create pipelines
                if pipeline is not None:
                    self.classification_pipeline = pipeline(
                        "text-classification",
                        model=self.sentiment_model,
                        tokenizer=self.sentiment_tokenizer,
                        return_all_scores=True
                    )
                
                logger.info("Indonesian NLP models loaded successfully")
                
            except Exception as e:
                logger.warning(f"Failed to load transformer models: {str(e)}, using fallback")
            
            self.is_loaded = True
            
        except Exception as e:
            logger.error(f"Failed to load Indonesian NLP models: {str(e)}")
            self.is_loaded = True  # Continue with fallback methods
    
    def validate_input(self, input_data: Any) -> bool:
        """
        Validate input data untuk NLP processing.
        """
        if not isinstance(input_data, dict):
            return False
        
        # Check for text
        if 'text' not in input_data:
            return False
        
        if not isinstance(input_data['text'], str):
            return False
        
        # Check text length
        max_length = self.config.get('MAX_TEXT_LENGTH', 5000)
        if len(input_data['text']) > max_length:
            return False
        
        # Check if text is not empty after preprocessing
        cleaned_text = self.preprocess_text(input_data['text'])
        if len(cleaned_text.strip()) == 0:
            return False
        
        return True
    
    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Indonesian text untuk sentiment analysis dan NLP tasks.
        """
        try:
            text = input_data['text']
            tasks = input_data.get('tasks', ['sentiment', 'keywords', 'language'])
            
            # Preprocess text
            processed_text = self.preprocess_text(text)
            
            result = {
                'original_text': text,
                'processed_text': processed_text,
                'language': self.detect_language(text),
                'text_length': len(text),
                'word_count': len(text.split())
            }
            
            # Sentiment Analysis
            if 'sentiment' in tasks:
                sentiment_result = self._analyze_sentiment(processed_text)
                result['sentiment'] = sentiment_result
            
            # Keyword Extraction
            if 'keywords' in tasks:
                keywords = self.extract_keywords(processed_text, max_keywords=10)
                result['keywords'] = keywords
            
            # Named Entity Recognition
            if 'ner' in tasks:
                entities = self._extract_entities(processed_text)
                result['entities'] = entities
            
            # Text Classification
            if 'classification' in tasks:
                classification = self._classify_text(processed_text)
                result['classification'] = classification
            
            # Text Statistics
            if 'statistics' in tasks:
                stats = self._calculate_text_statistics(text, processed_text)
                result['statistics'] = stats
            
            return result
            
        except Exception as e:
            raise PredictionError(f"Indonesian NLP processing failed: {str(e)}", self.model_name, input_data)
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment dari Indonesian text.
        """
        try:
            # Try transformer-based sentiment analysis
            if self.classification_pipeline is not None:
                return self._transformer_sentiment_analysis(text)
            else:
                return self._rule_based_sentiment_analysis(text)
                
        except Exception as e:
            logger.warning(f"Sentiment analysis failed: {str(e)}, using fallback")
            return self._rule_based_sentiment_analysis(text)
    
    def _transformer_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """
        Transformer-based sentiment analysis.
        """
        try:
            # Truncate text if too long
            max_length = 512
            if len(text.split()) > max_length:
                text = ' '.join(text.split()[:max_length])
            
            # Get predictions
            results = self.classification_pipeline(text)
            
            # Process results
            sentiment_scores = {}
            for result in results[0]:  # First (and only) text result
                label = result['label'].lower()
                score = result['score']
                
                # Map labels to standard format
                if 'pos' in label or 'positive' in label:
                    sentiment_scores['positive'] = score
                elif 'neg' in label or 'negative' in label:
                    sentiment_scores['negative'] = score
                else:
                    sentiment_scores['neutral'] = score
            
            # Determine overall sentiment
            if not sentiment_scores:
                # Fallback if no valid labels
                return self._rule_based_sentiment_analysis(text)
            
            predicted_sentiment = max(sentiment_scores, key=sentiment_scores.get)
            confidence = sentiment_scores[predicted_sentiment]
            
            # Convert to standard scale (-1 to 1)
            if predicted_sentiment == 'positive':
                sentiment_score = confidence
            elif predicted_sentiment == 'negative':
                sentiment_score = -confidence
            else:
                sentiment_score = 0.0
            
            return {
                'sentiment_label': predicted_sentiment,
                'sentiment_score': round(sentiment_score, 4),
                'confidence': round(confidence, 4),
                'scores': {k: round(v, 4) for k, v in sentiment_scores.items()},
                'method': 'transformer'
            }
            
        except Exception as e:
            logger.error(f"Transformer sentiment analysis failed: {str(e)}")
            return self._rule_based_sentiment_analysis(text)
    
    def _rule_based_sentiment_analysis(self, text: str) -> Dict[str, Any]:
        """
        Rule-based sentiment analysis sebagai fallback.
        """
        try:
            text_lower = text.lower()
            words = set(text_lower.split())
            
            # Count positive and negative words
            positive_count = len(words.intersection(self.positive_keywords))
            negative_count = len(words.intersection(self.negative_keywords))
            
            # Calculate sentiment score
            total_sentiment_words = positive_count + negative_count
            
            if total_sentiment_words == 0:
                sentiment_label = 'neutral'
                sentiment_score = 0.0
                confidence = 0.5
            else:
                sentiment_score = (positive_count - negative_count) / total_sentiment_words
                
                if sentiment_score > 0.1:
                    sentiment_label = 'positive'
                elif sentiment_score < -0.1:
                    sentiment_label = 'negative'
                else:
                    sentiment_label = 'neutral'
                
                confidence = min(0.9, abs(sentiment_score) + 0.3)
            
            # Create score distribution
            if sentiment_label == 'positive':
                scores = {'positive': confidence, 'neutral': 1-confidence, 'negative': 0.0}
            elif sentiment_label == 'negative':
                scores = {'negative': confidence, 'neutral': 1-confidence, 'positive': 0.0}
            else:
                scores = {'neutral': confidence, 'positive': (1-confidence)/2, 'negative': (1-confidence)/2}
            
            return {
                'sentiment_label': sentiment_label,
                'sentiment_score': round(sentiment_score, 4),
                'confidence': round(confidence, 4),
                'scores': {k: round(v, 4) for k, v in scores.items()},
                'positive_words': positive_count,
                'negative_words': negative_count,
                'method': 'rule_based'
            }
            
        except Exception as e:
            logger.error(f"Rule-based sentiment analysis failed: {str(e)}")
            return {
                'sentiment_label': 'neutral',
                'sentiment_score': 0.0,
                'confidence': 0.0,
                'error': str(e),
                'method': 'fallback'
            }
    
    def _extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract named entities dari Indonesian text.
        """
        try:
            entities = []
            
            # Simple rule-based NER untuk Indonesian
            # Person names (capitalized words)
            person_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
            persons = re.findall(person_pattern, text)
            
            for person in persons:
                # Filter out common words that might be capitalized
                if person.lower() not in {'yang', 'dan', 'atau', 'dengan', 'untuk', 'pada'}:
                    entities.append({
                        'text': person,
                        'label': 'PERSON',
                        'confidence': 0.7
                    })
            
            # Organizations (words with 'PT', 'CV', 'Ltd', etc.)
            org_pattern = r'\b(?:PT|CV|Ltd|Inc|Corp|Company)\s+[A-Z][a-zA-Z\s]+'
            orgs = re.findall(org_pattern, text)
            
            for org in orgs:
                entities.append({
                    'text': org.strip(),
                    'label': 'ORGANIZATION',
                    'confidence': 0.8
                })
            
            # Dates (simple patterns)
            date_patterns = [
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # DD/MM/YYYY or DD-MM-YYYY
                r'\b\d{1,2}\s+(?:Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember)\s+\d{2,4}\b'
            ]
            
            for pattern in date_patterns:
                dates = re.findall(pattern, text, re.IGNORECASE)
                for date in dates:
                    entities.append({
                        'text': date,
                        'label': 'DATE',
                        'confidence': 0.9
                    })
            
            # Money (Rupiah)
            money_pattern = r'\bRp\.?\s*\d+(?:[.,]\d+)*(?:\s*(?:juta|miliar|ribu))?\b'
            money_matches = re.findall(money_pattern, text, re.IGNORECASE)
            
            for money in money_matches:
                entities.append({
                    'text': money,
                    'label': 'MONEY',
                    'confidence': 0.9
                })
            
            # Remove duplicates
            unique_entities = []
            seen = set()
            
            for entity in entities:
                key = (entity['text'].lower(), entity['label'])
                if key not in seen:
                    seen.add(key)
                    unique_entities.append(entity)
            
            return unique_entities
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return []
    
    def _classify_text(self, text: str) -> Dict[str, Any]:
        """
        Classify text berdasarkan content type.
        """
        try:
            text_lower = text.lower()
            
            # Define classification categories dengan keywords
            categories = {
                'complaint': {
                    'keywords': ['keluhan', 'komplain', 'tidak puas', 'masalah', 'error', 'bug', 'salah'],
                    'weight': 1.0
                },
                'request': {
                    'keywords': ['minta', 'mohon', 'tolong', 'bantuan', 'permintaan', 'request'],
                    'weight': 1.0
                },
                'feedback': {
                    'keywords': ['saran', 'masukan', 'feedback', 'pendapat', 'kritik', 'evaluasi'],
                    'weight': 1.0
                },
                'question': {
                    'keywords': ['apa', 'bagaimana', 'kapan', 'dimana', 'mengapa', 'kenapa', '?'],
                    'weight': 1.0
                },
                'information': {
                    'keywords': ['informasi', 'info', 'pemberitahuan', 'pengumuman', 'berita'],
                    'weight': 0.8
                },
                'appreciation': {
                    'keywords': ['terima kasih', 'thanks', 'apresiasi', 'bagus', 'hebat', 'mantap'],
                    'weight': 0.9
                }
            }
            
            # Calculate scores untuk setiap category
            category_scores = {}
            
            for category, config in categories.items():
                score = 0
                matched_keywords = []
                
                for keyword in config['keywords']:
                    if keyword in text_lower:
                        score += config['weight']
                        matched_keywords.append(keyword)
                
                if score > 0:
                    category_scores[category] = {
                        'score': score,
                        'matched_keywords': matched_keywords
                    }
            
            # Determine primary classification
            if category_scores:
                primary_category = max(category_scores, key=lambda x: category_scores[x]['score'])
                confidence = min(0.95, category_scores[primary_category]['score'] / 3.0)
            else:
                primary_category = 'general'
                confidence = 0.5
            
            return {
                'primary_category': primary_category,
                'confidence': round(confidence, 4),
                'all_categories': {k: round(v['score'], 2) for k, v in category_scores.items()},
                'matched_keywords': category_scores.get(primary_category, {}).get('matched_keywords', [])
            }
            
        except Exception as e:
            logger.error(f"Text classification failed: {str(e)}")
            return {
                'primary_category': 'general',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def _calculate_text_statistics(self, original_text: str, processed_text: str) -> Dict[str, Any]:
        """
        Calculate comprehensive text statistics.
        """
        try:
            # Basic counts
            char_count = len(original_text)
            word_count = len(original_text.split())
            sentence_count = len(re.split(r'[.!?]+', original_text))
            paragraph_count = len([p for p in original_text.split('\n\n') if p.strip()])
            
            # Processed text stats
            processed_words = processed_text.split()
            unique_words = len(set(processed_words))
            
            # Language complexity
            avg_word_length = sum(len(word) for word in processed_words) / len(processed_words) if processed_words else 0
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            
            # Readability (simplified)
            readability_score = self._calculate_readability(word_count, sentence_count, avg_word_length)
            
            return {
                'character_count': char_count,
                'word_count': word_count,
                'unique_words': unique_words,
                'sentence_count': sentence_count,
                'paragraph_count': paragraph_count,
                'avg_word_length': round(avg_word_length, 2),
                'avg_sentence_length': round(avg_sentence_length, 2),
                'lexical_diversity': round(unique_words / word_count, 4) if word_count > 0 else 0,
                'readability_score': round(readability_score, 2)
            }
            
        except Exception as e:
            logger.error(f"Text statistics calculation failed: {str(e)}")
            return {
                'error': str(e)
            }
    
    def _calculate_readability(self, word_count: int, sentence_count: int, avg_word_length: float) -> float:
        """
        Calculate simplified readability score untuk Indonesian text.
        """
        try:
            if sentence_count == 0:
                return 0.0
            
            # Simplified readability formula adapted for Indonesian
            avg_sentence_length = word_count / sentence_count
            
            # Lower scores = easier to read
            readability = (avg_sentence_length * 0.5) + (avg_word_length * 2.0)
            
            # Normalize to 0-100 scale (100 = easiest)
            normalized_score = max(0, min(100, 100 - readability))
            
            return normalized_score
            
        except Exception as e:
            logger.warning(f"Readability calculation failed: {str(e)}")
            return 50.0  # Default moderate readability
    
    def preprocess_text(self, text: str) -> str:
        """
        Enhanced text preprocessing untuk Indonesian text.
        """
        if not isinstance(text, str):
            return str(text)
        
        # Basic cleaning
        text = text.strip()
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[!]{2,}', '!', text)
        text = re.sub(r'[?]{2,}', '?', text)
        text = re.sub(r'[.]{3,}', '...', text)
        
        # Normalize Indonesian contractions and informal words
        indonesian_normalizations = {
            'gak': 'tidak',
            'ga': 'tidak', 
            'nggak': 'tidak',
            'ngga': 'tidak',
            'udah': 'sudah',
            'udh': 'sudah',
            'blm': 'belum',
            'blom': 'belum',
            'krn': 'karena',
            'krna': 'karena',
            'dgn': 'dengan',
            'dg': 'dengan',
            'utk': 'untuk',
            'yg': 'yang',
            'tdk': 'tidak',
            'hrs': 'harus',
            'jd': 'jadi',
            'jdi': 'jadi',
            'bs': 'bisa',
            'bsa': 'bisa'
        }
        
        # Apply normalizations
        words = text.split()
        normalized_words = []
        
        for word in words:
            word_lower = word.lower()
            if word_lower in indonesian_normalizations:
                normalized_words.append(indonesian_normalizations[word_lower])
            else:
                normalized_words.append(word)
        
        text = ' '.join(normalized_words)
        
        return text.strip()
    
    def detect_language(self, text: str) -> str:
        """
        Enhanced language detection untuk Indonesian vs English.
        """
        try:
            text_lower = text.lower()
            words = text_lower.split()
            
            if not words:
                return 'unknown'
            
            # Indonesian indicators
            indonesian_indicators = {
                'yang', 'dan', 'di', 'ke', 'dari', 'untuk', 'dengan', 'pada', 'dalam',
                'adalah', 'akan', 'sudah', 'telah', 'dapat', 'bisa', 'harus', 'tidak',
                'juga', 'atau', 'tetapi', 'karena', 'jika', 'saya', 'anda', 'dia',
                'mereka', 'kita', 'ada', 'menjadi', 'membuat', 'melakukan'
            }
            
            # English indicators
            english_indicators = {
                'the', 'and', 'to', 'of', 'a', 'in', 'for', 'is', 'on', 'that',
                'by', 'this', 'with', 'i', 'you', 'it', 'not', 'or', 'be', 'are',
                'from', 'at', 'as', 'your', 'all', 'any', 'can', 'had', 'her',
                'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his'
            }
            
            # Count matches
            indonesian_count = sum(1 for word in words if word in indonesian_indicators)
            english_count = sum(1 for word in words if word in english_indicators)
            
            # Calculate percentages
            total_words = len(words)
            indonesian_percentage = indonesian_count / total_words
            english_percentage = english_count / total_words
            
            # Determine language
            if indonesian_percentage > english_percentage and indonesian_percentage > 0.1:
                return 'id'
            elif english_percentage > indonesian_percentage and english_percentage > 0.1:
                return 'en'
            else:
                # Additional heuristics
                # Check for Indonesian-specific patterns
                if any(pattern in text_lower for pattern in ['ber-', 'me-', 'ter-', 'ke-an', '-nya']):
                    return 'id'
                # Check for English-specific patterns
                elif any(pattern in text_lower for pattern in ['-ing', '-ed', '-ly', 'th-']):
                    return 'en'
                else:
                    return 'mixed' if indonesian_count > 0 and english_count > 0 else 'unknown'
                    
        except Exception as e:
            logger.warning(f"Language detection failed: {str(e)}")
            return 'unknown'
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """
        Enhanced keyword extraction untuk Indonesian text.
        """
        try:
            # Preprocess text
            text_lower = text.lower()
            
            # Remove punctuation and split
            words = re.findall(r'\b\w+\b', text_lower)
            
            # Filter out stopwords and short words
            filtered_words = [
                word for word in words 
                if word not in self.indonesian_stopwords 
                and len(word) > 2 
                and not word.isdigit()
            ]
            
            # Count frequency
            from collections import Counter
            word_freq = Counter(filtered_words)
            
            # Get top keywords
            top_keywords = [word for word, _ in word_freq.most_common(max_keywords)]
            
            return top_keywords
            
        except Exception as e:
            logger.error(f"Keyword extraction failed: {str(e)}")
            return []
    
    def batch_process(self, texts: List[str], tasks: List[str] = None) -> List[Dict[str, Any]]:
        """
        Process multiple texts dalam batch untuk efficiency.
        """
        try:
            if tasks is None:
                tasks = ['sentiment', 'keywords']
            
            results = []
            batch_size = self.config.get('BATCH_PROCESSING_SIZE', 16)
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_results = []
                
                for text in batch_texts:
                    try:
                        input_data = {'text': text, 'tasks': tasks}
                        result = self.safe_predict(input_data, use_cache=True)
                        batch_results.append(result)
                    except Exception as e:
                        logger.error(f"Batch processing failed for text: {str(e)}")
                        batch_results.append({
                            'error': str(e),
                            'original_text': text
                        })
                
                results.extend(batch_results)
            
            return results
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            return [{'error': str(e)} for _ in texts]
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get detailed information tentang loaded models.
        """
        info = super().get_model_info()
        
        info.update({
            'has_transformer_model': self.sentiment_model is not None,
            'has_classification_pipeline': self.classification_pipeline is not None,
            'supported_tasks': ['sentiment', 'keywords', 'ner', 'classification', 'statistics'],
            'supported_languages': ['id', 'en'],
            'fallback_methods_available': True,
            'bert_model': self.config.get('BERT_MODEL', 'Not specified'),
            'max_text_length': self.config.get('MAX_TEXT_LENGTH', 5000)
        })
        
        return info