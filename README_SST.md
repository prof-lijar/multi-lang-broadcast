# High-Performance Speech-to-Text Streamer

A real-time speech-to-text application using Google's Speech-to-Text API with minimal latency and optimized performance.

## Features

- 🎤 **Real-time microphone streaming** - Continuous audio capture
- ⚡ **Minimal latency** - Streaming recognition with interim results
- 📺 **Live terminal output** - Real-time text display with confidence scores
- 🚀 **High performance** - Multi-threaded processing and optimized audio handling
- 📊 **Performance monitoring** - CPU, memory, and processing metrics
- 🔧 **Configurable** - Adjustable sample rates, chunk sizes, and language settings

## Quick Start

### 1. Setup
```bash
# Run the setup script
python setup_sst.py
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Google Cloud Credentials
Place your Google Cloud service account JSON file as `credentials.json` in the root folder:
```bash
# Copy your downloaded service account JSON file to the root folder
cp /path/to/your/service-account-key.json ./credentials.json
```

Alternatively, you can set the environment variable:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/credentials.json"
```

### 4. Run the Application
```bash
python sst/sst_demo.py
```

## Configuration

### Credentials Setup
The program automatically looks for credentials in this order:
1. `credentials.json` in the root folder (recommended)
2. `GOOGLE_APPLICATION_CREDENTIALS` environment variable
3. Application Default Credentials (if using `gcloud auth`)

**Recommended**: Place your service account JSON file as `credentials.json` in the root folder.

### Audio Settings
- **Sample Rate**: 16000 Hz (optimal for Google Speech-to-Text)
- **Chunk Size**: 1024 samples (balance between latency and performance)
- **Channels**: Mono (1 channel for better performance)
- **Format**: 16-bit PCM

### Language Support
Change the `language_code` parameter in the code:
- `en-US` - English (US)
- `es-ES` - Spanish (Spain)
- `fr-FR` - French (France)
- `de-DE` - German (Germany)
- And many more...

## Performance Optimizations

### Latency Reduction
- **Streaming Recognition**: Uses Google's streaming API for real-time processing
- **Interim Results**: Shows partial results while processing
- **Small Chunk Size**: 1024 samples for minimal buffering delay
- **Queue Management**: Drops old audio if queue is full to maintain low latency

### Performance Features
- **Multi-threading**: Separate threads for audio capture, processing, and display
- **Memory Management**: Bounded queues to prevent memory leaks
- **CPU Monitoring**: Real-time performance metrics
- **Error Handling**: Graceful handling of audio and network issues

## Output Format

```
🎯 Hello world (95.2%)
⏳ This is a test...
🎯 This is a test message (87.3%)
📊 Performance: 15.2 chunks/sec | CPU: 12.3% | Memory: 45.1%
```

- 🎯 **Final results** with confidence scores
- ⏳ **Interim results** (partial/real-time)
- 📊 **Performance metrics** (updated every 5 seconds)

## Troubleshooting

### Audio Issues
- Check microphone permissions
- Verify audio device is working
- Try different chunk sizes if experiencing audio dropouts

### Google Cloud Issues
- Verify `credentials.json` file is valid JSON and in the root folder
- Check API is enabled in Google Cloud Console
- Ensure service account has Speech-to-Text permissions
- Make sure the service account JSON file is properly formatted

### Performance Issues
- Increase chunk size for better stability
- Reduce sample rate if CPU usage is high
- Check network connection for API calls

## Dependencies

- `google-cloud-speech` - Google Speech-to-Text API
- `pyaudio` - Audio capture and playback
- `psutil` - System performance monitoring
- `google-auth` - Google Cloud authentication

## License

This project is open source and available under the MIT License.
