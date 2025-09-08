import json
from django.test import Client

def test_faq():
    client = Client()
    
    # Try different login methods
    login_ok = False
    
    # Try with email-based usernames
    test_users = [
        ('michael.brown@horilla.com', 'admin'),
        ('sarah.anderson@horilla.com', 'admin'),
        ('admin', 'admin123'),
        ('admin', 'password')
    ]
    
    for username, password in test_users:
        if client.login(username=username, password=password):
            login_ok = True
            print(f"Login successful with: {username}")
            break
    
    if not login_ok:
        print("❌ All login attempts failed")
        return
    
    # Test query
    response = client.post(
        '/api/knowledge/api/chatbot/query/',
        data=json.dumps({'query': 'How do I create a new employee?'}),
        content_type='application/json'
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Success: {data.get('success')}")
        print(f"Response: {data.get('response', '')[:100]}...")
        print(f"FAQs: {len(data.get('referenced_faqs', []))}")
        
        faqs = data.get('referenced_faqs', [])
        for i, faq in enumerate(faqs[:2], 1):
            print(f"  FAQ {i}: {faq.get('question', 'N/A')}")
    else:
        print(f"Error: {response.content.decode()[:200]}")

test_faq()