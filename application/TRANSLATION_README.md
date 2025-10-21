# Live Translation Service

A real-time translation service using Google Cloud Translation API that can handle streaming text input and translate it in real-time.

## Features

- **Real-time Translation**: Translate streaming text input as it arrives
- **Multiple Language Support**: Support for 100+ languages via Google Cloud Translation
- **Language Detection**: Automatically detect the source language
- **Terminal Display**: Real-time translation results displayed in terminal
- **Statistics Tracking**: Monitor translation performance and latency
- **REST API**: Full REST API for integration with other services

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Cloud Setup

1. Create a Google Cloud project
2. Enable the Cloud Translation API
3. Create a service account and download the credentials JSON file
4. Place the `credentials.json` file in the root directory of the project

### 3. Configuration

The service uses the following configuration (can be set via environment variables):

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=credentials.json

# Translation Configuration
DEFAULT_SOURCE_LANGUAGE=en
DEFAULT_TARGET_LANGUAGE=es
TRANSLATION_MODEL=nmt
TRANSLATION_MIME_TYPE=text/plain
```

## Usage

### 1. Start the Service

```bash
python main.py
```

The service will start on `http://localhost:8000` by default.

### 2. Test the Service

Run the test script to see the live translation in action:

```bash
python test_live_translation.py
```

### 3. API Endpoints

#### Translate Single Text
```bash
POST /translate
{
    "text": "Hello, world!",
    "source_language": "en",
    "target_language": "es"
}
```

#### Stream Translation
```bash
POST /translate/stream
{
    "text": "This is a long text that will be streamed word by word",
    "source_language": "en",
    "target_language": "es",
    "batch_size": 3,
    "delay_ms": 200
}
```

#### Get Supported Languages
```bash
GET /translate/languages?target_language=en
```

#### Detect Language
```bash
POST /translate/detect
{
    "text": "Bonjour le monde!"
}
```

#### Get Service Status
```bash
GET /translate/status
```

## Live Translation Features

### Real-time Streaming
The service can process streaming text input and translate it in real-time:

```python
async def text_stream():
    words = ["Hello", "world", "this", "is", "streaming"]
    for word in words:
        yield word + " "
        await asyncio.sleep(0.1)

# Translate streaming text
async for result in service.translate_stream(
    text_stream=text_stream(),
    source_language="en",
    target_language="es"
):
    print(f"Translated: {result['translated_text']}")
```

### Terminal Display
Translations are displayed in the terminal with formatting:

```
================================================================================
🔄 LIVE TRANSLATION - 2024-01-15T10:30:45.123456
================================================================================
📝 Original (en): Hello, how are you today?
🌍 Translated (es): ¡Hola, cómo estás hoy?
⚡ Latency: 245.67ms
🤖 Model: nmt
================================================================================
```

### Statistics Tracking
The service tracks translation statistics:

- Total translations
- Successful translations
- Failed translations
- Average latency
- Last translation time

## Error Handling

The service includes comprehensive error handling:

- **Authentication Errors**: Clear messages for credential issues
- **API Errors**: Proper handling of Google Cloud API errors
- **Network Errors**: Retry logic and graceful degradation
- **Validation Errors**: Input validation and error responses

## Performance

- **Low Latency**: Optimized for real-time translation
- **Batch Processing**: Configurable batch sizes for efficiency
- **Connection Pooling**: Reuses Google Cloud client connections
- **Async Processing**: Non-blocking async operations

## Security

- **Credential Management**: Secure handling of Google Cloud credentials
- **Input Validation**: Validates all input parameters
- **Error Sanitization**: Prevents sensitive information leakage

## Monitoring

The service provides comprehensive monitoring:

- Health check endpoints
- Translation statistics
- Performance metrics
- Error tracking

## Examples

### Basic Translation
```python
from service.translate import get_translation_service

service = get_translation_service()
result = await service.translate_text(
    text="Hello, world!",
    source_language="en",
    target_language="es"
)
print(result["translated_text"])  # "¡Hola, mundo!"
```

### Streaming Translation
```python
async def my_text_stream():
    yield "Hello "
    await asyncio.sleep(0.1)
    yield "world "
    await asyncio.sleep(0.1)
    yield "streaming!"

async for result in service.translate_stream(
    text_stream=my_text_stream(),
    source_language="en",
    target_language="es"
):
    print(f"Translated: {result['translated_text']}")
```

## Troubleshooting

### Common Issues

1. **Credentials not found**
   - Ensure `credentials.json` is in the root directory
   - Check file permissions

2. **API not enabled**
   - Enable Cloud Translation API in Google Cloud Console
   - Verify project ID is correct

3. **Quota exceeded**
   - Check Google Cloud quotas
   - Consider upgrading your plan

4. **Network issues**
   - Check internet connection
   - Verify firewall settings

### Debug Mode

Enable debug logging by setting the environment variable:

```bash
DEBUG=true python main.py
```

## License

This project is part of the Multi-Language Broadcast system.
