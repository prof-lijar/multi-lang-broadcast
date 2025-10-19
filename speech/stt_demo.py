#!/usr/bin/env python3
"""
High-Performance Speech-to-Text using Google Speech-to-Text API
Features:
- Real-time microphone streaming
- Minimal latency with streaming recognition
- Live terminal output
- Optimized for performance
"""

import os
import sys
import time
import threading
import queue
from typing import Generator, Optional
import json

# Google Cloud Speech-to-Text
from google.cloud import speech
from google.oauth2 import service_account

# Audio processing
import pyaudio
import wave

# Performance monitoring
import psutil


class SpeechToTextStreamer:
    """High-performance speech-to-text streaming with minimal latency."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 chunk_size: int = 1024,
                 language_code: str = "en-US",
                 credentials_path: Optional[str] = None):
        """
        Initialize the speech-to-text streamer.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            chunk_size: Audio chunk size for streaming
            language_code: Language for speech recognition
            credentials_path: Path to Google Cloud credentials JSON
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.language_code = language_code
        
        # Audio configuration
        self.audio_format = pyaudio.paInt16
        self.channels = 1  # Mono audio for better performance
        
        # Initialize Google Speech client
        self._init_speech_client(credentials_path)
        
        # Audio streaming
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_streaming = False
        
        # Threading for performance
        self.audio_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        
        # Performance metrics
        self.start_time = None
        self.processed_chunks = 0
        
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
            print("\nPlease ensure you have valid Google Cloud credentials:")
            print("1. Place 'credentials.json' in the root folder, OR")
            print("2. Set GOOGLE_APPLICATION_CREDENTIALS environment variable, OR")
            print("3. Use 'gcloud auth application-default login'")
            sys.exit(1)
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio callback for real-time streaming."""
        if self.is_streaming:
            try:
                self.audio_queue.put_nowait(in_data)
            except queue.Full:
                # Drop oldest audio if queue is full to maintain low latency
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(in_data)
                except queue.Empty:
                    pass
        return (None, pyaudio.paContinue)
    
    def _process_audio_stream(self):
        """Process audio stream in separate thread for better performance."""
        def audio_generator() -> Generator[bytes, None, None]:
            """Generate audio chunks for streaming recognition."""
            while self.is_streaming:
                try:
                    # Get audio chunk with timeout to prevent blocking
                    chunk = self.audio_queue.get(timeout=0.1)
                    yield chunk
                    self.processed_chunks += 1
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Audio processing error: {e}")
                    break
        
        # Configure streaming recognition
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.sample_rate,
            language_code=self.language_code,
            enable_automatic_punctuation=True,
            model="latest_long",  # Use latest model for better accuracy
            use_enhanced=True,    # Enhanced model for better performance
        )
        
        streaming_config = speech.StreamingRecognitionConfig(
            config=config,
            interim_results=True,  # Get interim results for lower latency
            single_utterance=False,
        )
        
        try:
            # Start streaming recognition
            audio_requests = (
                speech.StreamingRecognizeRequest(audio_content=chunk)
                for chunk in audio_generator()
            )
            
            responses = self.speech_client.streaming_recognize(
                streaming_config, audio_requests
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
                
                # Output results based on finality
                if result.is_final:
                    self.result_queue.put(("FINAL", transcript, confidence))
                else:
                    self.result_queue.put(("INTERIM", transcript, confidence))
                    
        except Exception as e:
            print(f"Streaming recognition error: {e}")
    
    def _display_results(self):
        """Display results in terminal with performance metrics."""
        last_interim = ""
        
        while self.is_streaming:
            try:
                result_type, transcript, confidence = self.result_queue.get(timeout=0.1)
                
                if result_type == "FINAL":
                    # Clear interim text and show final result
                    if last_interim:
                        print("\r" + " " * len(last_interim) + "\r", end="", flush=True)
                        last_interim = ""
                    
                    # Display final result with confidence
                    confidence_pct = confidence * 100 if confidence else 0
                    print(f"🎯 {transcript} ({confidence_pct:.1f}%)")
                    
                elif result_type == "INTERIM":
                    # Show interim result (overwrite previous interim)
                    if last_interim:
                        print("\r" + " " * len(last_interim) + "\r", end="", flush=True)
                    
                    print(f"⏳ {transcript}", end="", flush=True)
                    last_interim = f"⏳ {transcript}"
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Display error: {e}")
    
    def _monitor_performance(self):
        """Monitor and display performance metrics."""
        while self.is_streaming:
            time.sleep(5)  # Update every 5 seconds
            
            if self.start_time:
                elapsed = time.time() - self.start_time
                chunks_per_sec = self.processed_chunks / elapsed if elapsed > 0 else 0
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                
                print(f"\n📊 Performance: {chunks_per_sec:.1f} chunks/sec | "
                      f"CPU: {cpu_percent:.1f}% | Memory: {memory_percent:.1f}%")
    
    def start_streaming(self):
        """Start real-time speech-to-text streaming."""
        print("🚀 Starting Speech-to-Text streaming...")
        print("📢 Speak into your microphone (Ctrl+C to stop)")
        print("=" * 60)
        
        # Initialize audio stream
        self.stream = self.audio.open(
            format=self.audio_format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size,
            stream_callback=self._audio_callback,
            start=False
        )
        
        self.is_streaming = True
        self.start_time = time.time()
        self.processed_chunks = 0
        
        # Start audio stream
        self.stream.start_stream()
        
        # Start processing threads
        audio_thread = threading.Thread(target=self._process_audio_stream, daemon=True)
        display_thread = threading.Thread(target=self._display_results, daemon=True)
        monitor_thread = threading.Thread(target=self._monitor_performance, daemon=True)
        
        audio_thread.start()
        display_thread.start()
        monitor_thread.start()
        
        try:
            # Keep main thread alive
            while self.is_streaming:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Stopping speech recognition...")
            self.stop_streaming()
    
    def stop_streaming(self):
        """Stop speech-to-text streaming and cleanup resources."""
        self.is_streaming = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        
        self.audio.terminate()
        
        if self.start_time:
            total_time = time.time() - self.start_time
            print(f"📈 Total processing time: {total_time:.2f}s")
            print(f"📈 Total chunks processed: {self.processed_chunks}")
            print(f"📈 Average chunks/sec: {self.processed_chunks/total_time:.2f}")
        
        print("✅ Speech-to-text streaming stopped")


def main():
    """Main function to run the speech-to-text application."""
    print("🎤 High-Performance Speech-to-Text Streamer")
    print("=" * 50)
    
    # Language selection menu
    print("Available languages:")
    print("1. English (en-US)")
    print("2. Korean (ko-KR)")
    print("3. Chinese (zh-CN)")
    print("4. Burmese (my-MM)")
    
    choice = input("\nSelect language (1-4) or press Enter for English: ").strip()
    
    language_map = {
        "1": "en-US",
        "2": "ko-KR", 
        "3": "zh-CN",
        "4": "my-MM"
    }
    
    LANGUAGE = language_map.get(choice, "en-US")
    print(f"✓ Selected language: {LANGUAGE}")
    
    # Configuration
    SAMPLE_RATE = 16000  # Optimal for Google Speech-to-Text
    CHUNK_SIZE = 1024    # Balance between latency and performance
    
    # Check for credentials in root folder first
    root_credentials = os.path.join(os.path.dirname(__file__), "..", "credentials.json")
    credentials_path = None
    
    if os.path.exists(root_credentials):
        credentials_path = root_credentials
        print(f"✓ Found credentials.json in root folder: {root_credentials}")
    else:
        # Check environment variable
        env_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if env_credentials and os.path.exists(env_credentials):
            credentials_path = env_credentials
            print(f"✓ Using credentials from environment: {env_credentials}")
        else:
            print("⚠️  No credentials.json found in root folder or GOOGLE_APPLICATION_CREDENTIALS not set")
            print("   The program will try to use Application Default Credentials")
            print("   If that fails, please:")
            print("   1. Place 'credentials.json' in the root folder, OR")
            print("   2. Set GOOGLE_APPLICATION_CREDENTIALS environment variable")
            
            # Ask user for credentials path as fallback
            custom_path = input("Enter path to credentials JSON (or press Enter to continue): ").strip()
            if custom_path and os.path.exists(custom_path):
                credentials_path = custom_path
    
    # Initialize and start streaming
    try:
        streamer = SpeechToTextStreamer(
            sample_rate=SAMPLE_RATE,
            chunk_size=CHUNK_SIZE,
            language_code=LANGUAGE,
            credentials_path=credentials_path
        )
        
        streamer.start_streaming()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
