"""
Text-to-Speech service using Google Cloud Text-to-Speech API.
"""

import os
import io
import logging
from typing import Optional, Dict, Any
from google.cloud import texttospeech
from google.cloud.texttospeech import AudioEncoding, SsmlVoiceGender

logger = logging.getLogger(__name__)


class TTSService:
    """Text-to-Speech service using Google Cloud Text-to-Speech API."""
    
    def __init__(self):
        """Initialize the TTS service."""
        try:
            self.client = texttospeech.TextToSpeechClient()
            logger.info("TTS service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize TTS service: {e}")
            raise
    
    def synthesize_speech(
        self,
        text: str,
        language_code: str = "en-US",
        voice_name: Optional[str] = None,
        ssml_gender: SsmlVoiceGender = SsmlVoiceGender.NEUTRAL,
        audio_encoding: AudioEncoding = AudioEncoding.MP3,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0
    ) -> bytes:
        """
        Synthesize speech from text using Google Cloud Text-to-Speech API.
        
        Args:
            text: The text to synthesize
            language_code: Language code (e.g., 'en-US', 'es-ES', 'fr-FR')
            voice_name: Specific voice name (optional)
            ssml_gender: Voice gender (NEUTRAL, MALE, FEMALE)
            audio_encoding: Audio encoding format
            speaking_rate: Speaking rate (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            volume_gain_db: Volume gain in dB (-96.0 to 16.0)
            
        Returns:
            bytes: Audio content as bytes
            
        Raises:
            Exception: If synthesis fails
        """
        try:
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request
            voice_params = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                ssml_gender=ssml_gender
            )
            
            # Set specific voice if provided
            if voice_name:
                voice_params.name = voice_name
            
            # Select the type of audio file you want returned
            audio_config = texttospeech.AudioConfig(
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db
            )
            
            # Perform the text-to-speech request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config
            )
            
            logger.info(f"Successfully synthesized speech for text: '{text[:50]}...'")
            return response.audio_content
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            raise
    
    def synthesize_speech_to_file(
        self,
        text: str,
        output_file: str,
        language_code: str = "en-US",
        voice_name: Optional[str] = None,
        ssml_gender: SsmlVoiceGender = SsmlVoiceGender.NEUTRAL,
        audio_encoding: AudioEncoding = AudioEncoding.MP3,
        speaking_rate: float = 1.0,
        pitch: float = 0.0,
        volume_gain_db: float = 0.0
    ) -> str:
        """
        Synthesize speech from text and save to file.
        
        Args:
            text: The text to synthesize
            output_file: Path to output audio file
            language_code: Language code (e.g., 'en-US', 'es-ES', 'fr-FR')
            voice_name: Specific voice name (optional)
            ssml_gender: Voice gender (NEUTRAL, MALE, FEMALE)
            audio_encoding: Audio encoding format
            speaking_rate: Speaking rate (0.25 to 4.0)
            pitch: Voice pitch (-20.0 to 20.0)
            volume_gain_db: Volume gain in dB (-96.0 to 16.0)
            
        Returns:
            str: Path to the created audio file
            
        Raises:
            Exception: If synthesis or file writing fails
        """
        try:
            # Get audio content
            audio_content = self.synthesize_speech(
                text=text,
                language_code=language_code,
                voice_name=voice_name,
                ssml_gender=ssml_gender,
                audio_encoding=audio_encoding,
                speaking_rate=speaking_rate,
                pitch=pitch,
                volume_gain_db=volume_gain_db
            )
            
            # Write audio content to file
            with open(output_file, "wb") as out:
                out.write(audio_content)
            
            logger.info(f"Audio content written to file: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Failed to synthesize speech to file: {e}")
            raise
    
    def get_available_voices(self, language_code: Optional[str] = None) -> list:
        """
        Get list of available voices.
        
        Args:
            language_code: Filter voices by language code (optional)
            
        Returns:
            list: List of available voices
        """
        try:
            response = self.client.list_voices(language_code=language_code)
            voices = []
            
            for voice in response.voices:
                voice_info = {
                    'name': voice.name,
                    'language_codes': list(voice.language_codes),
                    'ssml_gender': voice.ssml_gender.name,
                    'natural_sample_rate_hertz': voice.natural_sample_rate_hertz
                }
                voices.append(voice_info)
            
            logger.info(f"Retrieved {len(voices)} available voices")
            return voices
            
        except Exception as e:
            logger.error(f"Failed to get available voices: {e}")
            raise
    
    def get_supported_languages(self) -> Dict[str, Any]:
        """
        Get supported languages and their voice information.
        
        Returns:
            Dict: Dictionary mapping language codes to voice information
        """
        try:
            voices = self.get_available_voices()
            languages = {}
            
            for voice in voices:
                for lang_code in voice['language_codes']:
                    if lang_code not in languages:
                        languages[lang_code] = {
                            'voices': [],
                            'genders': set()
                        }
                    
                    languages[lang_code]['voices'].append(voice['name'])
                    languages[lang_code]['genders'].add(voice['ssml_gender'])
            
            # Convert sets to lists for JSON serialization
            for lang_code in languages:
                languages[lang_code]['genders'] = list(languages[lang_code]['genders'])
            
            logger.info(f"Retrieved {len(languages)} supported languages")
            return languages
            
        except Exception as e:
            logger.error(f"Failed to get supported languages: {e}")
            raise


# Convenience functions for common use cases
def create_tts_service() -> TTSService:
    """Create and return a TTS service instance."""
    return TTSService()


def quick_synthesize(text: str, language_code: str = "en-US") -> bytes:
    """
    Quick synthesis function for simple use cases.
    
    Args:
        text: Text to synthesize
        language_code: Language code
        
    Returns:
        bytes: Audio content
    """
    tts = create_tts_service()
    return tts.synthesize_speech(text, language_code)


def quick_synthesize_to_file(text: str, output_file: str, language_code: str = "en-US") -> str:
    """
    Quick synthesis to file function for simple use cases.
    
    Args:
        text: Text to synthesize
        output_file: Output file path
        language_code: Language code
        
    Returns:
        str: Path to output file
    """
    tts = create_tts_service()
    return tts.synthesize_speech_to_file(text, output_file, language_code)
