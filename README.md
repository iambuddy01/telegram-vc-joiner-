# Telegram VC Joiner Bot

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](https://choosealicense.com/licenses/mit/)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Contributions Welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg?style=flat)](CONTRIBUTING.md)
[![Code of Conduct](https://img.shields.io/badge/code%20of-conduct-ff69b4.svg?style=flat)](CODE_OF_CONDUCT.md)

A Python bot that automatically joins Telegram voice chats and plays audio content. This project is **open for contributions** and welcomes developers of all skill levels!

> 🚀 **Looking for contributors!** Whether you're a beginner or experienced developer, there are many ways to contribute to this project.

## Features

- Automatically joins Telegram voice chats
- Plays audio files in voice chats
- Imports and manages chat invitations
- Creates silence audio for testing
- Comprehensive logging system
- Media processing capabilities

## Files Structure

- `main.py` - Main bot application
- `import_invite_chat.py` - Handles chat invitation imports
- `create_silence.py` - Generates silence audio files
- `silence.mp3` - Default silence audio file
- `requirements.txt` - Python dependencies
- `.env` - Environment configuration (not included in repo)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/anoop14613742/telegram-vc-joiner-.git
cd telegram-vc-joiner-
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your configuration:
```
# Add your environment variables here
```

4. Run the bot:
```bash
python main.py
```

## Requirements

- Python 3.7+
- Telegram API credentials
- Required Python packages (see requirements.txt)

## Directories

- `backups/` - Backup files
- `cache/` - Temporary cache files
- `logs/` - Application logs
- `media/` - Media files
- `media/processed/` - Processed media files

## Usage

1. Configure your Telegram API credentials in the `.env` file
2. Run the main script to start the bot
3. Use the import script to manage chat invitations
4. The bot will automatically join and participate in voice chats

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