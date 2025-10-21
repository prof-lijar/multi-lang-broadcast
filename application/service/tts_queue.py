"""
TTS Queue Service for Sequential Audio Playback
Prevents overlapping speech by queuing TTS requests and playing them sequentially
"""

import queue
import threading
import time
import logging
import os
import subprocess
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TTSStatus(Enum):
    """Status of TTS processing"""
    QUEUED = "queued"
    GENERATING = "generating"
    PLAYING = "playing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TTSRequest:
    """Represents a TTS request"""
    id: str
    text: str
    language_code: str
    speaker1_config: Dict[str, Any]
    speaker2_config: Dict[str, Any]
    timestamp: datetime
    status: TTSStatus = TTSStatus.QUEUED
    audio_file: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2


class TTSQueue:
    """Queue-based TTS service for sequential audio playback"""
    
    def __init__(self, max_queue_size: int = 20):
        """
        Initialize the TTS queue
        
        Args:
            max_queue_size: Maximum number of TTS requests in queue
        """
        self.max_queue_size = max_queue_size
        self.tts_queue = queue.Queue(maxsize=max_queue_size)
        
        # Processing state
        self.is_processing = False
        self.is_playing = False
        self.current_request: Optional[TTSRequest] = None
        self.processing_thread = None
        
        # Callbacks for external services
        self.tts_callback: Optional[Callable] = None
        self.audio_callback: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'completed_requests': 0,
            'failed_requests': 0,
            'queue_size': 0,
            'currently_playing': False,
            'last_processed': None
        }
        
        # Thread locks
        self._stats_lock = threading.Lock()
        self._processing_lock = threading.Lock()
        
        logger.info("TTSQueue initialized for sequential audio playback")
    
    def set_callbacks(self, 
                     tts_callback: Callable,
                     audio_callback: Callable):
        """Set callback functions for external services"""
        self.tts_callback = tts_callback
        self.audio_callback = audio_callback
        logger.info("TTS and audio callbacks set")
    
    def add_request(self, 
                   text: str, 
                   language_code: str,
                   speaker1_config: Dict[str, Any],
                   speaker2_config: Dict[str, Any]) -> str:
        """
        Add a TTS request to the queue
        
        Args:
            text: Text to convert to speech
            language_code: Language for TTS
            speaker1_config: Configuration for speaker 1
            speaker2_config: Configuration for speaker 2
            
        Returns:
            Request ID for tracking
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS, skipping")
            return None
        
        request_id = f"tts_{int(time.time() * 1000)}_{len(text)}"
        request = TTSRequest(
            id=request_id,
            text=text.strip(),
            language_code=language_code,
            speaker1_config=speaker1_config,
            speaker2_config=speaker2_config,
            timestamp=datetime.utcnow()
        )
        
        try:
            self.tts_queue.put(request, timeout=1.0)
            
            with self._stats_lock:
                self.stats['total_requests'] += 1
                self.stats['queue_size'] = self.tts_queue.qsize()
            
            logger.info(f"Added TTS request to queue: '{text[:50]}...' (ID: {request_id})")
            
            # Start processing if not already running
            if not self.is_processing:
                self.start_processing()
            
            return request_id
            
        except queue.Full:
            logger.warning(f"TTS queue full, dropping request: '{text[:50]}...'")
            with self._stats_lock:
                self.stats['failed_requests'] += 1
            return None
    
    def start_processing(self):
        """Start the TTS processing thread"""
        if self.is_processing:
            logger.warning("TTS processing already started")
            return
        
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self._process_requests, daemon=True)
        self.processing_thread.start()
        logger.info("Started TTS processing thread")
    
    def stop_processing(self):
        """Stop the TTS processing thread"""
        self.is_processing = False
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=2.0)
        
        logger.info("Stopped TTS processing thread")
    
    def _process_requests(self):
        """Main processing thread - handles TTS requests sequentially"""
        while self.is_processing:
            try:
                # Get next request from queue (this blocks until one is available)
                request = self.tts_queue.get(timeout=1.0)
                
                with self._processing_lock:
                    self.current_request = request
                    self.is_playing = True
                
                logger.info(f"Processing TTS request: '{request.text[:50]}...'")
                
                try:
                    # Generate TTS audio
                    request.status = TTSStatus.GENERATING
                    audio_file = self._generate_tts(request)
                    
                    if audio_file:
                        request.audio_file = audio_file
                        request.status = TTSStatus.PLAYING
                        
                        # Play audio and wait for completion
                        self._play_audio(request)
                        
                        request.status = TTSStatus.COMPLETED
                        logger.info(f"TTS completed: '{request.text[:50]}...'")
                        
                        # Update statistics
                        with self._stats_lock:
                            self.stats['completed_requests'] += 1
                            self.stats['last_processed'] = datetime.utcnow().isoformat()
                    else:
                        raise Exception("TTS generation failed")
                        
                except Exception as e:
                    logger.error(f"TTS failed for '{request.text[:50]}...': {e}")
                    request.status = TTSStatus.FAILED
                    request.retry_count += 1
                    
                    if request.retry_count < request.max_retries:
                        logger.info(f"Retrying TTS (attempt {request.retry_count + 1})")
                        # Put back in queue for retry
                        self.tts_queue.put(request, timeout=1.0)
                    else:
                        with self._stats_lock:
                            self.stats['failed_requests'] += 1
                
                finally:
                    with self._processing_lock:
                        self.current_request = None
                        self.is_playing = False
                    
                    # Mark task as done
                    self.tts_queue.task_done()
                    
                    # Update queue size
                    with self._stats_lock:
                        self.stats['queue_size'] = self.tts_queue.qsize()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in TTS processing: {e}")
                time.sleep(1.0)
    
    def _generate_tts(self, request: TTSRequest) -> Optional[str]:
        """Generate TTS audio file"""
        if not self.tts_callback:
            logger.error("No TTS callback set")
            return None
        
        try:
            # Call TTS service to generate audio
            audio_file = self.tts_callback(
                text=request.text,
                language_code=request.language_code
            )
            
            if audio_file and os.path.exists(audio_file):
                logger.info(f"Generated TTS audio: {audio_file}")
                return audio_file
            else:
                logger.error(f"TTS callback returned invalid file: {audio_file}")
                return None
                
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None
    
    def _play_audio(self, request: TTSRequest):
        """Play audio and wait for completion"""
        if not self.audio_callback:
            logger.error("No audio callback set")
            return
        
        try:
            # Call audio service to play the audio
            self.audio_callback(
                audio_file=request.audio_file,
                speaker1_config=request.speaker1_config,
                speaker2_config=request.speaker2_config
            )
            
            # Wait for audio to finish playing
            self._wait_for_audio_completion(request.audio_file)
            
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
            raise
    
    def _wait_for_audio_completion(self, audio_file: str):
        """Wait for audio file to finish playing"""
        try:
            # Get audio duration using ffprobe
            duration_cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration',
                '-of', 'csv=p=0', audio_file
            ]
            
            result = subprocess.run(duration_cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                logger.info(f"Audio duration: {duration:.2f} seconds")
                
                # Wait for the duration plus a small buffer
                time.sleep(duration + 0.5)
            else:
                # Fallback: wait a reasonable amount of time
                logger.warning("Could not determine audio duration, waiting 3 seconds")
                time.sleep(3.0)
                
        except Exception as e:
            logger.warning(f"Error determining audio duration: {e}, waiting 3 seconds")
            time.sleep(3.0)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get TTS queue statistics"""
        with self._stats_lock:
            stats = self.stats.copy()
            stats['queue_size'] = self.tts_queue.qsize()
            stats['currently_playing'] = self.is_playing
            stats['current_request'] = {
                'id': self.current_request.id if self.current_request else None,
                'text': self.current_request.text[:50] + '...' if self.current_request else None,
                'status': self.current_request.status.value if self.current_request else None
            }
        
        return stats
    
    def clear_queue(self):
        """Clear all queued requests"""
        with self._processing_lock:
            # Clear the queue
            while not self.tts_queue.empty():
                try:
                    self.tts_queue.get_nowait()
                    self.tts_queue.task_done()
                except queue.Empty:
                    break
            
            with self._stats_lock:
                self.stats['queue_size'] = 0
        
        logger.info("TTS queue cleared")
    
    def is_busy(self) -> bool:
        """Check if TTS is currently processing or playing"""
        return self.is_playing or not self.tts_queue.empty()


# Global instance
_tts_queue = None

def get_tts_queue() -> TTSQueue:
    """Get the global TTS queue instance"""
    global _tts_queue
    if _tts_queue is None:
        _tts_queue = TTSQueue()
    return _tts_queue

def initialize_tts_queue() -> bool:
    """Initialize the TTS queue with callbacks"""
    try:
        queue = get_tts_queue()
        
        # Import services here to avoid circular imports
        from service.tts import get_tts_service
        from service.output_audio import get_audio_service
        
        # Set up callbacks
        def tts_callback(text, language_code):
            tts_service = get_tts_service()
            if tts_service.is_initialized:
                tts_service.set_language(language_code)
                return tts_service.text_to_speech(text)
            return None
        
        def audio_callback(audio_file, speaker1_config, speaker2_config):
            audio_service = get_audio_service()
            if audio_service.speaker1_assignment and audio_service.speaker2_assignment:
                # Convert MP3 to WAV if needed
                wav_file = audio_file
                if audio_file.endswith('.mp3'):
                    wav_file = audio_file.replace('.mp3', '.wav')
                    try:
                        subprocess.run([
                            'ffmpeg', '-i', audio_file, '-acodec', 'pcm_s16le', 
                            '-ar', '44100', '-ac', '2', '-y', wav_file
                        ], check=True, capture_output=True)
                    except subprocess.CalledProcessError:
                        wav_file = audio_file  # Use original if conversion fails
                
                # Start dual playback
                audio_service._start_dual_playback(wav_file, wav_file)
        
        queue.set_callbacks(tts_callback, audio_callback)
        queue.start_processing()
        
        logger.info("TTS queue initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize TTS queue: {e}")
        return False
