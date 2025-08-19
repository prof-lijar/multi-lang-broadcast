# Whisper OpenAI - Real-time Transcription & Translation

A Python application that provides real-time speech transcription and translation using OpenAI's Whisper model and Google Translate.

## Features

- 🎤 **Real-time Transcription**: Live speech-to-text using Whisper
- 🌍 **Live Translation**: Real-time translation between multiple languages
- 🎵 **Audio Streaming**: Continuous audio processing with microphone input
- 📝 **Multiple Languages**: Support for English, Korean, Japanese, Thai, and more
- ⚡ **Fast Processing**: Optimized for real-time performance

## Prerequisites

- **Python Version**: 3.8 or higher (3.9+ recommended)
- **FFmpeg**: Required for audio processing
- **Microphone**: For real-time audio input

## Setup Instructions

### macOS Setup

#### 1. Install Python 3.9+ (if not already installed)

**Option A: Using Homebrew (Recommended)**

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.9
brew install python@3.9

# Verify installation
python3 --version
```

**Option B: Using pyenv**

```bash
# Install pyenv
brew install pyenv

# Add pyenv to your shell
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
echo 'eval "$(pyenv init -)"' >> ~/.zshrc

# Restart your terminal or run
source ~/.zshrc

# Install Python 3.9
pyenv install 3.9.18
pyenv global 3.9.18

# Verify installation
python --version
```

#### 2. Install FFmpeg

```bash
# Using Homebrew
brew install ffmpeg

# Verify installation
ffmpeg -version
```

#### 3. Clone and Setup Project

```bash
# Clone the repository
git clone <your-repo-url>
cd whisper-openai

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Environment Setup (Optional)

```bash
# Create .env file if needed for API keys
touch .env

# Add any required environment variables
echo "OPENAI_API_KEY=your_api_key_here" >> .env
```

### Windows Setup

#### 1. Install Python 3.9+ (if not already installed)

**Option A: Using Windows Store**

1. Open Microsoft Store
2. Search for "Python 3.9"
3. Install the latest version

**Option B: Using pyenv-win**

```cmd
# Install pyenv-win using PowerShell
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"

# Add pyenv to PATH (add to System Environment Variables)
# Add these paths to your PATH:
# %USERPROFILE%\.pyenv\pyenv-win\bin
# %USERPROFILE%\.pyenv\pyenv-win\shims

# Restart your terminal, then install Python 3.9
pyenv install 3.9.18
pyenv global 3.9.18

# Verify installation
python --version
```

#### 2. Install FFmpeg

**Option A: Using Chocolatey**

```cmd
# Install Chocolatey first (run as Administrator)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install FFmpeg
choco install ffmpeg

# Verify installation
ffmpeg -version
```

**Option B: Manual Installation**

1. Download FFmpeg from https://ffmpeg.org/download.html#build-windows
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your system PATH
4. Restart your terminal and verify: `ffmpeg -version`

#### 3. Clone and Setup Project

```cmd
# Clone the repository
git clone <your-repo-url>
cd whisper-openai

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

#### 4. Environment Setup (Optional)

```cmd
# Create .env file if needed for API keys
echo OPENAI_API_KEY=your_api_key_here > .env
```

## Usage

### 1. Real-time Transcription

```bash
# Start real-time transcription
python stream_transcribe.py
```

**Features:**

- Select from multiple languages (English, Korean, Japanese, Thai)
- Real-time speech-to-text conversion
- Press Ctrl+C to stop

### 2. Live Translation

```bash
# Start live translation
python live_translate.py
```

**Features:**

- Multiple language pairs (English↔Korean, English↔Spanish, etc.)
- Real-time transcription and translation
- Translation caching for better performance
- Press Ctrl+C to stop

### 3. File Transcription

```bash
# Transcribe an audio file
python transcribe.py
```

**Note:** Edit `transcribe.py` to specify your audio file path.

## Dependencies

- `openai-whisper`: OpenAI's Whisper speech recognition model
- `pyaudio`: Audio I/O library for microphone input
- `numpy`: Numerical computing library
- `googletrans==4.0.0rc1`: Google Translate API wrapper

## Troubleshooting

### Common Issues

**1. PyAudio Installation Issues (Windows)**

```cmd
# If pip install pyaudio fails, try:
pip install pipwin
pipwin install pyaudio
```

**2. FFmpeg Not Found**

- Ensure FFmpeg is installed and added to PATH
- Restart your terminal after installation

**3. Microphone Access Issues**

- Check system microphone permissions
- Ensure microphone is not being used by other applications

**4. Memory Issues with Large Models**

- Use smaller models like "base" or "small" instead of "medium" or "large"
- Close other applications to free up memory

### Performance Tips

- Use "base" model for faster processing
- Ensure good microphone quality
- Close unnecessary applications
- Use wired headphones for better audio input

## Project Structure

```
whisper-openai/
├── stream_transcribe.py    # Real-time transcription
├── live_translate.py       # Live translation
├── transcribe.py          # File transcription
├── live_translate_fast.py # Fast translation variant
├── requirements.txt       # Python dependencies
├── sample.mp3            # Sample audio file
└── README.md             # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the [MIT License](LICENSE).

## Support

If you encounter any issues or have questions, please:

1. Check the troubleshooting section above
2. Search existing issues
3. Create a new issue with detailed information about your problem
