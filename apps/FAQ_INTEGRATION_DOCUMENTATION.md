# FAQ Integration Documentation

## Overview
Integrasi FAQ telah berhasil diimplementasikan dalam sistem AI Assistant Horilla HRMS. Sistem sekarang dapat mencari dan menggunakan informasi dari FAQ Helpdesk untuk memberikan jawaban yang lebih akurat dan spesifik.

## What Was Implemented

### 1. FAQ Search Integration
- **File Modified**: `knowledge/chatbot_service.py`
- **New Import**: Added `from helpdesk.models import FAQ`
- **New Method**: `_faq_search()` - Searches through helpdesk FAQ entries
- **New Method**: `_calculate_faq_relevance()` - Calculates relevance score for FAQ entries

### 2. Search Strategy Prioritization
- FAQ search is now **Strategy 1** (highest priority)
- Knowledge documents search moved to Strategy 2-4
- This ensures FAQ answers are found first for common questions

### 3. Response Generation Enhancement
- Modified `generate_response()` method to handle FAQ results
- Added `referenced_faqs` tracking
- FAQ answers are properly formatted in AI responses

## How It Works

### Search Process
1. **FAQ Search**: System first searches through helpdesk FAQ entries
2. **Keyword Matching**: Searches both question and answer fields
3. **Relevance Scoring**: Calculates score based on keyword matches
4. **Fallback**: If not enough results, searches knowledge documents

### Example Query
**Query**: "How to create an Employee?"

**FAQ Found**:
- Question: "How to create an Employee?"
- Answer: "Employee > Employees > Create > Fill out the form"

**AI Response**: 
```
Untuk membuat seorang pegawai Anda, Anda harus mendaftarkan sendiri melalui perangkat lunak yang tersedia. Ini dilaksanakan dengan memulai dalam menu Employee dan mengeklik button "Employees" hanya untuk dapat melihat ruang kemudian dibawah "Create". Setelah Anda memutuskan untuk membuat seorang pegawai baru, Anda harus merespon ke formulir yang disediakan. Fill out semua kolom dengan informasi identifikasi yang sesuai dan akhirnya diisi ke dalam sistem perilaku rekayasa manusia (HR). Referensi: Employee > Employees > Create
```

## Technical Details

### Code Changes

#### 1. FAQ Search Method
```python
def _faq_search(self, query: str, user: User, max_results: int) -> List[Dict[str, Any]]:
    """Search in helpdesk FAQ"""
    try:
        # Build search query for FAQ
        search_terms = query.lower().split()
        q_objects = Q()
        
        for term in search_terms:
            q_objects |= (
                Q(question__icontains=term) |
                Q(answer__icontains=term)
            )
        
        # Get FAQ entries
        faqs = FAQ.objects.filter(
            q_objects,
            is_active=True
        ).select_related('category')[:max_results * 2]
        
        results = []
        for faq in faqs:
            # Calculate simple relevance score
            score = self._calculate_faq_relevance(query, faq)
            if score > 0:
                results.append({
                    'faq': faq,
                    'similarity_score': score,
                    'snippet': faq.answer[:200] + '...' if len(faq.answer) > 200 else faq.answer,
                    'method': 'faq_search',
                    'type': 'faq'
                })
        
        return sorted(results, key=lambda x: x['similarity_score'], reverse=True)[:max_results]
        
    except Exception as e:
        logger.error(f"FAQ search failed: {e}")
        return []
```

#### 2. Response Generation Enhancement
```python
# Handle FAQ results in generate_response method
if doc_data.get('type') == 'faq':
    faq = doc_data['faq']
    referenced_faqs.append(faq)
    context_part = f"FAQ: {faq.question}\nAnswer: {faq.answer}"
    if faq.category:
        context_part += f"\nCategory: {faq.category.title}"
else:
    # Handle regular documents
    doc = doc_data['document']
    referenced_documents.append(doc)
    context_part = f"Document: {doc.title}\nContent: {doc_data.get('snippet', '')}"
```

## Testing Results

### Test Script: `test_faq_integration.py`
- **FAQ Found**: ✅ "How to create an Employee?"
- **FAQ Answer**: ✅ "Employee > Employees > Create > Fill out the form"
- **AI Response**: ✅ Properly formatted with FAQ reference
- **Referenced FAQs**: ✅ 5 FAQs found and referenced

### Performance
- **Search Speed**: Fast (FAQ search is prioritized)
- **Accuracy**: High (exact FAQ matches found)
- **Relevance**: Improved (FAQ answers are more specific than general documents)

## Benefits

1. **Faster Responses**: FAQ search is faster than document embedding search
2. **More Accurate**: FAQ answers are specifically written for common questions
3. **Better User Experience**: Users get direct, actionable answers
4. **Reduced Load**: Less dependency on AI semantic search for common queries

## FAQ Data Source

### Location
- **File**: `/load_data/faq.json`
- **Model**: `helpdesk.models.FAQ`
- **Fields**: `question`, `answer`, `category`, `is_active`

### Sample FAQ Entry
```json
{
    "question": "How to create an Employee?",
    "answer": "Employee > Employees > Create > Fill out the form",
    "category": "Employee Management",
    "is_active": true
}
```

## API Endpoints

### Chatbot API
- **URL**: `/ai_services/chatbot/chat/`
- **Method**: POST
- **Parameters**: `query` (string)
- **Response**: JSON with AI response and referenced FAQs

### Response Format
```json
{
    "success": true,
    "response": "AI generated response...",
    "confidence_score": 0.8,
    "referenced_documents": [],
    "referenced_faqs": [
        {
            "question": "How to create an Employee?",
            "answer": "Employee > Employees > Create > Fill out the form"
        }
    ]
}
```

## Future Enhancements

1. **FAQ Categories**: Implement category-based search filtering
2. **FAQ Ranking**: Improve relevance scoring algorithm
3. **FAQ Analytics**: Track which FAQs are most frequently used
4. **FAQ Management**: Admin interface for managing FAQ entries
5. **Multi-language**: Support for FAQ in multiple languages

## Troubleshooting

### Common Issues

1. **FAQ Not Found**
   - Check if FAQ exists in database: `FAQ.objects.filter(question__icontains='keyword')`
   - Verify FAQ is active: `is_active=True`
   - Check search terms match FAQ content

2. **No FAQ Results**
   - Verify FAQ data is loaded: `python manage.py loaddata load_data/faq.json`
   - Check database connection
   - Review search query terms

3. **AI Not Using FAQ**
   - Verify FAQ search is prioritized in `retrieve_relevant_documents`
   - Check FAQ relevance scoring
   - Review context building in `generate_response`

### Debug Commands
```bash
# Test FAQ integration
python3 test_faq_integration.py

# Check FAQ count
python3 manage.py shell -c "from helpdesk.models import FAQ; print(f'Total FAQs: {FAQ.objects.count()}')"

# Test specific FAQ
python3 manage.py shell -c "from helpdesk.models import FAQ; faq = FAQ.objects.filter(question__icontains='employee').first(); print(f'FAQ: {faq.question if faq else None}')"
```

## Conclusion

FAQ integration has been successfully implemented and tested. The system now provides more accurate and faster responses for common HR questions by prioritizing FAQ search over document search. This enhancement significantly improves the user experience and reduces response time for frequently asked questions.