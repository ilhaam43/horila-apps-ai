#!/usr/bin/env python3
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'horilla.settings')
django.setup()

from knowledge.models import KnowledgeDocument

print("=== Checking Knowledge Base for Employee Creation Info ===")

# Check Employee Handbook
handbook = KnowledgeDocument.objects.filter(title__icontains='Employee Handbook').first()
if handbook:
    print(f"\nEmployee Handbook found: {handbook.title}")
    print(f"Content preview: {handbook.content[:500]}...")
else:
    print("\nNo Employee Handbook found")

# Search for any document containing employee creation info
print("\n=== Searching for employee creation documents ===")
creation_docs = KnowledgeDocument.objects.filter(
    content__icontains='employee'
).filter(
    content__icontains='create'
)

if creation_docs.exists():
    for doc in creation_docs[:3]:
        print(f"\nFound: {doc.title}")
        print(f"Content: {doc.content[:300]}...")
else:
    print("No documents found containing both 'employee' and 'create'")

# Check all documents for FAQ-like content
print("\n=== Checking for FAQ content ===")
faq_docs = KnowledgeDocument.objects.filter(
    content__icontains='How to'
)

if faq_docs.exists():
    for doc in faq_docs[:3]:
        print(f"\nFAQ-like document: {doc.title}")
        print(f"Content: {doc.content[:300]}...")
else:
    print("No FAQ-like documents found")

print("\n=== Summary ===")
print(f"Total documents in knowledge base: {KnowledgeDocument.objects.count()}")
print("Document titles:")
for doc in KnowledgeDocument.objects.all()[:10]:
    print(f"- {doc.title}")