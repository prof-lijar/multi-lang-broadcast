"""
SLLM Translation Service using Ollama
Provides local translation capabilities using small language models
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SLLMTranslationService:
    """
    Small Language Model translation service using Ollama
    Handles local translation with Ollama models
    """
    
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", model: str = "qwen2:0.5b"):
        """Initialize the SLLM translation service"""
        self.ollama_url = ollama_url
        self.model = model
        self.is_initialized = False
        
        # Translation statistics
        self.stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "average_latency_ms": 0,
            "last_translation_time": None
        }
        
    def initialize(self) -> bool:
        """
        Initialize the Ollama connection
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Test the connection
            if self._test_connection():
                self.is_initialized = True
                logger.info(f"✅ SLLM Translation service initialized successfully with model: {self.model}")
                return True
            else:
                logger.error("❌ Failed to test Ollama connection")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize SLLM Translation service: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """
        Test the connection to Ollama API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Test with a simple request
                test_payload = {
                    "model": self.model,
                    "prompt": "Hello",
                    "stream": False
                }
                
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=test_payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return True
                    else:
                        logger.error(f"Ollama test failed with status: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def translate_text(
        self,
        text: str,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate a single text string using Ollama
        
        Args:
            text: Text to translate
            source_language: Source language code (e.g., 'en')
            target_language: Target language code (e.g., 'es')
            
        Returns:
            Dict containing translation result and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("SLLM Translation service not initialized")
        
        start_time = time.time()
        
        try:
            # Create translation prompt
            prompt = self._create_translation_prompt(text, source_language, target_language)
            
            # Prepare request payload
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            
            # Make request to Ollama
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status != 200:
                        raise Exception(f"Ollama API returned status {response.status}")
                    
                    result = await response.json()
                    
                    # Calculate latency
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Update statistics
                    self.stats["total_translations"] += 1
                    self.stats["successful_translations"] += 1
                    self.stats["last_translation_time"] = datetime.utcnow().isoformat()
                    
                    # Update average latency
                    if self.stats["average_latency_ms"] == 0:
                        self.stats["average_latency_ms"] = latency_ms
                    else:
                        self.stats["average_latency_ms"] = (self.stats["average_latency_ms"] + latency_ms) / 2
                    
                    # Extract translated text from response
                    translated_text = result.get("response", "").strip()
                    
                    # Prepare result
                    result_dict = {
                        "original_text": text,
                        "translated_text": translated_text,
                        "source_language": source_language or "auto",
                        "target_language": target_language or "en",
                        "model": self.model,
                        "latency_ms": round(latency_ms, 2),
                        "timestamp": datetime.utcnow().isoformat(),
                        "success": True
                    }
                    
                    # Display in terminal
                    self._display_translation(result_dict)
                    
                    return result_dict
                    
        except Exception as e:
            self.stats["failed_translations"] += 1
            logger.error(f"SLLM Translation error: {e}")
            return {
                "original_text": text,
                "translated_text": None,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _create_translation_prompt(self, text: str, source_language: Optional[str], target_language: Optional[str]) -> str:
        """
        Create a translation prompt for the Ollama model
        
        Args:
            text: Text to translate
            source_language: Source language
            target_language: Target language
            
        Returns:
            str: Formatted prompt for translation
        """
        # Language code to full name mapping with script specifications
        language_names = {
            'en': 'English',
            'ko': 'Korean (using Hangul script)',
            'zh': 'Chinese (using Simplified Chinese characters)',
            'ja': 'Japanese (using Hiragana, Katakana, and Kanji)',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian (using Cyrillic script)',
            'ar': 'Arabic (using Arabic script)',
            'hi': 'Hindi (using Devanagari script)',
            'th': 'Thai (using Thai script)',
            'vi': 'Vietnamese',
            'tr': 'Turkish',
            'pl': 'Polish',
            'nl': 'Dutch',
            'sv': 'Swedish',
            'da': 'Danish',
            'no': 'Norwegian',
            'fi': 'Finnish',
            'cs': 'Czech',
            'hu': 'Hungarian',
            'ro': 'Romanian',
            'bg': 'Bulgarian (using Cyrillic script)',
            'hr': 'Croatian',
            'sk': 'Slovak',
            'sl': 'Slovenian',
            'et': 'Estonian',
            'lv': 'Latvian',
            'lt': 'Lithuanian',
            'el': 'Greek (using Greek script)',
            'he': 'Hebrew (using Hebrew script)',
            'fa': 'Persian (using Arabic script)',
            'ur': 'Urdu (using Arabic script)',
            'bn': 'Bengali (using Bengali script)',
            'ta': 'Tamil (using Tamil script)',
            'te': 'Telugu (using Telugu script)',
            'ml': 'Malayalam (using Malayalam script)',
            'kn': 'Kannada (using Kannada script)',
            'gu': 'Gujarati (using Gujarati script)',
            'pa': 'Punjabi (using Gurmukhi script)',
            'ne': 'Nepali (using Devanagari script)',
            'si': 'Sinhala (using Sinhala script)',
            'my': 'Burmese (using Myanmar script)',
            'km': 'Khmer (using Khmer script)',
            'lo': 'Lao (using Lao script)',
            'ka': 'Georgian (using Georgian script)',
            'am': 'Amharic (using Geez script)',
            'sw': 'Swahili',
            'zu': 'Zulu',
            'af': 'Afrikaans',
            'is': 'Icelandic',
            'ga': 'Irish',
            'cy': 'Welsh',
            'mt': 'Maltese',
            'eu': 'Basque',
            'ca': 'Catalan',
            'gl': 'Galician'
        }
        
        # Get language names
        source_name = language_names.get(source_language, source_language) if source_language else 'English'
        target_name = language_names.get(target_language, target_language) if target_language else 'English'
        
        # Create clear, specific prompt with script emphasis
        if source_language and target_language and source_language != target_language:
            if target_language == 'ko':
                return f"Translate the following text from {source_name} to {target_name}. IMPORTANT: Output must be in Korean Hangul script (한글), not Chinese characters. ONLY provide the direct translation, nothing else, no questions, no additional text:\n\n{text}"
            elif target_language == 'zh':
                return f"Translate the following text from {source_name} to {target_name}. IMPORTANT: Output must be in Simplified Chinese characters (简体中文), not Korean Hangul. Only provide the translation, no explanations:\n\n{text}"
            elif target_language == 'ja':
                return f"Translate the following text from {source_name} to {target_name}. IMPORTANT: Output must be in Japanese (ひらがな、カタカナ、漢字), not Korean Hangul. Only provide the translation, no explanations:\n\n{text}"
            else:
                return f"Translate the following text from {source_name} to {target_name}. ONLY provide the direct translation, nothing else, no questions, no additional text:\n\n{text}"
        elif target_language:
            if target_language == 'ko':
                return f"Translate the following text to {target_name}. IMPORTANT: Output must be in Korean Hangul script (한글), not Chinese characters. ONLY provide the direct translation, nothing else, no questions, no additional text:\n\n{text}"
            elif target_language == 'zh':
                return f"Translate the following text to {target_name}. IMPORTANT: Output must be in Simplified Chinese characters (简体中文), not Korean Hangul. Only provide the translation, no explanations:\n\n{text}"
            elif target_language == 'ja':
                return f"Translate the following text to {target_name}. IMPORTANT: Output must be in Japanese (ひらがな、カタカナ、漢字), not Korean Hangul. Only provide the translation, no explanations:\n\n{text}"
            else:
                return f"Translate the following text to {target_name}. ONLY provide the direct translation, nothing else, no questions, no additional text:\n\n{text}"
        else:
            return f"Translate the following text to English. ONLY provide the direct translation, nothing else, no questions, no additional text:\n\n{text}"
    
    def _display_translation(self, result: Dict[str, Any]) -> None:
        """
        Display translation result in terminal with formatting
        
        Args:
            result: Translation result dictionary
        """
        if result["success"]:
            print("\n" + "="*80)
            print(f"🔄 SLLM TRANSLATION - {result['timestamp']}")
            print("="*80)
            print(f"📝 Original ({result['source_language']}): {result['original_text']}")
            print(f"🌍 Translated ({result['target_language']}): {result['translated_text']}")
            print(f"⚡ Latency: {result['latency_ms']}ms")
            print(f"🤖 Model: {result['model']}")
            print("="*80)
        else:
            print(f"\n❌ SLLM Translation failed: {result.get('error', 'Unknown error')}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get translation service statistics
        
        Returns:
            Dict containing service statistics
        """
        return {
            "is_initialized": self.is_initialized,
            "stats": self.stats.copy(),
            "settings": {
                "ollama_url": self.ollama_url,
                "model": self.model
            }
        }
    
    def reset_statistics(self) -> None:
        """Reset translation statistics"""
        self.stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "average_latency_ms": 0,
            "last_translation_time": None
        }
        logger.info("SLLM Translation statistics reset")


# Global SLLM translation service instance
_sllm_translation_service: Optional[SLLMTranslationService] = None

def get_sllm_translation_service() -> SLLMTranslationService:
    """
    Get the global SLLM translation service instance
    
    Returns:
        SLLMTranslationService: The global SLLM translation service instance
    """
    global _sllm_translation_service
    if _sllm_translation_service is None:
        _sllm_translation_service = SLLMTranslationService()
    return _sllm_translation_service

def initialize_sllm_translation_service() -> bool:
    """
    Initialize the global SLLM translation service
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    service = get_sllm_translation_service()
    return service.initialize()
