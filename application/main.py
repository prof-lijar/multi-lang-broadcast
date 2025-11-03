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
from typing import Dict, Any, Optional
from service.audio import get_audio_recording_service, initialize_audio_recording_service
from service.stt import get_stt_service, initialize_stt_service
from service.translate import get_translation_service, initialize_translation_service
from service.sllm import get_sllm_translation_service, initialize_sllm_translation_service
from service.marianmt import get_marianmt_service
from service.nllb import get_nllb_service
from service.tts import get_tts_service, initialize_tts_service
from service.multi_device_audio import get_audio_device_manager, initialize_audio_device_manager


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
        # Initialize audio recording service
        if initialize_audio_recording_service():
            print("✅ Audio recording service initialized successfully")
        else:
            print("⚠️ Audio recording service initialization failed")
        
        # Initialize STT service with Korean language
        if initialize_stt_service(language_code="ko-KR"):
            print("✅ STT service initialized successfully with Korean language")
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
        
        # Initialize NLLB Translation service
        nllb_service = get_nllb_service()
        print("✅ NLLB Translation service initialized (model loading in background)")
        
        # Initialize TTS service
        if initialize_tts_service():
            print("✅ TTS service initialized successfully")
        else:
            print("⚠️ TTS service initialization failed")
        
        # Initialize Audio Device Manager
        if initialize_audio_device_manager():
            print("✅ Audio Device Manager initialized successfully")
        else:
            print("⚠️ Audio Device Manager initialization failed")
            
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
        audio_manager = get_audio_device_manager()
        
        # Get device status
        device_status = audio_manager.get_device_status()
        
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
    language_code: str = "ko-KR"

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

class SLLMMultipleTranslationRequest(BaseModel):
    text: str
    source_language: str = "en"

@app.post("/sllm/translate/multiple", response_model=Dict[str, Any])
async def sllm_translate_to_multiple_languages(request: SLLMMultipleTranslationRequest):
    """Translate text to multiple languages using SLLM (Korean, Chinese, Japanese)"""
    try:
        sllm_service = get_sllm_translation_service()
        
        if not sllm_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="SLLM Translation service not initialized"
            )
        
        # Define target languages
        target_languages = [
            {"code": "ko", "name": "Korean"},
            {"code": "zh", "name": "Chinese"}, 
            {"code": "ja", "name": "Japanese"}
        ]
        
        translations = {}
        
        # Translate to each language
        for lang in target_languages:
            try:
                result = await sllm_service.translate_text(
                    text=request.text,
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
                "source_language": request.source_language,
                "translations": translations
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SLLM Multiple translation failed: {str(e)}"
        )

class SLLMKoreanTranslationRequest(BaseModel):
    text: str
    source_language: str = "ko"

@app.post("/sllm/translate/korean", response_model=Dict[str, Any])
async def sllm_translate_from_korean(request: SLLMKoreanTranslationRequest):
    """Translate Korean text to multiple languages using SLLM (English, Chinese, Japanese)"""
    try:
        sllm_service = get_sllm_translation_service()
        
        if not sllm_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="SLLM Translation service not initialized"
            )
        
        # Define target languages for Korean source
        target_languages = [
            {"code": "en", "name": "English"},
            {"code": "zh", "name": "Chinese"}, 
            {"code": "ja", "name": "Japanese"}
        ]
        
        translations = {}
        
        # Translate to each language
        for lang in target_languages:
            try:
                result = await sllm_service.translate_text(
                    text=request.text,
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
                "source_language": request.source_language,
                "translations": translations
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"SLLM Korean translation failed: {str(e)}"
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

# MarianMT Translation endpoints
class MarianMTTranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

@app.post("/marianmt/translate", response_model=Dict[str, Any])
async def marianmt_translate_text(request: MarianMTTranslationRequest):
    """Translate text using MarianMT (offline translation)"""
    try:
        marianmt_service = get_marianmt_service()
        
        # Translate the text using MarianMT
        result = await marianmt_service.translate_text(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"MarianMT Translation failed: {str(e)}"
        )

@app.get("/marianmt/status", response_model=Dict[str, Any])
async def get_marianmt_status():
    """Get MarianMT translation service status and statistics"""
    try:
        marianmt_service = get_marianmt_service()
        stats = marianmt_service.get_statistics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MarianMT status: {str(e)}"
        )

@app.get("/marianmt/models", response_model=Dict[str, Any])
async def get_marianmt_models():
    """Get loaded MarianMT models and supported language pairs"""
    try:
        marianmt_service = get_marianmt_service()
        
        loaded_models = marianmt_service.get_loaded_models()
        supported_pairs = marianmt_service.get_supported_language_pairs()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "loaded_models": loaded_models,
                "supported_language_pairs": supported_pairs
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MarianMT models: {str(e)}"
        )

# NLLB Translation endpoints
class NLLBTranslationRequest(BaseModel):
    text: str
    source_lang: str
    target_lang: str

@app.post("/nllb/translate", response_model=Dict[str, Any])
async def nllb_translate_text(request: NLLBTranslationRequest):
    """Translate text using NLLB (Facebook's 200-language model)"""
    try:
        nllb_service = get_nllb_service()
        
        # Translate the text using NLLB
        result = await nllb_service.translate_text(
            text=request.text,
            source_lang=request.source_lang,
            target_lang=request.target_lang
        )
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"NLLB Translation failed: {str(e)}"
        )

@app.get("/nllb/status", response_model=Dict[str, Any])
async def get_nllb_status():
    """Get NLLB translation service status and statistics"""
    try:
        nllb_service = get_nllb_service()
        stats = nllb_service.get_statistics()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get NLLB status: {str(e)}"
        )

@app.get("/nllb/languages", response_model=Dict[str, Any])
async def get_nllb_languages():
    """Get supported languages for NLLB translation"""
    try:
        nllb_service = get_nllb_service()
        languages = nllb_service.get_supported_languages()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "supported_languages": languages,
                "total_languages": len(languages)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get NLLB languages: {str(e)}"
        )

class NLLBKoreanTranslationRequest(BaseModel):
    text: str
    source_lang: str = "ko"

@app.post("/nllb/translate/korean", response_model=Dict[str, Any])
async def nllb_translate_from_korean(request: NLLBKoreanTranslationRequest):
    """Translate Korean text to multiple languages using NLLB (English, Chinese, Japanese)"""
    try:
        nllb_service = get_nllb_service()
        
        # Define target languages for Korean source
        target_languages = [
            {"code": "en", "name": "English"},
            {"code": "zh", "name": "Chinese"}, 
            {"code": "ja", "name": "Japanese"}
        ]
        
        translations = {}
        
        # Translate to each language
        for lang in target_languages:
            try:
                result = await nllb_service.translate_text(
                    text=request.text,
                    source_lang=request.source_lang,
                    target_lang=lang["code"]
                )
                
                if result.get("success", False):
                    translations[lang["code"]] = {
                        "language": lang["name"],
                        "translated_text": result["translated_text"],
                        "latency_ms": result.get("latency_ms", 0)
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
                "source_language": request.source_lang,
                "translations": translations
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"NLLB Korean translation failed: {str(e)}"
        )

# TTS (Text-to-Speech) endpoints
class TTSRequest(BaseModel):
    text: str
    language: str = "en"
    slow: bool = False

@app.post("/tts/generate", response_model=Dict[str, Any])
async def generate_tts_audio(request: TTSRequest):
    """Generate audio from text using Google TTS"""
    try:
        tts_service = get_tts_service()
        
        if not tts_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="TTS service not initialized"
            )
        
        # Generate audio
        result = tts_service.generate_audio(
            text=request.text,
            language=request.language,
            slow=request.slow
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
            detail=f"TTS generation failed: {str(e)}"
        )

class TTSPlayRequest(BaseModel):
    text: str
    language: str = "en"
    device_id: Optional[int] = None
    slow: bool = False

@app.post("/tts/play", response_model=Dict[str, Any])
async def play_tts_audio(request: TTSPlayRequest):
    """Generate and play TTS audio"""
    try:
        tts_service = get_tts_service()
        audio_manager = get_audio_device_manager()
        
        if not tts_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="TTS service not initialized"
            )
        
        # Generate audio
        audio_result = tts_service.generate_audio(
            text=request.text,
            language=request.language,
            slow=request.slow
        )
        
        if not audio_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=audio_result["error"]
            )
        
        # Play audio
        if request.device_id is not None:
            # Play on specific device
            device = audio_manager.get_device(request.device_id)
            if not device:
                raise HTTPException(
                    status_code=400,
                    detail=f"Device {request.device_id} not found"
                )
            
            # Load audio file
            audio_data, sample_rate = audio_manager.load_audio_file(audio_result["audio_file"])
            if audio_data is None:
                raise HTTPException(
                    status_code=400,
                    detail="Failed to load generated audio file"
                )
            
            # Play on device
            success = audio_manager.play_on_device(request.device_id, audio_data, sample_rate)
            
            result = {
                "success": success,
                "device_id": request.device_id,
                "text": request.text,
                "language": request.language,
                "audio_file": audio_result["audio_file"]
            }
        else:
            # Play using TTS service (default device)
            play_result = tts_service.play_audio(audio_result["audio_file"])
            result = {
                "success": play_result["success"],
                "playback_id": play_result.get("playback_id"),
                "text": request.text,
                "language": request.language,
                "audio_file": audio_result["audio_file"]
            }
        
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
            detail=f"TTS playback failed: {str(e)}"
        )

class MultiLanguageTTSRequest(BaseModel):
    translations: Dict[str, str]  # language_code: text
    device_mapping: Dict[str, int]  # language_code: device_id
    languages: Dict[str, str] = {"ko": "ko", "zh": "zh", "ja": "ja", "en": "en"}  # language_code: tts_language

@app.post("/tts/play-multi", response_model=Dict[str, Any])
async def play_multi_language_tts(request: MultiLanguageTTSRequest):
    """Generate and play TTS audio for multiple languages on different devices"""
    try:
        tts_service = get_tts_service()
        audio_manager = get_audio_device_manager()
        
        if not tts_service.is_initialized:
            raise HTTPException(
                status_code=503,
                detail="TTS service not initialized"
            )
        
        # Generate audio for all translations
        audio_result = tts_service.generate_multiple_audio(
            translations=request.translations,
            languages=request.languages
        )
        
        if not audio_result["success"]:
            raise HTTPException(
                status_code=400,
                detail=audio_result["error"]
            )
        
        # Prepare audio files and device mapping
        audio_files = {}
        device_mapping = {}
        
        for lang_code, result in audio_result["results"].items():
            if result["success"] and lang_code in request.device_mapping:
                audio_files[lang_code] = result["audio_file"]
                device_mapping[lang_code] = request.device_mapping[lang_code]
        
        if not audio_files:
            raise HTTPException(
                status_code=400,
                detail="No valid audio files generated"
            )
        
        # Play on different devices
        play_result = audio_manager.play_multi_language_audio(audio_files, device_mapping)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "play_result": play_result,
                "audio_files": audio_files,
                "device_mapping": device_mapping,
                "translations": request.translations
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Multi-language TTS playback failed: {str(e)}"
        )

@app.post("/tts/stop", response_model=Dict[str, Any])
async def stop_tts_playback():
    """Stop all TTS playback"""
    try:
        tts_service = get_tts_service()
        audio_manager = get_audio_device_manager()
        
        # Stop TTS service playback
        tts_result = tts_service.stop_playback()
        
        # Stop audio device manager playback
        audio_manager.stop_all_playback()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "tts_stopped": tts_result["success"],
                "audio_stopped": True,
                "message": "All audio playback stopped"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop playback: {str(e)}"
        )

@app.get("/tts/status", response_model=Dict[str, Any])
async def get_tts_status():
    """Get TTS service status and playback information"""
    try:
        tts_service = get_tts_service()
        audio_manager = get_audio_device_manager()
        
        # Get TTS status
        tts_status = tts_service.get_playback_status()
        
        # Get audio device status
        device_status = audio_manager.get_device_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "tts_status": tts_status,
                "device_status": device_status,
                "is_initialized": tts_service.is_initialized
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get TTS status: {str(e)}"
        )

# Audio Device Management endpoints
@app.get("/audio/devices", response_model=Dict[str, Any])
async def get_audio_devices():
    """Get list of available audio devices"""
    try:
        audio_manager = get_audio_device_manager()
        devices = audio_manager.discover_devices()
        
        device_list = []
        for device in devices:
            device_info = {
                "index": device.index,
                "name": device.name,
                "max_input_channels": device.max_input_channels,
                "max_output_channels": device.max_output_channels,
                "default_samplerate": device.default_samplerate,
                "is_default": device.is_default,
                "status": device.status
            }
            device_list.append(device_info)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "devices": device_list,
                "count": len(device_list)
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audio devices: {str(e)}"
        )

@app.post("/audio/test-device", response_model=Dict[str, Any])
async def test_audio_device(device_id: int):
    """Test a specific audio device"""
    try:
        audio_manager = get_audio_device_manager()
        
        # Test the device
        success = audio_manager.test_device(device_id)
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "device_id": device_id,
                "test_passed": success,
                "message": "Test passed" if success else "Test failed"
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test device: {str(e)}"
        )

@app.get("/audio/status", response_model=Dict[str, Any])
async def get_audio_status():
    """Get current audio system status"""
    try:
        audio_manager = get_audio_device_manager()
        device_status = audio_manager.get_device_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "data": device_status
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audio status: {str(e)}"
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
