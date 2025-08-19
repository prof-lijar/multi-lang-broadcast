import whisper
import warnings
import pyaudio
import wave
import threading
import time
import numpy as np
import tempfile
import os

# Suppress the FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

class StreamTranscriber:
    def __init__(self, model_name="base", language="en"):
        self.model = whisper.load_model(model_name)
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.audio_frames = []
        self.language = language
        
        # Audio settings
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 2048  # Larger chunk size to reduce buffer pressure
        self.record_seconds = 2  # Shorter chunks for more responsive transcription
        
    def start_streaming(self):
        """Start real-time streaming transcription"""
        print("🎤 Starting real-time transcription...")
        print(f"🌍 Selected language: {self.language}")
        print("Speak into your microphone. Press Ctrl+C to stop.")
        print("-" * 50)
        
        self.is_recording = True
        
        # Start recording in a separate thread
        recording_thread = threading.Thread(target=self._record_audio)
        recording_thread.start()
        
        try:
            while self.is_recording:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping transcription...")
            self.is_recording = False
            recording_thread.join()
        
        self.cleanup()
    
    def _record_audio(self):
        """Record audio in chunks and transcribe"""
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=None
        )
        
        print("🎵 Listening...")
        
        while self.is_recording:
            frames = []
            
            # Record for specified duration
            for _ in range(0, int(self.rate / self.chunk * self.record_seconds)):
                if not self.is_recording:
                    break
                try:
                    data = stream.read(self.chunk, exception_on_overflow=False)
                    frames.append(data)
                except OSError as e:
                    if "Input overflowed" in str(e):
                        # Skip this chunk if buffer overflowed
                        continue
                    else:
                        raise e
            
            if frames:
                # Transcribe the audio chunk
                self._transcribe_chunk(frames)
        
        stream.stop_stream()
        stream.close()
    
    def _transcribe_chunk(self, frames):
        """Transcribe a chunk of audio"""
        try:
            # Save audio chunk to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                wf = wave.open(temp_file.name, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                # Transcribe using Whisper with selected language
                result = self.model.transcribe(temp_file.name, language=self.language)
                text = result["text"].strip()
                
                # Clean up temporary file
                os.unlink(temp_file.name)
                
                # Print transcription if there's actual content
                if text:
                    print(f"📝 {text}")
                    
        except Exception as e:
            print(f"❌ Transcription error: {e}")
    
    def cleanup(self):
        """Clean up audio resources"""
        self.audio.terminate()
        print("✅ Transcription stopped.")

def select_language():
    """Display language selection menu and return selected language code"""
    languages = {
        "1": ("en", "English"),
        "2": ("ko", "Korean"),
        "3": ("ja", "Japanese"),
        "4": ("th", "Thai")
    }
    
    print("🌍 Select a language for transcription:")
    print("1. English")
    print("2. Korean")
    print("3. Japanese")
    print("4. Thai")
    print("-" * 30)
    
    while True:
        choice = input("Enter your choice (1-4): ").strip()
        if choice in languages:
            language_code, language_name = languages[choice]
            print(f"✅ Selected: {language_name}")
            return language_code
        else:
            print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")

def main():
    print("🎤 Real-time Whisper Transcription")
    print("=" * 40)
    
    # Select language
    selected_language = select_language()
    
    # Create transcriber instance with selected language
    transcriber = StreamTranscriber(model_name="base", language=selected_language)
    
    try:
        transcriber.start_streaming()
    except Exception as e:
        print(f"❌ Error: {e}")
        transcriber.cleanup()

if __name__ == "__main__":
    main()
