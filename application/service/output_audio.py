"""
Audio Output Service for Multi-Language Broadcast
Handles audio device management and playback functionality
"""

import logging
import subprocess
import threading
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import os

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


class AudioOutputService:
    """Service for managing audio output devices and playback"""
    
    def __init__(self):
        self.devices: Dict[int, AudioDevice] = {}
        self.current_device: Optional[AudioDevice] = None
        self._playback_process: Optional[subprocess.Popen] = None
        self._playback_lock = threading.Lock()
        
    def initialize(self) -> bool:
        """Initialize the audio service and discover devices"""
        try:
            logger.info("Initializing audio output service...")
            self._discover_devices()
            self._set_default_device()
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


# Global service instance
audio_service = AudioOutputService()


def get_audio_service() -> AudioOutputService:
    """Get the global audio service instance"""
    return audio_service


def initialize_audio_service() -> bool:
    """Initialize the global audio service"""
    return audio_service.initialize()
