from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os
from pathlib import Path

@dataclass
class EmbeddingConfig:
    """Configuration for embedding models"""
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    max_sequence_length: int = 512
    device: str = "cpu"
    batch_size: int = 32

@dataclass
class VectorDBConfig:
    """Configuration for vector database"""
    provider: str = "chromadb"  # chromadb, faiss, pinecone
    collection_name: str = "recruitment_candidates"
    persist_directory: str = "./data/chromadb"
    distance_metric: str = "cosine"  # cosine, euclidean, manhattan
    index_type: str = "HNSW"  # HNSW, IVF, Flat
    
    # ChromaDB specific
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    
    # Pinecone specific (if used)
    pinecone_api_key: Optional[str] = None
    pinecone_environment: Optional[str] = None
    pinecone_index_name: Optional[str] = None

@dataclass
class LLMConfig:
    """Configuration for Large Language Models"""
    provider: str = "ollama"  # ollama, openai, huggingface
    model_name: str = "llama2"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 60
    
    # OpenAI specific (if used)
    openai_api_key: Optional[str] = None
    
    # HuggingFace specific (if used)
    hf_token: Optional[str] = None

@dataclass
class DocumentProcessingConfig:
    """Configuration for document processing"""
    supported_formats: List[str] = None
    max_file_size_mb: int = 10
    chunk_size: int = 1000
    chunk_overlap: int = 200
    text_splitter: str = "recursive"  # recursive, character, token
    
    def __post_init__(self):
        if self.supported_formats is None:
            self.supported_formats = ['.pdf', '.docx', '.txt', '.md']

@dataclass
class RAGConfig:
    """Main RAG system configuration"""
    embedding: EmbeddingConfig = None
    vector_db: VectorDBConfig = None
    llm: LLMConfig = None
    document_processing: DocumentProcessingConfig = None
    
    # Search configuration
    similarity_threshold: float = 0.7
    max_results: int = 10
    rerank_results: bool = True
    
    # Caching
    enable_cache: bool = True
    cache_ttl_hours: int = 24
    
    # Analysis configuration
    analysis_prompts: Dict[str, str] = None
    
    def __post_init__(self):
        if self.embedding is None:
            self.embedding = EmbeddingConfig()
        if self.vector_db is None:
            self.vector_db = VectorDBConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.document_processing is None:
            self.document_processing = DocumentProcessingConfig()
        if self.analysis_prompts is None:
            self.analysis_prompts = self._default_prompts()
    
    def _default_prompts(self) -> Dict[str, str]:
        return {
            "resume_analysis": """
            Analyze the following resume and provide a structured assessment:
            
            Resume Content:
            {resume_text}
            
            Job Requirements:
            {job_requirements}
            
            Please provide:
            1. Skills Match Score (0-100)
            2. Experience Relevance (0-100)
            3. Education Fit (0-100)
            4. Overall Recommendation (Hire/Consider/Reject)
            5. Key Strengths (bullet points)
            6. Areas of Concern (bullet points)
            7. Suggested Interview Questions (3-5 questions)
            
            Format your response as JSON.
            """,
            
            "candidate_comparison": """
            Compare the following candidates for the position:
            
            Position: {job_title}
            Requirements: {job_requirements}
            
            Candidates:
            {candidates_data}
            
            Provide:
            1. Ranking with scores
            2. Comparative analysis
            3. Hiring recommendations
            4. Risk assessment for each candidate
            
            Format as JSON with detailed explanations.
            """,
            
            "skill_extraction": """
            Extract and categorize skills from the following resume:
            
            Resume: {resume_text}
            
            Categorize skills into:
            1. Technical Skills
            2. Soft Skills
            3. Industry Knowledge
            4. Certifications
            5. Languages
            
            Rate proficiency level (Beginner/Intermediate/Advanced/Expert) where possible.
            Return as structured JSON.
            """,
            
            "job_match": """
            Determine how well this candidate matches the job requirements:
            
            Candidate Profile:
            {candidate_profile}
            
            Job Description:
            {job_description}
            
            Provide:
            1. Match percentage (0-100)
            2. Matching criteria analysis
            3. Gap analysis
            4. Improvement suggestions
            5. Interview focus areas
            
            Return detailed JSON response.
            """
        }

class RAGConfigManager:
    """Manager for RAG configuration"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.getenv('RAG_CONFIG_PATH', 'rag_config.json')
        self._config = None
    
    def load_config(self) -> RAGConfig:
        """Load configuration from file or environment"""
        if self._config is None:
            self._config = self._load_from_env()
        return self._config
    
    def _load_from_env(self) -> RAGConfig:
        """Load configuration from environment variables"""
        embedding_config = EmbeddingConfig(
            model_name=os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'),
            dimension=int(os.getenv('EMBEDDING_DIMENSION', '384')),
            device=os.getenv('EMBEDDING_DEVICE', 'cpu'),
            batch_size=int(os.getenv('EMBEDDING_BATCH_SIZE', '32'))
        )
        
        vector_db_config = VectorDBConfig(
            provider=os.getenv('VECTOR_DB_PROVIDER', 'chromadb'),
            collection_name=os.getenv('VECTOR_DB_COLLECTION', 'recruitment_candidates'),
            persist_directory=os.getenv('VECTOR_DB_PERSIST_DIR', './data/chromadb'),
            chroma_host=os.getenv('CHROMA_HOST', 'localhost'),
            chroma_port=int(os.getenv('CHROMA_PORT', '8000'))
        )
        
        llm_config = LLMConfig(
            provider=os.getenv('LLM_PROVIDER', 'ollama'),
            model_name=os.getenv('LLM_MODEL', 'llama2'),
            base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
            temperature=float(os.getenv('LLM_TEMPERATURE', '0.1')),
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '2048'))
        )
        
        doc_config = DocumentProcessingConfig(
            max_file_size_mb=int(os.getenv('MAX_FILE_SIZE_MB', '10')),
            chunk_size=int(os.getenv('CHUNK_SIZE', '1000')),
            chunk_overlap=int(os.getenv('CHUNK_OVERLAP', '200'))
        )
        
        return RAGConfig(
            embedding=embedding_config,
            vector_db=vector_db_config,
            llm=llm_config,
            document_processing=doc_config,
            similarity_threshold=float(os.getenv('SIMILARITY_THRESHOLD', '0.7')),
            max_results=int(os.getenv('MAX_SEARCH_RESULTS', '10'))
        )
    
    def save_config(self, config: RAGConfig) -> None:
        """Save configuration to file"""
        import json
        from dataclasses import asdict
        
        config_dict = asdict(config)
        with open(self.config_path, 'w') as f:
            json.dump(config_dict, f, indent=2)
    
    def update_config(self, **kwargs) -> RAGConfig:
        """Update configuration with new values"""
        config = self.load_config()
        
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        return config

# Global configuration instance
config_manager = RAGConfigManager()

def get_rag_config() -> RAGConfig:
    """Get the current RAG configuration"""
    return config_manager.load_config()

def update_rag_config(**kwargs) -> RAGConfig:
    """Update RAG configuration"""
    return config_manager.update_config(**kwargs)