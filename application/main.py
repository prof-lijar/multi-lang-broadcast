"""
FastAPI Application for Multi-Language Broadcast
Main application entry point with health endpoint
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime
import os
import asyncio
import json
import base64
import logging
import subprocess
import threading
import time
from typing import Dict, Any, List, Optional
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from service.output_audio import get_audio_service, initialize_audio_service
from service.translate import get_translation_service, initialize_translation_service
from service.stt import get_stt_service, initialize_stt_service
from service.tts import get_tts_service, initialize_tts_service
from service.tts_queue import get_tts_queue, initialize_tts_queue

# Logger
logger = logging.getLogger(__name__)

# Request models
class TranslationRequest(BaseModel):
    text: str
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    model: Optional[str] = None
    mime_type: Optional[str] = None

class StreamingTranslationRequest(BaseModel):
    text: str
    source_language: Optional[str] = None
    target_language: Optional[str] = None
    model: Optional[str] = None
    mime_type: Optional[str] = None
    batch_size: int = 1
    delay_ms: int = 100

class LanguageDetectionRequest(BaseModel):
    text: str

class STTRequest(BaseModel):
    language_code: Optional[str] = "en-US"
    sample_rate: Optional[int] = 16000
    chunk_size: Optional[int] = 1024

class STTFileRequest(BaseModel):
    audio_data: str  # Base64 encoded audio data
    language_code: Optional[str] = "en-US"
    sample_rate: Optional[int] = 16000

class SpeakerAssignmentRequest(BaseModel):
    speaker1: Dict[str, Any]
    speaker2: Dict[str, Any]

class DualAudioRequest(BaseModel):
    speaker1: Dict[str, Any]
    speaker2: Dict[str, Any]
    test_text: Optional[str] = "Hello, this is a test of dual speaker audio output."

class PlayDualAudioRequest(BaseModel):
    speaker1: Dict[str, Any]
    speaker2: Dict[str, Any]

class TTSQueueRequest(BaseModel):
    text: str
    language_code: str = "en-US"
    speaker1_config: Dict[str, Any]
    speaker2_config: Dict[str, Any]

class TTSRequest(BaseModel):
    text: str
    language_code: Optional[str] = "en-US"
    voice_gender: Optional[str] = "NEUTRAL"
    play_audio: Optional[bool] = True
    cleanup: Optional[bool] = True

class TTSFileRequest(BaseModel):
    text: str
    language_code: Optional[str] = "en-US"
    voice_gender: Optional[str] = "NEUTRAL"
    filename: Optional[str] = None

# Lifespan event handler for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on application startup and cleanup on shutdown"""
    # Startup
    try:
        # Initialize audio service
        audio_service = get_audio_service()
        if audio_service.initialize():
            print("✅ Audio service initialized successfully")
        else:
            print("⚠️ Audio service initialization failed")
        
        # Initialize translation service
        if initialize_translation_service():
            print("✅ Translation service initialized successfully")
        else:
            print("⚠️ Translation service initialization failed")
        
        # Initialize STT service
        if initialize_stt_service():
            print("✅ STT service initialized successfully")
        else:
            print("⚠️ STT service initialization failed")
        
        # Initialize TTS service
        if initialize_tts_service():
            print("✅ TTS service initialized successfully")
        else:
            print("⚠️ TTS service initialization failed")
        
        # Initialize TTS queue
        if initialize_tts_queue():
            print("✅ TTS queue initialized successfully")
        else:
            print("⚠️ TTS queue initialization failed")
            
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
    
    yield
    
    # Shutdown (cleanup if needed)
    # Add any cleanup code here if needed in the future

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Language Broadcast API",
    description="API for live translation and multi-language broadcasting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files (serve app_ui.html and other files from the application directory)
import os
static_dir = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """Serve the main UI"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_ui.html")
    return FileResponse(html_path)

@app.get("/app_ui.html")
async def app_ui():
    """Serve the main UI at /app_ui.html"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_ui.html")
    return FileResponse(html_path)

@app.post("/app_ui.html")
async def app_ui_post():
    """Handle POST requests to /app_ui.html (treat as GET)"""
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_ui.html")
    return FileResponse(html_path)

@app.get("/api", response_model=Dict[str, Any])
async def api_info():
    """API information endpoint"""
    return {
        "message": "Multi-Language Broadcast API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs"
    }

@app.get("/health", response_model=Dict[str, Any])
async def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "multi-lang-broadcast",
        "version": "1.0.0"
    }

@app.get("/health/detailed", response_model=Dict[str, Any])
async def detailed_health_check():
    """Detailed health check with system information"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "multi-lang-broadcast",
        "version": "1.0.0",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": os.sys.version,
        "uptime": "N/A"  # Could be implemented with startup time tracking
    }

@app.get("/audio-output-devices", response_model=Dict[str, Any])
async def get_audio_output_devices():
    """Get list of available audio output devices and their status"""
    try:
        audio_service = get_audio_service()
        
        # Get device status
        device_status = audio_service.get_device_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": device_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve audio devices: {str(e)}"
        )

@app.get("/audio-output-devices/{card_id}", response_model=Dict[str, Any])
async def get_audio_device_details(card_id: int):
    """Get detailed information about a specific audio device"""
    try:
        audio_service = get_audio_service()
        devices = audio_service.get_devices()
        
        # Find the requested device
        device = None
        for d in devices:
            if d.card_id == card_id:
                device = d
                break
        
        if not device:
            raise HTTPException(
                status_code=404,
                detail=f"Audio device with card ID {card_id} not found"
            )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "card_id": device.card_id,
                "device_id": device.device_id,
                "name": device.name,
                "description": device.description,
                "device_type": device.device_type.value,
                "is_active": device.is_active,
                "volume": device.volume,
                "is_muted": device.is_muted
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve device details: {str(e)}"
        )

# Translation endpoints
@app.post("/translate", response_model=Dict[str, Any])
async def translate_text(request: TranslationRequest):
    """Translate a single text string"""
    try:
        translation_service = get_translation_service()
        
        if not translation_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Translation service not initialized"
            )
        
        # Validate text is not empty
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )
        
        # Validate mime_type if provided
        valid_mime_types = ["text/plain", "text/html", None]
        if request.mime_type and request.mime_type not in valid_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mime_type. Must be one of: text/plain, text/html, or omitted"
            )
        
        result = await translation_service.translate_text(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            model=request.model,
            mime_type=request.mime_type
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )

@app.post("/translate/stream")
async def translate_stream(request: StreamingTranslationRequest):
    """Translate streaming text input in real-time"""
    try:
        translation_service = get_translation_service()
        
        if not translation_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Translation service not initialized"
            )
        
        # Validate text is not empty
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )
        
        # Validate mime_type if provided
        valid_mime_types = ["text/plain", "text/html", None]
        if request.mime_type and request.mime_type not in valid_mime_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mime_type. Must be one of: text/plain, text/html, or omitted"
            )
        
        # Create a simple async generator for the text
        async def text_stream():
            # Split text into words for streaming simulation
            words = request.text.split()
            for word in words:
                yield word + " "
                await asyncio.sleep(0.1)  # Simulate streaming delay
        
        # Create streaming response
        async def generate_translations():
            async for result in translation_service.translate_stream(
                text_stream=text_stream(),
                source_language=request.source_language,
                target_language=request.target_language,
                model=request.model,
                mime_type=request.mime_type,
                batch_size=request.batch_size,
                delay_ms=request.delay_ms
            ):
                yield f"data: {json.dumps(result)}\n\n"
        
        return StreamingResponse(
            generate_translations(),
            media_type="text/plain",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Streaming translation failed: {str(e)}"
        )

@app.get("/translate/languages", response_model=Dict[str, Any])
async def get_supported_languages(target_language: str = "en"):
    """Get list of supported languages for translation"""
    try:
        translation_service = get_translation_service()
        
        if not translation_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Translation service not initialized"
            )
        
        languages = translation_service.get_supported_languages(target_language)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "languages": languages,
                "count": len(languages)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get supported languages: {str(e)}"
        )

@app.post("/translate/detect", response_model=Dict[str, Any])
async def detect_language(request: LanguageDetectionRequest):
    """Detect the language of the input text"""
    try:
        translation_service = get_translation_service()
        
        if not translation_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Translation service not initialized"
            )
        
        # Validate text is not empty
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=400,
                detail="Text cannot be empty"
            )
        
        result = translation_service.detect_language(request.text)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Language detection failed: {str(e)}"
        )

@app.get("/translate/status", response_model=Dict[str, Any])
async def get_translation_status():
    """Get translation service status and statistics"""
    try:
        translation_service = get_translation_service()
        stats = translation_service.get_statistics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get translation status: {str(e)}"
        )

@app.post("/translate/reset-stats")
async def reset_translation_statistics():
    """Reset translation service statistics"""
    try:
        translation_service = get_translation_service()
        translation_service.reset_statistics()
        
        return {
            "status": "success",
            "message": "Translation statistics reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset statistics: {str(e)}"
        )

# STT endpoints
@app.post("/stt/transcribe-file", response_model=Dict[str, Any])
async def transcribe_audio_file(request: STTFileRequest):
    """Transcribe audio from base64 encoded audio data"""
    try:
        stt_service = get_stt_service()
        
        if not stt_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="STT service not initialized"
            )
        
        # Decode base64 audio data
        try:
            audio_data = base64.b64decode(request.audio_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 audio data: {str(e)}"
            )
        
        result = await stt_service.transcribe_audio_file(
            audio_data=audio_data,
            language_code=request.language_code
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Audio transcription failed: {str(e)}"
        )

@app.get("/stt/input-devices", response_model=Dict[str, Any])
async def get_audio_input_devices():
    """Get list of available audio input devices with their channel information"""
    try:
        stt_service = get_stt_service()
        
        if not stt_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="STT service not initialized"
            )
        
        devices = stt_service.get_input_devices()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "devices": devices,
                "count": len(devices)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audio input devices: {str(e)}"
        )

@app.post("/stt/set-input-device", response_model=Dict[str, Any])
async def set_audio_input_device(device_index: Optional[int] = None, channels: int = 1):
    """Set the audio input device and channel configuration"""
    try:
        stt_service = get_stt_service()
        
        if not stt_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="STT service not initialized"
            )
        
        stt_service.set_input_device(device_index, channels)
        
        return {
            "status": "success",
            "message": "Input device configuration updated",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "device_index": device_index,
                "channels": channels
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set input device: {str(e)}"
        )

@app.get("/stt/stream")
async def stream_speech_to_text(language_code: str = "en-US"):
    """Stream real-time speech-to-text results"""
    try:
        stt_service = get_stt_service()
        
        if not stt_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="STT service not initialized"
            )
        
        async def generate_transcriptions():
            try:
                print(f"🚀 Starting transcription stream for language: {language_code}")
                async for result in stt_service.start_streaming(language_code):
                    print(f"📤 Yielding result to client: {result}")
                    yield f"data: {json.dumps(result)}\n\n"
            except Exception as e:
                print(f"❌ Error in transcription stream: {e}")
                yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
        
        return StreamingResponse(
            generate_transcriptions(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Speech-to-text streaming failed: {str(e)}"
        )

@app.post("/stt/stop")
async def stop_speech_to_text():
    """Stop the current speech-to-text streaming"""
    try:
        stt_service = get_stt_service()
        stt_service.stop_streaming()
        
        return {
            "status": "success",
            "message": "Speech-to-text streaming stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop speech-to-text: {str(e)}"
        )

@app.post("/stt/restart")
async def restart_speech_to_text():
    """Restart the speech-to-text streaming if it gets stuck"""
    try:
        stt_service = get_stt_service()
        stt_service.restart_streaming()
        
        return {
            "status": "success",
            "message": "Speech-to-text streaming restarted",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart speech-to-text: {str(e)}"
        )

@app.get("/stt/status", response_model=Dict[str, Any])
async def get_stt_status():
    """Get STT service status and statistics"""
    try:
        stt_service = get_stt_service()
        stats = stt_service.get_statistics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get STT status: {str(e)}"
        )

@app.post("/stt/reset-stats")
async def reset_stt_statistics():
    """Reset STT service statistics"""
    try:
        stt_service = get_stt_service()
        stt_service.reset_statistics()
        
        return {
            "status": "success",
            "message": "STT statistics reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset STT statistics: {str(e)}"
        )

@app.get("/stt/languages", response_model=Dict[str, Any])
async def get_supported_stt_languages():
    """Get list of supported languages for speech-to-text"""
    # Common Google Speech-to-Text supported languages
    languages = [
        {"code": "en-US", "name": "English (US)"},
        {"code": "en-GB", "name": "English (UK)"},
        {"code": "es-ES", "name": "Spanish (Spain)"},
        {"code": "es-MX", "name": "Spanish (Mexico)"},
        {"code": "fr-FR", "name": "French (France)"},
        {"code": "de-DE", "name": "German (Germany)"},
        {"code": "it-IT", "name": "Italian (Italy)"},
        {"code": "pt-BR", "name": "Portuguese (Brazil)"},
        {"code": "pt-PT", "name": "Portuguese (Portugal)"},
        {"code": "ru-RU", "name": "Russian (Russia)"},
        {"code": "ja-JP", "name": "Japanese (Japan)"},
        {"code": "ko-KR", "name": "Korean (South Korea)"},
        {"code": "zh-CN", "name": "Chinese (Simplified)"},
        {"code": "zh-TW", "name": "Chinese (Traditional)"},
        {"code": "ar-SA", "name": "Arabic (Saudi Arabia)"},
        {"code": "hi-IN", "name": "Hindi (India)"},
        {"code": "th-TH", "name": "Thai (Thailand)"},
        {"code": "vi-VN", "name": "Vietnamese (Vietnam)"},
        {"code": "my-MM", "name": "Burmese (Myanmar)"},
        {"code": "km-KH", "name": "Khmer (Cambodia)"}
    ]
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "languages": languages,
            "count": len(languages)
        }
    }

# TTS endpoints
@app.post("/tts/speak", response_model=Dict[str, Any])
async def text_to_speech_speak(request: TTSRequest):
    """Convert text to speech and play it immediately"""
    try:
        tts_service = get_tts_service()
        
        if not tts_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="TTS service not initialized"
            )
        
        # Set language and voice gender if different from default
        if request.language_code != tts_service.language_code:
            tts_service.set_language(request.language_code)
        if request.voice_gender != str(tts_service.voice_gender):
            tts_service.set_voice_gender(request.voice_gender)
        
        if request.play_audio:
            # Convert text to speech and play it
            tts_service.speak(request.text, cleanup=request.cleanup)
            
            return {
                "status": "success",
                "message": "Text converted to speech and played",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "text": request.text,
                    "language_code": request.language_code,
                    "voice_gender": request.voice_gender,
                    "played": True
                }
            }
        else:
            # Just convert to audio file without playing
            audio_file = tts_service.text_to_speech(request.text)
            
            return {
                "status": "success",
                "message": "Text converted to speech file",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "text": request.text,
                    "language_code": request.language_code,
                    "voice_gender": request.voice_gender,
                    "audio_file": audio_file,
                    "played": False
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTS failed: {str(e)}"
        )

@app.post("/tts/generate-file", response_model=Dict[str, Any])
async def text_to_speech_file(request: TTSFileRequest):
    """Convert text to speech and return audio file path"""
    try:
        tts_service = get_tts_service()
        
        if not tts_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="TTS service not initialized"
            )
        
        # Set language and voice gender if different from default
        if request.language_code != tts_service.language_code:
            tts_service.set_language(request.language_code)
        if request.voice_gender != str(tts_service.voice_gender):
            tts_service.set_voice_gender(request.voice_gender)
        
        # Convert text to speech file
        audio_file = tts_service.text_to_speech(request.text, filename=request.filename)
        
        return {
            "status": "success",
            "message": "Text converted to speech file",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "text": request.text,
                "language_code": request.language_code,
                "voice_gender": request.voice_gender,
                "audio_file": audio_file
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"TTS file generation failed: {str(e)}"
        )

@app.get("/tts/status", response_model=Dict[str, Any])
async def get_tts_status():
    """Get TTS service status and statistics"""
    try:
        tts_service = get_tts_service()
        stats = tts_service.get_statistics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get TTS status: {str(e)}"
        )

@app.post("/tts/reset-stats")
async def reset_tts_statistics():
    """Reset TTS service statistics"""
    try:
        tts_service = get_tts_service()
        tts_service.reset_statistics()
        
        return {
            "status": "success",
            "message": "TTS statistics reset",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset TTS statistics: {str(e)}"
        )

@app.post("/tts/dual-speakers", response_model=Dict[str, Any])
async def text_to_speech_dual_speakers(request: TTSRequest):
    """Convert text to speech and play on both assigned DAC speakers (cards 3 and 4)"""
    try:
        tts_service = get_tts_service()
        audio_service = get_audio_service()
        
        if not tts_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="TTS service not initialized"
            )
        
        # Check if speakers are assigned
        if not audio_service.speaker1_assignment or not audio_service.speaker2_assignment:
            raise HTTPException(
                status_code=400,
                detail="Both speakers must be assigned before testing dual TTS"
            )
        
        # Validate that assigned devices are DAC devices (cards 3 and 4)
        speaker1_device_id = audio_service.speaker1_assignment.device_id
        speaker2_device_id = audio_service.speaker2_assignment.device_id
        
        # Check if devices are DAC devices (cards 3 and 4)
        dac_devices = audio_service.get_dac_devices()
        dac_card_ids = [device.card_id for device in dac_devices]
        
        if speaker1_device_id not in dac_card_ids or speaker2_device_id not in dac_card_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Only DAC devices (cards {dac_card_ids}) can be used for dual speaker TTS. "
                       f"Current assignments: Speaker1=card {speaker1_device_id}, Speaker2=card {speaker2_device_id}"
            )
        
        # Ensure we're using the correct DAC devices (cards 3 and 4)
        if not (speaker1_device_id in [3, 4] and speaker2_device_id in [3, 4]):
            raise HTTPException(
                status_code=400,
                detail="Dual speaker TTS requires DAC devices (cards 3 and 4). "
                       f"Current assignments: Speaker1=card {speaker1_device_id}, Speaker2=card {speaker2_device_id}"
            )
        
        # Set language and voice gender if different from default
        if request.language_code != tts_service.language_code:
            tts_service.set_language(request.language_code)
        if request.voice_gender != str(tts_service.voice_gender):
            tts_service.set_voice_gender(request.voice_gender)
        
        # Generate audio file
        audio_file = tts_service.text_to_speech(request.text)
        
        # Convert MP3 to WAV for aplay compatibility
        wav_file = audio_file.replace('.mp3', '.wav')
        try:
            # Use ffmpeg to convert MP3 to WAV
            subprocess.run([
                'ffmpeg', '-i', audio_file, '-acodec', 'pcm_s16le', 
                '-ar', '44100', '-ac', '2', '-y', wav_file
            ], check=True, capture_output=True)
            
            # Start dual playback
            audio_service._start_dual_playback(wav_file, wav_file)
            
            # Clean up files if requested
            if request.cleanup:
                try:
                    os.remove(audio_file)
                    os.remove(wav_file)
                except OSError as e:
                    logger.warning(f"Could not clean up temporary files: {e}")
            
            return {
                "status": "success",
                "message": "Text converted to speech and playing on both speakers",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "text": request.text,
                    "language_code": request.language_code,
                    "voice_gender": request.voice_gender,
                    "speaker1": {
                        "language": audio_service.speaker1_assignment.language,
                        "device": audio_service.speaker1_assignment.device_name
                    },
                    "speaker2": {
                        "language": audio_service.speaker2_assignment.language,
                        "device": audio_service.speaker2_assignment.device_name
                    },
                    "audio_file": wav_file
                }
            }
            
        except subprocess.CalledProcessError as e:
            # If ffmpeg fails, try to play the MP3 directly (may not work with aplay)
            logger.warning(f"ffmpeg conversion failed: {e}, trying direct playback")
            audio_service._start_dual_playback(audio_file, audio_file)
            
            if request.cleanup:
                try:
                    os.remove(audio_file)
                except OSError as e:
                    logger.warning(f"Could not clean up temporary file: {e}")
            
            return {
                "status": "success",
                "message": "Text converted to speech and playing on both speakers (MP3 format)",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "text": request.text,
                    "language_code": request.language_code,
                    "voice_gender": request.voice_gender,
                    "speaker1": {
                        "language": audio_service.speaker1_assignment.language,
                        "device": audio_service.speaker1_assignment.device_name
                    },
                    "speaker2": {
                        "language": audio_service.speaker2_assignment.language,
                        "device": audio_service.speaker2_assignment.device_name
                    },
                    "audio_file": audio_file
                }
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Dual speaker TTS failed: {str(e)}"
        )

@app.post("/tts/setup-dac-speakers", response_model=Dict[str, Any])
async def setup_dac_speakers():
    """Automatically set up DAC devices (cards 3 and 4) for dual speaker TTS"""
    try:
        audio_service = get_audio_service()
        
        # Get available DAC devices
        dac_devices = audio_service.get_dac_devices()
        
        if len(dac_devices) < 2:
            raise HTTPException(
                status_code=400,
                detail=f"Need at least 2 DAC devices for dual speaker setup. Found: {len(dac_devices)}"
            )
        
        # Sort DAC devices by card_id to ensure consistent assignment
        dac_devices.sort(key=lambda x: x.card_id)
        
        # Assign first two DAC devices (should be cards 3 and 4)
        speaker1_device = dac_devices[0]  # Card 3
        speaker2_device = dac_devices[1]  # Card 4
        
        # Set up speaker assignments
        success = audio_service.set_speaker_assignments(
            speaker1={
                'language': 'en',
                'device': speaker1_device.card_id,
                'device_name': speaker1_device.name
            },
            speaker2={
                'language': 'ko',  # Default to Korean for second speaker
                'device': speaker2_device.card_id,
                'device_name': speaker2_device.name
            }
        )
        
        if success:
            return {
                "status": "success",
                "message": "DAC speakers set up successfully for dual TTS",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "speaker1": {
                        "language": "en",
                        "device": speaker1_device.card_id,
                        "device_name": speaker1_device.name,
                        "description": speaker1_device.description
                    },
                    "speaker2": {
                        "language": "ko",
                        "device": speaker2_device.card_id,
                        "device_name": speaker2_device.name,
                        "description": speaker2_device.description
                    },
                    "available_dac_devices": [
                        {
                            "card_id": device.card_id,
                            "name": device.name,
                            "description": device.description
                        } for device in dac_devices
                    ]
                }
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to set up DAC speaker assignments"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to setup DAC speakers: {str(e)}"
        )

@app.get("/tts/languages", response_model=Dict[str, Any])
async def get_supported_tts_languages():
    """Get list of supported languages for text-to-speech"""
    # Common Google Text-to-Speech supported languages
    languages = [
        {"code": "en-US", "name": "English (US)"},
        {"code": "en-GB", "name": "English (UK)"},
        {"code": "en-AU", "name": "English (Australia)"},
        {"code": "es-ES", "name": "Spanish (Spain)"},
        {"code": "es-MX", "name": "Spanish (Mexico)"},
        {"code": "fr-FR", "name": "French (France)"},
        {"code": "de-DE", "name": "German (Germany)"},
        {"code": "it-IT", "name": "Italian (Italy)"},
        {"code": "pt-BR", "name": "Portuguese (Brazil)"},
        {"code": "pt-PT", "name": "Portuguese (Portugal)"},
        {"code": "ru-RU", "name": "Russian (Russia)"},
        {"code": "ja-JP", "name": "Japanese (Japan)"},
        {"code": "ko-KR", "name": "Korean (South Korea)"},
        {"code": "zh-CN", "name": "Chinese (Simplified)"},
        {"code": "zh-TW", "name": "Chinese (Traditional)"},
        {"code": "ar-SA", "name": "Arabic (Saudi Arabia)"},
        {"code": "hi-IN", "name": "Hindi (India)"},
        {"code": "th-TH", "name": "Thai (Thailand)"},
        {"code": "vi-VN", "name": "Vietnamese (Vietnam)"},
        {"code": "nl-NL", "name": "Dutch (Netherlands)"},
        {"code": "sv-SE", "name": "Swedish (Sweden)"},
        {"code": "no-NO", "name": "Norwegian (Norway)"},
        {"code": "da-DK", "name": "Danish (Denmark)"},
        {"code": "fi-FI", "name": "Finnish (Finland)"},
        {"code": "pl-PL", "name": "Polish (Poland)"},
        {"code": "tr-TR", "name": "Turkish (Turkey)"},
        {"code": "cs-CZ", "name": "Czech (Czech Republic)"},
        {"code": "hu-HU", "name": "Hungarian (Hungary)"},
        {"code": "ro-RO", "name": "Romanian (Romania)"},
        {"code": "bg-BG", "name": "Bulgarian (Bulgaria)"},
        {"code": "hr-HR", "name": "Croatian (Croatia)"},
        {"code": "sk-SK", "name": "Slovak (Slovakia)"},
        {"code": "sl-SI", "name": "Slovenian (Slovenia)"},
        {"code": "et-EE", "name": "Estonian (Estonia)"},
        {"code": "lv-LV", "name": "Latvian (Latvia)"},
        {"code": "lt-LT", "name": "Lithuanian (Lithuania)"},
        {"code": "el-GR", "name": "Greek (Greece)"},
        {"code": "he-IL", "name": "Hebrew (Israel)"},
        {"code": "id-ID", "name": "Indonesian (Indonesia)"},
        {"code": "ms-MY", "name": "Malay (Malaysia)"},
        {"code": "tl-PH", "name": "Filipino (Philippines)"},
        {"code": "uk-UA", "name": "Ukrainian (Ukraine)"},
        {"code": "ca-ES", "name": "Catalan (Spain)"},
        {"code": "eu-ES", "name": "Basque (Spain)"},
        {"code": "gl-ES", "name": "Galician (Spain)"}
    ]
    
    return {
        "status": "success",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "languages": languages,
            "count": len(languages)
        }
    }

# WebSocket endpoint for real-time audio streaming
@app.websocket("/stt/ws")
async def websocket_speech_to_text(websocket: WebSocket):
    """WebSocket endpoint for real-time speech-to-text streaming"""
    await websocket.accept()
    
    try:
        stt_service = get_stt_service()
        
        if not stt_service.is_initialized:
            await websocket.send_json({
                "type": "error",
                "message": "STT service not initialized"
            })
            await websocket.close()
            return
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Listen for audio data from client
        while True:
            try:
                # Receive data from WebSocket
                data = await websocket.receive()
                
                if data["type"] == "websocket.receive":
                    if "bytes" in data:
                        # Process audio data
                        audio_data = data["bytes"]
                        language_code = "en-US"  # Default language, could be passed from client
                        
                        # Process audio and send results
                        async for result in stt_service.process_websocket_audio(audio_data, language_code):
                            await websocket.send_json(result)
                            
                    elif "text" in data:
                        # Handle text messages (like language selection)
                        try:
                            message = json.loads(data["text"])
                            if message.get("type") == "language":
                                language_code = message.get("language", "en-US")
                        except json.JSONDecodeError:
                            pass
                            
            except WebSocketDisconnect:
                print("WebSocket client disconnected")
                break
            except Exception as e:
                print(f"WebSocket processing error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                })
                break
            
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
        except:
            pass
        finally:
            try:
                await websocket.close()
            except:
                pass

# Audio Output endpoints
@app.post("/audio-output/assign-speakers", response_model=Dict[str, Any])
async def assign_speakers(request: SpeakerAssignmentRequest):
    """Assign speakers for dual audio output"""
    try:
        audio_service = get_audio_service()
        
        success = audio_service.set_speaker_assignments(
            speaker1=request.speaker1,
            speaker2=request.speaker2
        )
        
        if success:
            return {
                "status": "success",
                "message": "Speaker assignments updated",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "speaker1": request.speaker1,
                    "speaker2": request.speaker2
                }
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to set speaker assignments"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to assign speakers: {str(e)}"
        )

@app.post("/audio-output/test", response_model=Dict[str, Any])
async def test_dual_audio(request: DualAudioRequest):
    """Test dual audio output with assigned speakers using test_audio.wav"""
    try:
        audio_service = get_audio_service()
        
        print(f"Test request received: speaker1={request.speaker1}, speaker2={request.speaker2}")
        
        # Set speaker assignments
        assignment_success = audio_service.set_speaker_assignments(
            speaker1=request.speaker1,
            speaker2=request.speaker2
        )
        
        if not assignment_success:
            raise HTTPException(
                status_code=400,
                detail="Failed to set speaker assignments"
            )
        
        print(f"Speaker assignments set successfully")
        print(f"Speaker1 assignment: {audio_service.speaker1_assignment}")
        print(f"Speaker2 assignment: {audio_service.speaker2_assignment}")
        
        # Use the simple test method that plays test_audio.wav
        success = audio_service.test_dual_playback_simple()
        
        if success:
            return {
                "status": "success",
                "message": "Dual audio test started with test_audio.wav",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to start dual audio test - check server logs for details"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Test dual audio error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test dual audio: {str(e)}"
        )

@app.post("/audio-output/stop", response_model=Dict[str, Any])
async def stop_dual_audio():
    """Stop dual audio playback"""
    try:
        audio_service = get_audio_service()
        audio_service.stop_dual_playback()
        
        return {
            "status": "success",
            "message": "Dual audio playback stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop dual audio: {str(e)}"
        )

@app.get("/audio-output/status", response_model=Dict[str, Any])
async def get_audio_output_status():
    """Get audio output service status"""
    try:
        audio_service = get_audio_service()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "is_dual_playing": audio_service.is_dual_playing(),
                "speaker1_assignment": {
                    "language": audio_service.speaker1_assignment.language if audio_service.speaker1_assignment else None,
                    "device_id": audio_service.speaker1_assignment.device_id if audio_service.speaker1_assignment else None,
                    "device_name": audio_service.speaker1_assignment.device_name if audio_service.speaker1_assignment else None
                },
                "speaker2_assignment": {
                    "language": audio_service.speaker2_assignment.language if audio_service.speaker2_assignment else None,
                    "device_id": audio_service.speaker2_assignment.device_id if audio_service.speaker2_assignment else None,
                    "device_name": audio_service.speaker2_assignment.device_name if audio_service.speaker2_assignment else None
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audio output status: {str(e)}"
        )

@app.post("/audio-output/play-dual", response_model=Dict[str, Any])
async def play_dual_audio(request: PlayDualAudioRequest):
    """Queue dual audio for sequential playback (prevents overlapping speech)"""
    try:
        audio_service = get_audio_service()
        tts_queue = get_tts_queue()
        
        # Set speaker assignments
        assignment_success = audio_service.set_speaker_assignments(
            speaker1=request.speaker1,
            speaker2=request.speaker2
        )
        
        if not assignment_success:
            raise HTTPException(
                status_code=400,
                detail="Failed to set speaker assignments"
            )
        
        # Check if both speakers have text to speak
        speaker1_text = request.speaker1.get('text', '').strip()
        speaker2_text = request.speaker2.get('text', '').strip()
        
        if not speaker1_text and not speaker2_text:
            raise HTTPException(
                status_code=400,
                detail="At least one speaker must have text to speak"
            )
        
        # Determine which text to use for TTS
        # If both speakers have text, use the translated text (speaker2)
        # If only one has text, use that one
        if speaker1_text and speaker2_text:
            tts_text = speaker2_text  # Usually the translated text
            tts_language = request.speaker2.get('language', 'en-US')
        elif speaker1_text:
            tts_text = speaker1_text
            tts_language = request.speaker1.get('language', 'en-US')
        else:
            tts_text = speaker2_text
            tts_language = request.speaker2.get('language', 'en-US')
        
        # Add to TTS queue for sequential processing
        request_id = tts_queue.add_request(
            text=tts_text,
            language_code=tts_language,
            speaker1_config=request.speaker1,
            speaker2_config=request.speaker2
        )
        
        if request_id:
            return {
                "status": "success",
                "message": "Audio queued for sequential playback",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "request_id": request_id,
                    "text": tts_text,
                    "language": tts_language,
                    "speaker1": {
                        "text": speaker1_text,
                        "language": request.speaker1.get('language', 'en-US'),
                        "device": request.speaker1.get('device', 'unknown')
                    },
                    "speaker2": {
                        "text": speaker2_text,
                        "language": request.speaker2.get('language', 'en-US'),
                        "device": request.speaker2.get('device', 'unknown')
                    },
                    "queue_position": tts_queue.get_statistics()['queue_size']
                }
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to queue audio (queue may be full)"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to queue dual audio: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue dual audio: {str(e)}"
        )

@app.post("/audio-output/test-simple", response_model=Dict[str, Any])
async def test_simple_dual_audio():
    """Test dual audio with simple tones"""
    try:
        audio_service = get_audio_service()
        
        success = audio_service.test_dual_playback_simple()
        
        if success:
            return {
                "status": "success",
                "message": "Simple dual audio test started",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to start simple dual audio test"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test simple dual audio: {str(e)}"
        )

# TTS Queue Management endpoints
@app.post("/tts/queue", response_model=Dict[str, Any])
async def queue_tts(request: TTSQueueRequest):
    """Add a TTS request to the sequential queue"""
    try:
        tts_queue = get_tts_queue()
        
        request_id = tts_queue.add_request(
            text=request.text,
            language_code=request.language_code,
            speaker1_config=request.speaker1_config,
            speaker2_config=request.speaker2_config
        )
        
        if request_id:
            return {
                "status": "success",
                "message": "TTS request queued for sequential playback",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "request_id": request_id,
                    "text": request.text,
                    "language_code": request.language_code,
                    "queue_position": tts_queue.get_statistics()['queue_size']
                }
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to queue TTS request (queue may be full)"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to queue TTS: {str(e)}"
        )

@app.get("/tts/queue/status", response_model=Dict[str, Any])
async def get_tts_queue_status():
    """Get TTS queue status and statistics"""
    try:
        tts_queue = get_tts_queue()
        stats = tts_queue.get_statistics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get TTS queue status: {str(e)}"
        )

@app.post("/tts/queue/clear", response_model=Dict[str, Any])
async def clear_tts_queue():
    """Clear all TTS requests from the queue"""
    try:
        tts_queue = get_tts_queue()
        tts_queue.clear_queue()
        
        return {
            "status": "success",
            "message": "TTS queue cleared",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear TTS queue: {str(e)}"
        )


if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "false").lower() == "true"
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )
