import whisper
import warnings
import pyaudio
import wave
import threading
import time
import numpy as np
import tempfile
import os
from googletrans import Translator
import json

# Suppress the FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

class LiveTranslator:
    def __init__(self, source_lang="en", target_lang="ko", model_name="base"):
        self.model = whisper.load_model(model_name)
        self.translator = Translator()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        self.audio_frames = []
        
        # Audio settings
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 2048
        self.record_seconds = 2
        
        # Translation cache to avoid re-translating the same text
        self.translation_cache = {}
        
    def start_live_translation(self):
        """Start real-time transcription and translation"""
        print(f"🎤 Starting live translation: {self.source_lang.upper()} → {self.target_lang.upper()}")
        print("Speak into your microphone. Press Ctrl+C to stop.")
        print("-" * 60)
        
        self.is_recording = True
        
        # Start recording in a separate thread
        recording_thread = threading.Thread(target=self._record_audio)
        recording_thread.start()
        
        try:
            while self.is_recording:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping live translation...")
            self.is_recording = False
            recording_thread.join()
        
        self.cleanup()
    
    def _record_audio(self):
        """Record audio in chunks and transcribe/translate"""
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
                        continue
                    else:
                        raise e
            
            if frames:
                # Transcribe and translate the audio chunk
                self._process_chunk(frames)
        
        stream.stop_stream()
        stream.close()
    
    def _process_chunk(self, frames):
        """Transcribe and translate a chunk of audio"""
        try:
            # Save audio chunk to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                wf = wave.open(temp_file.name, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
                wf.close()
                
                # Transcribe using Whisper
                result = self.model.transcribe(temp_file.name, language=self.source_lang)
                original_text = result["text"].strip()
                
                # Clean up temporary file
                os.unlink(temp_file.name)
                
                # Process if there's actual content
                if original_text:
                    self._translate_and_display(original_text)
                    
        except Exception as e:
            print(f"❌ Processing error: {e}")
    
    def _translate_and_display(self, original_text):
        """Translate text and display both original and translated versions"""
        try:
            # Check cache first
            if original_text in self.translation_cache:
                translated_text = self.translation_cache[original_text]
            else:
                # Translate the text
                translation = self.translator.translate(
                    original_text, 
                    src=self.source_lang, 
                    dest=self.target_lang
                )
                translated_text = translation.text
                
                # Cache the translation
                self.translation_cache[original_text] = translated_text
            
            # Display results with appropriate flags
            if self.source_lang == "en" and self.target_lang == "ko":
                print(f"🇺🇸 {original_text}")
                print(f"🇰🇷 {translated_text}")
            elif self.source_lang == "ko" and self.target_lang == "en":
                print(f"🇰🇷 {original_text}")
                print(f"🇺🇸 {translated_text}")
            else:
                # Generic display for other language pairs
                print(f"🔤 {original_text}")
                print(f"🌍 {translated_text}")
            print("-" * 40)
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            print(f"🇺🇸 {original_text}")
            print("-" * 40)
    
    def cleanup(self):
        """Clean up audio resources"""
        self.audio.terminate()
        print("✅ Live translation stopped.")

def main():
    print("🌍 Live Translation with Whisper")
    print("=" * 50)
    
    # Language options
    print("Available language pairs:")
    print("1. English → Korean (en → ko)")
    print("2. Korean → English (ko → en)")
    print("3. English → Spanish (en → es)")
    print("4. English → French (en → fr)")
    print("5. English → German (en → de)")
    print("6. English → Japanese (en → ja)")
    print("7. Custom language pair")
    
    choice = input("\nSelect option (1-7) or press Enter for English→Korean: ").strip()
    
    if choice == "1" or choice == "":
        source_lang, target_lang = "en", "ko"
    elif choice == "2":
        source_lang, target_lang = "ko", "en"
    elif choice == "3":
        source_lang, target_lang = "en", "es"
    elif choice == "4":
        source_lang, target_lang = "en", "fr"
    elif choice == "5":
        source_lang, target_lang = "en", "de"
    elif choice == "6":
        source_lang, target_lang = "en", "ja"
    elif choice == "7":
        source_lang = input("Enter source language code (e.g., 'en'): ").strip()
        target_lang = input("Enter target language code (e.g., 'ko'): ").strip()
    else:
        source_lang, target_lang = "en", "ko"
    
    # Create translator instance
    translator = LiveTranslator(
        source_lang=source_lang, 
        target_lang=target_lang, 
        model_name="base"
    )
    
    try:
        translator.start_live_translation()
    except Exception as e:
        print(f"❌ Error: {e}")
        translator.cleanup()

if __name__ == "__main__":
    main()
