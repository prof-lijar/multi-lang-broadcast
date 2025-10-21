#!/usr/bin/env python3
"""
Test script for the Live Translation Service
Demonstrates real-time translation capabilities
"""

import asyncio
import sys
import os
from typing import AsyncGenerator

# Add the application directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from service.translate import get_translation_service, initialize_translation_service

async def simulate_streaming_text() -> AsyncGenerator[str, None]:
    """
    Simulate streaming text input by yielding words one by one
    """
    sample_texts = [
        "Hello, how are you today?",
        "This is a test of the live translation service.",
        "The weather is beautiful today.",
        "I hope you are having a great day!",
        "Thank you for using our translation service."
    ]
    
    for text in sample_texts:
        words = text.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.5)  # Simulate streaming delay
        yield "\n"  # Add line break between sentences
        await asyncio.sleep(1.0)  # Pause between sentences

async def test_single_translation():
    """Test single text translation"""
    print("🔄 Testing single text translation...")
    
    service = get_translation_service()
    
    # Test with different language pairs
    test_cases = [
        ("Hello, world!", "en", "es"),
        ("Bonjour le monde!", "fr", "en"),
        ("Hola mundo!", "es", "fr"),
        ("Guten Tag!", "de", "en")
    ]
    
    for text, source_lang, target_lang in test_cases:
        print(f"\n📝 Testing: '{text}' ({source_lang} → {target_lang})")
        result = await service.translate_text(
            text=text,
            source_language=source_lang,
            target_language=target_lang
        )
        
        if result["success"]:
            print(f"✅ Translation successful!")
        else:
            print(f"❌ Translation failed: {result.get('error', 'Unknown error')}")

async def test_streaming_translation():
    """Test streaming text translation"""
    print("\n🔄 Testing streaming text translation...")
    
    service = get_translation_service()
    
    print("📡 Starting streaming translation (English → Spanish)...")
    print("="*60)
    
    async for result in service.translate_stream(
        text_stream=simulate_streaming_text(),
        source_language="en",
        target_language="es",
        batch_size=3,  # Process 3 words at a time
        delay_ms=200   # 200ms delay between translations
    ):
        if result["success"]:
            print(f"🌍 Translated: {result['translated_text']}")
        else:
            print(f"❌ Translation failed: {result.get('error', 'Unknown error')}")

async def test_language_detection():
    """Test language detection"""
    print("\n🔄 Testing language detection...")
    
    service = get_translation_service()
    
    test_texts = [
        "Hello, how are you?",
        "Bonjour, comment allez-vous?",
        "Hola, ¿cómo estás?",
        "Guten Tag, wie geht es dir?",
        "Ciao, come stai?"
    ]
    
    for text in test_texts:
        result = service.detect_language(text)
        if result["language_code"]:
            print(f"📝 '{text}' → Detected: {result['language_code']} (confidence: {result['confidence']:.2f})")
        else:
            print(f"❌ Failed to detect language for: '{text}'")

async def test_supported_languages():
    """Test getting supported languages"""
    print("\n🔄 Testing supported languages...")
    
    service = get_translation_service()
    
    languages = service.get_supported_languages("en")
    print(f"📋 Found {len(languages)} supported languages:")
    
    # Show first 10 languages
    for i, lang in enumerate(languages[:10]):
        print(f"  {i+1}. {lang['name']} ({lang['code']})")
    
    if len(languages) > 10:
        print(f"  ... and {len(languages) - 10} more languages")

async def main():
    """Main test function"""
    print("🚀 Live Translation Service Test")
    print("="*50)
    
    # Initialize the translation service
    print("🔧 Initializing translation service...")
    if not initialize_translation_service():
        print("❌ Failed to initialize translation service!")
        print("Please ensure:")
        print("1. credentials.json is in the root directory")
        print("2. Google Cloud Translation API is enabled")
        print("3. Your project has the necessary permissions")
        return
    
    print("✅ Translation service initialized successfully!")
    
    # Get service statistics
    service = get_translation_service()
    stats = service.get_statistics()
    print(f"\n📊 Service Status:")
    print(f"  Project ID: {stats['settings']['project_id']}")
    print(f"  Location: {stats['settings']['location']}")
    print(f"  Default Source: {stats['settings']['default_source_language']}")
    print(f"  Default Target: {stats['settings']['default_target_language']}")
    
    try:
        # Run tests
        await test_single_translation()
        await test_language_detection()
        await test_supported_languages()
        await test_streaming_translation()
        
        # Show final statistics
        final_stats = service.get_statistics()
        print(f"\n📈 Final Statistics:")
        print(f"  Total translations: {final_stats['stats']['total_translations']}")
        print(f"  Successful: {final_stats['stats']['successful_translations']}")
        print(f"  Failed: {final_stats['stats']['failed_translations']}")
        print(f"  Average latency: {final_stats['stats']['average_latency_ms']:.2f}ms")
        
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main())
