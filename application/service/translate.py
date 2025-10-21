"""
Live Translation Service using Google Cloud Translation API
Provides real-time translation capabilities for streaming text input
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import json

from google.cloud import translate
from google.auth.exceptions import DefaultCredentialsError
from google.api_core import exceptions as gcp_exceptions

from config import get_settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TranslationService:
    """
    Live translation service using Google Cloud Translation API
    Handles streaming text translation with real-time output
    """
    
    def __init__(self):
        """Initialize the translation service"""
        self.settings = get_settings()
        self.client: Optional[translate.TranslationServiceClient] = None
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
        Initialize the Google Cloud Translation client
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Set up authentication
            if self.settings.google_application_credentials:
                # Get the absolute path to credentials.json from root directory
                root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                credentials_path = os.path.join(root_dir, self.settings.google_application_credentials)
                
                if os.path.exists(credentials_path):
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
                    logger.info(f"✅ Using Google Cloud credentials from: {credentials_path}")
                else:
                    logger.warning(f"⚠️ Credentials file not found at: {credentials_path}")
                    logger.info("Please ensure credentials.json is in the root directory")
            
            # Initialize the client
            self.client = translate.TranslationServiceClient()
            
            # Test the connection
            if self._test_connection():
                self.is_initialized = True
                logger.info("✅ Google Cloud Translation service initialized successfully")
                return True
            else:
                logger.error("❌ Failed to test Google Cloud Translation connection")
                return False
                
        except DefaultCredentialsError as e:
            logger.error(f"❌ Google Cloud credentials not found: {e}")
            logger.error("Please set GOOGLE_APPLICATION_CREDENTIALS environment variable or run 'gcloud auth application-default login'")
            return False
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Cloud Translation service: {e}")
            return False
    
    def _test_connection(self) -> bool:
        """
        Test the connection to Google Cloud Translation API
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if not self.client:
                return False
                
            # Test with a simple translation
            parent = f"projects/{self.settings.google_cloud_project_id}/locations/{self.settings.google_cloud_location}"
            
            response = self.client.translate_text(
                request={
                    "contents": ["Hello"],
                    "target_language_code": "es",
                    "parent": parent,
                    "mime_type": "text/plain"
                }
            )
            
            return len(response.translations) > 0
            
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
        Translate a single text string
        
        Args:
            text: Text to translate
            source_language: Source language code (e.g., 'en')
            target_language: Target language code (e.g., 'es')
            model: Translation model to use
            mime_type: MIME type of the text
            
        Returns:
            Dict containing translation result and metadata
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        start_time = time.time()
        
        try:
            # Use defaults if not provided
            source_lang = source_language or self.settings.default_source_language
            target_lang = target_language or self.settings.default_target_language
            translation_model = model or self.settings.translation_model
            mime = mime_type or self.settings.translation_mime_type
            
            # Prepare the request
            parent = f"projects/{self.settings.google_cloud_project_id}/locations/{self.settings.google_cloud_location}"
            
            request_params = {
                "contents": [text],
                "target_language_code": target_lang,
                "parent": parent,
                "mime_type": mime
            }
            
            # Add source language if specified
            if source_lang:
                request_params["source_language_code"] = source_lang
            
            # Add model if specified and not default
            if translation_model and translation_model not in ["nmt", "base"]:
                request_params["model"] = f"{parent}/models/{translation_model}"
            
            # Perform translation
            response = self.client.translate_text(request=request_params)
            
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
            
            # Prepare result
            result = {
                "original_text": text,
                "translated_text": response.translations[0].translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "detected_language": response.translations[0].detected_language_code if hasattr(response.translations[0], 'detected_language_code') else source_lang,
                "model": translation_model,
                "mime_type": mime,
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            }
            
            # Display in terminal
            self._display_translation(result)
            
            return result
            
        except gcp_exceptions.GoogleAPIError as e:
            self.stats["failed_translations"] += 1
            logger.error(f"Google Cloud Translation API error: {e}")
            return {
                "original_text": text,
                "translated_text": None,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
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
            model: Translation model to use
            mime_type: MIME type of the text
            batch_size: Number of text chunks to process together
            delay_ms: Delay between translations in milliseconds
            
        Yields:
            Dict containing translation results
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        buffer = []
        
        async for text_chunk in text_stream:
            if text_chunk.strip():  # Only process non-empty chunks
                buffer.append(text_chunk.strip())
                
                # Process batch when it reaches the specified size
                if len(buffer) >= batch_size:
                    # Combine text chunks
                    combined_text = " ".join(buffer)
                    
                    # Translate the batch
                    result = await self.translate_text(
                        text=combined_text,
                        source_language=source_language,
                        target_language=target_language,
                        model=model,
                        mime_type=mime_type
                    )
                    
                    yield result
                    
                    # Clear buffer
                    buffer = []
                    
                    # Add delay if specified
                    if delay_ms > 0:
                        await asyncio.sleep(delay_ms / 1000.0)
        
        # Process any remaining text in buffer
        if buffer:
            combined_text = " ".join(buffer)
            result = await self.translate_text(
                text=combined_text,
                source_language=source_language,
                target_language=target_language,
                model=model,
                mime_type=mime_type
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
            target_language: Language to return language names in
            
        Returns:
            List of supported languages with codes and names
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        try:
            parent = f"projects/{self.settings.google_cloud_project_id}/locations/{self.settings.google_cloud_location}"
            
            response = self.client.get_supported_languages(
                request={
                    "parent": parent,
                    "display_language_code": target_language
                }
            )
            
            languages = []
            for language in response.languages:
                languages.append({
                    "code": language.language_code,
                    "name": language.display_name
                })
            
            return languages
            
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            return []
    
    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the input text
        
        Args:
            text: Text to detect language for
            
        Returns:
            Dict containing detected language information
        """
        if not self.is_initialized:
            raise RuntimeError("Translation service not initialized")
        
        try:
            parent = f"projects/{self.settings.google_cloud_project_id}/locations/{self.settings.google_cloud_location}"
            
            response = self.client.detect_language(
                request={
                    "parent": parent,
                    "content": text,
                    "mime_type": "text/plain"
                }
            )
            
            detection = response.languages[0]
            
            return {
                "text": text,
                "language_code": detection.language_code,
                "confidence": detection.confidence,
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
        return {
            "is_initialized": self.is_initialized,
            "stats": self.stats.copy(),
            "settings": {
                "project_id": self.settings.google_cloud_project_id,
                "location": self.settings.google_cloud_location,
                "default_source_language": self.settings.default_source_language,
                "default_target_language": self.settings.default_target_language,
                "translation_model": self.settings.translation_model
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

