"""
NLLB Translation Service
Provides translation capabilities using Facebook's NLLB-200 model
Supports 200+ languages with high quality translations
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, BitsAndBytesConfig
import gc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NLLBService:
    """
    NLLB translation service using Facebook's NLLB-200 model
    Provides high-quality translation with support for 200+ languages
    """
    
    def __init__(self, device: str = "auto", max_length: int = 512, use_quantization: bool = True):
        """
        Initialize the NLLB service
        
        Args:
            device: Device to run models on ("auto", "cpu", "cuda", "mps")
            max_length: Maximum sequence length for translation
            use_quantization: Whether to use 8-bit quantization for memory efficiency
        """
        self.device = self._get_device(device)
        self.max_length = max_length
        self.use_quantization = use_quantization
        self.model = None
        self.tokenizer = None
        self.is_initialized = False
        
        # Translation statistics
        self.stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "average_latency_ms": 0,
            "last_translation_time": None,
            "model_loaded": False
        }
        
        # Language code mapping for M2M100
        self.language_codes = {
            "en": "en",            # English
            "es": "es",            # Spanish
            "fr": "fr",            # French
            "de": "de",            # German
            "it": "it",            # Italian
            "pt": "pt",            # Portuguese
            "ru": "ru",            # Russian
            "zh": "zh",            # Chinese
            "ja": "ja",            # Japanese
            "ko": "ko",            # Korean
            "ar": "ar",            # Arabic
            "hi": "hin_Deva",      # Hindi
            "th": "tha_Thai",      # Thai
            "vi": "vie_Latn",      # Vietnamese
            "tr": "tur_Latn",      # Turkish
            "pl": "pol_Latn",      # Polish
            "nl": "nld_Latn",      # Dutch
            "sv": "swe_Latn",      # Swedish
            "da": "dan_Latn",      # Danish
            "no": "nor_Latn",      # Norwegian
            "fi": "fin_Latn",      # Finnish
            "cs": "ces_Latn",      # Czech
            "hu": "hun_Latn",      # Hungarian
            "ro": "ron_Latn",      # Romanian
            "bg": "bul_Cyrl",      # Bulgarian
            "hr": "hrv_Latn",      # Croatian
            "sk": "slk_Latn",      # Slovak
            "sl": "slv_Latn",      # Slovenian
            "et": "est_Latn",      # Estonian
            "lv": "lvs_Latn",      # Latvian
            "lt": "lit_Latn",      # Lithuanian
            "el": "ell_Grek",      # Greek
            "he": "heb_Hebr",      # Hebrew
            "fa": "pes_Arab",      # Persian
            "ur": "urd_Arab",      # Urdu
            "bn": "ben_Beng",      # Bengali
            "ta": "tam_Taml",      # Tamil
            "te": "tel_Telu",      # Telugu
            "ml": "mal_Mlym",      # Malayalam
            "kn": "kan_Knda",      # Kannada
            "gu": "guj_Gujr",      # Gujarati
            "pa": "pan_Guru",      # Punjabi
            "ne": "npi_Deva",      # Nepali
            "si": "sin_Sinh",      # Sinhala
            "my": "mya_Mymr",      # Burmese
            "km": "khm_Khmr",      # Khmer
            "lo": "lao_Laoo",      # Lao
            "ka": "kat_Geor",      # Georgian
            "am": "amh_Ethi",      # Amharic
            "sw": "swh_Latn",      # Swahili
            "zu": "zul_Latn",      # Zulu
            "af": "afr_Latn",      # Afrikaans
            "is": "isl_Latn",      # Icelandic
            "ga": "gle_Latn",      # Irish
            "cy": "cym_Latn",      # Welsh
            "mt": "mlt_Latn",      # Maltese
            "eu": "eus_Latn",      # Basque
            "ca": "cat_Latn",      # Catalan
            "gl": "glg_Latn",      # Galician
        }
        
        logger.info(f"🚀 NLLB Service initialized on device: {self.device}")
        
        # Auto-load model on initialization
        asyncio.create_task(self._auto_load_model())
    
    def _get_device(self, device: str) -> str:
        """Determine the best available device"""
        if device == "auto":
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"
            else:
                return "cpu"
        return device
    
    async def _auto_load_model(self) -> None:
        """Auto-load model in background during initialization"""
        try:
            await self.load_model()
        except Exception as e:
            logger.warning(f"⚠️ Auto-loading NLLB model failed: {e}")
    
    async def load_model(self, model_name: str = "facebook/m2m100_418M") -> bool:
        """
        Load the NLLB model
        
        Args:
            model_name: Name of the NLLB model to load
            
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            logger.info(f"🔄 Loading NLLB model: {model_name}")
            start_time = time.time()
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Configure quantization if requested
            quantization_config = None
            if self.use_quantization and self.device == "cuda":
                quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                logger.info("🔧 Using 8-bit quantization for memory efficiency")
            
            # Load model
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32
            )
            
            # Move to device
            if not quantization_config:  # Don't move quantized models
                self.model = self.model.to(self.device)
            
            self.model.eval()
            self.is_initialized = True
            
            load_time = time.time() - start_time
            self.stats["model_loaded"] = True
            
            logger.info(f"✅ NLLB model loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load NLLB model: {e}")
            return False
    
    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Translate text using NLLB
        
        Args:
            text: Text to translate
            source_lang: Source language code (e.g., 'en')
            target_lang: Target language code (e.g., 'ko')
            max_length: Maximum sequence length
            
        Returns:
            Dict containing translation result and metadata
        """
        if not self.is_initialized:
            # Try to load model if not initialized
            success = await self.load_model()
            if not success:
                return {
                    "original_text": text,
                    "translated_text": None,
                    "error": "NLLB model not loaded",
                    "success": False,
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        start_time = time.time()
        
        try:
            # Get language codes
            source_code = self.language_codes.get(source_lang, source_lang)
            target_code = self.language_codes.get(target_lang, target_lang)
            
            # Tokenize input with source language
            inputs = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True)
            if self.device != "cpu":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Generate translation with target language
            with torch.no_grad():
                translated_tokens = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.get_lang_id(target_code),
                    max_length=max_length or self.max_length,
                    num_beams=4,
                    early_stopping=True,
                    do_sample=False
                )
            
            # Decode result
            translated_texts = self.tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
            translated_text = translated_texts[0].strip()
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Update statistics
            self.stats["total_translations"] += 1
            self.stats["successful_translations"] += 1
            self.stats["last_translation_time"] = datetime.utcnow().isoformat()
            
            # Update average latency
            if self.stats["average_latency_ms"] == 0:
                self.stats["average_latency_ms"] = latency_ms
            else:
                self.stats["average_latency_ms"] = (self.stats["average_latency_ms"] + latency_ms) / 2
            
            # Prepare result
            result = {
                "original_text": text,
                "translated_text": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
                "source_code": source_code,
                "target_code": target_code,
                "model_name": "facebook/m2m100_418M",
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            }
            
            # Display result
            self._display_translation(result)
            
            return result
            
        except Exception as e:
            self.stats["failed_translations"] += 1
            logger.error(f"❌ NLLB Translation error: {e}")
            return {
                "original_text": text,
                "translated_text": None,
                "error": str(e),
                "success": False,
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def translate_batch(
        self,
        texts: List[str],
        source_lang: str,
        target_lang: str,
        max_length: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Translate a batch of texts
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            max_length: Maximum sequence length
            
        Returns:
            List of translation results
        """
        results = []
        
        for text in texts:
            result = await self.translate_text(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                max_length=max_length
            )
            results.append(result)
        
        return results
    
    def _display_translation(self, result: Dict[str, Any]) -> None:
        """
        Display translation result in terminal with formatting
        
        Args:
            result: Translation result dictionary
        """
        if result["success"]:
            print("\n" + "="*80)
            print(f"🔄 NLLB TRANSLATION - {result['timestamp']}")
            print("="*80)
            print(f"📝 Original ({result['source_language']}): {result['original_text']}")
            print(f"🌍 Translated ({result['target_language']}): {result['translated_text']}")
            print(f"⚡ Latency: {result['latency_ms']}ms")
            print(f"🤖 Model: {result['model_name']}")
            print(f"🔤 Source Code: {result['source_code']}")
            print(f"🔤 Target Code: {result['target_code']}")
            print("="*80)
        else:
            print(f"\n❌ Translation failed: {result.get('error', 'Unknown error')}")
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """
        Get list of supported languages
        
        Returns:
            List of supported languages with codes and names
        """
        languages = []
        for lang_code, nllb_code in self.language_codes.items():
            languages.append({
                "code": lang_code,
                "nllb_code": nllb_code,
                "name": self._get_language_name(lang_code)
            })
        return languages
    
    def _get_language_name(self, lang_code: str) -> str:
        """Get human-readable language name"""
        names = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
            "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
            "th": "Thai", "vi": "Vietnamese", "tr": "Turkish", "pl": "Polish",
            "nl": "Dutch", "sv": "Swedish", "da": "Danish", "no": "Norwegian",
            "fi": "Finnish", "cs": "Czech", "hu": "Hungarian", "ro": "Romanian",
            "bg": "Bulgarian", "hr": "Croatian", "sk": "Slovak", "sl": "Slovenian",
            "et": "Estonian", "lv": "Latvian", "lt": "Lithuanian", "el": "Greek",
            "he": "Hebrew", "fa": "Persian", "ur": "Urdu", "bn": "Bengali",
            "ta": "Tamil", "te": "Telugu", "ml": "Malayalam", "kn": "Kannada",
            "gu": "Gujarati", "pa": "Punjabi", "ne": "Nepali", "si": "Sinhala",
            "my": "Burmese", "km": "Khmer", "lo": "Lao", "ka": "Georgian",
            "am": "Amharic", "sw": "Swahili", "zu": "Zulu", "af": "Afrikaans",
            "is": "Icelandic", "ga": "Irish", "cy": "Welsh", "mt": "Maltese",
            "eu": "Basque", "ca": "Catalan", "gl": "Galician"
        }
        return names.get(lang_code, lang_code.upper())
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get service statistics
        
        Returns:
            Dict containing service statistics
        """
        return {
            "is_initialized": self.is_initialized,
            "device": self.device,
            "max_length": self.max_length,
            "use_quantization": self.use_quantization,
            "stats": self.stats.copy(),
            "supported_languages": len(self.language_codes)
        }
    
    def reset_statistics(self) -> None:
        """Reset service statistics"""
        self.stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "average_latency_ms": 0,
            "last_translation_time": None,
            "model_loaded": self.stats.get("model_loaded", False)
        }
        logger.info("NLLB statistics reset")


# Global service instance
_nllb_service: Optional[NLLBService] = None

def get_nllb_service(device: str = "auto", max_length: int = 512, use_quantization: bool = True) -> NLLBService:
    """
    Get the global NLLB service instance
    
    Args:
        device: Device to run models on
        max_length: Maximum sequence length
        use_quantization: Whether to use quantization
        
    Returns:
        NLLBService: The global service instance
    """
    global _nllb_service
    if _nllb_service is None:
        _nllb_service = NLLBService(device=device, max_length=max_length, use_quantization=use_quantization)
    return _nllb_service

async def translate_with_nllb(
    text: str,
    source_lang: str,
    target_lang: str,
    device: str = "auto"
) -> Dict[str, Any]:
    """
    Convenience function for quick NLLB translation
    
    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        device: Device to run on
        
    Returns:
        Dict containing translation result
    """
    service = get_nllb_service(device=device)
    return await service.translate_text(text, source_lang, target_lang)


# Example usage and testing
async def main():
    """Example usage of NLLB service"""
    print("🚀 NLLB Translation Service Example")
    print("="*50)
    
    # Initialize service
    service = get_nllb_service(device="auto", use_quantization=True)
    
    # Example translations
    examples = [
        ("Hello, how are you today?", "en", "ko"),
        ("안녕하세요, 오늘 어떻게 지내세요?", "ko", "en"),
        ("Bonjour, comment allez-vous?", "fr", "en"),
        ("Hola, ¿cómo estás?", "es", "en"),
        ("Guten Tag, wie geht es Ihnen?", "de", "en"),
    ]
    
    for text, source, target in examples:
        print(f"\n🔄 Translating: '{text}' ({source} -> {target})")
        result = await service.translate_text(text, source, target)
        
        if result["success"]:
            print(f"✅ Result: {result['translated_text']}")
        else:
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
    
    # Show statistics
    stats = service.get_statistics()
    print(f"\n📊 Statistics: {stats}")
    
    # Show supported languages
    languages = service.get_supported_languages()
    print(f"\n🌍 Supported languages: {len(languages)}")
    for lang in languages[:10]:  # Show first 10
        print(f"  - {lang['code']}: {lang['name']} ({lang['nllb_code']})")


if __name__ == "__main__":
    asyncio.run(main())
