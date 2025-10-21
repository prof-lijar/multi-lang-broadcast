"""
FastAPI Application for Multi-Language Broadcast
Main application entry point with health endpoint
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime
import os
import asyncio
import json
from typing import Dict, Any, List, Optional
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from service.output_audio import get_audio_service, initialize_audio_service
from service.translate import get_translation_service, initialize_translation_service

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

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Language Broadcast API",
    description="API for live translation and multi-language broadcasting",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
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
            
    except Exception as e:
        print(f"❌ Error initializing services: {e}")

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Root endpoint with basic API information"""
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
