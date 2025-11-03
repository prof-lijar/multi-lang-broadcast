"""
MarianMT Translation Service
Provides offline translation capabilities using Hugging Face MarianMT models
Supports multilingual translation with high performance and low latency
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import torch
from transformers import MarianMTModel, MarianTokenizer
import gc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarianMTService:
    """
    MarianMT translation service using Hugging Face models
    Provides fast, offline translation with multilingual support
    """
    
    def __init__(self, device: str = "auto", max_length: int = 512):
        """
        Initialize the MarianMT service
        
        Args:
            device: Device to run models on ("auto", "cpu", "cuda", "mps")
            max_length: Maximum sequence length for translation
        """
        self.device = self._get_device(device)
        self.max_length = max_length
        self.models: Dict[str, Dict[str, Any]] = {}
        self.is_initialized = False
        
        # Translation statistics
        self.stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "average_latency_ms": 0,
            "last_translation_time": None,
            "models_loaded": 0
        }
        
        # Supported language pairs (common ones)
        self.supported_pairs = {
            "en-es": "Helsinki-NLP/opus-mt-en-es",
            "en-fr": "Helsinki-NLP/opus-mt-en-fr", 
            "en-de": "Helsinki-NLP/opus-mt-en-de",
            "en-it": "Helsinki-NLP/opus-mt-en-it",
            "en-pt": "Helsinki-NLP/opus-mt-en-pt",
            "en-ru": "Helsinki-NLP/opus-mt-en-ru",
            "en-zh": "Helsinki-NLP/opus-mt-en-zh",
            "en-ja": "Helsinki-NLP/opus-mt-en-ja",
            "en-ko": "pytorch-models/opus-mt-tc-big-en-ko",  # Korean model from pytorch-models
            "en-ar": "Helsinki-NLP/opus-mt-en-ar",
            "es-en": "Helsinki-NLP/opus-mt-es-en",
            "fr-en": "Helsinki-NLP/opus-mt-fr-en",
            "de-en": "Helsinki-NLP/opus-mt-de-en",
            "it-en": "Helsinki-NLP/opus-mt-it-en",
            "pt-en": "Helsinki-NLP/opus-mt-pt-en",
            "ru-en": "Helsinki-NLP/opus-mt-ru-en",
            "zh-en": "Helsinki-NLP/opus-mt-zh-en",
            "ja-en": "Helsinki-NLP/opus-mt-ja-en",
            "ko-en": "pytorch-models/opus-mt-tc-big-ko-en",  # Korean to English model
            "ar-en": "Helsinki-NLP/opus-mt-ar-en",
            # Multilingual models
            # "mul-mul": "Helsinki-NLP/opus-mt-mul-mul",  # Tatoeba Challenge - requires auth
            "en-mul": "Helsinki-NLP/opus-mt-en-ROMANCE",  # English to Romance languages
        }
        
        logger.info(f"🚀 MarianMT Service initialized on device: {self.device}")
    
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
    
    async def load_model(self, source_lang: str, target_lang: str, model_name: Optional[str] = None) -> bool:
        """
        Load a MarianMT model for the specified language pair
        
        Args:
            source_lang: Source language code (e.g., 'en')
            target_lang: Target language code (e.g., 'es')
            model_name: Optional custom model name
            
        Returns:
            bool: True if model loaded successfully, False otherwise
        """
        try:
            # Determine model name
            if model_name:
                model_key = f"{source_lang}-{target_lang}"
            else:
                model_key = f"{source_lang}-{target_lang}"
                model_name = self.supported_pairs.get(model_key)
                
            if not model_name:
                # Try reverse pair
                reverse_key = f"{target_lang}-{source_lang}"
                model_name = self.supported_pairs.get(reverse_key)
                if model_name:
                    # Swap source and target for reverse model
                    source_lang, target_lang = target_lang, source_lang
                else:
                    # Try multilingual model as fallback
                    model_name = self.supported_pairs.get("mul-mul")
                    if not model_name:
                        # Try other fallback models
                        fallback_models = [
                            "Helsinki-NLP/opus-mt-en-ROMANCE",  # English to Romance languages
                            "Helsinki-NLP/opus-mt-en-zh",  # English to Chinese (as fallback)
                        ]
                        for fallback_model in fallback_models:
                            try:
                                # Test if model exists by trying to load tokenizer
                                test_tokenizer = MarianTokenizer.from_pretrained(fallback_model)
                                model_name = fallback_model
                                logger.info(f"🔄 Using fallback model: {fallback_model}")
                                break
                            except:
                                continue
                        
                        if not model_name:
                            logger.error(f"❌ No model found for {source_lang} -> {target_lang}")
                            return False
            
            if not model_name:
                logger.error(f"❌ No model found for {source_lang} -> {target_lang}")
                return False
            
            # Check if model is already loaded
            if model_key in self.models:
                logger.info(f"✅ Model {model_key} already loaded")
                return True
            
            logger.info(f"🔄 Loading model: {model_name}")
            start_time = time.time()
            
            # Load tokenizer and model
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
            
            # Move to device
            model = model.to(self.device)
            model.eval()
            
            # Store model info
            self.models[model_key] = {
                "model": model,
                "tokenizer": tokenizer,
                "model_name": model_name,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "loaded_at": datetime.utcnow().isoformat()
            }
            
            load_time = time.time() - start_time
            self.stats["models_loaded"] += 1
            
            logger.info(f"✅ Model {model_key} loaded in {load_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load model {model_key}: {e}")
            return False
    
    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        model_name: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Translate text using MarianMT
        
        Args:
            text: Text to translate
            source_lang: Source language code
            target_lang: Target language code
            model_name: Optional custom model name
            max_length: Maximum sequence length
            
        Returns:
            Dict containing translation result and metadata
        """
        start_time = time.time()
        
        try:
            # Ensure model is loaded
            model_key = f"{source_lang}-{target_lang}"
            if model_key not in self.models:
                success = await self.load_model(source_lang, target_lang, model_name)
                if not success:
                    return {
                        "original_text": text,
                        "translated_text": None,
                        "error": f"Failed to load model for {source_lang} -> {target_lang}",
                        "success": False,
                        "timestamp": datetime.utcnow().isoformat()
                    }
            
            # Get model and tokenizer
            model_info = self.models[model_key]
            model = model_info["model"]
            tokenizer = model_info["tokenizer"]
            
            # Prepare text for translation
            if model_info["model_name"] == "Helsinki-NLP/opus-mt-mul-mul":
                # Use 3-letter language codes for multilingual model
                lang_codes = {
                    "en": "eng", "es": "spa", "fr": "fra", "de": "deu", 
                    "it": "ita", "pt": "por", "ru": "rus", "zh": "zho",
                    "ja": "jpn", "ko": "kor", "ar": "arb"
                }
                target_code = lang_codes.get(target_lang, target_lang)
                input_text = f"{target_code}>> {text}"
            elif model_info["source_lang"] != source_lang:
                # Handle reverse models
                input_text = text
            else:
                input_text = text
            
            # Tokenize input
            inputs = tokenizer(
                [input_text], 
                return_tensors="pt", 
                padding=True, 
                truncation=True,
                max_length=max_length or self.max_length
            ).to(self.device)
            
            # Generate translation
            with torch.no_grad():
                translated = model.generate(
                    **inputs,
                    max_length=max_length or self.max_length,
                    num_beams=4,
                    early_stopping=True,
                    do_sample=False
                )
            
            # Decode result
            translated_texts = tokenizer.batch_decode(translated, skip_special_tokens=True)
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
                "model_name": model_info["model_name"],
                "latency_ms": round(latency_ms, 2),
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            }
            
            # Display result
            self._display_translation(result)
            
            return result
            
        except Exception as e:
            self.stats["failed_translations"] += 1
            logger.error(f"❌ Translation error: {e}")
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
        model_name: Optional[str] = None,
        max_length: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Translate a batch of texts
        
        Args:
            texts: List of texts to translate
            source_lang: Source language code
            target_lang: Target language code
            model_name: Optional custom model name
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
                model_name=model_name,
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
            print(f"🔄 MARIANMT TRANSLATION - {result['timestamp']}")
            print("="*80)
            print(f"📝 Original ({result['source_language']}): {result['original_text']}")
            print(f"🌍 Translated ({result['target_language']}): {result['translated_text']}")
            print(f"⚡ Latency: {result['latency_ms']}ms")
            print(f"🤖 Model: {result['model_name']}")
            print("="*80)
        else:
            print(f"\n❌ Translation failed: {result.get('error', 'Unknown error')}")
    
    def get_loaded_models(self) -> List[Dict[str, Any]]:
        """
        Get information about loaded models
        
        Returns:
            List of loaded model information
        """
        models_info = []
        for model_key, model_info in self.models.items():
            models_info.append({
                "model_key": model_key,
                "model_name": model_info["model_name"],
                "source_lang": model_info["source_lang"],
                "target_lang": model_info["target_lang"],
                "loaded_at": model_info["loaded_at"]
            })
        return models_info
    
    def get_supported_language_pairs(self) -> List[str]:
        """
        Get list of supported language pairs
        
        Returns:
            List of supported language pair codes
        """
        return list(self.supported_pairs.keys())
    
    def unload_model(self, source_lang: str, target_lang: str) -> bool:
        """
        Unload a specific model to free memory
        
        Args:
            source_lang: Source language code
            target_lang: Target language code
            
        Returns:
            bool: True if model unloaded successfully
        """
        model_key = f"{source_lang}-{target_lang}"
        
        if model_key in self.models:
            # Move model to CPU and delete
            model_info = self.models[model_key]
            model_info["model"].cpu()
            del model_info["model"]
            del model_info["tokenizer"]
            del self.models[model_key]
            
            # Force garbage collection
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"✅ Model {model_key} unloaded")
            return True
        
        logger.warning(f"⚠️ Model {model_key} not found")
        return False
    
    def unload_all_models(self) -> None:
        """Unload all models to free memory"""
        for model_key in list(self.models.keys()):
            source_lang, target_lang = model_key.split("-")
            self.unload_model(source_lang, target_lang)
        
        logger.info("✅ All models unloaded")
    
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
            "stats": self.stats.copy(),
            "loaded_models": len(self.models),
            "supported_pairs": len(self.supported_pairs)
        }
    
    def reset_statistics(self) -> None:
        """Reset service statistics"""
        self.stats = {
            "total_translations": 0,
            "successful_translations": 0,
            "failed_translations": 0,
            "average_latency_ms": 0,
            "last_translation_time": None,
            "models_loaded": len(self.models)
        }
        logger.info("MarianMT statistics reset")


# Global service instance
_marianmt_service: Optional[MarianMTService] = None

def get_marianmt_service(device: str = "auto", max_length: int = 512) -> MarianMTService:
    """
    Get the global MarianMT service instance
    
    Args:
        device: Device to run models on
        max_length: Maximum sequence length
        
    Returns:
        MarianMTService: The global service instance
    """
    global _marianmt_service
    if _marianmt_service is None:
        _marianmt_service = MarianMTService(device=device, max_length=max_length)
    return _marianmt_service

async def translate_with_marianmt(
    text: str,
    source_lang: str,
    target_lang: str,
    model_name: Optional[str] = None,
    device: str = "auto"
) -> Dict[str, Any]:
    """
    Convenience function for quick translation
    
    Args:
        text: Text to translate
        source_lang: Source language code
        target_lang: Target language code
        model_name: Optional custom model name
        device: Device to run on
        
    Returns:
        Dict containing translation result
    """
    service = get_marianmt_service(device=device)
    return await service.translate_text(text, source_lang, target_lang, model_name)


# Example usage and testing
async def main():
    """Example usage of MarianMT service"""
    print("🚀 MarianMT Translation Service Example")
    print("="*50)
    
    # Initialize service
    service = get_marianmt_service(device="auto")
    
    # Example translations
    examples = [
        ("Hello, how are you today?", "en", "es"),
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
    
    # Show loaded models
    models = service.get_loaded_models()
    print(f"\n🤖 Loaded models: {len(models)}")
    for model in models:
        print(f"  - {model['model_key']}: {model['model_name']}")


if __name__ == "__main__":
    asyncio.run(main())
