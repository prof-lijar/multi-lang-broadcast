"""
Speech-to-Text Service using sounddevice for audio recording
"""

import os
import queue
import threading
from typing import Optional, Dict, Any
from datetime import datetime
import numpy as np
import sounddevice as sd

# Google Cloud Speech-to-Text
from google.cloud import speech
from google.oauth2 import service_account


class STTService:
    """Audio recording and transcription service using sounddevice and Google Cloud Speech-to-Text."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 language_code: str = "en-US",
                 credentials_path: Optional[str] = None):
        """
        Initialize the audio recording and transcription service.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels (1 for mono, 2 for stereo)
            language_code: Language code for speech recognition (default: "en-US")
            credentials_path: Path to Google Cloud credentials JSON file
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.language_code = language_code
        
        # Initialize Google Speech client
        self._init_speech_client(credentials_path)
        
        # Recording state
        self.is_recording = False
        self.stream = None
        self.recorded_audio = []
        self.recording_thread = None
        self._recording_lock = threading.Lock()
        
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
            
            # Check for credentials.json in application folder
            app_credentials = os.path.join(os.path.dirname(os.path.dirname(__file__)), "credentials.json")
            if os.path.exists(app_credentials):
                possible_paths.append(app_credentials)
            
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
            # Don't raise - allow service to work for recording even if transcription fails
            self.speech_client = None
    
    def start_record(self):
        """Start recording audio."""
        with self._recording_lock:
            if self.is_recording:
                print("⚠️ Recording is already in progress")
                return False
            
            try:
                self.recorded_audio = []
                self.is_recording = True
                
                # Start recording stream
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype='int16',
                    callback=self._audio_callback
                )
                
                self.stream.start()
                print(f"✅ Started recording audio at {self.sample_rate} Hz, {self.channels} channel(s)")
                return True
                    
            except Exception as e:
                print(f"❌ Failed to start recording: {e}")
                self.is_recording = False
                return False
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Callback function for audio stream."""
        if status:
            print(f"⚠️ Audio callback status: {status}")
        
        if self.is_recording:
            # Convert to int16 format and store
            audio_chunk = indata.copy()
            self.recorded_audio.append(audio_chunk)
    
    def end_record(self) -> Optional[np.ndarray]:
        """
        Stop recording audio and return the recorded audio data.
        
        Returns:
            numpy array of recorded audio data, or None if recording was not active
        """
        with self._recording_lock:
            if not self.is_recording:
                print("⚠️ No recording is currently in progress")
                return None
            
            try:
                # Stop the stream
                if self.stream is not None:
                    self.stream.stop()
                    self.stream.close()
                    self.stream = None
                
                self.is_recording = False
                
                # Concatenate all audio chunks
                if self.recorded_audio:
                    audio_data = np.concatenate(self.recorded_audio, axis=0)
                    print(f"✅ Stopped recording. Captured {len(audio_data)} samples ({len(audio_data) / self.sample_rate:.2f} seconds)")
                    return audio_data
                else:
                    print("⚠️ No audio data was recorded")
                    return None
                        
            except Exception as e:
                print(f"❌ Failed to stop recording: {e}")
                self.is_recording = False
                return None
    
    def transcribe(self, audio_data: np.ndarray, language_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe recorded audio to text using Google Cloud Speech-to-Text.
        
        Args:
            audio_data: Numpy array of audio data (int16 format)
            language_code: Language code for transcription (optional, uses default if not provided)
        
        Returns:
            Dictionary containing:
            - status: "success" or "error"
            - transcript: Transcribed text (if successful)
            - confidence: Confidence score (if available)
            - error: Error message (if failed)
            - timestamp: ISO timestamp
        """
        if not self.is_initialized or self.speech_client is None:
            error_msg = "Google Speech-to-Text client not initialized"
            self.error_count += 1
            self.last_error = error_msg
            return {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        if audio_data is None or len(audio_data) == 0:
            error_msg = "No audio data provided for transcription"
            self.error_count += 1
            self.last_error = error_msg
            return {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        try:
            # Convert numpy array to int16 if needed
            if audio_data.dtype != np.int16:
                # Normalize to int16 range if float
                if audio_data.dtype == np.float32 or audio_data.dtype == np.float64:
                    audio_data = (audio_data * 32767).astype(np.int16)
                else:
                    audio_data = audio_data.astype(np.int16)
            
            # Flatten if multi-channel (take first channel for mono-like conversion)
            if len(audio_data.shape) > 1:
                audio_data = audio_data[:, 0] if audio_data.shape[1] > 0 else audio_data.flatten()
            
            # Convert numpy array to bytes
            audio_bytes = audio_data.tobytes()
            
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate,
                language_code=language_code or self.language_code,
                enable_automatic_punctuation=True,
                model="latest_long",
                use_enhanced=True,
            )
            
            audio = speech.RecognitionAudio(content=audio_bytes)
            
            # Perform the recognition
            response = self.speech_client.recognize(config=config, audio=audio)
            
            # Process results
            if response.results:
                result = response.results[0]
                if result.alternatives:
                    transcript = result.alternatives[0].transcript
                    confidence = result.alternatives[0].confidence
                    
                    print(f"✅ Transcription successful: '{transcript}' (confidence: {confidence})")
                    return {
                        "status": "success",
                        "transcript": transcript.strip(),
                        "confidence": confidence if confidence else 0.0,
                        "timestamp": datetime.utcnow().isoformat(),
                        "language": language_code or self.language_code
                    }
            
            # No results found
            return {
                "status": "success",
                "transcript": "",
                "confidence": 0.0,
                "timestamp": datetime.utcnow().isoformat(),
                "language": language_code or self.language_code
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Transcription error: {error_msg}")
            self.error_count += 1
            self.last_error = error_msg
            return {
                "status": "error",
                "error": error_msg,
                "timestamp": datetime.utcnow().isoformat()
            }
        

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
    channels: int = 1,
    language_code: str = "en-US",
    credentials_path: Optional[str] = None
) -> bool:
    """Initialize the global STT service."""
    global _stt_service
    try:
        _stt_service = STTService(
            sample_rate=sample_rate,
            channels=channels,
            language_code=language_code,
            credentials_path=credentials_path
        )
        return True
    except Exception as e:
        print(f"Failed to initialize STT service: {e}")
        return False
