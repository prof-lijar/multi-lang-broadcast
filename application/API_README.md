# Multi-Language Broadcast API Documentation

## Overview

The Multi-Language Broadcast API is a FastAPI-based service that provides real-time speech-to-text, text-to-speech, translation, and dual audio output capabilities. This API enables live translation and multi-language broadcasting with support for multiple languages and audio devices.

## Base Information

- **API Version**: 1.0.0
- **Base URL**: `http://localhost:8000` (default)
- **Documentation**: `/docs` (Swagger UI)
- **Alternative Docs**: `/redoc` (ReDoc)

## Authentication

Currently, no authentication is required. All endpoints are publicly accessible.

## Response Format

All API responses follow a consistent format:

```json
{
  "status": "success|error",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": { ... },
  "message": "Optional message"
}
```

## API Endpoints

### Health & Status

#### GET `/`

**Description**: Root endpoint with basic API information

**Response**:

```json
{
  "message": "Multi-Language Broadcast API",
  "version": "1.0.0",
  "status": "running",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "docs": "/docs"
}
```

#### GET `/health`

**Description**: Basic health check for monitoring and load balancers

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "service": "multi-lang-broadcast",
  "version": "1.0.0"
}
```

#### GET `/health/detailed`

**Description**: Detailed health check with system information

**Response**:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "service": "multi-lang-broadcast",
  "version": "1.0.0",
  "environment": "development",
  "python_version": "3.x.x",
  "uptime": "N/A"
}
```

### Audio Output Management

#### GET `/audio-output-devices`

**Description**: Get list of available audio output devices and their status

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "devices": [...],
    "active_devices": [...]
  }
}
```

#### GET `/audio-output-devices/{card_id}`

**Description**: Get detailed information about a specific audio device

**Parameters**:

- `card_id` (int): Audio device card ID

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "card_id": 0,
    "device_id": "hw:0,0",
    "name": "Built-in Audio",
    "description": "Built-in Audio Analog Stereo",
    "device_type": "OUTPUT",
    "is_active": true,
    "volume": 75,
    "is_muted": false
  }
}
```

#### POST `/audio-output/assign-speakers`

**Description**: Assign speakers for dual audio output

**Request Body**:

```json
{
  "speaker1": {
    "language": "en-US",
    "device_id": "hw:0,0",
    "device_name": "Speaker 1"
  },
  "speaker2": {
    "language": "es-ES",
    "device_id": "hw:0,1",
    "device_name": "Speaker 2"
  }
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Speaker assignments updated",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "speaker1": { ... },
    "speaker2": { ... }
  }
}
```

#### POST `/audio-output/test`

**Description**: Test dual audio output with assigned speakers using test_audio.wav

**Request Body**:

```json
{
  "speaker1": {
    "language": "en-US",
    "device_id": "hw:0,0",
    "device_name": "Speaker 1"
  },
  "speaker2": {
    "language": "es-ES",
    "device_id": "hw:0,1",
    "device_name": "Speaker 2"
  },
  "test_text": "Hello, this is a test of dual speaker audio output."
}
```

#### POST `/audio-output/stop`

**Description**: Stop dual audio playback

**Response**:

```json
{
  "status": "success",
  "message": "Dual audio playback stopped",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### GET `/audio-output/status`

**Description**: Get audio output service status

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "is_dual_playing": false,
    "speaker1_assignment": {
      "language": "en-US",
      "device_id": "hw:0,0",
      "device_name": "Speaker 1"
    },
    "speaker2_assignment": {
      "language": "es-ES",
      "device_id": "hw:0,1",
      "device_name": "Speaker 2"
    }
  }
}
```

#### POST `/audio-output/test-simple`

**Description**: Test dual audio with simple tones

**Response**:

```json
{
  "status": "success",
  "message": "Simple dual audio test started",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### Translation Services

#### POST `/translate`

**Description**: Translate a single text string

**Request Body**:

```json
{
  "text": "Hello, how are you?",
  "source_language": "en",
  "target_language": "es",
  "model": "base",
  "mime_type": "text/plain"
}
```

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "translated_text": "Hola, ¿cómo estás?",
    "source_language": "en",
    "target_language": "es",
    "confidence": 0.95
  }
}
```

#### POST `/translate/stream`

**Description**: Translate streaming text input in real-time

**Request Body**:

```json
{
  "text": "This is a long text that will be streamed",
  "source_language": "en",
  "target_language": "es",
  "model": "base",
  "mime_type": "text/plain",
  "batch_size": 1,
  "delay_ms": 100
}
```

**Response**: Server-Sent Events stream with translation results

#### GET `/translate/languages`

**Description**: Get list of supported languages for translation

**Query Parameters**:

- `target_language` (string, optional): Target language code (default: "en")

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "languages": [
      {"code": "en", "name": "English"},
      {"code": "es", "name": "Spanish"},
      ...
    ],
    "count": 100
  }
}
```

#### POST `/translate/detect`

**Description**: Detect the language of the input text

**Request Body**:

```json
{
  "text": "Hola, ¿cómo estás?"
}
```

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "language": "es",
    "confidence": 0.98
  }
}
```

#### GET `/translate/status`

**Description**: Get translation service status and statistics

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "is_initialized": true,
    "total_translations": 150,
    "successful_translations": 148,
    "failed_translations": 2,
    "average_response_time": 0.5
  }
}
```

#### POST `/translate/reset-stats`

**Description**: Reset translation service statistics

**Response**:

```json
{
  "status": "success",
  "message": "Translation statistics reset",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### Speech-to-Text (STT) Services

#### POST `/stt/transcribe-file`

**Description**: Transcribe audio from base64 encoded audio data

**Request Body**:

```json
{
  "audio_data": "base64_encoded_audio_data",
  "language_code": "en-US",
  "sample_rate": 16000
}
```

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "transcript": "Hello, this is a test transcription",
    "confidence": 0.95,
    "language_code": "en-US",
    "duration": 2.5
  }
}
```

#### GET `/stt/stream`

**Description**: Stream real-time speech-to-text results

**Query Parameters**:

- `language_code` (string, optional): Language code for transcription (default: "en-US")

**Response**: Server-Sent Events stream with transcription results

#### POST `/stt/stop`

**Description**: Stop the current speech-to-text streaming

**Response**:

```json
{
  "status": "success",
  "message": "Speech-to-text streaming stopped",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### POST `/stt/restart`

**Description**: Restart the speech-to-text streaming if it gets stuck

**Response**:

```json
{
  "status": "success",
  "message": "Speech-to-text streaming restarted",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### GET `/stt/status`

**Description**: Get STT service status and statistics

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "is_initialized": true,
    "is_streaming": false,
    "total_transcriptions": 75,
    "successful_transcriptions": 73,
    "failed_transcriptions": 2,
    "average_response_time": 0.3
  }
}
```

#### POST `/stt/reset-stats`

**Description**: Reset STT service statistics

**Response**:

```json
{
  "status": "success",
  "message": "STT statistics reset",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### GET `/stt/languages`

**Description**: Get list of supported languages for speech-to-text

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "languages": [
      {"code": "en-US", "name": "English (US)"},
      {"code": "en-GB", "name": "English (UK)"},
      {"code": "es-ES", "name": "Spanish (Spain)"},
      ...
    ],
    "count": 20
  }
}
```

#### WebSocket `/stt/ws`

**Description**: WebSocket endpoint for real-time speech-to-text streaming

**Connection**: WebSocket connection for real-time audio processing

**Message Format**:

- **Audio Data**: Send binary audio data
- **Text Messages**: JSON format for configuration
  ```json
  {
    "type": "language",
    "language": "en-US"
  }
  ```

### Text-to-Speech (TTS) Services

#### POST `/tts/speak`

**Description**: Convert text to speech and play it immediately

**Request Body**:

```json
{
  "text": "Hello, this is a test of text-to-speech",
  "language_code": "en-US",
  "voice_gender": "NEUTRAL",
  "play_audio": true,
  "cleanup": true
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Text converted to speech and played",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "text": "Hello, this is a test of text-to-speech",
    "language_code": "en-US",
    "voice_gender": "NEUTRAL",
    "played": true
  }
}
```

#### POST `/tts/generate-file`

**Description**: Convert text to speech and return audio file path

**Request Body**:

```json
{
  "text": "Hello, this is a test of text-to-speech",
  "language_code": "en-US",
  "voice_gender": "NEUTRAL",
  "filename": "output.wav"
}
```

**Response**:

```json
{
  "status": "success",
  "message": "Text converted to speech file",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "text": "Hello, this is a test of text-to-speech",
    "language_code": "en-US",
    "voice_gender": "NEUTRAL",
    "audio_file": "/path/to/output.wav"
  }
}
```

#### GET `/tts/status`

**Description**: Get TTS service status and statistics

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "is_initialized": true,
    "total_speeches": 50,
    "successful_speeches": 48,
    "failed_speeches": 2,
    "average_response_time": 1.2
  }
}
```

#### POST `/tts/reset-stats`

**Description**: Reset TTS service statistics

**Response**:

```json
{
  "status": "success",
  "message": "TTS statistics reset",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### GET `/tts/languages`

**Description**: Get list of supported languages for text-to-speech

**Response**:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "languages": [
      {"code": "en-US", "name": "English (US)"},
      {"code": "en-GB", "name": "English (UK)"},
      {"code": "es-ES", "name": "Spanish (Spain)"},
      ...
    ],
    "count": 50
  }
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200**: Success
- **400**: Bad Request (invalid parameters)
- **404**: Not Found (resource not found)
- **500**: Internal Server Error
- **503**: Service Unavailable (service not initialized)

Error responses follow this format:

```json
{
  "detail": "Error description",
  "status_code": 400
}
```

## WebSocket Usage

For real-time audio processing, use the WebSocket endpoint `/stt/ws`:

```javascript
const ws = new WebSocket("ws://localhost:8000/stt/ws");

ws.onopen = function () {
  console.log("WebSocket connected");
};

ws.onmessage = function (event) {
  const data = JSON.parse(event.data);
  console.log("Transcription result:", data);
};

// Send audio data
ws.send(audioBuffer);

// Send configuration
ws.send(
  JSON.stringify({
    type: "language",
    language: "en-US",
  })
);
```

## Server-Sent Events (SSE)

For streaming responses, use Server-Sent Events:

```javascript
const eventSource = new EventSource("/stt/stream?language_code=en-US");

eventSource.onmessage = function (event) {
  const data = JSON.parse(event.data);
  console.log("Streaming result:", data);
};
```

## Configuration

The API can be configured using environment variables:

- `HOST`: Server host (default: "0.0.0.0")
- `PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (default: "false")
- `ENVIRONMENT`: Environment name (default: "development")

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for production use.

## CORS

CORS is configured to allow all origins (`*`). For production, configure specific allowed origins.

## Static Files

Static files are served from the current directory under `/static/` path.

## Examples

### Complete Translation Workflow

1. **Detect Language**:

   ```bash
   curl -X POST "http://localhost:8000/translate/detect" \
        -H "Content-Type: application/json" \
        -d '{"text": "Hola, ¿cómo estás?"}'
   ```

2. **Translate Text**:

   ```bash
   curl -X POST "http://localhost:8000/translate" \
        -H "Content-Type: application/json" \
        -d '{"text": "Hello, how are you?", "source_language": "en", "target_language": "es"}'
   ```

3. **Convert to Speech**:
   ```bash
   curl -X POST "http://localhost:8000/tts/speak" \
        -H "Content-Type: application/json" \
        -d '{"text": "Hola, ¿cómo estás?", "language_code": "es-ES"}'
   ```

### Audio Device Management

1. **List Audio Devices**:

   ```bash
   curl -X GET "http://localhost:8000/audio-output-devices"
   ```

2. **Assign Speakers**:

   ```bash
   curl -X POST "http://localhost:8000/audio-output/assign-speakers" \
        -H "Content-Type: application/json" \
        -d '{
          "speaker1": {"language": "en-US", "device_id": "hw:0,0", "device_name": "Speaker 1"},
          "speaker2": {"language": "es-ES", "device_id": "hw:0,1", "device_name": "Speaker 2"}
        }'
   ```

3. **Test Dual Audio**:
   ```bash
   curl -X POST "http://localhost:8000/audio-output/test" \
        -H "Content-Type: application/json" \
        -d '{
          "speaker1": {"language": "en-US", "device_id": "hw:0,0", "device_name": "Speaker 1"},
          "speaker2": {"language": "es-ES", "device_id": "hw:0,1", "device_name": "Speaker 2"}
        }'
   ```

## Support

For issues and questions, please refer to the main project documentation or create an issue in the project repository.
