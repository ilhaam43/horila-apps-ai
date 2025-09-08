#!/usr/bin/env python3
"""
Script untuk membuat data test untuk chatbot knowledge management system.
Script ini akan membuat beberapa dokumen contoh dan kategori untuk menguji
fungsionalitas RAG (Retrieval-Augmented Generation) chatbot.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from django.contrib.auth.models import User
from knowledge.models import (
    DocumentCategory, DocumentTag, KnowledgeDocument, 
    DocumentVersion, AIAssistant
)

def create_test_data():
    """Membuat data test untuk chatbot"""
    print("Creating test data for chatbot...")
    
    # Get or create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Admin',
            'last_name': 'User',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"Created admin user: {admin_user.username}")
    
    # Create categories
    categories_data = [
        {
            'name': 'Company Policies',
            'description': 'Official company policies and procedures',
            'color': '#007bff'
        },
        {
            'name': 'Technical Documentation',
            'description': 'Technical guides and documentation',
            'color': '#28a745'
        },
        {
            'name': 'HR Guidelines',
            'description': 'Human resources policies and guidelines',
            'color': '#ffc107'
        },
        {
            'name': 'Training Materials',
            'description': 'Training and educational materials',
            'color': '#dc3545'
        }
    ]
    
    categories = {}
    for cat_data in categories_data:
        category, created = DocumentCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={
                'description': cat_data['description'],
                'color': cat_data['color']
            }
        )
        categories[cat_data['name']] = category
        if created:
            print(f"Created category: {category.name}")
    
    # Create tags
    tags_data = [
        'policy', 'procedure', 'technical', 'guide', 'training',
        'hr', 'security', 'development', 'api', 'database'
    ]
    
    tags = {}
    for tag_name in tags_data:
        tag, created = DocumentTag.objects.get_or_create(
            name=tag_name,
            defaults={}
        )
        tags[tag_name] = tag
        if created:
            print(f"Created tag: {tag.name}")
    
    # Create AI Assistant
    ai_assistant, created = AIAssistant.objects.get_or_create(
        name='Knowledge Assistant',
        defaults={
            'description': 'AI assistant for knowledge management',
            'model_name': 'llama2',
            'is_active': True
        }
    )
    if created:
        print(f"Created AI assistant: {ai_assistant.name}")
    
    # Create sample documents
    documents_data = [
        {
            'title': 'Employee Handbook 2024',
            'content': '''
# Employee Handbook 2024

## Welcome to Our Company

This handbook contains important information about our company policies, procedures, and benefits.

## Work Hours
- Standard work hours: 9:00 AM to 5:00 PM
- Lunch break: 12:00 PM to 1:00 PM
- Flexible work arrangements available upon approval

## Leave Policy
- Annual leave: 20 days per year
- Sick leave: 10 days per year
- Maternity/Paternity leave: As per local regulations

## Code of Conduct
- Treat all colleagues with respect
- Maintain confidentiality of company information
- Follow safety protocols at all times

## Benefits
- Health insurance coverage
- Retirement savings plan
- Professional development opportunities
            ''',
            'category': 'Company Policies',
            'tags': ['policy', 'hr', 'guide'],
            'document_type': 'policy'
        },
        {
            'title': 'API Development Guidelines',
            'content': '''
# API Development Guidelines

## Overview
This document outlines the best practices for developing APIs in our organization.

## REST API Standards
- Use HTTP methods appropriately (GET, POST, PUT, DELETE)
- Follow RESTful URL conventions
- Return appropriate HTTP status codes
- Use JSON for request and response bodies

## Authentication
- All APIs must implement authentication
- Use JWT tokens for stateless authentication
- Implement rate limiting to prevent abuse

## Documentation
- Document all endpoints using OpenAPI/Swagger
- Provide example requests and responses
- Keep documentation up to date

## Error Handling
- Return consistent error response format
- Include meaningful error messages
- Log errors for debugging purposes

## Testing
- Write unit tests for all API endpoints
- Implement integration tests
- Use automated testing in CI/CD pipeline
            ''',
            'category': 'Technical Documentation',
            'tags': ['technical', 'api', 'development', 'guide'],
            'document_type': 'guide'
        },
        {
            'title': 'Database Security Best Practices',
            'content': '''
# Database Security Best Practices

## Access Control
- Implement role-based access control (RBAC)
- Use principle of least privilege
- Regularly review and audit user permissions
- Remove unused accounts promptly

## Data Encryption
- Encrypt sensitive data at rest
- Use TLS for data in transit
- Implement field-level encryption for PII

## Backup and Recovery
- Perform regular automated backups
- Test backup restoration procedures
- Store backups in secure, separate locations
- Document recovery procedures

## Monitoring and Auditing
- Enable database audit logging
- Monitor for suspicious activities
- Set up alerts for security events
- Regular security assessments

## Password Policies
- Enforce strong password requirements
- Implement password rotation policies
- Use multi-factor authentication where possible
- Avoid default passwords
            ''',
            'category': 'Technical Documentation',
            'tags': ['technical', 'security', 'database', 'guide'],
            'document_type': 'guide'
        },
        {
            'title': 'New Employee Onboarding Process',
            'content': '''
# New Employee Onboarding Process

## Pre-boarding (Before First Day)
- Send welcome email with first day information
- Prepare workspace and equipment
- Create user accounts and access credentials
- Schedule orientation meetings

## First Day
- Welcome and office tour
- IT setup and system access
- HR documentation completion
- Introduction to team members
- Review of employee handbook

## First Week
- Department-specific training
- Assign buddy/mentor
- Set up initial goals and expectations
- Schedule regular check-ins

## First Month
- Complete mandatory training modules
- Performance goal setting
- Feedback session with manager
- Integration assessment

## 90-Day Review
- Comprehensive performance review
- Career development discussion
- Adjustment of goals if needed
- Feedback collection for process improvement
            ''',
            'category': 'HR Guidelines',
            'tags': ['hr', 'procedure', 'training'],
            'document_type': 'procedure'
        },
        {
            'title': 'Remote Work Policy',
            'content': '''
# Remote Work Policy

## Eligibility
- Employees with at least 6 months tenure
- Roles suitable for remote work
- Manager approval required
- Performance standards must be met

## Work Arrangements
- Hybrid: 2-3 days in office, 2-3 days remote
- Full remote: Special approval required
- Core hours: 10:00 AM to 3:00 PM (local time)
- Flexible scheduling within business hours

## Equipment and Technology
- Company-provided laptop and accessories
- Secure VPN connection required
- Home office setup allowance available
- IT support for remote workers

## Communication
- Daily check-ins with team
- Weekly one-on-ones with manager
- Use company communication tools
- Response time expectations

## Performance Management
- Results-oriented performance metrics
- Regular progress reviews
- Clear deliverables and deadlines
- Continuous feedback culture
            ''',
            'category': 'Company Policies',
            'tags': ['policy', 'hr', 'procedure'],
            'document_type': 'policy'
        },
        {
            'title': 'Python Development Standards',
            'content': '''
# Python Development Standards

## Code Style
- Follow PEP 8 style guide
- Use meaningful variable and function names
- Maximum line length: 88 characters
- Use type hints for function parameters and returns

## Project Structure
- Use virtual environments for all projects
- Organize code into logical modules
- Separate configuration from code
- Include comprehensive README files

## Testing
- Write unit tests using pytest
- Aim for 80%+ code coverage
- Use fixtures for test data
- Mock external dependencies

## Dependencies
- Pin dependency versions in requirements.txt
- Use requirements-dev.txt for development dependencies
- Regular security updates for packages
- Document dependency choices

## Documentation
- Use docstrings for all functions and classes
- Follow Google or NumPy docstring format
- Generate API documentation automatically
- Keep documentation up to date
            ''',
            'category': 'Technical Documentation',
            'tags': ['technical', 'development', 'guide'],
            'document_type': 'guide'
        }
    ]
    
    # Create documents
    for doc_data in documents_data:
        document, created = KnowledgeDocument.objects.get_or_create(
            title=doc_data['title'],
            defaults={
                'content': doc_data['content'],
                'category': categories[doc_data['category']],
                'document_type': doc_data['document_type'],
                'status': 'published',
                'visibility': 'public',
                'created_by': admin_user,
                'updated_by': admin_user
            }
        )
        
        if created:
            # Add tags
            for tag_name in doc_data['tags']:
                if tag_name in tags:
                    document.tags.add(tags[tag_name])
            
            # Create document version
            DocumentVersion.objects.create(
                document=document,
                version_number='1.0',
                content=doc_data['content'],
                created_by=admin_user,
                change_summary='Initial version'
            )
            
            print(f"Created document: {document.title}")
    
    print("\nTest data creation completed!")
    print(f"Created {DocumentCategory.objects.count()} categories")
    print(f"Created {DocumentTag.objects.count()} tags")
    print(f"Created {KnowledgeDocument.objects.count()} documents")
    print(f"Created {AIAssistant.objects.count()} AI assistants")
    
    print("\nYou can now test the chatbot with questions like:")
    print("- What is the company's remote work policy?")
    print("- How many days of annual leave do employees get?")
    print("- What are the API development guidelines?")
    print("- Tell me about database security best practices")
    print("- What is the onboarding process for new employees?")

if __name__ == '__main__':
    create_test_data()