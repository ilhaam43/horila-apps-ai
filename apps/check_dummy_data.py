#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from knowledge.models import KnowledgeDocument, DocumentCategory, DocumentTag

print(f'Categories: {DocumentCategory.objects.count()}')
print(f'Documents: {KnowledgeDocument.objects.count()}')
print(f'Tags: {DocumentTag.objects.count()}')

print('\nCategories:')
for cat in DocumentCategory.objects.all():
    print(f'- {cat.name}: {cat.description}')

print('\nSample documents:')
for doc in KnowledgeDocument.objects.all()[:5]:
    print(f'- {doc.title} ({doc.category.name}) - {doc.status}')
    print(f'  Tags: {", ".join([tag.name for tag in doc.tags.all()])}')
    print(f'  Created: {doc.created_at.strftime("%Y-%m-%d")}')
    print()

print('\nDocument status distribution:')
from django.db.models import Count
status_counts = KnowledgeDocument.objects.values('status').annotate(count=Count('status'))
for item in status_counts:
    print(f'- {item["status"]}: {item["count"]} documents')