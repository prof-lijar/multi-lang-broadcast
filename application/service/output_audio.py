"""
Audio Output Service for Multi-Language Broadcast
Handles audio device management and playback functionality
"""

import logging
import subprocess
import threading
import time
import tempfile
import os
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import asyncio
from datetime import datetime

# Google Cloud Text-to-Speech
try:
    from google.cloud import texttospeech
    from google.oauth2 import service_account
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Warning: Google Cloud Text-to-Speech not available. Install with: pip install google-cloud-texttospeech")

logger = logging.getLogger(__name__)


class AudioDeviceType(Enum):
    """Audio device types"""
    HDMI = "hdmi"
    USB = "usb"
    ANALOG = "analog"
    UNKNOWN = "unknown"


@dataclass
class AudioDevice:
    """Audio device information"""
    card_id: int
    device_id: int
    name: str
    description: str
    device_type: AudioDeviceType
    is_active: bool = False
    volume: int = 0
    is_muted: bool = False

@dataclass
class SpeakerAssignment:
    """Speaker assignment for dual audio output"""
    language: str
    device_id: int
    device_name: str = ""


class AudioOutputService:
    """Service for managing audio output devices and playback"""
    
    def __init__(self):
        self.devices: Dict[int, AudioDevice] = {}
        self.current_device: Optional[AudioDevice] = None
        self._playback_process: Optional[subprocess.Popen] = None
        self._playback_lock = threading.Lock()
        
        # TTS client
        self.tts_client: Optional[texttospeech.TextToSpeechClient] = None
        self._tts_initialized = False
        
        # Dual speaker assignments
        self.speaker1_assignment: Optional[SpeakerAssignment] = None
        self.speaker2_assignment: Optional[SpeakerAssignment] = None
        
        # Active playback processes for dual speakers
        self._dual_playback_processes: List[subprocess.Popen] = []
        self._dual_playback_lock = threading.Lock()
        
    def initialize(self) -> bool:
        """Initialize the audio service and discover devices"""
        try:
            logger.info("Initializing audio output service...")
            self._discover_devices()
            self._set_default_device()
            self._initialize_tts()
            logger.info(f"Audio service initialized with {len(self.devices)} devices")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize audio service: {e}")
            return False
    
    def _discover_devices(self) -> None:
        """Discover available audio output devices"""
        try:
            # Get list of playback devices
            result = subprocess.run(['aplay', '-l'], capture_output=True, text=True, check=True)
            lines = result.stdout.strip().split('\n')
            
            # Parse device information
            for line in lines:
                if 'card' in line and 'device' in line:
                    
                    # Parse card and device IDs using regex-like approach
                    import re
                    
                    # Extract card ID
                    card_match = re.search(r'card (\d+):', line)
                    if not card_match:
                        continue
                    card_id = int(card_match.group(1))
                    
                    # Extract device ID
                    device_match = re.search(r'device (\d+):', line)
                    if not device_match:
                        continue
                    device_id = int(device_match.group(1))
                    
                    # Extract name (in brackets)
                    name_match = re.search(r'card \d+: (\w+) \[([^\]]+)\]', line)
                    if name_match:
                        name = name_match.group(1)
                        description = name_match.group(2)
                    else:
                        # Fallback parsing
                        parts = line.split()
                        name = ""
                        description = ""
                        for part in parts:
                            if '[' in part and ']' in part:
                                name = part.strip('[]')
                            elif part not in ['card', 'device'] and not part.isdigit() and ':' not in part:
                                description += part + " "
                    
                    device_type = self._determine_device_type(name, description)
                    device = AudioDevice(
                        card_id=card_id,
                        device_id=device_id,
                        name=name,
                        description=description.strip(),
                        device_type=device_type
                    )
                    
                    
                    # Get additional device info
                    self._get_device_info(device)
                    self.devices[card_id] = device
                        
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to discover audio devices: {e}")
        except Exception as e:
            logger.error(f"Error discovering devices: {e}")
    
    def _determine_device_type(self, name: str, description: str) -> AudioDeviceType:
        """Determine device type from name and description"""
        name_lower = name.lower()
        desc_lower = description.lower()
        
        if 'hdmi' in name_lower or 'hdmi' in desc_lower:
            return AudioDeviceType.HDMI
        elif 'usb' in name_lower or 'usb' in desc_lower:
            return AudioDeviceType.USB
        elif 'analog' in name_lower or 'analog' in desc_lower:
            return AudioDeviceType.ANALOG
        else:
            return AudioDeviceType.UNKNOWN
    
    def _get_device_info(self, device: AudioDevice) -> None:
        """Get additional information about a device"""
        try:
            # Get volume and mute status
            result = subprocess.run(
                ['amixer', '-c', str(device.card_id), 'scontents'],
                capture_output=True, text=True, check=True
            )
            
            # Parse volume information
            lines = result.stdout.split('\n')
            for line in lines:
                if 'Playback' in line and 'dB' in line:
                    # Extract volume percentage
                    if '[' in line and '%' in line:
                        volume_str = line.split('[')[1].split('%')[0]
                        try:
                            device.volume = int(volume_str)
                        except ValueError:
                            pass
                    
                    # Check if muted
                    if '[off]' in line:
                        device.is_muted = True
                        
        except subprocess.CalledProcessError:
            # Device might not support volume control
            pass
        except Exception as e:
            logger.warning(f"Could not get info for device {device.name}: {e}")
    
    def _set_default_device(self) -> None:
        """Set the default audio device (prefer USB DAC, only set DAC devices as current)"""
        # Only set USB DAC devices as current device
        for device in self.devices.values():
            if device.device_type == AudioDeviceType.USB and 'dac' in device.name.lower():
                self.current_device = device
                device.is_active = True
                logger.info(f"Set default device to USB DAC: {device.name}")
                return
        
        # If no DAC device is available, don't set any current device
        logger.warning("No DAC (USB Audio) devices found, no current device set")
    
    def _initialize_tts(self) -> None:
        """Initialize Google Cloud Text-to-Speech client"""
        if not TTS_AVAILABLE:
            logger.warning("Google Cloud Text-to-Speech not available")
            return
        
        try:
            # Find credentials file
            credentials_path = self._find_credentials_file()
            if credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                self.tts_client = texttospeech.TextToSpeechClient(credentials=credentials)
                logger.info(f"TTS client initialized with credentials: {credentials_path}")
            else:
                # Try default credentials
                self.tts_client = texttospeech.TextToSpeechClient()
                logger.info("TTS client initialized with default credentials")
            
            self._tts_initialized = True
            logger.info("Google Cloud Text-to-Speech initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS client: {e}")
            self._tts_initialized = False
    
    def _find_credentials_file(self) -> Optional[str]:
        """Find Google Cloud credentials file"""
        possible_paths = [
            "credentials.json",
            "../credentials.json",
            "../../credentials.json",
            os.path.join(os.path.expanduser("~"), "credentials.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "credentials.json"),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        return None
    
    def get_devices(self) -> List[AudioDevice]:
        """Get list of all available audio devices"""
        return list(self.devices.values())
    
    def get_dac_devices(self) -> List[AudioDevice]:
        """Get list of only DAC (USB Audio) devices, excluding HDMI devices"""
        return [device for device in self.devices.values() 
                if device.device_type == AudioDeviceType.USB and 'dac' in device.name.lower()]
    
    def get_current_device(self) -> Optional[AudioDevice]:
        """Get the currently active audio device"""
        return self.current_device
    
    def set_device(self, card_id: int) -> bool:
        """Set the active audio device"""
        if card_id not in self.devices:
            logger.error(f"Device with card ID {card_id} not found")
            return False
        
        # Deactivate current device
        if self.current_device:
            self.current_device.is_active = False
        
        # Activate new device
        self.current_device = self.devices[card_id]
        self.current_device.is_active = True
        
        logger.info(f"Switched to audio device: {self.current_device.name}")
        return True
    
    def set_volume(self, card_id: int, volume: int) -> bool:
        """Set volume for a specific device (0-100)"""
        if card_id not in self.devices:
            logger.error(f"Device with card ID {card_id} not found")
            return False
        
        # Clamp volume to valid range
        volume = max(0, min(100, volume))
        
        try:
            # Convert percentage to ALSA volume (0-128)
            alsa_volume = int((volume / 100) * 128)
            
            subprocess.run(
                ['amixer', '-c', str(card_id), 'set', 'PCM', f'{alsa_volume}%'],
                check=True, capture_output=True
            )
            
            self.devices[card_id].volume = volume
            logger.info(f"Set volume for device {card_id} to {volume}%")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to set volume for device {card_id}: {e}")
            return False
    
    def mute_device(self, card_id: int, mute: bool = True) -> bool:
        """Mute or unmute a specific device"""
        if card_id not in self.devices:
            logger.error(f"Device with card ID {card_id} not found")
            return False
        
        try:
            mute_cmd = 'mute' if mute else 'unmute'
            subprocess.run(
                ['amixer', '-c', str(card_id), 'set', 'PCM', mute_cmd],
                check=True, capture_output=True
            )
            
            self.devices[card_id].is_muted = mute
            logger.info(f"{'Muted' if mute else 'Unmuted'} device {card_id}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to mute/unmute device {card_id}: {e}")
            return False
    
    def play_audio_file(self, file_path: str, device_id: Optional[int] = None) -> bool:
        """Play an audio file through the specified or current device"""
        if not os.path.exists(file_path):
            logger.error(f"Audio file not found: {file_path}")
            return False
        
        device = self.current_device
        if device_id is not None and device_id in self.devices:
            device = self.devices[device_id]
        
        if not device:
            logger.error("No audio device available")
            return False
        
        try:
            with self._playback_lock:
                # Stop any existing playback
                self.stop_playback()
                
                # Start new playback
                cmd = [
                    'aplay', 
                    '-D', f'hw:{device.card_id},{device.device_id}',
                    file_path
                ]
                
                self._playback_process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                
                logger.info(f"Started playing {file_path} on device {device.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to play audio file: {e}")
            return False
    
    def play_audio_stream(self, audio_data: bytes, device_id: Optional[int] = None) -> bool:
        """Play audio data from memory through the specified or current device"""
        device = self.current_device
        if device_id is not None and device_id in self.devices:
            device = self.devices[device_id]
        
        if not device:
            logger.error("No audio device available")
            return False
        
        try:
            with self._playback_lock:
                # Stop any existing playback
                self.stop_playback()
                
                # Start new playback from stdin
                cmd = [
                    'aplay', 
                    '-D', f'hw:{device.card_id},{device.device_id}',
                    '-f', 'S16_LE',  # 16-bit signed little-endian
                    '-r', '44100',   # Sample rate
                    '-c', '2'        # Stereo
                ]
                
                self._playback_process = subprocess.Popen(
                    cmd, 
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE
                )
                
                # Send audio data
                self._playback_process.stdin.write(audio_data)
                self._playback_process.stdin.close()
                
                logger.info(f"Started playing audio stream on device {device.name}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to play audio stream: {e}")
            return False
    
    def stop_playback(self) -> None:
        """Stop current audio playback"""
        with self._playback_lock:
            if self._playback_process:
                try:
                    self._playback_process.terminate()
                    self._playback_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._playback_process.kill()
                except Exception as e:
                    logger.warning(f"Error stopping playback: {e}")
                finally:
                    self._playback_process = None
    
    def is_playing(self) -> bool:
        """Check if audio is currently playing"""
        with self._playback_lock:
            return self._playback_process is not None and self._playback_process.poll() is None
    
    def get_device_status(self) -> Dict:
        """Get comprehensive status of DAC (USB Audio) devices only, excluding HDMI devices"""
        status = {
            "current_device": None,
            "devices": [],
            "is_playing": self.is_playing()
        }
        
        # Filter to only include DAC (USB Audio) devices
        dac_devices = [device for device in self.devices.values() 
                      if device.device_type == AudioDeviceType.USB and 'dac' in device.name.lower()]
        
        # Set current device only if it's a DAC device
        if self.current_device and self.current_device in dac_devices:
            status["current_device"] = {
                "card_id": self.current_device.card_id,
                "name": self.current_device.name,
                "description": self.current_device.description,
                "device_type": self.current_device.device_type.value,
                "volume": self.current_device.volume,
                "is_muted": self.current_device.is_muted
            }
        
        # Add only DAC devices to the devices list
        for device in dac_devices:
            status["devices"].append({
                "card_id": device.card_id,
                "device_id": device.device_id,
                "name": device.name,
                "description": device.description,
                "device_type": device.device_type.value,
                "is_active": device.is_active,
                "volume": device.volume,
                "is_muted": device.is_muted
            })
        
        return status
    
    def refresh_devices(self) -> bool:
        """Refresh the list of available devices"""
        try:
            self.devices.clear()
            self._discover_devices()
            if not self.current_device or self.current_device.card_id not in self.devices:
                self._set_default_device()
            return True
        except Exception as e:
            logger.error(f"Failed to refresh devices: {e}")
            return False
    
    def set_speaker_assignments(self, speaker1: Dict, speaker2: Dict) -> bool:
        """Set speaker assignments for dual audio output"""
        try:
            logger.info(f"Setting speaker assignments: speaker1={speaker1}, speaker2={speaker2}")
            logger.info(f"Available devices: {list(self.devices.keys())}")
            
            # Validate speaker assignments
            if speaker1.get('device') and speaker1['device'] in self.devices:
                device1 = self.devices[speaker1['device']]
                self.speaker1_assignment = SpeakerAssignment(
                    language=speaker1['language'],
                    device_id=speaker1['device'],
                    device_name=device1.name
                )
                logger.info(f"Speaker 1 assigned: {speaker1['language']} → {device1.name}")
            else:
                logger.error(f"Speaker 1 device not found: {speaker1.get('device')} not in {list(self.devices.keys())}")
                self.speaker1_assignment = None
            
            if speaker2.get('device') and speaker2['device'] in self.devices:
                device2 = self.devices[speaker2['device']]
                self.speaker2_assignment = SpeakerAssignment(
                    language=speaker2['language'],
                    device_id=speaker2['device'],
                    device_name=device2.name
                )
                logger.info(f"Speaker 2 assigned: {speaker2['language']} → {device2.name}")
            else:
                logger.error(f"Speaker 2 device not found: {speaker2.get('device')} not in {list(self.devices.keys())}")
                self.speaker2_assignment = None
            
            # Check if both assignments were successful
            if not self.speaker1_assignment or not self.speaker2_assignment:
                logger.error("One or both speaker assignments failed")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to set speaker assignments: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _text_to_speech(self, text: str, language_code: str) -> Optional[str]:
        """Convert text to speech using Google Cloud TTS"""
        logger.info(f"TTS request: '{text}' in {language_code}")
        
        if not self._tts_initialized or not self.tts_client:
            logger.error("TTS not initialized")
            logger.error(f"TTS initialized: {self._tts_initialized}")
            logger.error(f"TTS client: {self.tts_client}")
            return None
        
        try:
            # Set up the text input
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Build the voice request
            voice = texttospeech.VoiceSelectionParams(
                language_code=language_code,
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
            )
            
            # Select the type of audio file
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )
            
            logger.info(f"Calling Google Cloud TTS API...")
            # Perform the text-to-speech request
            response = self.tts_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            
            logger.info(f"TTS API response received, audio content size: {len(response.audio_content)} bytes")
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_file.write(response.audio_content)
                temp_file_path = temp_file.name
            
            logger.info(f"TTS audio generated: {temp_file_path}")
            return temp_file_path
            
        except Exception as e:
            logger.error(f"TTS synthesis failed: {e}")
            import traceback
            logger.error(f"TTS traceback: {traceback.format_exc()}")
            return None
    
    def play_dual_audio(self, text1: str, text2: str, language1: str, language2: str) -> bool:
        """Play different text on two speakers simultaneously"""
        logger.info(f"Starting dual audio playback: '{text1}' ({language1}) and '{text2}' ({language2})")
        
        if not self.speaker1_assignment or not self.speaker2_assignment:
            logger.error("Speaker assignments not set")
            logger.error(f"Speaker1 assignment: {self.speaker1_assignment}")
            logger.error(f"Speaker2 assignment: {self.speaker2_assignment}")
            return False
        
        try:
            # Stop any existing dual playback
            self.stop_dual_playback()
            
            # Check if TTS is available
            if not self._tts_initialized:
                logger.error("TTS not initialized")
                return False
            
            # Generate TTS audio for both speakers
            logger.info(f"Generating TTS for speaker 1: '{text1}' in {language1}")
            audio_file1 = self._text_to_speech(text1, language1)
            
            logger.info(f"Generating TTS for speaker 2: '{text2}' in {language2}")
            audio_file2 = self._text_to_speech(text2, language2)
            
            if not audio_file1:
                logger.error(f"Failed to generate TTS audio for speaker 1: '{text1}'")
                return False
            if not audio_file2:
                logger.error(f"Failed to generate TTS audio for speaker 2: '{text2}'")
                return False
            
            logger.info(f"TTS audio files generated: {audio_file1}, {audio_file2}")
            
            # Start dual playback
            self._start_dual_playback(audio_file1, audio_file2)
            
            # Clean up temporary files after a delay
            def cleanup_files():
                time.sleep(10)  # Wait for playback to complete
                try:
                    if os.path.exists(audio_file1):
                        os.remove(audio_file1)
                    if os.path.exists(audio_file2):
                        os.remove(audio_file2)
                except Exception as e:
                    logger.warning(f"Failed to cleanup TTS files: {e}")
            
            threading.Thread(target=cleanup_files, daemon=True).start()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to play dual audio: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def _start_dual_playback(self, audio_file1: str, audio_file2: str) -> None:
        """Start dual audio playback on assigned speakers"""
        try:
            with self._dual_playback_lock:
                # Start playback on speaker 1
                if self.speaker1_assignment:
                    device1 = self.devices[self.speaker1_assignment.device_id]
                    cmd1 = [
                        'aplay', 
                        '-D', f'hw:{device1.card_id},{device1.device_id}',
                        audio_file1
                    ]
                    process1 = subprocess.Popen(cmd1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self._dual_playback_processes.append(process1)
                    logger.info(f"Started playback on speaker 1: {device1.name}")
                
                # Start playback on speaker 2
                if self.speaker2_assignment:
                    device2 = self.devices[self.speaker2_assignment.device_id]
                    cmd2 = [
                        'aplay', 
                        '-D', f'hw:{device2.card_id},{device2.device_id}',
                        audio_file2
                    ]
                    process2 = subprocess.Popen(cmd2, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    self._dual_playback_processes.append(process2)
                    logger.info(f"Started playback on speaker 2: {device2.name}")
                
        except KeyError as e:
            logger.error(f"Device not found in devices dictionary: {e}")
            logger.error(f"Available devices: {list(self.devices.keys())}")
            logger.error(f"Speaker1 device_id: {self.speaker1_assignment.device_id if self.speaker1_assignment else None}")
            logger.error(f"Speaker2 device_id: {self.speaker2_assignment.device_id if self.speaker2_assignment else None}")
        except Exception as e:
            logger.error(f"Failed to start dual playback: {e}")
    
    def stop_dual_playback(self) -> None:
        """Stop dual audio playback"""
        with self._dual_playback_lock:
            for process in self._dual_playback_processes:
                try:
                    process.terminate()
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                except Exception as e:
                    logger.warning(f"Error stopping dual playback process: {e}")
            
            self._dual_playback_processes.clear()
            logger.info("Dual playback stopped")
    
    def is_dual_playing(self) -> bool:
        """Check if dual audio is currently playing"""
        with self._dual_playback_lock:
            return any(process.poll() is None for process in self._dual_playback_processes)
    
    def test_dual_playback_simple(self) -> bool:
        """Test dual playback with test_audio.wav file"""
        try:
            logger.info("Testing dual playback with test_audio.wav...")
            
            if not self.speaker1_assignment or not self.speaker2_assignment:
                logger.error("Speaker assignments not set for test")
                return False
            
            # Stop any existing playback
            self.stop_dual_playback()
            
            # Find the test_audio.wav file
            test_audio_paths = [
                "test_audio.wav",
                "application/test_audio.wav",
                "../test_audio.wav",
                os.path.join(os.path.dirname(__file__), "..", "test_audio.wav"),
                os.path.join(os.path.dirname(__file__), "test_audio.wav")
            ]
            
            test_audio_file = None
            for path in test_audio_paths:
                if os.path.exists(path):
                    test_audio_file = os.path.abspath(path)
                    break
            
            if not test_audio_file:
                logger.error("test_audio.wav file not found in any of the expected locations")
                logger.error(f"Searched paths: {test_audio_paths}")
                return False
            
            logger.info(f"Using test audio file: {test_audio_file}")
            
            # Start dual playback with the same file on both speakers
            self._start_dual_playback(test_audio_file, test_audio_file)
            
            logger.info("Dual playback test started with test_audio.wav")
            return True
                
        except Exception as e:
            logger.error(f"Simple dual playback test failed: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False


# Global service instance
audio_service = AudioOutputService()


def get_audio_service() -> AudioOutputService:
    """Get the global audio service instance"""
    return audio_service


def initialize_audio_service() -> bool:
    """Initialize the global audio service"""
    return audio_service.initialize()
