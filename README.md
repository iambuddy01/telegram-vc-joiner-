# Telegram Voice Chat Bot

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/anoop14613742/telegram-vc-joiner-)
[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](CONTRIBUTING.md)

Advanced Telegram voice chat bot with **PyTgCalls 2.2.5**, enhanced audio processing, and **600% volume boost**. Features auto-installing dependencies, multiple account management, and Heroku-ready deployment.

## 🚀 Quick Deploy to Heroku

**One-click deployment** - Click the button above to instantly deploy to Heroku!

Alternatively, follow our [detailed Heroku deployment guide](README_HEROKU.md) for manual setup.

## ✨ Features

### 🎵 Audio & Voice Chat
- **Enhanced audio processing** with up to 600% volume boost
- **PyTgCalls 2.2.5** integration with modern GroupCallFactory API
- **Auto-queue management** with playlist support
- **Pause/Resume functionality** with position tracking
- **Multiple audio formats** support (MP3, WAV, OGG, M4A)
- **Real-time volume control** during playback

### 👥 Account Management
- **Multiple Telegram accounts** support
- **Secure session storage** with encryption options
- **Auto-reconnection** on disconnects
- **Performance monitoring** and statistics

### �️ Technical Excellence
- **Auto-installing dependencies** on first run
- **Modern async/await** patterns throughout
- **Comprehensive error handling** and logging
- **JSON performance optimization** with orjson
- **Memory-efficient** operations
- **Thread-safe** voice chat operations

## 🎯 Special Invitation to Telegram Experts

**Calling all Telegram Bot & API specialists!** We're actively seeking experienced contributors who have expertise in:

### 🔥 Priority Areas for Expert Contributors

- **Telethon Library Experts** - Help optimize our Telegram client implementation
- **Voice Chat Specialists** - Improve audio handling and voice chat functionality
- **TgCalls Developers** - Enhance voice call integration and performance
- **Telegram Bot API Veterans** - Share best practices and advanced patterns
- **Audio Processing Engineers** - Optimize audio streaming and processing
- **Network Protocol Experts** - Improve connection stability and error handling
- **Security Specialists** - Enhance authentication and data protection

## 📋 Requirements

- **Python 3.11+** (recommended for Heroku)
- **Telegram API credentials** (API ID, API Hash)
- **Bot Token** from @BotFather
- **FFmpeg** (automatically installed on Heroku)

## 🚀 Quick Start

### Option 1: Deploy to Heroku (Recommended)

1. **Click the "Deploy to Heroku" button** above
2. **Fill in the environment variables**:
   - `API_ID` - Get from [my.telegram.org](https://my.telegram.org)
   - `API_HASH` - Get from [my.telegram.org](https://my.telegram.org)
   - `BOT_TOKEN` - Get from [@BotFather](https://t.me/BotFather)
   - `OWNER_IDS` - Get your user ID from [@userinfobot](https://t.me/userinfobot)
3. **Deploy** and your bot will be live!

### Option 2: Local Development

```bash
# Clone the repository
git clone https://github.com/anoop14613742/telegram-vc-joiner-.git
cd telegram-vc-joiner-

# Install dependencies (auto-installs on first run)
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Get API_ID & API_HASH from https://my.telegram.org
# Get BOT_TOKEN from @BotFather
# Get OWNER_IDS from @userinfobot

# Run the bot
python main.py
```

## 🎮 Usage

1. **Start the bot**: Send `/start` to your bot on Telegram
2. **Add accounts**: Use "👥 Accounts" menu to add Telegram accounts
3. **Join voice chats**: Use "🎤 Voice Chat" → "🎤 Join Voice Chat"
4. **Play media**: Upload audio files and play with enhanced volume
5. **Control playback**: Use pause/resume/stop controls
6. **Adjust volume**: Real-time volume control up to 600%

## 📁 Project Structure

```
telegram-vc-joiner-/
├── main.py                 # Main bot application
├── requirements.txt        # Python dependencies
├── Procfile               # Heroku process file
├── runtime.txt            # Python version for Heroku
├── Aptfile                # System dependencies for Heroku
├── app.json               # Heroku app configuration
├── .env.example           # Environment variables template
├── README_HEROKU.md       # Detailed Heroku deployment guide
├── logs/                  # Application logs
├── media/                 # Uploaded media files
├── cache/                 # Temporary cache
└── backups/               # Session backups
```

## Contributing

We welcome contributions from everyone! This project is open for contributions and we're excited to work with the community.

### Quick Start for Contributors

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a new branch** for your feature or bug fix
4. **Make your changes** and test them
5. **Submit a pull request** with a clear description

### Ways to Contribute

- 🐛 **Report bugs** - Help us identify and fix issues
- ✨ **Suggest features** - Share ideas for new functionality
- 📝 **Improve documentation** - Help make our docs better
- 🔧 **Submit code** - Fix bugs or add new features
- 🧪 **Add tests** - Help improve our test coverage
- 🎨 **UI/UX improvements** - Enhance user experience

### Development Guidelines

Please read our [Contributing Guidelines](CONTRIBUTING.md) for detailed information about:

- Setting up the development environment
- Coding standards and best practices
- Testing requirements
- Pull request process
- Code review guidelines

### Code of Conduct

This project follows our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you agree to uphold this code. Please report unacceptable behavior to the project maintainers.

### Getting Help

- 📋 **Issues**: Report bugs or request features
- 💬 **Discussions**: Ask questions or share ideas
- 📧 **Email**: Contact maintainers for sensitive issues

### Recognition

Contributors are recognized in our:
- README contributors section
- Release notes
- GitHub contributor graphs

Thank you for helping make this project better! 🙏

## License

This project is open source and available under the [MIT License](LICENSE).