"""
FastAPI Application for Multi-Language Broadcast
Main application entry point with health endpoint
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from datetime import datetime
import os
import base64
from typing import Dict, Any
from service.output_audio import get_audio_service, initialize_audio_service
from service.audio import get_audio_recording_service, initialize_audio_recording_service
from service.stt import get_stt_service, initialize_stt_service
from service.translate import get_translation_service, initialize_translation_service
from service.sllm import get_sllm_translation_service, initialize_sllm_translation_service


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

# Mount static files
app.mount("/static", StaticFiles(directory="."), name="static")

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
        
        # Initialize audio recording service
        if initialize_audio_recording_service():
            print("✅ Audio recording service initialized successfully")
        else:
            print("⚠️ Audio recording service initialization failed")
        
        # Initialize STT service
        if initialize_stt_service():
            print("✅ STT service initialized successfully")
        else:
            print("⚠️ STT service initialization failed")
        
        # Initialize Translation service
        if initialize_translation_service():
            print("✅ Translation service initialized successfully")
        else:
            print("⚠️ Translation service initialization failed")
        
        # Initialize SLLM Translation service
        if initialize_sllm_translation_service():
            print("✅ SLLM Translation service initialized successfully")
        else:
            print("⚠️ SLLM Translation service initialization failed")
            
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

# Recording endpoints
@app.post("/record/start", response_model=Dict[str, Any])
async def start_recording():
    """Start audio recording"""
    try:
        recording_service = get_audio_recording_service()
        
        if recording_service.start_recording():
            return {
                "status": "success",
                "message": "Recording started",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Failed to start recording"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start recording: {str(e)}"
        )

@app.post("/record/stop", response_model=Dict[str, Any])
async def stop_recording():
    """Stop audio recording and return audio data"""
    try:
        recording_service = get_audio_recording_service()
        
        audio_data = recording_service.stop_recording()
        
        if audio_data:
            # Encode audio data as base64 for transmission
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "status": "success",
                "message": "Recording stopped",
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "audio_data": audio_base64,
                    "size_bytes": len(audio_data)
                }
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="No audio data recorded"
            )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop recording: {str(e)}"
        )

from pydantic import BaseModel

class TranscriptionRequest(BaseModel):
    audio_data: str
    language_code: str = "en-US"

@app.post("/record/transcribe", response_model=Dict[str, Any])
async def transcribe_recording(request: TranscriptionRequest):
    """Transcribe recorded audio using STT service"""
    try:
        stt_service = get_stt_service()
        
        if not stt_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="STT service not initialized"
            )
        
        # Decode base64 audio data
        try:
            audio_bytes = base64.b64decode(request.audio_data)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid base64 audio data: {str(e)}"
            )
        
        # Transcribe audio
        print(f"🔍 Starting transcription with {len(audio_bytes)} bytes of audio data")
        result = await stt_service.transcribe_audio_file(
            audio_data=audio_bytes,
            language_code=request.language_code
        )
        print(f"🔍 STT service returned: {result}")
        
        # If transcription was successful, combine all results into a single transcript
        if result.get("status") == "success" and result.get("results"):
            combined_transcript = ""
            total_confidence = 0
            
            for i, res in enumerate(result["results"]):
                if i > 0:
                    combined_transcript += " "
                combined_transcript += res["transcript"]
                total_confidence += res.get("confidence", 0)
            
            # Update the result with combined transcript
            result["combined_transcript"] = combined_transcript
            result["average_confidence"] = total_confidence / len(result["results"]) if result["results"] else 0
            
            print(f"🔍 Combined transcript: '{combined_transcript}'")
        
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
            detail=f"Transcription failed: {str(e)}"
        )

@app.get("/record/status", response_model=Dict[str, Any])
async def get_recording_status():
    """Get current recording status"""
    try:
        recording_service = get_audio_recording_service()
        status = recording_service.get_recording_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get recording status: {str(e)}"
        )

# Translation endpoints
class TranslationRequest(BaseModel):
    text: str
    source_language: str = "en"
    target_language: str

@app.post("/translate", response_model=Dict[str, Any])
async def translate_text(request: TranslationRequest):
    """Translate text to a specific language"""
    try:
        translation_service = get_translation_service()
        
        if not translation_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Translation service not initialized"
            )
        
        # Translate the text
        result = await translation_service.translate_text(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language
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

class MultipleTranslationRequest(BaseModel):
    text: str
    source_language: str = "en"

@app.post("/translate/multiple", response_model=Dict[str, Any])
async def translate_to_multiple_languages(request: MultipleTranslationRequest):
    """Translate text to multiple languages (Korean, Chinese, Japanese)"""
    try:
        translation_service = get_translation_service()
        
        if not translation_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="Translation service not initialized"
            )
        
        # Define target languages
        target_languages = [
            {"code": "ko", "name": "Korean"},
            {"code": "zh", "name": "Chinese"}, 
            {"code": "ja", "name": "Japanese"}
        ]
        
        translations = {}
        
        # Use combined transcript if available, otherwise use the original text
        text_to_translate = request.text
        if hasattr(request, 'combined_transcript') and request.combined_transcript:
            text_to_translate = request.combined_transcript
            print(f"🔄 Using combined transcript for translation: '{text_to_translate}'")
        
        # Translate to each language
        for lang in target_languages:
            try:
                result = await translation_service.translate_text(
                    text=text_to_translate,
                    source_language=request.source_language,
                    target_language=lang["code"]
                )
                
                if result.get("success", False):
                    translations[lang["code"]] = {
                        "language": lang["name"],
                        "translated_text": result["translated_text"],
                        "confidence": result.get("confidence", 1.0)
                    }
                else:
                    translations[lang["code"]] = {
                        "language": lang["name"],
                        "error": result.get("error", "Translation failed")
                    }
                    
            except Exception as e:
                translations[lang["code"]] = {
                    "language": lang["name"],
                    "error": str(e)
                }
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "original_text": request.text,
                "combined_transcript": text_to_translate,
                "source_language": request.source_language,
                "translations": translations
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Multiple translation failed: {str(e)}"
        )

# SLLM Translation endpoints
class SLLMTranslationRequest(BaseModel):
    text: str
    source_language: str = "auto"
    target_language: str = "en"

@app.post("/sllm/translate", response_model=Dict[str, Any])
async def sllm_translate_text(request: SLLMTranslationRequest):
    """Translate text using SLLM (Small Language Model) via Ollama"""
    try:
        sllm_service = get_sllm_translation_service()
        
        if not sllm_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="SLLM Translation service not initialized"
            )
        
        # Translate the text using SLLM
        result = await sllm_service.translate_text(
            text=request.text,
            source_language=request.source_language if request.source_language != "auto" else None,
            target_language=request.target_language
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
            detail=f"SLLM Translation failed: {str(e)}"
        )

@app.get("/sllm/status", response_model=Dict[str, Any])
async def get_sllm_status():
    """Get SLLM translation service status and statistics"""
    try:
        sllm_service = get_sllm_translation_service()
        stats = sllm_service.get_statistics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get SLLM status: {str(e)}"
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
