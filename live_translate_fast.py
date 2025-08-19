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
import queue
from concurrent.futures import ThreadPoolExecutor
import io

# Suppress the FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

class FastLiveTranslator:
    def __init__(self, source_lang="en", target_lang="ko", model_name="tiny"):
        # Use tiny model for faster processing
        self.model = whisper.load_model(model_name)
        self.translator = Translator()
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.audio = pyaudio.PyAudio()
        self.is_recording = False
        
        # Audio settings optimized for speed
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024  # Smaller chunks for more frequent processing
        self.record_seconds = 1.5  # Shorter chunks for faster response
        
        # Queues for async processing
        self.audio_queue = queue.Queue(maxsize=10)
        self.result_queue = queue.Queue()
        
        # Translation cache
        self.translation_cache = {}
        
        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=2)
        
    def start_live_translation(self):
        """Start real-time transcription and translation"""
        print(f"🚀 Starting FAST live translation: {self.source_lang.upper()} → {self.target_lang.upper()}")
        print("Speak into your microphone. Press Ctrl+C to stop.")
        print("-" * 60)
        
        self.is_recording = True
        
        # Start multiple threads for parallel processing
        audio_thread = threading.Thread(target=self._record_audio)
        process_thread = threading.Thread(target=self._process_audio_queue)
        
        audio_thread.start()
        process_thread.start()
        
        try:
            while self.is_recording:
                # Display results from result queue
                try:
                    result = self.result_queue.get_nowait()
                    self._display_result(result)
                except queue.Empty:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping live translation...")
            self.is_recording = False
            audio_thread.join()
            process_thread.join()
        
        self.cleanup()
    
    def _record_audio(self):
        """Record audio in chunks and add to queue"""
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
                # Add to processing queue
                try:
                    self.audio_queue.put_nowait(frames)
                except queue.Full:
                    # Skip this chunk if queue is full
                    continue
        
        stream.stop_stream()
        stream.close()
    
    def _process_audio_queue(self):
        """Process audio chunks from queue"""
        while self.is_recording:
            try:
                frames = self.audio_queue.get(timeout=0.1)
                # Process in thread pool for non-blocking operation
                future = self.executor.submit(self._transcribe_and_translate, frames)
                # Add result to display queue
                self.result_queue.put(future.result())
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Processing error: {e}")
    
    def _transcribe_and_translate(self, frames):
        """Transcribe and translate audio frames"""
        try:
            # Convert audio frames to numpy array for faster processing
            audio_data = np.frombuffer(b''.join(frames), dtype=np.int16)
            
            # Normalize audio
            audio_data = audio_data.astype(np.float32) / 32768.0
            
            # Use Whisper's transcribe with optimized settings
            result = self.model.transcribe(
                audio_data,
                language=self.source_lang,
                task="transcribe",
                fp16=False,  # Use FP32 for CPU
                verbose=False  # Reduce output
            )
            
            original_text = result["text"].strip()
            
            if original_text:
                return self._translate_text(original_text)
            return None
                    
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None
    
    def _translate_text(self, original_text):
        """Translate text with caching"""
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
            
            return {
                'original': original_text,
                'translated': translated_text
            }
            
        except Exception as e:
            print(f"❌ Translation error: {e}")
            return {
                'original': original_text,
                'translated': '[Translation Error]'
            }
    
    def _display_result(self, result):
        """Display translation result"""
        if not result:
            return
            
        original_text = result['original']
        translated_text = result['translated']
        
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
    
    def cleanup(self):
        """Clean up resources"""
        self.executor.shutdown(wait=True)
        self.audio.terminate()
        print("✅ Fast live translation stopped.")

def main():
    print("🚀 FAST Live Translation with Whisper")
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
    
    # Create translator instance with tiny model for speed
    translator = FastLiveTranslator(
        source_lang=source_lang, 
        target_lang=target_lang, 
        model_name="tiny"  # Use tiny model for maximum speed
    )
    
    try:
        translator.start_live_translation()
    except Exception as e:
        print(f"❌ Error: {e}")
        translator.cleanup()

if __name__ == "__main__":
    main()
