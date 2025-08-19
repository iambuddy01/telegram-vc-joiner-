# Telegram VC Joiner Bot

A Python bot that automatically joins Telegram voice chats and plays audio content.

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

Feel free to submit issues and enhancement requests!

## License

This project is open source and available under the [MIT License](LICENSE).