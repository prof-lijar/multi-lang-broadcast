import whisper
import warnings

# Suppress the FP16 warning
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU; using FP32 instead")

model = whisper.load_model("small")      # or "base", "medium", "turbo", etc.
result = model.transcribe("sample.mp3")   # replace with your file
print(result["text"])
