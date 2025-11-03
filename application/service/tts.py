"""
Text-to-Speech Service using Google TTS
Handles audio generation for translated texts
"""

import os
import tempfile
import threading
import time
from typing import Dict, Any, Optional, List
from gtts import gTTS
import pygame
import soundfile as sf
import numpy as np
from datetime import datetime
import uuid


class TTSService:
    """Text-to-Speech service using Google TTS"""
    
    def __init__(self):
        self.is_initialized = False
        self.audio_cache = {}  # Cache for generated audio files
        self.active_playbacks = {}  # Track active playback sessions
        self.cleanup_thread = None
        self._initialize_pygame()
        
    def _initialize_pygame(self):
        """Initialize pygame mixer for audio playback"""
        try:
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            self.is_initialized = True
            print("✅ TTS Service initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize TTS service: {e}")
            self.is_initialized = False
    
    def generate_audio(self, text: str, language: str = "en", slow: bool = False) -> Dict[str, Any]:
        """Generate audio from text using Google TTS"""
        try:
            if not self.is_initialized:
                return {
                    "success": False,
                    "error": "TTS service not initialized"
                }
            
            # Create cache key
            cache_key = f"{text}_{language}_{slow}"
            
            # Check cache first
            if cache_key in self.audio_cache:
                cached_file = self.audio_cache[cache_key]
                if os.path.exists(cached_file):
                    return {
                        "success": True,
                        "audio_file": cached_file,
                        "cached": True
                    }
            
            # Generate new audio
            tts = gTTS(text=text, lang=language, slow=slow)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                tts.save(tmp_file.name)
                audio_file = tmp_file.name
            
            # Cache the file
            self.audio_cache[cache_key] = audio_file
            
            return {
                "success": True,
                "audio_file": audio_file,
                "cached": False,
                "text": text,
                "language": language
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate audio: {str(e)}"
            }
    
    def play_audio(self, audio_file: str, device_id: Optional[int] = None) -> Dict[str, Any]:
        """Play audio file"""
        try:
            if not os.path.exists(audio_file):
                return {
                    "success": False,
                    "error": "Audio file not found"
                }
            
            # Generate playback ID
            playback_id = str(uuid.uuid4())
            
            # Start playback in separate thread
            playback_thread = threading.Thread(
                target=self._play_audio_thread,
                args=(audio_file, playback_id, device_id)
            )
            playback_thread.daemon = True
            playback_thread.start()
            
            # Store playback info
            self.active_playbacks[playback_id] = {
                "audio_file": audio_file,
                "start_time": time.time(),
                "device_id": device_id,
                "status": "playing"
            }
            
            print(f"🎵 TTS playback started on device {device_id}: {audio_file}")
            
            return {
                "success": True,
                "playback_id": playback_id,
                "message": "Audio playback started"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to play audio: {str(e)}"
            }
    
    def _play_audio_thread(self, audio_file: str, playback_id: str, device_id: Optional[int] = None):
        """Play audio in separate thread"""
        try:
            import sounddevice as sd
            import soundfile as sf
            
            # Load audio file
            audio_data, sample_rate = sf.read(audio_file)
            
            # Ensure stereo format
            if len(audio_data.shape) == 1:
                audio_data = np.column_stack((audio_data, audio_data))
            elif audio_data.shape[1] == 1:
                audio_data = np.repeat(audio_data, 2, axis=1)
            
            # Play on specific device if provided
            if device_id is not None:
                print(f"🔊 TTS playing on device {device_id}")
                sd.play(audio_data, samplerate=sample_rate, device=device_id)
                sd.wait()
            else:
                # Use default device
                print(f"🔊 TTS playing on default device")
                sd.play(audio_data, samplerate=sample_rate)
                sd.wait()
            
            # Update status
            if playback_id in self.active_playbacks:
                self.active_playbacks[playback_id]["status"] = "completed"
                self.active_playbacks[playback_id]["end_time"] = time.time()
            
        except Exception as e:
            print(f"❌ TTS playback error: {e}")
            if playback_id in self.active_playbacks:
                self.active_playbacks[playback_id]["status"] = "error"
                self.active_playbacks[playback_id]["error"] = str(e)
    
    def stop_playback(self, playback_id: Optional[str] = None) -> Dict[str, Any]:
        """Stop audio playback"""
        try:
            if playback_id:
                # Stop specific playback
                if playback_id in self.active_playbacks:
                    pygame.mixer.music.stop()
                    self.active_playbacks[playback_id]["status"] = "stopped"
                    return {
                        "success": True,
                        "message": f"Playback {playback_id} stopped"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Playback not found"
                    }
            else:
                # Stop all playback
                pygame.mixer.music.stop()
                for pid in self.active_playbacks:
                    self.active_playbacks[pid]["status"] = "stopped"
                
                return {
                    "success": True,
                    "message": "All playback stopped"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to stop playback: {str(e)}"
            }
    
    def get_playback_status(self) -> Dict[str, Any]:
        """Get current playback status"""
        try:
            current_time = time.time()
            active_count = 0
            completed_count = 0
            
            for playback_id, info in self.active_playbacks.items():
                if info["status"] == "playing":
                    active_count += 1
                elif info["status"] == "completed":
                    completed_count += 1
                
                # Clean up old completed playbacks (older than 5 minutes)
                if (info["status"] in ["completed", "stopped", "error"] and 
                    current_time - info.get("end_time", info["start_time"]) > 300):
                    try:
                        if os.path.exists(info["audio_file"]):
                            os.unlink(info["audio_file"])
                    except:
                        pass
                    del self.active_playbacks[playback_id]
            
            return {
                "success": True,
                "active_playbacks": active_count,
                "completed_playbacks": completed_count,
                "total_playbacks": len(self.active_playbacks),
                "is_playing": pygame.mixer.music.get_busy()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get playback status: {str(e)}"
            }
    
    def generate_multiple_audio(self, translations: Dict[str, str], languages: Dict[str, str]) -> Dict[str, Any]:
        """Generate audio for multiple translations"""
        try:
            results = {}
            audio_files = {}
            
            for lang_code, text in translations.items():
                if not text or text.strip() == "":
                    continue
                
                # Get language code for TTS
                tts_lang = languages.get(lang_code, lang_code)
                
                # Generate audio
                audio_result = self.generate_audio(text, tts_lang)
                
                if audio_result["success"]:
                    results[lang_code] = {
                        "success": True,
                        "audio_file": audio_result["audio_file"],
                        "text": text,
                        "language": tts_lang
                    }
                    audio_files[lang_code] = audio_result["audio_file"]
                else:
                    results[lang_code] = {
                        "success": False,
                        "error": audio_result["error"]
                    }
            
            return {
                "success": True,
                "results": results,
                "audio_files": audio_files
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to generate multiple audio: {str(e)}"
            }
    
    def cleanup_cache(self):
        """Clean up old cached audio files"""
        try:
            current_time = time.time()
            to_remove = []
            
            for cache_key, file_path in self.audio_cache.items():
                if os.path.exists(file_path):
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > 3600:  # Remove files older than 1 hour
                        to_remove.append(cache_key)
                        try:
                            os.unlink(file_path)
                        except:
                            pass
                else:
                    to_remove.append(cache_key)
            
            for key in to_remove:
                del self.audio_cache[key]
                
        except Exception as e:
            print(f"Error cleaning up TTS cache: {e}")


# Global TTS service instance
_tts_service = None

def get_tts_service() -> TTSService:
    """Get global TTS service instance"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

def initialize_tts_service() -> bool:
    """Initialize TTS service"""
    try:
        service = get_tts_service()
        return service.is_initialized
    except Exception as e:
        print(f"Failed to initialize TTS service: {e}")
        return False