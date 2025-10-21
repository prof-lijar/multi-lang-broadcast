#!/usr/bin/env python3
"""
Test script for the live translation functionality
"""

import asyncio
import json
import requests
import time

async def test_translation_api():
    """Test the translation API endpoint"""
    print("🧪 Testing Translation API...")
    
    # Test data
    test_cases = [
        {
            "text": "Hello, how are you?",
            "target_language": "ko",
            "expected_contains": ["안녕", "어떻게", "있어"]
        },
        {
            "text": "Good morning",
            "target_language": "zh",
            "expected_contains": ["早上", "好"]
        },
        {
            "text": "Thank you very much",
            "target_language": "ja",
            "expected_contains": ["ありがとう", "ございます"]
        }
    ]
    
    base_url = "http://localhost:8000"
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: Translating '{test_case['text']}' to {test_case['target_language']}")
        
        try:
            response = requests.post(
                f"{base_url}/translate",
                json={
                    "text": test_case["text"],
                    "target_language": test_case["target_language"]
                },
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Status: {result.get('status')}")
                
                if result.get('status') == 'success':
                    translated_text = result.get('data', {}).get('translated_text', '')
                    print(f"🌐 Translation: {translated_text}")
                    
                    # Check if translation contains expected keywords
                    contains_expected = any(
                        keyword in translated_text 
                        for keyword in test_case['expected_contains']
                    )
                    
                    if contains_expected:
                        print("✅ Translation looks correct!")
                    else:
                        print("⚠️ Translation might not be accurate")
                else:
                    print(f"❌ Translation failed: {result.get('error', 'Unknown error')}")
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
        
        # Wait between tests
        await asyncio.sleep(1)

async def test_stt_status():
    """Test STT service status"""
    print("\n🎤 Testing STT Service Status...")
    
    try:
        response = requests.get("http://localhost:8000/stt/status", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ STT Service Status: {result.get('status')}")
            
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"📊 STT Stats:")
                print(f"   - Initialized: {data.get('is_initialized')}")
                print(f"   - Streaming: {data.get('is_streaming')}")
                print(f"   - Processed chunks: {data.get('processed_chunks', 0)}")
                print(f"   - Total transcripts: {data.get('total_transcripts', 0)}")
                print(f"   - Error count: {data.get('error_count', 0)}")
            else:
                print(f"❌ STT Service not available")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ STT status check failed: {e}")

async def test_translation_status():
    """Test translation service status"""
    print("\n🌐 Testing Translation Service Status...")
    
    try:
        response = requests.get("http://localhost:8000/translate/status", timeout=5)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Translation Service Status: {result.get('status')}")
            
            if result.get('status') == 'success':
                data = result.get('data', {})
                print(f"📊 Translation Stats:")
                print(f"   - Initialized: {data.get('is_initialized')}")
                print(f"   - Total translations: {data.get('total_translations', 0)}")
                print(f"   - Successful: {data.get('successful_translations', 0)}")
                print(f"   - Failed: {data.get('failed_translations', 0)}")
            else:
                print(f"❌ Translation Service not available")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Translation status check failed: {e}")

async def main():
    """Run all tests"""
    print("🚀 Starting Live Translation Tests")
    print("=" * 50)
    
    # Test service status first
    await test_stt_status()
    await test_translation_status()
    
    # Test translation API
    await test_translation_api()
    
    print("\n" + "=" * 50)
    print("✅ Tests completed!")
    print("\n📋 Next steps:")
    print("1. Start the application: python main.py")
    print("2. Open the UI: http://localhost:8000/app_ui.html")
    print("3. Test live transcription and translation")

if __name__ == "__main__":
    asyncio.run(main())
