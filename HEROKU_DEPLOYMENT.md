# Heroku Configuration for Telegram VC Bot

## Environment Variables Required

Set these environment variables in your Heroku app settings:

### Required Variables:
- `API_ID`: Your Telegram API ID (get from https://my.telegram.org)
- `API_HASH`: Your Telegram API Hash (get from https://my.telegram.org)
- `BOT_TOKEN`: Your Telegram Bot Token (get from @BotFather)
- `OWNER_IDS`: Comma-separated list of authorized user IDs (e.g., "123456789,987654321")

### Optional Variables:
- `JOIN_DELAY`: Delay between joins in seconds (default: 2)
- `LEAVE_DELAY`: Delay between leaves in seconds (default: 1)
- `MAX_VOLUME`: Maximum volume level 1-600 (default: 600)
- `VOICE_JOIN_DELAY`: Delay before joining voice chat (default: 3)
- `MAX_ACCOUNTS`: Maximum number of accounts (default: 50)
- `FFMPEG_PATH`: Path to FFmpeg binary (default: "ffmpeg")

## Heroku Buildpacks Required:

1. heroku/python
2. heroku-community/apt

## Deployment Steps:

1. Create a new Heroku app:
   ```bash
   heroku create your-vc-bot-name
   ```

2. Add buildpacks:
   ```bash
   heroku buildpacks:add heroku/python
   heroku buildpacks:add heroku-community/apt
   ```

3. Set environment variables:
   ```bash
   heroku config:set API_ID=your_api_id
   heroku config:set API_HASH=your_api_hash
   heroku config:set BOT_TOKEN=your_bot_token
   heroku config:set OWNER_IDS=your_user_id
   ```

4. Deploy:
   ```bash
   git add .
   git commit -m "Deploy VC bot to Heroku"
   git push heroku main
   ```

5. Scale the worker:
   ```bash
   heroku ps:scale web=1
   ```

## FFmpeg Installation

FFmpeg will be automatically installed via the Aptfile for audio processing.

## Notes:

- The bot will auto-install all Python dependencies on startup
- Persistent storage is limited on Heroku - user sessions may be lost on dyno restart
- For production use, consider upgrading to a paid dyno for better reliability
- Monitor logs with: `heroku logs --tail`
