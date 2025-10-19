#!/usr/bin/env python3
"""
Text-to-Speech Demo using Google Cloud Text-to-Speech

This demo program uses Google Cloud Text-to-Speech service to convert text to speech
and play it using pygame for audio playback.

Requirements:
- google-cloud-texttospeech: Google Cloud Text-to-Speech client library
- pygame: For audio playback

Before running this demo, make sure you have:
1. Enabled Text-to-Speech API in Google Cloud Console
2. Created a service account and downloaded credentials.json
3. Placed credentials.json in the project directory
4. Installed required dependencies
"""

import os
import tempfile
import time
import subprocess
import sys
import json
from pathlib import Path
from typing import Optional

try:
    from google.cloud import texttospeech
    from google.oauth2 import service_account
    import pygame
except ImportError as e:
    print(f"Missing required library: {e}")
    print("Please install required dependencies:")
    print("pip install google-cloud-texttospeech pygame")
    exit(1)


def find_credentials_file():
    """Find the credentials.json file in common locations"""
    possible_locations = [
        "credentials.json",  # Current directory
        "../credentials.json",  # Parent directory
        "../../credentials.json",  # Grandparent directory
        os.path.join(os.path.expanduser("~"), "credentials.json"),  # Home directory
        os.path.join(os.path.dirname(__file__), "credentials.json"),  # Same directory as script
        os.path.join(os.path.dirname(__file__), "..", "credentials.json"),  # Parent of script directory
    ]
    
    for location in possible_locations:
        if os.path.exists(location):
            return os.path.abspath(location)
    
    return None


def validate_credentials_file(credentials_path: str) -> bool:
    """Validate that the credentials.json file is properly formatted"""
    try:
        with open(credentials_path, 'r') as f:
            creds = json.load(f)
        
        # Check for required fields in service account key
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email', 'client_id']
        for field in required_fields:
            if field not in creds:
                print(f"Missing required field '{field}' in credentials.json")
                return False
        
        if creds.get('type') != 'service_account':
            print("Credentials file must be a service account key")
            return False
            
        return True
    except json.JSONDecodeError:
        print("Invalid JSON format in credentials.json")
        return False
    except Exception as e:
        print(f"Error reading credentials file: {e}")
        return False


def check_authentication():
    """Check if Google Cloud authentication is properly set up using credentials.json"""
    credentials_path = find_credentials_file()
    
    if not credentials_path:
        print("credentials.json file not found")
        return False
    
    if not validate_credentials_file(credentials_path):
        return False
    
    try:
        # Create credentials from service account file
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        
        # Try to create a client to test authentication
        client = texttospeech.TextToSpeechClient(credentials=credentials)
        print(f"Authentication successful using: {credentials_path}")
        return True
    except Exception as e:
        print(f"Authentication check failed: {e}")
        return False


def setup_authentication():
    """Guide user through authentication setup using credentials.json"""
    print("\n" + "=" * 60)
    print("Google Cloud Authentication Setup")
    print("=" * 60)
    print("To use Google Cloud Text-to-Speech, you need to:")
    print("1. Enable Text-to-Speech API in Google Cloud Console")
    print("2. Create a service account and download credentials.json")
    print("\nSteps to set up credentials.json:")
    print("1. Go to Google Cloud Console > IAM & Admin > Service Accounts")
    print("2. Create a new service account or use existing one")
    print("3. Grant 'Cloud Text-to-Speech API User' role")
    print("4. Create and download a JSON key file")
    print("5. Rename the downloaded file to 'credentials.json'")
    print("6. Place it in the project root directory or same directory as this script")
    print("\nThe program will automatically find credentials.json in:")
    print("- Current directory")
    print("- Parent directories")
    print("- Home directory")
    print("- Same directory as this script")
    print("=" * 60)


class TTSDemo:
    """Text-to-Speech Demo class using Google Cloud Text-to-Speech"""
    
    def __init__(self, language_code: str = 'en-US', voice_gender: str = 'NEUTRAL'):
        """
        Initialize TTS Demo
        
        Args:
            language_code: Language code for TTS (default: 'en-US' for English US)
            voice_gender: Voice gender - 'NEUTRAL', 'MALE', or 'FEMALE' (default: 'NEUTRAL')
        """
        self.language_code = language_code
        self.voice_gender = getattr(texttospeech.SsmlVoiceGender, voice_gender)
        self.temp_dir = tempfile.gettempdir()
        
        # Initialize Google Cloud Text-to-Speech client with credentials.json
        try:
            credentials_path = find_credentials_file()
            if not credentials_path:
                raise FileNotFoundError("credentials.json file not found")
            
            # Create credentials from service account file
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
            
            self.client = texttospeech.TextToSpeechClient(credentials=credentials)
            print(f"Google Cloud TTS client initialized successfully using: {credentials_path}")
        except Exception as e:
            print(f"Failed to initialize Google Cloud TTS client: {e}")
            print("Make sure you have:")
            print("1. Enabled Text-to-Speech API in Google Cloud Console")
            print("2. Created a service account and downloaded credentials.json")
            print("3. Placed credentials.json in the project directory")
            raise
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
        print(f"TTS Demo initialized - Language: {language_code}, Voice Gender: {voice_gender}")
    
    def text_to_speech(self, text: str, filename: Optional[str] = None) -> str:
        """
        Convert text to speech and save as audio file using Google Cloud TTS
        
        Args:
            text: Text to convert to speech
            filename: Optional filename for the audio file
            
        Returns:
            Path to the generated audio file
        """
        try:
            print(f"Converting text to speech: '{text}'")
            
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request, select the language code and the SSML voice gender
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                ssml_gender=self.voice_gender
            )
            
            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            # Perform the text-to-speech request on the text input with the selected
            # voice parameters and audio file type
            response = self.client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            # Generate filename if not provided
            if filename is None:
                timestamp = int(time.time())
                filename = f"tts_output_{timestamp}.mp3"
            
            # Save to temporary directory
            filepath = os.path.join(self.temp_dir, filename)
            
            # The response's audio_content is binary
            with open(filepath, "wb") as out:
                # Write the response to the output file
                out.write(response.audio_content)
            
            print(f"Audio saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error converting text to speech: {e}")
            raise
    
    def play_audio(self, filepath: str) -> None:
        """
        Play audio file using pygame
        
        Args:
            filepath: Path to the audio file to play
        """
        try:
            print(f"Playing audio: {filepath}")
            
            # Load and play the audio file
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()
            
            # Wait for playback to complete
            while pygame.mixer.music.get_busy():
                time.sleep(0.1)
            
            print("Audio playback completed")
            
        except Exception as e:
            print(f"Error playing audio: {e}")
            raise
    
    def speak(self, text: str, cleanup: bool = True) -> None:
        """
        Convert text to speech and play it immediately
        
        Args:
            text: Text to speak
            cleanup: Whether to delete the temporary audio file after playing
        """
        try:
            # Convert text to speech
            audio_file = self.text_to_speech(text)
            
            # Play the audio
            self.play_audio(audio_file)
            
            # Clean up temporary file if requested
            if cleanup:
                try:
                    os.remove(audio_file)
                    print(f"Cleaned up temporary file: {audio_file}")
                except OSError as e:
                    print(f"Warning: Could not delete temporary file {audio_file}: {e}")
                    
        except Exception as e:
            print(f"Error in speak method: {e}")
            raise
    
    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            pygame.mixer.quit()
            # Google Cloud Text-to-Speech client doesn't need explicit cleanup
            print("TTS Demo cleanup completed")
        except Exception as e:
            print(f"Error during cleanup: {e}")


def main():
    """Main function to demonstrate TTS functionality"""
    print("=" * 60)
    print("Google Cloud Text-to-Speech Demo")
    print("=" * 60)
    
    # Check authentication first
    if not check_authentication():
        setup_authentication()
        return
    
    # Initialize TTS demo with Google Cloud TTS
    tts_demo = TTSDemo(language_code='en-US', voice_gender='NEUTRAL')
    
    try:
        # The specific message requested
        message = "hello, im LI JAR. I Love AI"
        
        print(f"\nSpeaking message: '{message}'")
        print("-" * 40)
        
        # Convert and play the message
        tts_demo.speak(message)
        
        print("\n" + "=" * 60)
        print("TTS Demo completed successfully!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user")
    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Text-to-Speech API is enabled in Google Cloud Console")
        print("2. Ensure credentials.json file is present and valid")
        print("3. Check your Google Cloud project billing is enabled")
        print("4. Verify service account has 'Cloud Text-to-Speech API User' role")
    finally:
        # Clean up resources
        tts_demo.cleanup()


if __name__ == "__main__":
    main()
