# Speech-to-Text (STT) Service

A high-performance speech-to-text service built with FastAPI and Google Cloud Speech-to-Text API, providing real-time audio transcription capabilities.

## Features

- **Real-time streaming transcription** with minimal latency
- **WebSocket support** for live audio streaming
- **File transcription** for batch processing
- **Multi-language support** with 20+ languages
- **Performance monitoring** with CPU and memory tracking
- **RESTful API** with comprehensive endpoints
- **Web client** for easy testing and demonstration

## API Endpoints

### Core STT Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/stt/stream` | GET | Stream real-time speech-to-text results |
| `/stt/ws` | WebSocket | WebSocket endpoint for live audio streaming |
| `/stt/transcribe-file` | POST | Transcribe audio from base64 encoded data |
| `/stt/stop` | POST | Stop current streaming session |
| `/stt/status` | GET | Get service status and statistics |
| `/stt/reset-stats` | POST | Reset service statistics |
| `/stt/languages` | GET | Get supported languages |

### Request/Response Examples

#### Start Streaming
```bash
curl "http://localhost:8000/stt/stream?language_code=en-US"
```

#### Transcribe Audio File
```bash
curl -X POST "http://localhost:8000/stt/transcribe-file" \
  -H "Content-Type: application/json" \
  -d '{
    "audio_data": "base64_encoded_audio_data",
    "language_code": "en-US",
    "sample_rate": 16000
  }'
```

#### Get Service Status
```bash
curl "http://localhost:8000/stt/status"
```

## WebSocket Usage

Connect to the WebSocket endpoint for real-time streaming:

```javascript
const ws = new WebSocket('ws://localhost:8000/stt/ws');

ws.onopen = function(event) {
    console.log('Connected to STT service');
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'final') {
        console.log('Final transcript:', data.transcript);
    } else if (data.type === 'interim') {
        console.log('Interim transcript:', data.transcript);
    }
};
```

## Supported Languages

The service supports 20+ languages including:

- English (US/UK)
- Spanish (Spain/Mexico)
- French, German, Italian
- Portuguese (Brazil/Portugal)
- Russian, Japanese, Korean
- Chinese (Simplified/Traditional)
- Arabic, Hindi, Thai
- Vietnamese, Burmese, Khmer

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Cloud Setup

1. Create a Google Cloud Project
2. Enable the Speech-to-Text API
3. Create a service account and download the credentials JSON
4. Place the credentials file in the root directory as `credentials.json`

### 3. Run the Service

```bash
python main.py
```

The service will be available at `http://localhost:8000`

## Usage Examples

### Python Client

```python
from stt_client_example import STTClient

client = STTClient("http://localhost:8000")

# Get service status
status = client.get_status()
print(status)

# Transcribe a file
result = client.transcribe_file("audio.wav", "en-US")
print(result)

# Start streaming (WebSocket)
await client.start_websocket_streaming("en-US")
```

### Web Client
also at http://localhost:8000/static/stt_web_client.html

Open `stt_web_client.html` in a web browser to test the WebSocket functionality with a user-friendly interface.

## Configuration

### Environment Variables

- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `DEBUG`: Enable debug mode (default: false)
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to credentials file

### STT Service Parameters

- `sample_rate`: Audio sample rate (default: 16000 Hz)
- `chunk_size`: Audio chunk size (default: 1024)
- `language_code`: Default language (default: en-US)
- `enable_monitoring`: Enable performance monitoring (default: true)

## Performance Features

- **Low latency streaming** with optimized audio processing
- **Debouncing** to prevent rapid-fire updates
- **Queue management** to prevent memory buildup
- **Error handling** with automatic recovery
- **Performance monitoring** with CPU and memory tracking

## Error Handling

The service includes comprehensive error handling:

- **Connection errors**: Automatic reconnection attempts
- **Audio processing errors**: Graceful degradation
- **API errors**: Detailed error messages
- **Resource management**: Automatic cleanup

## Monitoring & Statistics

The service provides detailed statistics:

- Processed audio chunks
- Total transcripts generated
- Average confidence scores
- Error counts and types
- CPU and memory usage
- Processing speed metrics

## Security Considerations

- **CORS enabled** for cross-origin requests
- **Input validation** for all endpoints
- **Resource limits** to prevent abuse
- **Error sanitization** to prevent information leakage

## Troubleshooting

### Common Issues

1. **Audio not detected**: Check microphone permissions
2. **Connection failed**: Verify Google Cloud credentials
3. **Poor transcription quality**: Check audio quality and language settings
4. **High latency**: Adjust chunk size and sample rate

### Debug Mode

Enable debug mode for detailed logging:

```bash
DEBUG=true python main.py
```

## API Documentation

Once the service is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## License

This project is part of the Multi-Language Broadcast system and follows the same licensing terms.
