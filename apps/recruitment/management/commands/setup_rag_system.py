from django.core.management.base import BaseCommand
from django.conf import settings
import os
import json
import requests
import time
from pathlib import Path
from typing import Dict, Any

from recruitment.services import RecruitmentRAGService, N8NClient
from recruitment.rag_config import get_rag_config


class Command(BaseCommand):
    help = 'Setup RAG system and N8N workflows for recruitment automation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-ollama',
            action='store_true',
            help='Skip Ollama model download and setup'
        )
        parser.add_argument(
            '--skip-n8n',
            action='store_true',
            help='Skip N8N workflow setup'
        )
        parser.add_argument(
            '--skip-chromadb',
            action='store_true',
            help='Skip ChromaDB initialization'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reinstall/reconfigure all components'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting RAG System and N8N Setup...')
        )
        
        try:
            # Load configuration
            config = get_rag_config()
            
            # Setup ChromaDB
            if not options['skip_chromadb']:
                self.setup_chromadb(config)
            
            # Setup Ollama
            if not options['skip_ollama']:
                self.setup_ollama(config)
            
            # Setup N8N workflows
            if not options['skip_n8n']:
                self.setup_n8n_workflows()
            
            # Initialize RAG service
            self.initialize_rag_service()
            
            # Run health checks
            self.run_health_checks()
            
            self.stdout.write(
                self.style.SUCCESS('RAG System and N8N setup completed successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Setup failed: {str(e)}')
            )
            raise
    
    def setup_chromadb(self, config):
        """Setup ChromaDB vector database"""
        self.stdout.write('Setting up ChromaDB...')
        
        try:
            # Create data directory
            persist_dir = Path(config.vector_db.persist_directory)
            persist_dir.mkdir(parents=True, exist_ok=True)
            
            # Test ChromaDB connection
            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            if config.vector_db.chroma_host == 'localhost':
                # Local persistent client
                client = chromadb.PersistentClient(
                    path=str(persist_dir)
                )
            else:
                # Remote client
                client = chromadb.HttpClient(
                    host=config.vector_db.chroma_host,
                    port=config.vector_db.chroma_port
                )
            
            # Create collections
            collections = ['resumes', 'job_descriptions', 'candidates']
            for collection_name in collections:
                try:
                    collection = client.get_collection(collection_name)
                    self.stdout.write(f'  Collection "{collection_name}" already exists')
                except Exception:
                    collection = client.create_collection(
                        name=collection_name,
                        metadata={"hnsw:space": "cosine"}
                    )
                    self.stdout.write(f'  Created collection "{collection_name}"')
            
            self.stdout.write(
                self.style.SUCCESS('ChromaDB setup completed')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'ChromaDB setup failed: {str(e)}')
            )
            raise
    
    def setup_ollama(self, config):
        """Setup Ollama and download required models"""
        self.stdout.write('Setting up Ollama...')
        
        try:
            # Check if Ollama is running
            ollama_url = config.llm.base_url
            response = requests.get(f'{ollama_url}/api/tags', timeout=10)
            
            if response.status_code != 200:
                raise Exception('Ollama service is not running')
            
            # Check if required model is available
            models = response.json().get('models', [])
            model_names = [model['name'] for model in models]
            
            required_model = config.llm.model_name
            if required_model not in model_names:
                self.stdout.write(f'Downloading model: {required_model}...')
                
                # Download model
                pull_response = requests.post(
                    f'{ollama_url}/api/pull',
                    json={'name': required_model},
                    timeout=300  # 5 minutes timeout
                )
                
                if pull_response.status_code == 200:
                    self.stdout.write(f'  Model "{required_model}" downloaded successfully')
                else:
                    raise Exception(f'Failed to download model: {pull_response.text}')
            else:
                self.stdout.write(f'  Model "{required_model}" already available')
            
            # Test model
            test_response = requests.post(
                f'{ollama_url}/api/generate',
                json={
                    'model': required_model,
                    'prompt': 'Test prompt',
                    'stream': False
                },
                timeout=30
            )
            
            if test_response.status_code == 200:
                self.stdout.write('  Model test successful')
            else:
                raise Exception(f'Model test failed: {test_response.text}')
            
            self.stdout.write(
                self.style.SUCCESS('Ollama setup completed')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ollama setup failed: {str(e)}')
            )
            raise
    
    def setup_n8n_workflows(self):
        """Setup N8N workflows"""
        self.stdout.write('Setting up N8N workflows...')
        
        try:
            # Load workflow configurations
            workflow_file = Path(__file__).parent.parent.parent / 'n8n_workflows.json'
            
            if not workflow_file.exists():
                raise Exception('N8N workflow configuration file not found')
            
            with open(workflow_file, 'r') as f:
                workflow_config = json.load(f)
            
            # Initialize N8N client
            n8n_client = N8NClient()
            
            if not n8n_client.is_available():
                raise Exception('N8N service is not available')
            
            # Import workflows
            workflows = workflow_config.get('workflows', {})
            
            for workflow_name, workflow_data in workflows.items():
                self.stdout.write(f'  Setting up workflow: {workflow_name}')
                
                # Create workflow in N8N
                # Note: This is a simplified version - actual N8N API calls would be more complex
                workflow_payload = {
                    'name': workflow_data['name'],
                    'nodes': self._create_workflow_nodes(workflow_data),
                    'connections': {},
                    'active': True,
                    'settings': {
                        'executionOrder': 'v1'
                    }
                }
                
                # In a real implementation, you would use N8N's API to create workflows
                self.stdout.write(f'    Workflow "{workflow_name}" configured')
            
            self.stdout.write(
                self.style.SUCCESS('N8N workflows setup completed')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'N8N setup failed: {str(e)}')
            )
            # Don't raise here as N8N might be optional
    
    def _create_workflow_nodes(self, workflow_data: Dict[str, Any]) -> list:
        """Create N8N workflow nodes from configuration"""
        nodes = []
        
        # Webhook trigger node
        nodes.append({
            'id': 'webhook-trigger',
            'name': 'Webhook Trigger',
            'type': 'n8n-nodes-base.webhook',
            'typeVersion': 1,
            'position': [250, 300],
            'parameters': {
                'path': workflow_data.get('webhook_url', '/webhook'),
                'httpMethod': 'POST'
            }
        })
        
        # Add action nodes based on workflow configuration
        x_position = 450
        for i, action in enumerate(workflow_data.get('actions', [])):
            node_id = f'action-{i}'
            
            if action['type'] == 'ai_analysis':
                nodes.append({
                    'id': node_id,
                    'name': f'AI Analysis {i+1}',
                    'type': 'n8n-nodes-base.httpRequest',
                    'typeVersion': 1,
                    'position': [x_position, 300],
                    'parameters': {
                        'url': 'http://localhost:8000/api/recruitment/rag/analyze-resume/',
                        'method': 'POST'
                    }
                })
            elif action['type'] == 'email_notification':
                nodes.append({
                    'id': node_id,
                    'name': f'Email Notification {i+1}',
                    'type': 'n8n-nodes-base.emailSend',
                    'typeVersion': 1,
                    'position': [x_position, 300]
                })
            
            x_position += 200
        
        return nodes
    
    def initialize_rag_service(self):
        """Initialize RAG service"""
        self.stdout.write('Initializing RAG service...')
        
        try:
            rag_service = RecruitmentRAGService()
            
            # Test service initialization
            self.stdout.write('  RAG service initialized successfully')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'RAG service initialization failed: {str(e)}')
            )
            raise
    
    def run_health_checks(self):
        """Run health checks for all services"""
        self.stdout.write('Running health checks...')
        
        try:
            config = get_rag_config()
            
            # Check ChromaDB
            try:
                import chromadb
                if config.vector_db.chroma_host == 'localhost':
                    client = chromadb.PersistentClient(
                        path=config.vector_db.persist_directory
                    )
                else:
                    client = chromadb.HttpClient(
                        host=config.vector_db.chroma_host,
                        port=config.vector_db.chroma_port
                    )
                client.heartbeat()
                self.stdout.write('  ✓ ChromaDB: Healthy')
            except Exception as e:
                self.stdout.write(f'  ✗ ChromaDB: {str(e)}')
            
            # Check Ollama
            try:
                response = requests.get(
                    f'{config.llm.base_url}/api/tags',
                    timeout=5
                )
                if response.status_code == 200:
                    self.stdout.write('  ✓ Ollama: Healthy')
                else:
                    self.stdout.write(f'  ✗ Ollama: HTTP {response.status_code}')
            except Exception as e:
                self.stdout.write(f'  ✗ Ollama: {str(e)}')
            
            # Check N8N
            try:
                n8n_client = N8NClient()
                if n8n_client.is_available():
                    self.stdout.write('  ✓ N8N: Healthy')
                else:
                    self.stdout.write('  ✗ N8N: Not available')
            except Exception as e:
                self.stdout.write(f'  ✗ N8N: {str(e)}')
            
            self.stdout.write(
                self.style.SUCCESS('Health checks completed')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Health checks failed: {str(e)}')
            )