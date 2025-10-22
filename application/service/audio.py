"""
Audio Recording Service
Simple and performant audio recording with transcription capabilities
"""

import os
import time
import threading
import queue
import wave
import tempfile
from typing import Optional, Dict, Any
from datetime import datetime
import pyaudio
import numpy as np


class AudioRecordingService:
    """Simple and performant audio recording service."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 chunk_size: int = 1024,
                 format: int = pyaudio.paInt16):
        """
        Initialize audio recording service.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels
            chunk_size: Audio chunk size for recording
            format: Audio format (paInt16 for 16-bit)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = format
        
        # Recording state
        self.is_recording = False
        self.audio_data = []
        self.recording_start_time = None
        
        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        # Threading for recording
        self.recording_thread = None
        self.recording_queue = queue.Queue()
        
        # Service status
        self.is_initialized = True
        self.error_count = 0
        self.last_error = None
    
    def start_recording(self) -> bool:
        """Start audio recording."""
        if self.is_recording:
            return False
        
        try:
            # Initialize audio stream
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size,
                stream_callback=self._audio_callback
            )
            
            # Start recording
            self.is_recording = True
            self.audio_data = []
            self.recording_start_time = time.time()
            
            # Start recording thread
            self.recording_thread = threading.Thread(target=self._recording_loop, daemon=True)
            self.recording_thread.start()
            
            print(f"🎤 Recording started at {self.sample_rate}Hz")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start recording: {e}")
            self.error_count += 1
            self.last_error = str(e)
            return False
    
    def stop_recording(self) -> Optional[bytes]:
        """Stop audio recording and return audio data."""
        if not self.is_recording:
            return None
        
        try:
            # Stop recording
            self.is_recording = False
            
            # Stop and close stream
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Wait for recording thread to finish
            if self.recording_thread and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=1.0)
            
            # Convert audio data to bytes
            if self.audio_data:
                # Convert list of numpy arrays to bytes
                audio_bytes = b''.join(self.audio_data)
                duration = time.time() - self.recording_start_time if self.recording_start_time else 0
                print(f"🎤 Recording stopped. Duration: {duration:.2f}s, Size: {len(audio_bytes)} bytes")
                return audio_bytes
            else:
                print("⚠️ No audio data recorded")
                return None
                
        except Exception as e:
            print(f"❌ Failed to stop recording: {e}")
            self.error_count += 1
            self.last_error = str(e)
            return None
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio callback for recording."""
        if self.is_recording:
            try:
                # Put audio data in queue for processing
                self.recording_queue.put_nowait(in_data)
            except queue.Full:
                # If queue is full, skip this chunk
                pass
        return (None, pyaudio.paContinue)
    
    def _recording_loop(self):
        """Recording loop that processes audio data."""
        chunk_count = 0
        while self.is_recording:
            try:
                # Get audio chunk with timeout
                chunk = self.recording_queue.get(timeout=0.1)
                if chunk:
                    self.audio_data.append(chunk)
                    chunk_count += 1
                    
                    # Debug: print every 50 chunks to monitor recording
                    if chunk_count % 50 == 0:
                        print(f"🎤 Recording: {chunk_count} chunks, {len(self.audio_data)} total chunks")
                        
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Recording loop error: {e}")
                break
        
        print(f"🎤 Recording loop finished: {chunk_count} chunks processed")
    
    def get_recording_status(self) -> Dict[str, Any]:
        """Get current recording status."""
        duration = 0
        if self.recording_start_time and self.is_recording:
            duration = time.time() - self.recording_start_time
        
        return {
            "is_recording": self.is_recording,
            "duration_seconds": duration,
            "audio_data_size": len(self.audio_data),
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "error_count": self.error_count,
            "last_error": self.last_error
        }
    
    def cleanup(self):
        """Cleanup audio resources."""
        if self.is_recording:
            self.stop_recording()
        
        if self.audio:
            self.audio.terminate()
        
        print("✅ Audio recording service cleaned up")


# Global service instance
_audio_recording_service: Optional[AudioRecordingService] = None


def get_audio_recording_service() -> AudioRecordingService:
    """Get the global audio recording service instance."""
    global _audio_recording_service
    if _audio_recording_service is None:
        raise Exception("Audio recording service not initialized. Call initialize_audio_recording_service() first.")
    return _audio_recording_service


def initialize_audio_recording_service(
    sample_rate: int = 16000,
    channels: int = 1,
    chunk_size: int = 1024
) -> bool:
    """Initialize the global audio recording service."""
    global _audio_recording_service
    try:
        _audio_recording_service = AudioRecordingService(
            sample_rate=sample_rate,
            channels=channels,
            chunk_size=chunk_size
        )
        print("✅ Audio recording service initialized")
        return True
    except Exception as e:
        print(f"❌ Failed to initialize audio recording service: {e}")
        return False
