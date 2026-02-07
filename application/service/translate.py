"""
Live Translation Service using Google Gemini LLM
Provides real-time translation capabilities for streaming text input
"""

import asyncio
import logging
import os
import time
import json
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime

import google.generativeai as genai

from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Comprehensive language map for display names and supported languages
SUPPORTED_LANGUAGES = [
    {"code": "en", "name": "English"},
    {"code": "es", "name": "Spanish"},
    {"code": "fr", "name": "French"},
    {"code": "de", "name": "German"},
    {"code": "it", "name": "Italian"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "ru", "name": "Russian"},
    {"code": "ja", "name": "Japanese"},
    {"code": "ko", "name": "Korean"},
    {"code": "zh", "name": "Chinese (Simplified)"},
    {"code": "zh-TW", "name": "Chinese (Traditional)"},
    {"code": "ar", "name": "Arabic"},
    {"code": "hi", "name": "Hindi"},
    {"code": "th", "name": "Thai"},
    {"code": "vi", "name": "Vietnamese"},
    {"code": "my", "name": "Burmese"},
    {"code": "km", "name": "Khmer"},
    {"code": "nl", "name": "Dutch"},
    {"code": "sv", "name": "Swedish"},
    {"code": "no", "name": "Norwegian"},
    {"code": "da", "name": "Danish"},
    {"code": "fi", "name": "Finnish"},
    {"code": "pl", "name": "Polish"},
    {"code": "tr", "name": "Turkish"},
    {"code": "cs", "name": "Czech"},
    {"code": "hu", "name": "Hungarian"},
    {"code": "ro", "name": "Romanian"},
    {"code": "bg", "name": "Bulgarian"},
    {"code": "hr", "name": "Croatian"},
    {"code": "sk", "name": "Slovak"},
    {"code": "sl", "name": "Slovenian"},
    {"code": "et", "name": "Estonian"},
    {"code": "lv", "name": "Latvian"},
    {"code": "lt", "name": "Lithuanian"},
    {"code": "el", "name": "Greek"},
    {"code": "he", "name": "Hebrew"},
    {"code": "id", "name": "Indonesian"},
    {"code": "ms", "name": "Malay"},
    {"code": "tl", "name": "Filipino"},
    {"code": "uk", "name": "Ukrainian"},
    {"code": "ca", "name": "Catalan"},
    {"code": "eu", "name": "Basque"},
    {"code": "gl", "name": "Galician"},
]

LANGUAGE_NAME_MAP = {lang["code"]: lang["name"] for lang in SUPPORTED_LANGUAGES}


def _get_language_name(code: str) -> str:
    """Get human-readable language name from code."""
    return LANGUAGE_NAME_MAP.get(code, code)


class TranslationService:
    """
    Live translation service using Google Gemini LLM
    Handles streaming text translation with real-time output
    """
    
    def __init__(self):
        """Initialize the translation service"""
        self.settings = get_settings()
        self.model: Optional[genai.GenerativeModel] = None
        self.is_initialized = False
        self.translation_queue: asyncio.Queue = asyncio.Queue()
        self.active_translations: Dict[str, Dict] = {}
        
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
        Initialize the Google Gemini client
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            api_key = self.settings.google_api_key
            if not api_key:
                logger.error("❌ GOOGLE_API_KEY not set in environment / .env")
                return False

            genai.configure(api_key=api_key)

            model_name = getattr(self.settings, "gemini_model", "gemini-2.0-flash")
            self.model = genai.GenerativeModel(model_name)

            # Test the connection
            if self._test_connection():
                self.is_initialized = True
                logger.info(f"✅ Google Gemini translation service initialized (model: {model_name})")
                return True
            else:
                logger.error("❌ Failed to test Google Gemini connection")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Gemini translation service: {e}")
            return False
    
    def _test_connection(self) -> bool:
        """
        Test the connection to Google Gemini API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.model:
                return False
                
            response = self.model.generate_content(
                "Translate 'Hello' to Spanish. Reply with ONLY the translated text, nothing else."
            )
            result = response.text.strip()
            return len(result) > 0
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def translate_text(
        self,
        text: str,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        model: Optional[str] = None,
        mime_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Translate a single text string using Google Gemini LLM
        
        Args:
            text: Text to translate
            source_language: Source language code (e.g., 'en')
            target_language: Target language code (e.g., 'es')
            model: Unused (kept for interface compatibility)
            mime_type: Unused (kept for interface compatibility)
            
        Returns:
            Dict containing translation result and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        start_time = time.time()
        
        try:
            target_lang = target_language or self.settings.default_target_language
            
            # Auto-detect source language if not provided
            if source_language:
                source_lang = source_language
            else:
                detection_result = self.detect_language(text)
                if detection_result.get("language_code"):
                    source_lang = detection_result["language_code"]
                    logger.info(f"🔍 Auto-detected source language: {source_lang}")
                else:
                    source_lang = self.settings.default_source_language
                    logger.warning(f"⚠️ Language detection failed, using default: {source_lang}")
            
            source_name = _get_language_name(source_lang)
            target_name = _get_language_name(target_lang)

            prompt = (
                f"Translate the following text from {source_name} to {target_name}.\n"
                f"Reply with ONLY the translated text. Do not include any explanation, "
                f"notes, or the original text.\n\n"
                f"Text to translate:\n{text}"
            )

            # Run the synchronous Gemini call in a thread to keep async
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, self.model.generate_content, prompt
            )

            translated_text = response.text.strip()

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self.stats["total_translations"] += 1
            self.stats["successful_translations"] += 1
            self.stats["last_translation_time"] = datetime.utcnow().isoformat()
            
            if self.stats["average_latency_ms"] == 0:
                self.stats["average_latency_ms"] = latency_ms
            else:
                self.stats["average_latency_ms"] = (self.stats["average_latency_ms"] + latency_ms) / 2
            
            gemini_model = getattr(self.settings, "gemini_model", "gemini-2.0-flash")

            result = {
                "original_text": text,
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "detected_language": source_lang if not source_language else None,
                "model": gemini_model,
                "mime_type": "text/plain",
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            }
            
            self._display_translation(result)
            return result
            
        except Exception as e:
            self.stats["failed_translations"] += 1
            logger.error(f"Translation error: {e}")
            return {
                "original_text": text,
                "translated_text": None,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def translate_stream(
        self,
        text_stream: AsyncGenerator[str, None],
        source_language: Optional[str] = None,
        target_language: Optional[str] = None,
        model: Optional[str] = None,
        mime_type: Optional[str] = None,
        batch_size: int = 1,
        delay_ms: int = 100
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Translate streaming text input in real-time
        
        Args:
            text_stream: Async generator yielding text chunks
            source_language: Source language code
            target_language: Target language code
            model: Unused (kept for interface compatibility)
            mime_type: Unused (kept for interface compatibility)
            batch_size: Number of text chunks to process together
            delay_ms: Delay between translations in milliseconds
            
        Yields:
            Dict containing translation results
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        buffer = []
        
        async for text_chunk in text_stream:
            if text_chunk.strip():
                buffer.append(text_chunk.strip())
                
                if len(buffer) >= batch_size:
                    combined_text = " ".join(buffer)
                    
                    result = await self.translate_text(
                        text=combined_text,
                        source_language=source_language,
                        target_language=target_language,
                    )
                    
                    yield result
                    buffer = []
                    
                    if delay_ms > 0:
                        await asyncio.sleep(delay_ms / 1000.0)
        
        # Process any remaining text in buffer
        if buffer:
            combined_text = " ".join(buffer)
            result = await self.translate_text(
                text=combined_text,
                source_language=source_language,
                target_language=target_language,
            )
            yield result
    
    def _display_translation(self, result: Dict[str, Any]) -> None:
        """
        Display translation result in terminal with formatting
        
        Args:
            result: Translation result dictionary
        """
        if result["success"]:
            print("\n" + "="*80)
            print(f"🔄 LIVE TRANSLATION - {result['timestamp']}")
            print("="*80)
            print(f"📝 Original ({result['source_language']}): {result['original_text']}")
            print(f"🌍 Translated ({result['target_language']}): {result['translated_text']}")
            print(f"⚡ Latency: {result['latency_ms']}ms")
            print(f"🤖 Model: {result['model']}")
            print("="*80)
        else:
            print(f"\n❌ Translation failed: {result.get('error', 'Unknown error')}")
    
    def get_supported_languages(self, target_language: str = "en") -> List[Dict[str, str]]:
        """
        Get list of supported languages
        
        Args:
            target_language: Unused (kept for interface compatibility)
            
        Returns:
            List of supported languages with codes and names
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        return [lang.copy() for lang in SUPPORTED_LANGUAGES]
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the input text using Gemini
        
        Args:
            text: Text to detect language for
            
        Returns:
            Dict containing detected language information
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        try:
            prompt = (
                "Detect the language of the following text.\n"
                "Reply with ONLY a JSON object in this exact format: "
                '{\"language_code\": \"<ISO 639-1 code>\", \"confidence\": <0.0-1.0>}\n'
                "Do not include any other text.\n\n"
                f"Text:\n{text}"
            )

            response = self.model.generate_content(prompt)
            raw = response.text.strip()

            # Strip markdown fences if present
            if raw.startswith("```"):
                lines = raw.split("\n")
                # Remove first and last lines (fences)
                lines = [l for l in lines if not l.strip().startswith("```")]
                raw = "\n".join(lines).strip()

            parsed = json.loads(raw)
            
            return {
                "text": text,
                "language_code": parsed.get("language_code"),
                "confidence": parsed.get("confidence", 0.9),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Language detection failed: {e}")
            return {
                "text": text,
                "language_code": None,
                "confidence": 0.0,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get translation service statistics
        
        Returns:
            Dict containing service statistics
        """
        gemini_model = getattr(self.settings, "gemini_model", "gemini-2.0-flash")
        return {
            "is_initialized": self.is_initialized,
            "stats": self.stats.copy(),
            "settings": {
                "model": gemini_model,
                "default_source_language": self.settings.default_source_language,
                "default_target_language": self.settings.default_target_language,
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
        logger.info("Translation statistics reset")


# Global translation service instance
_translation_service: Optional[TranslationService] = None

def get_translation_service() -> TranslationService:
    """
    Get the global translation service instance
    
    Returns:
        TranslationService: The global translation service instance
    """
    global _translation_service
    if _translation_service is None:
        _translation_service = TranslationService()
    return _translation_service

def initialize_translation_service() -> bool:
    """
    Initialize the global translation service
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    service = get_translation_service()
    return service.initialize()
