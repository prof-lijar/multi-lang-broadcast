"""
Speech-to-Text Service using Google Speech-to-Text API
Provides real-time speech recognition with streaming capabilities
"""

import os
import sys
import time
import threading
import queue
import asyncio
from typing import Generator, Optional, Dict, Any, List, AsyncGenerator
import json
import base64
import io
import wave
from datetime import datetime

# Google Cloud Speech-to-Text
from google.cloud import speech
from google.oauth2 import service_account

# Audio processing
import pyaudio
import numpy as np

# Performance monitoring
import psutil


class STTService:
    """High-performance speech-to-text service with streaming capabilities."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_size: int = 1024,
                 language_code: str = "en-US",
                 credentials_path: Optional[str] = None,
                 enable_monitoring: bool = True):
        """
        Initialize the speech-to-text service.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            chunk_size: Audio chunk size for streaming
            language_code: Language for speech recognition
            credentials_path: Path to Google Cloud credentials JSON
            enable_monitoring: Whether to enable performance monitoring
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.language_code = language_code
        self.enable_monitoring = enable_monitoring
        
        # Audio configuration
        self.audio_format = pyaudio.paInt16
        self.channels = 1  # Mono audio for better performance
        self.input_device_index = None  # Use default input device if None
        
        # Initialize Google Speech client
        self._init_speech_client(credentials_path)
        
        # Audio streaming
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_streaming = False
        
        # Threading for performance - increased queue sizes for better buffering
        self.audio_queue = queue.Queue(maxsize=100)  # Increased from 10 to 100
        self.result_queue = queue.Queue(maxsize=200)  # Increased from 50 to 200
        
        # Performance metrics
        self.start_time = None
        self.processed_chunks = 0
        self.total_transcripts = 0
        self.total_confidence = 0.0
        
        # Debouncing for results
        self.last_result_time = 0
        self.debounce_interval = 0.1  # 100ms debounce interval
        
        # Heartbeat mechanism to keep streaming active
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 5.0  # Send heartbeat every 5 seconds
        
        # Track last results to prevent duplicates
        self.last_final_transcript = ""
        self.last_interim_transcript = ""
        
        # Service status
        self.is_initialized = True
        self.error_count = 0
        self.last_error = None
        
    def _init_speech_client(self, credentials_path: Optional[str]):
        """Initialize Google Speech-to-Text client with credentials."""
        try:
            # Check for credentials in multiple locations
            possible_paths = []
            
            if credentials_path and os.path.exists(credentials_path):
                possible_paths.append(credentials_path)
            
            # Check for credentials.json in root folder
            root_credentials = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
            if os.path.exists(root_credentials):
                possible_paths.append(root_credentials)
            
            # Check for credentials.json in multi-lang-broadcast folder
            broadcast_credentials = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "credentials.json")
            if os.path.exists(broadcast_credentials):
                possible_paths.append(broadcast_credentials)
            
            # Check environment variable
            env_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if env_credentials and os.path.exists(env_credentials):
                possible_paths.append(env_credentials)
            
            # Use the first valid credentials file found
            if possible_paths:
                credentials_file = possible_paths[0]
                print(f"✓ Using credentials file: {credentials_file}")
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_file,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.speech_client = speech.SpeechClient(credentials=credentials)
            else:
                # Try to use default credentials (ADC - Application Default Credentials)
                print("✓ Using Application Default Credentials")
                self.speech_client = speech.SpeechClient()
            
            print("✓ Google Speech-to-Text client initialized")
            
        except Exception as e:
            print(f"✗ Failed to initialize Google Speech client: {e}")
            self.is_initialized = False
            self.last_error = str(e)
            # Don't raise - allow service instance to be created but marked as not initialized
            self.speech_client = None
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio callback for real-time streaming."""
        if self.is_streaming:
            try:
                # Try to put audio data with timeout to prevent blocking
                self.audio_queue.put_nowait(in_data)
                # Debug: print when we receive audio data
                if self.processed_chunks % 100 == 0:  # Print every 100 chunks
                    print(f"🎤 Audio callback: received {len(in_data)} bytes, chunk {self.processed_chunks}")
            except queue.Full:
                # Clear some old audio data to make room for new data
                try:
                    # Remove up to 5 old chunks to make room
                    for _ in range(min(5, self.audio_queue.qsize())):
                        self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(in_data)
                    print(f"⚠️ Audio queue full, cleared old chunks to make room")
                except queue.Empty:
                    # If queue is empty, just put the new data
                    try:
                        self.audio_queue.put_nowait(in_data)
                    except queue.Full:
                        print(f"⚠️ Audio queue still full, dropping audio chunk")
        return (None, pyaudio.paContinue)
    
    def _process_audio_stream(self, language_code: str = None):
        """Process audio stream in separate thread for better performance."""
        def audio_generator() -> Generator[bytes, None, None]:
            """Generate audio chunks for streaming recognition."""
            consecutive_empty_count = 0
            max_consecutive_empty = 100  # Allow up to 10 seconds of no audio before giving up
            
            while self.is_streaming:
                try:
                    # Get audio chunk with shorter timeout for more responsive processing
                    chunk = self.audio_queue.get(timeout=0.05)  # Reduced from 0.1 to 0.05
                    yield chunk
                    self.processed_chunks += 1
                    consecutive_empty_count = 0  # Reset counter on successful chunk
                    
                    # Debug: print when we process audio chunks
                    if self.processed_chunks % 50 == 0:  # Print every 50 chunks
                        print(f"🔄 Processing audio chunk {self.processed_chunks}, size: {len(chunk)} bytes")
                        
                except queue.Empty:
                    consecutive_empty_count += 1
                    if consecutive_empty_count > max_consecutive_empty:
                        print(f"⚠️ No audio data for {max_consecutive_empty * 0.05} seconds, checking if streaming should continue")
                        # Check if we should continue or if there's an issue
                        if not self.is_streaming:
                            break
                        consecutive_empty_count = 0  # Reset to continue checking
                    continue
                except Exception as e:
                    print(f"Audio processing error: {e}")
                    self.error_count += 1
                    self.last_error = str(e)
                    break
        
        # Configure streaming recognition with improved settings
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.sample_rate,
            language_code=language_code or self.language_code,
            enable_automatic_punctuation=True,
            model="latest_long",  # Use latest model for better accuracy
            use_enhanced=True,    # Enhanced model for better performance
            enable_word_time_offsets=True,  # Enable word-level timing
            enable_word_confidence=True,    # Enable word-level confidence
        )
        
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,  # Get interim results for lower latency
            single_utterance=False,
        )
        
        try:
            # Start streaming recognition with retry mechanism
            max_retries = 3
            retry_count = 0
            
            while retry_count < max_retries and self.is_streaming:
                try:
                    # Start streaming recognition
                    audio_requests = (
                        speech.StreamingRecognizeRequest(audio_content=chunk)
                        for chunk in audio_generator()
                    )
                    
                    responses = self.speech_client.streaming_recognize(
                        streaming_config, audio_requests
                    )
                    
                    # Process responses with improved error handling
                    for response in responses:
                        if not self.is_streaming:
                            break
                            
                        if not response.results:
                            continue
                        
                        result = response.results[0]
                        if not result.alternatives:
                            continue
                        
                        transcript = result.alternatives[0].transcript
                        confidence = result.alternatives[0].confidence
                        
                        # Clean transcript for comparison
                        clean_transcript = transcript.strip()
                        
                        # Output results based on finality
                        if result.is_final:
                            # Skip if this is the same final result we just processed
                            if clean_transcript == self.last_final_transcript or not clean_transcript:
                                continue
                            
                            try:
                                self.result_queue.put_nowait(("FINAL", clean_transcript, confidence))
                                self.last_final_transcript = clean_transcript
                                self.total_transcripts += 1
                                self.total_confidence += confidence if confidence else 0
                                print(f"📝 Final result queued: '{clean_transcript}'")
                            except queue.Full:
                                # Clear old results if queue is full to prevent memory buildup
                                try:
                                    self.result_queue.get_nowait()
                                    self.result_queue.put_nowait(("FINAL", clean_transcript, confidence))
                                    self.last_final_transcript = clean_transcript
                                    self.total_transcripts += 1
                                    self.total_confidence += confidence if confidence else 0
                                    print(f"📝 Final result queued (after clearing old): '{clean_transcript}'")
                                except queue.Empty:
                                    pass
                        else:
                            # Skip if this is the same interim result we just processed
                            if clean_transcript == self.last_interim_transcript or not clean_transcript:
                                continue
                            
                            try:
                                self.result_queue.put_nowait(("INTERIM", clean_transcript, confidence))
                                self.last_interim_transcript = clean_transcript
                                print(f"📝 Interim result queued: '{clean_transcript}'")
                            except queue.Full:
                                # For interim results, just skip if queue is full
                                print(f"⚠️ Result queue full, skipping interim result: '{clean_transcript}'")
                                pass
                    
                    # If we get here, the streaming completed successfully
                    break
                    
                except Exception as e:
                    retry_count += 1
                    print(f"Streaming recognition error (attempt {retry_count}/{max_retries}): {e}")
                    self.error_count += 1
                    self.last_error = str(e)
                    
                    if retry_count < max_retries:
                        print(f"Retrying streaming recognition in 1 second...")
                        time.sleep(1)
                    else:
                        print(f"Max retries reached, giving up on streaming recognition")
                        break
                    
        except Exception as e:
            print(f"Streaming recognition setup error: {e}")
            self.error_count += 1
            self.last_error = str(e)
    
    async def start_streaming(self, language_code: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Start real-time speech-to-text streaming and yield results."""
        if not self.is_initialized:
            raise Exception("STT service not initialized")
        
        print(f"🚀 Starting Speech-to-Text streaming for language: {language_code}")
        print(f"🎤 Audio format: {self.audio_format}, Sample rate: {self.sample_rate}, Channels: {self.channels}")
        
        # Initialize audio stream
        try:
            stream_params = {
                'format': self.audio_format,
                'channels': self.channels,
                'rate': self.sample_rate,
                'input': True,
                'frames_per_buffer': self.chunk_size,
                'stream_callback': self._audio_callback,
                'start': False
            }
            
            # Add input_device_index if specified
            if self.input_device_index is not None:
                stream_params['input_device_index'] = self.input_device_index
                print(f"✅ Using input device index: {self.input_device_index}")
            
            self.stream = self.audio.open(**stream_params)
            print("✅ Audio stream initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize audio stream: {e}")
            raise
        
        self.is_streaming = True
        self.start_time = time.time()
        self.processed_chunks = 0
        
        # Reset tracking variables
        self.last_final_transcript = ""
        self.last_interim_transcript = ""
        self.last_result_time = 0
        
        # Start audio stream
        try:
            self.stream.start_stream()
            print("✅ Audio stream started successfully")
        except Exception as e:
            print(f"❌ Failed to start audio stream: {e}")
            raise
        
        # Start processing thread
        audio_thread = threading.Thread(
            target=self._process_audio_stream, 
            args=(language_code,),
            daemon=True
        )
        audio_thread.start()
        
        try:
            # Yield results as they come in
            print("🔄 Starting main transcription loop...")
            loop_count = 0
            while self.is_streaming:
                try:
                    result_type, transcript, confidence = self.result_queue.get(timeout=0.1)
                    print(f"📝 Received result: {result_type} - '{transcript}' (confidence: {confidence})")
                    
                    # Apply debouncing to prevent rapid-fire updates
                    current_time = time.time()
                    if current_time - self.last_result_time < self.debounce_interval:
                        continue
                    
                    # Clean transcript for comparison (remove extra whitespace)
                    clean_transcript = transcript.strip()
                    
                    if result_type == "FINAL":
                        # Skip if this is the same final result we just processed
                        if clean_transcript == self.last_final_transcript or not clean_transcript:
                            print(f"⏭️ Skipping duplicate final result: '{clean_transcript}'")
                            continue
                        
                        print(f"🎯 Final transcript: '{clean_transcript}' - YIELDING TO CLIENT")
                        self.last_final_transcript = clean_transcript
                        yield {
                            "type": "final",
                            "transcript": clean_transcript,
                            "confidence": confidence,
                            "timestamp": datetime.utcnow().isoformat(),
                            "language": language_code or self.language_code
                        }
                        self.last_result_time = current_time
                        
                    elif result_type == "INTERIM":
                        # Skip only if empty, allow interim results to flow through
                        if not clean_transcript:
                            print(f"⏭️ Skipping empty interim result")
                            continue
                        
                        print(f"⏳ Interim transcript: '{clean_transcript}' - YIELDING TO CLIENT")
                        self.last_interim_transcript = clean_transcript
                        yield {
                            "type": "interim",
                            "transcript": clean_transcript,
                            "confidence": confidence,
                            "timestamp": datetime.utcnow().isoformat(),
                            "language": language_code or self.language_code
                        }
                        self.last_result_time = current_time
                        
                except queue.Empty:
                    loop_count += 1
                    current_time = time.time()
                    
                    # Send heartbeat if no results for a while
                    if current_time - self.last_heartbeat > self.heartbeat_interval:
                        print(f"💓 Sending heartbeat to keep connection alive")
                        yield {
                            "type": "heartbeat",
                            "message": "Streaming active",
                            "timestamp": datetime.utcnow().isoformat(),
                            "processed_chunks": self.processed_chunks,
                            "queue_size": self.audio_queue.qsize()
                        }
                        self.last_heartbeat = current_time
                    
                    if loop_count % 100 == 0:  # Print every 100 loops (10 seconds)
                        print(f"⏳ Waiting for audio results... (loop {loop_count})")
                    await asyncio.sleep(0.01)  # Small delay to prevent busy waiting
                    continue
                except Exception as e:
                    print(f"Display error: {e}")
                    self.error_count += 1
                    self.last_error = str(e)
                    break
                    
        finally:
            self.stop_streaming()
    
    async def process_websocket_audio(self, audio_data: bytes, language_code: str = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Process audio data received from WebSocket and yield transcription results."""
        if not self.is_initialized:
            raise Exception("STT service not initialized")
        
        try:
            # Configure streaming recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                language_code=language_code or self.language_code,
                enable_automatic_punctuation=True,
                model="latest_long",
                use_enhanced=True,
            )
            
            streaming_config = speech.StreamingRecognitionConfig(
                config=config,
                interim_results=True,
                single_utterance=False,
            )
            
            # Create audio request
            audio_request = speech.StreamingRecognizeRequest(audio_content=audio_data)
            
            # Process the audio
            responses = self.speech_client.streaming_recognize(
                streaming_config, [audio_request]
            )
            
            # Process responses
            for response in responses:
                if not response.results:
                    continue
                
                result = response.results[0]
                if not result.alternatives:
                    continue
                
                transcript = result.alternatives[0].transcript
                confidence = result.alternatives[0].confidence
                
                # Clean transcript for comparison
                clean_transcript = transcript.strip()
                
                if result.is_final:
                    if clean_transcript and clean_transcript != self.last_final_transcript:
                        yield {
                            "type": "final",
                            "transcript": clean_transcript,
                            "confidence": confidence,
                            "timestamp": datetime.utcnow().isoformat(),
                            "language": language_code or self.language_code
                        }
                        self.last_final_transcript = clean_transcript
                        self.total_transcripts += 1
                        self.total_confidence += confidence if confidence else 0
                else:
                    if clean_transcript and clean_transcript != self.last_interim_transcript:
                        yield {
                            "type": "interim",
                            "transcript": clean_transcript,
                            "confidence": confidence,
                            "timestamp": datetime.utcnow().isoformat(),
                            "language": language_code or self.language_code
                        }
                        self.last_interim_transcript = clean_transcript
                        
        except Exception as e:
            print(f"WebSocket audio processing error: {e}")
            self.error_count += 1
            self.last_error = str(e)
            yield {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def stop_streaming(self):
        """Stop speech-to-text streaming and cleanup resources."""
        self.is_streaming = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        # Don't terminate audio here as it might be used by other services
        # self.audio.terminate()
        
        print("✅ Speech-to-text streaming stopped")
    
    def restart_streaming(self):
        """Restart streaming if it gets stuck or stops working."""
        print("🔄 Restarting streaming...")
        self.stop_streaming()
        
        # Clear queues to prevent stale data
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
        while not self.result_queue.empty():
            try:
                self.result_queue.get_nowait()
            except queue.Empty:
                break
        
        # Reset tracking variables
        self.last_final_transcript = ""
        self.last_interim_transcript = ""
        self.last_result_time = 0
        self.last_heartbeat = time.time()
        
        print("✅ Streaming restarted")
    
    async def transcribe_audio_file(self, audio_data: bytes, language_code: str = None, sample_rate: int = None) -> Dict[str, Any]:
        """Transcribe audio from file data."""
        if not self.is_initialized or self.speech_client is None:
            if self.last_error:
                error_msg = f"STT service not initialized: {self.last_error}"
            else:
                error_msg = "STT service not initialized. Google Cloud credentials are required."
            raise Exception(f"{error_msg} Please check Google Cloud credentials configuration. See CREDENTIALS_SETUP.md for instructions.")
        
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Audio data is empty")
        
        try:
            # Use provided sample rate or default
            sample_rate_hertz = sample_rate or self.sample_rate
            
            # Try with ENCODING_UNSPECIFIED first (allows Google to auto-detect encoding for FLAC, LINEAR16, etc.)
            # If that fails, fall back to LINEAR16
            configs_to_try = [
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED,
                    "sample_rate_hertz": sample_rate_hertz,
                },
                {
                    "encoding": speech.RecognitionConfig.AudioEncoding.LINEAR16,
                    "sample_rate_hertz": sample_rate_hertz,
                },
            ]
            
            def _perform_recognition(config_params):
                """Helper function to perform recognition (runs in executor)"""
                config = speech.RecognitionConfig(
                    encoding=config_params["encoding"],
                    sample_rate_hertz=config_params["sample_rate_hertz"],
                    language_code=language_code or self.language_code,
                    enable_automatic_punctuation=True,
                    model="latest_long",
                    use_enhanced=True,
                )
                
                audio = speech.RecognitionAudio(content=audio_data)
                
                # Perform the recognition (blocking call)
                return self.speech_client.recognize(config=config, audio=audio)
            
            response = None
            last_error = None
            for config_params in configs_to_try:
                try:
                    # Run blocking recognition in executor to avoid blocking event loop
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, 
                        _perform_recognition, 
                        config_params
                    )
                    break  # Success, exit the retry loop
                    
                except Exception as e:
                    last_error = e
                    print(f"Recognition attempt failed with {config_params['encoding']}: {str(e)}")
                    # If this is not the last config to try, continue to next
                    if config_params != configs_to_try[-1]:
                        continue
                    # If this was the last config, re-raise the error
                    raise Exception(f"Failed with both encoding types. Last error: {str(e)}") from e
            
            if response is None:
                raise Exception("No response from Google Speech API")
            
            results = []
            for result in response.results:
                if not result.alternatives:
                    continue
                alternative = result.alternatives[0]
                results.append({
                    "transcript": alternative.transcript,
                    "confidence": alternative.confidence,
                    "language": language_code or self.language_code
                })
            
            if not results:
                raise Exception("No transcription results returned from Google Speech API")
            
            return {
                "status": "success",
                "results": results,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            import traceback
            error_traceback = traceback.format_exc()
            print(f"STT transcription error: {e}\n{error_traceback}")
            # Re-raise the exception so the endpoint can handle it properly
            raise Exception(f"Transcription failed: {str(e)}") from e
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get service statistics and performance metrics."""
        stats = {
            "is_initialized": self.is_initialized,
            "is_streaming": self.is_streaming,
            "processed_chunks": self.processed_chunks,
            "total_transcripts": self.total_transcripts,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "average_confidence": (
                self.total_confidence / self.total_transcripts 
                if self.total_transcripts > 0 else 0
            )
        }
        
        if self.start_time:
            elapsed = time.time() - self.start_time
            stats.update({
                "uptime_seconds": elapsed,
                "chunks_per_second": self.processed_chunks / elapsed if elapsed > 0 else 0
            })
        
        if self.enable_monitoring:
            stats.update({
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent
            })
        
        return stats
    
    def reset_statistics(self):
        """Reset service statistics."""
        self.processed_chunks = 0
        self.total_transcripts = 0
        self.total_confidence = 0.0
        self.error_count = 0
        self.last_error = None
        self.start_time = None
    
    def set_input_device(self, device_index: Optional[int] = None, channels: int = 1):
        """Set the input device and channel configuration."""
        self.input_device_index = device_index
        self.channels = channels
        print(f"✓ Input device set to index: {device_index}, channels: {channels}")
    
    def get_input_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices with their properties."""
        devices = []
        
        try:
            for i in range(self.audio.get_device_count()):
                device_info = self.audio.get_device_info_by_index(i)
                
                # Only include input devices (devices with input channels > 0)
                if device_info.get('maxInputChannels', 0) > 0:
                    devices.append({
                        'index': i,
                        'name': device_info.get('name', 'Unknown Device'),
                        'max_input_channels': device_info.get('maxInputChannels', 0),
                        'default_sample_rate': int(device_info.get('defaultSampleRate', 16000)),
                        'host_api': device_info.get('hostApi', 0)
                    })
            
            print(f"✓ Found {len(devices)} audio input devices")
            return devices
            
        except Exception as e:
            print(f"✗ Error getting input devices: {e}")
            return []


# Global service instance
_stt_service: Optional[STTService] = None


def get_stt_service() -> STTService:
    """Get the global STT service instance."""
    global _stt_service
    if _stt_service is None:
        raise Exception("STT service not initialized. Call initialize_stt_service() first.")
    return _stt_service


def initialize_stt_service(
    sample_rate: int = 16000,
    chunk_size: int = 1024,
    language_code: str = "en-US",
    credentials_path: Optional[str] = None,
    enable_monitoring: bool = True
) -> bool:
    """Initialize the global STT service."""
    global _stt_service
    try:
        _stt_service = STTService(
            sample_rate=sample_rate,
            chunk_size=chunk_size,
            language_code=language_code,
            credentials_path=credentials_path,
            enable_monitoring=enable_monitoring
        )
        return True
    except Exception as e:
        print(f"Failed to initialize STT service: {e}")
        return False
