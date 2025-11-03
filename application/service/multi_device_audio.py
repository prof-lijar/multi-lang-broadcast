"""
Multi-Device Audio Manager
Handles audio playback on multiple devices/speakers
"""

import os
import sys
import threading
import time
import tempfile
import soundfile as sf
import numpy as np
from typing import Dict, Any, Optional, List, Callable
import pygame
import subprocess
import platform
import sounddevice as sd


class AudioDevice:
    """Represents an audio device"""
    
    def __init__(self, index: int, name: str, max_input_channels: int = 0, 
                 max_output_channels: int = 2, default_samplerate: int = 44100, 
                 is_default: bool = False):
        self.index = index
        self.name = name
        self.max_input_channels = max_input_channels
        self.max_output_channels = max_output_channels
        self.default_samplerate = default_samplerate
        self.is_default = is_default
        self.status = "idle"


class AudioDeviceManager:
    """Manages multiple audio devices for playback"""
    
    def __init__(self):
        self.devices = []
        self.active_playbacks = {}  # Track active playback sessions
        self.is_playing = False
        self._discover_devices()
    
    def _discover_devices(self):
        """Discover available audio devices using sounddevice"""
        try:
            # Initialize pygame mixer for playback
            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
            pygame.mixer.init()
            
            # Get devices using sounddevice
            devices_info = sd.query_devices()
            self.devices = []
            
            for i, device_info in enumerate(devices_info):
                # Only include devices with output capabilities
                if device_info['max_output_channels'] > 0:
                    device = AudioDevice(
                        index=i,
                        name=device_info['name'],
                        max_input_channels=device_info['max_input_channels'],
                        max_output_channels=device_info['max_output_channels'],
                        default_samplerate=int(device_info['default_samplerate']),
                        is_default=(i == sd.default.device[1])  # Check if this is the default output device
                    )
                    self.devices.append(device)
                    print(f"✅ Found audio device {i}: {device.name} (Output: {device.max_output_channels} channels)")
            
            # If no devices found, create a default device
            if not self.devices:
                default_device = AudioDevice(
                    index=0,
                    name="Default Audio Device",
                    max_output_channels=2,
                    default_samplerate=22050,
                    is_default=True
                )
                self.devices.append(default_device)
                print("⚠️ No audio devices found, using default device")
            
            print(f"✅ Discovered {len(self.devices)} audio output devices")
            
        except Exception as e:
            print(f"❌ Error discovering audio devices: {e}")
            # Create fallback default device
            default_device = AudioDevice(
                index=0,
                name="Default Audio Device",
                max_output_channels=2,
                default_samplerate=22050,
                is_default=True
            )
            self.devices = [default_device]
    
    def discover_devices(self) -> List[AudioDevice]:
        """Get list of discovered devices"""
        return self.devices
    
    def get_device(self, device_id: int) -> Optional[AudioDevice]:
        """Get device by ID"""
        for device in self.devices:
            if device.index == device_id:
                return device
        return None
    
    def test_device(self, device_id: int) -> bool:
        """Test if a device is working"""
        try:
            device = self.get_device(device_id)
            if not device:
                return False
            
            # Create a short test tone
            test_tone, sample_rate = self.create_test_tone(0.5, 440.0)
            
            # Try to play on the device
            success = self.play_on_device(device_id, test_tone, sample_rate)
            return success
            
        except Exception as e:
            print(f"Error testing device {device_id}: {e}")
            return False
    
    def create_test_tone(self, duration: float = 2.0, frequency: float = 440.0) -> tuple:
        """Create a test tone"""
        try:
            sample_rate = 22050
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            tone = np.sin(2 * np.pi * frequency * t) * 0.3
            
            # Convert to stereo
            stereo_tone = np.array([tone, tone]).T
            
            return stereo_tone, sample_rate
            
        except Exception as e:
            print(f"Error creating test tone: {e}")
            return None, None
    
    def load_audio_file(self, file_path: str) -> tuple:
        """Load audio file and return audio data and sample rate"""
        try:
            audio_data, sample_rate = sf.read(file_path)
            
            # Ensure stereo
            if len(audio_data.shape) == 1:
                audio_data = np.array([audio_data, audio_data]).T
            elif audio_data.shape[1] == 1:
                audio_data = np.repeat(audio_data, 2, axis=1)
            
            return audio_data, sample_rate
            
        except Exception as e:
            print(f"Error loading audio file {file_path}: {e}")
            return None, None
    
    def play_on_device(self, device_id: int, audio_data: np.ndarray, 
                      sample_rate: int, status_callback: Optional[Callable] = None, 
                      block: bool = True) -> bool:
        """Play audio on a specific device using sounddevice"""
        try:
            device = self.get_device(device_id)
            if not device:
                print(f"Device {device_id} not found")
                return False
            
            # Configure device-specific stream settings
            device_info = sd.query_devices(device_id)
            channels = min(device_info['max_output_channels'], audio_data.shape[1])
            
            # Set device status
            device.status = "playing"
            if status_callback:
                status_callback(device_id, "playing")
            
            # Ensure audio data is in the right format
            if len(audio_data.shape) == 1:
                # Mono to stereo
                audio_data = np.column_stack((audio_data, audio_data))
            elif audio_data.shape[1] == 1:
                # Single channel to stereo
                audio_data = np.repeat(audio_data, 2, axis=1)
            
            # Play on specific device using sounddevice with device-specific stream
            try:
                print(f"🔊 Playing audio on device {device_id}: {device.name}")
                
                # Create a device-specific output stream
                stream = sd.OutputStream(
                    device=device_id,
                    channels=channels,
                    samplerate=sample_rate,
                    dtype=audio_data.dtype
                )
                
                with stream:
                    stream.start()
                    stream.write(audio_data)
                    stream.stop()
                
                # Update status
                device.status = "idle"
                if status_callback:
                    status_callback(device_id, "completed")
                
                print(f"✅ Audio playback completed on device {device_id}")
                return True
                
            except Exception as e:
                print(f"Error playing audio on device {device_id}: {e}")
                device.status = "error"
                if status_callback:
                    status_callback(device_id, "error")
                return False
            
        except Exception as e:
            print(f"Error in play_on_device: {e}")
            return False
    
    def play_on_all_devices(self, file_path: str) -> Dict[int, bool]:
        """Play audio file on all devices"""
        try:
            # Load audio file
            audio_data, sample_rate = self.load_audio_file(file_path)
            if audio_data is None:
                return {}
            
            results = {}
            threads = []
            
            # Play on each device in separate thread
            for device in self.devices:
                if device.max_output_channels > 0:
                    thread = threading.Thread(
                        target=self._play_on_device_thread,
                        args=(device.index, audio_data, sample_rate, results)
                    )
                    thread.daemon = True
                    thread.start()
                    threads.append(thread)
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=30)  # 30 second timeout
            
            return results
            
        except Exception as e:
            print(f"Error playing on all devices: {e}")
            return {}
    
    def _play_on_device_thread(self, device_id: int, audio_data: np.ndarray, 
                              sample_rate: int, results: Dict[int, bool]):
        """Play audio on device in separate thread"""
        try:
            success = self.play_on_device(device_id, audio_data, sample_rate)
            results[device_id] = success
        except Exception as e:
            print(f"Error in device thread {device_id}: {e}")
            results[device_id] = False
    
    def stop_all_playback(self):
        """Stop all audio playback"""
        try:
            pygame.mixer.music.stop()
            sd.stop()  # Stop all sounddevice streams
            self.is_playing = False
            
            # Update all device statuses
            for device in self.devices:
                device.status = "idle"
            
            # Clear active playbacks
            self.active_playbacks.clear()
            
        except Exception as e:
            print(f"Error stopping all playback: {e}")
    
    def get_device_status(self) -> Dict[str, Any]:
        """Get status of all devices"""
        try:
            device_status = {}
            for device in self.devices:
                device_status[str(device.index)] = {
                    "name": device.name,
                    "status": device.status,
                    "max_output_channels": device.max_output_channels,
                    "is_default": device.is_default
                }
            
            return {
                "devices": device_status,
                "total_devices": len(self.devices),
                "is_playing": self.is_playing
            }
            
        except Exception as e:
            print(f"Error getting device status: {e}")
            return {"devices": {}, "total_devices": 0, "is_playing": False}
    
    def play_multi_language_audio(self, audio_files: Dict[str, str], 
                                device_mapping: Dict[str, int]) -> Dict[str, Any]:
        """Play different audio files on different devices for multi-language output"""
        try:
            results = {}
            threads = []
            
            print(f"🎵 Starting multi-language playback on devices: {device_mapping}")
            
            # First, validate all devices and load audio files
            playback_tasks = []
            for lang_code, audio_file in audio_files.items():
                if lang_code in device_mapping:
                    device_id = device_mapping[lang_code]
                    device = self.get_device(device_id)
                    
                    if not device:
                        print(f"⚠️ Device {device_id} not found for language {lang_code}")
                        continue
                        
                    # Load audio file
                    audio_data, sample_rate = self.load_audio_file(audio_file)
                    if audio_data is not None:
                        print(f"✅ Loaded audio for {lang_code} - Device {device_id}")
                        playback_tasks.append((device_id, audio_data, sample_rate, lang_code))
                    
            # Start playback on all devices simultaneously
            for device_id, audio_data, sample_rate, lang_code in playback_tasks:
                print(f"🔊 Starting playback for {lang_code} on device {device_id}")
                thread = threading.Thread(
                    target=self._play_multi_lang_thread,
                    args=(device_id, audio_data, sample_rate, lang_code, results)
                )
                thread.daemon = True
                thread.start()
                threads.append(thread)
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=60)  # 60 second timeout
            
            successful_count = sum(1 for r in results.values() if r.get("success", False))
            print(f"✅ Multi-language playback completed: {successful_count}/{len(audio_files)} successful")
            
            return {
                "success": True,
                "results": results,
                "total_languages": len(audio_files),
                "successful_playbacks": successful_count
            }
            
        except Exception as e:
            print(f"❌ Error in play_multi_language_audio: {e}")
            return {
                "success": False,
                "error": f"Failed to play multi-language audio: {str(e)}"
            }
    
    def _play_multi_lang_thread(self, device_id: int, audio_data: np.ndarray, 
                               sample_rate: int, lang_code: str, results: Dict[str, Any]):
        """Play multi-language audio in separate thread"""
        try:
            success = self.play_on_device(device_id, audio_data, sample_rate)
            results[lang_code] = {
                "success": success,
                "device_id": device_id,
                "language": lang_code
            }
        except Exception as e:
            results[lang_code] = {
                "success": False,
                "error": str(e),
                "device_id": device_id,
                "language": lang_code
            }


# Global audio device manager instance
_audio_manager = None

def get_audio_device_manager() -> AudioDeviceManager:
    """Get global audio device manager instance"""
    global _audio_manager
    if _audio_manager is None:
        _audio_manager = AudioDeviceManager()
    return _audio_manager

def initialize_audio_device_manager() -> bool:
    """Initialize audio device manager"""
    try:
        manager = get_audio_device_manager()
        return len(manager.devices) > 0
    except Exception as e:
        print(f"Failed to initialize audio device manager: {e}")
        return False
