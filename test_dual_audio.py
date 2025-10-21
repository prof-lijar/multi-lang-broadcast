#!/usr/bin/env python3
"""
Dual Audio Card Playback Test
Plays test_audio.wav simultaneously on two selected sound cards
"""

import pyaudio
import wave
import threading
import time
import sys
import os
from typing import List, Tuple, Optional

class DualAudioPlayer:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.streams = []
        self.audio_data = None
        self.is_playing = False
        
    def list_audio_devices(self) -> List[Tuple[int, str, int]]:
        """List all available audio output devices"""
        devices = []
        print("\n" + "="*60)
        print("AVAILABLE AUDIO OUTPUT DEVICES:")
        print("="*60)
        
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxOutputChannels'] > 0:  # Only output devices
                devices.append((i, device_info['name'], device_info['maxOutputChannels']))
                print(f"Index: {i:2d} | Channels: {device_info['maxOutputChannels']} | Name: {device_info['name']}")
        
        print("="*60)
        return devices
    
    def load_audio_file(self, filename: str) -> bool:
        """Load audio file and prepare for playback"""
        if not os.path.exists(filename):
            print(f"Error: Audio file '{filename}' not found!")
            return False
            
        try:
            with wave.open(filename, 'rb') as wf:
                self.audio_data = {
                    'frames': wf.readframes(wf.getnframes()),
                    'channels': wf.getnchannels(),
                    'sample_width': wf.getsampwidth(),
                    'frame_rate': wf.getframerate(),
                    'nframes': wf.getnframes()
                }
            print(f"✓ Loaded audio file: {filename}")
            print(f"  - Channels: {self.audio_data['channels']}")
            print(f"  - Sample Rate: {self.audio_data['frame_rate']} Hz")
            print(f"  - Duration: {self.audio_data['nframes'] / self.audio_data['frame_rate']:.2f} seconds")
            return True
        except Exception as e:
            print(f"Error loading audio file: {e}")
            return False
    
    def create_stream(self, device_index: int, device_name: str) -> Optional[pyaudio.Stream]:
        """Create a PyAudio stream for the specified device"""
        try:
            stream = self.p.open(
                format=self.p.get_format_from_width(self.audio_data['sample_width']),
                channels=self.audio_data['channels'],
                rate=self.audio_data['frame_rate'],
                output=True,
                output_device_index=device_index,
                frames_per_buffer=1024
            )
            print(f"✓ Created stream for device {device_index}: {device_name}")
            return stream
        except Exception as e:
            print(f"✗ Failed to create stream for device {device_index}: {e}")
            return None
    
    def play_audio_on_stream(self, stream: pyaudio.Stream, device_name: str):
        """Play audio on a specific stream (runs in separate thread)"""
        try:
            # Reset audio data position
            audio_frames = self.audio_data['frames']
            chunk_size = 1024 * self.audio_data['channels'] * self.audio_data['sample_width']
            
            print(f"🎵 Starting playback on: {device_name}")
            
            for i in range(0, len(audio_frames), chunk_size):
                if not self.is_playing:
                    break
                chunk = audio_frames[i:i + chunk_size]
                stream.write(chunk)
            
            print(f"✓ Finished playback on: {device_name}")
            
        except Exception as e:
            print(f"✗ Error during playback on {device_name}: {e}")
    
    def play_dual_audio(self, device1_index: int, device2_index: int, device_names: Tuple[str, str]):
        """Play audio simultaneously on two devices"""
        if not self.audio_data:
            print("Error: No audio data loaded!")
            return
        
        print(f"\n🎵 Starting dual audio playback...")
        print(f"Device 1: {device_names[0]} (Index: {device1_index})")
        print(f"Device 2: {device_names[1]} (Index: {device2_index})")
        print("-" * 60)
        
        # Create streams for both devices
        stream1 = self.create_stream(device1_index, device_names[0])
        stream2 = self.create_stream(device2_index, device_names[1])
        
        if not stream1 or not stream2:
            print("Error: Failed to create one or both audio streams!")
            return
        
        self.streams = [stream1, stream2]
        self.is_playing = True
        
        # Create threads for simultaneous playback
        thread1 = threading.Thread(
            target=self.play_audio_on_stream, 
            args=(stream1, device_names[0])
        )
        thread2 = threading.Thread(
            target=self.play_audio_on_stream, 
            args=(stream2, device_names[1])
        )
        
        # Start both threads
        thread1.start()
        thread2.start()
        
        # Wait for both threads to complete
        thread1.join()
        thread2.join()
        
        print("\n✓ Dual audio playback completed!")
    
    def stop_playback(self):
        """Stop current playback"""
        self.is_playing = False
        for stream in self.streams:
            if stream:
                stream.stop_stream()
                stream.close()
        self.streams = []
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_playback()
        self.p.terminate()

def get_user_device_selection(devices: List[Tuple[int, str, int]]) -> Tuple[int, int]:
    """Get device selection from user"""
    while True:
        try:
            print(f"\nSelect two devices for dual playback:")
            device1_idx = int(input("Enter index for first device: "))
            device2_idx = int(input("Enter index for second device: "))
            
            # Validate selections
            valid_indices = [d[0] for d in devices]
            if device1_idx not in valid_indices:
                print(f"Error: Device index {device1_idx} not found!")
                continue
            if device2_idx not in valid_indices:
                print(f"Error: Device index {device2_idx} not found!")
                continue
            if device1_idx == device2_idx:
                print("Error: Please select two different devices!")
                continue
                
            return device1_idx, device2_idx
            
        except ValueError:
            print("Error: Please enter valid device indices (numbers)!")

def main():
    """Main function"""
    print("🎵 Dual Audio Card Playback Test")
    print("=" * 40)
    
    # Initialize player
    player = DualAudioPlayer()
    
    try:
        # List available devices
        devices = player.list_audio_devices()
        
        if len(devices) < 2:
            print(f"\nError: Found only {len(devices)} audio output device(s).")
            print("You need at least 2 audio output devices for dual playback.")
            return
        
        # Load audio file
        audio_file = "test_audio.wav"
        if not player.load_audio_file(audio_file):
            return
        
        # Get user selection
        device1_idx, device2_idx = get_user_device_selection(devices)
        
        # Get device names
        device1_name = next(d[1] for d in devices if d[0] == device1_idx)
        device2_name = next(d[1] for d in devices if d[0] == device2_idx)
        
        # Confirm selection
        print(f"\nSelected devices:")
        print(f"Device 1: {device1_name} (Index: {device1_idx})")
        print(f"Device 2: {device2_name} (Index: {device2_idx})")
        
        confirm = input("\nProceed with dual playback? (y/n): ").lower().strip()
        if confirm != 'y':
            print("Playback cancelled.")
            return
        
        # Play dual audio
        player.play_dual_audio(device1_idx, device2_idx, (device1_name, device2_name))
        
    except KeyboardInterrupt:
        print("\n\nPlayback interrupted by user.")
        player.stop_playback()
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    finally:
        player.cleanup()
        print("Cleanup completed.")

if __name__ == "__main__":
    main()
