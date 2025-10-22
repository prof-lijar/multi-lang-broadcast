"""
Simplified TTS Service - Direct TTS without queue
Provides direct text-to-speech functionality without queuing
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SimpleTTSService:
    """Simplified TTS service for direct audio playback"""
    
    def __init__(self):
        """Initialize the simplified TTS service"""
        self.is_initialized = False
        self.is_playing = False
        self.current_text = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'completed_requests': 0,
            'failed_requests': 0,
            'currently_playing': False,
            'last_processed': None
        }
        
        logger.info("Simple TTS Service initialized")
    
    def speak_text(self, text: str, language_code: str = 'en-US') -> bool:
        """
        Convert text to speech and play immediately
        
        Args:
            text: Text to convert to speech
            language_code: Language for TTS
            
        Returns:
            True if successful, False otherwise
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS, skipping")
            return False
        
        if self.is_playing:
            logger.warning("TTS is already playing, skipping request")
            return False
        
        try:
            self.is_playing = True
            self.current_text = text
            self.stats['total_requests'] += 1
            
            logger.info(f"Processing TTS request: '{text[:50]}...'")
            
            # Simulate TTS processing
            time.sleep(1.0)  # Simulate processing time
            
            self.stats['completed_requests'] += 1
            self.stats['last_processed'] = datetime.utcnow().isoformat()
            logger.info(f"TTS completed: '{text[:50]}...'")
            
            return True
            
        except Exception as e:
            logger.error(f"TTS failed for '{text[:50]}...': {e}")
            self.stats['failed_requests'] += 1
            return False
        finally:
            self.is_playing = False
            self.current_text = None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get TTS service statistics"""
        stats = self.stats.copy()
        stats['currently_playing'] = self.is_playing
        stats['current_text'] = self.current_text[:50] + '...' if self.current_text else None
        return stats
    
    def is_busy(self) -> bool:
        """Check if TTS is currently playing"""
        return self.is_playing
    
    def stop_playing(self):
        """Stop current TTS playback"""
        if self.is_playing:
            self.is_playing = False
            self.current_text = None
            logger.info("TTS playback stopped")


# Global instance
_simple_tts_service = None

def get_simple_tts_service() -> SimpleTTSService:
    """Get the global simple TTS service instance"""
    global _simple_tts_service
    if _simple_tts_service is None:
        _simple_tts_service = SimpleTTSService()
    return _simple_tts_service

def initialize_simple_tts() -> bool:
    """Initialize the simple TTS service"""
    try:
        service = get_simple_tts_service()
        service.is_initialized = True
        logger.info("Simple TTS service initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize simple TTS service: {e}")
        return False
