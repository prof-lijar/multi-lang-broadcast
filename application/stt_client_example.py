#!/usr/bin/env python3
"""
STT Client Example
Demonstrates how to use the Speech-to-Text API endpoints
"""

import asyncio
import json
import base64
import websockets
import requests
from typing import Dict, Any


class STTClient:
    """Client for interacting with the STT API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.ws_url = base_url.replace("http", "ws")
    
    def get_supported_languages(self) -> Dict[str, Any]:
        """Get list of supported languages"""
        response = requests.get(f"{self.base_url}/stt/languages")
        return response.json()
    
    def get_status(self) -> Dict[str, Any]:
        """Get STT service status"""
        response = requests.get(f"{self.base_url}/stt/status")
        return response.json()
    
    def transcribe_file(self, audio_file_path: str, language_code: str = "en-US") -> Dict[str, Any]:
        """Transcribe an audio file"""
        # Read and encode audio file
        with open(audio_file_path, "rb") as f:
            audio_data = f.read()
        
        audio_b64 = base64.b64encode(audio_data).decode('utf-8')
        
        payload = {
            "audio_data": audio_b64,
            "language_code": language_code
        }
        
        response = requests.post(f"{self.base_url}/stt/transcribe-file", json=payload)
        return response.json()
    
    def start_streaming(self, language_code: str = "en-US"):
        """Start streaming transcription via HTTP"""
        response = requests.get(f"{self.base_url}/stt/stream", params={"language_code": language_code}, stream=True)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)
                        print(f"📝 {data['type'].upper()}: {data['transcript']} (confidence: {data.get('confidence', 0):.2f})")
                    except json.JSONDecodeError:
                        print(f"Raw data: {data_str}")
    
    async def start_websocket_streaming(self, language_code: str = "en-US"):
        """Start streaming transcription via WebSocket"""
        uri = f"{self.ws_url}/stt/ws"
        
        try:
            async with websockets.connect(uri) as websocket:
                print("🔗 Connected to WebSocket")
                
                # Start streaming
                async for message in websocket:
                    data = json.loads(message)
                    
                    if data.get("type") == "connected":
                        print(f"✅ {data['message']}")
                    elif data.get("type") == "error":
                        print(f"❌ Error: {data['message']}")
                        break
                    elif data.get("type") in ["final", "interim"]:
                        transcript = data.get("transcript", "")
                        confidence = data.get("confidence", 0)
                        print(f"📝 {data['type'].upper()}: {transcript} (confidence: {confidence:.2f})")
                        
        except websockets.exceptions.ConnectionClosed:
            print("🔌 WebSocket connection closed")
        except Exception as e:
            print(f"❌ WebSocket error: {e}")
    
    def stop_streaming(self) -> Dict[str, Any]:
        """Stop the current streaming session"""
        response = requests.post(f"{self.base_url}/stt/stop")
        return response.json()
    
    def reset_statistics(self) -> Dict[str, Any]:
        """Reset STT service statistics"""
        response = requests.post(f"{self.base_url}/stt/reset-stats")
        return response.json()


async def main():
    """Main function demonstrating STT client usage"""
    print("🎤 STT Client Example")
    print("=" * 50)
    
    client = STTClient()
    
    # Check service status
    print("\n1. Checking STT service status...")
    status = client.get_status()
    print(f"Status: {status}")
    
    # Get supported languages
    print("\n2. Getting supported languages...")
    languages = client.get_supported_languages()
    print(f"Supported languages: {len(languages['data']['languages'])}")
    
    # Example usage menu
    print("\n3. Choose an option:")
    print("1. Test file transcription (requires audio file)")
    print("2. Start HTTP streaming")
    print("3. Start WebSocket streaming")
    print("4. Check status")
    print("5. Reset statistics")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        # File transcription
        audio_file = input("Enter path to audio file: ").strip()
        if audio_file:
            language = input("Enter language code (default: en-US): ").strip() or "en-US"
            print(f"\nTranscribing {audio_file}...")
            result = client.transcribe_file(audio_file, language)
            print(f"Result: {json.dumps(result, indent=2)}")
    
    elif choice == "2":
        # HTTP streaming
        language = input("Enter language code (default: en-US): ").strip() or "en-US"
        print(f"\nStarting HTTP streaming for language: {language}")
        print("Speak into your microphone (Ctrl+C to stop)")
        try:
            client.start_streaming(language)
        except KeyboardInterrupt:
            print("\n🛑 Stopping streaming...")
            client.stop_streaming()
    
    elif choice == "3":
        # WebSocket streaming
        language = input("Enter language code (default: en-US): ").strip() or "en-US"
        print(f"\nStarting WebSocket streaming for language: {language}")
        print("Speak into your microphone (Ctrl+C to stop)")
        try:
            await client.start_websocket_streaming(language)
        except KeyboardInterrupt:
            print("\n🛑 Stopping streaming...")
            client.stop_streaming()
    
    elif choice == "4":
        # Check status
        status = client.get_status()
        print(f"\nSTT Service Status:")
        print(json.dumps(status, indent=2))
    
    elif choice == "5":
        # Reset statistics
        result = client.reset_statistics()
        print(f"\nReset result: {result}")
    
    else:
        print("Invalid choice")


if __name__ == "__main__":
    asyncio.run(main())
