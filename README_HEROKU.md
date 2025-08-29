# 🚀 Heroku Deployment Guide for Telegram VC Bot

## Quick Start

1. **Fork/Clone this repository** to your GitHub account
2. **Create a Heroku account** at [heroku.com](https://heroku.com)
3. **Install Heroku CLI** from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)

## Step-by-Step Deployment

### 1. Get Required Credentials

#### Telegram API Credentials
1. Go to [my.telegram.org](https://my.telegram.org)
2. Log in with your phone number
3. Go to **API Development Tools**
4. Create a new application
5. Note down your **API ID** and **API Hash**

#### Bot Token
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot with `/newbot`
3. Note down your **Bot Token**

#### Your User ID
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. Note down your **User ID**

### 2. Deploy to Heroku

#### Option A: Deploy Button (Easiest)
[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/anoop14613742/telegram-vc-joiner-)

#### Option B: Manual Deployment

```bash
# Clone your repository
git clone https://github.com/anoop14613742/telegram-vc-joiner-.git
cd telegram-vc-joiner-

# Login to Heroku
heroku login

# Create a new Heroku app
heroku create your-vc-bot-name

# Add buildpacks
heroku buildpacks:add heroku/python
heroku buildpacks:add heroku-community/apt

# Set environment variables (IMPORTANT: No quotes around values)
heroku config:set API_ID=your_api_id_here
heroku config:set API_HASH=your_api_hash_here
heroku config:set BOT_TOKEN=your_bot_token_here
heroku config:set OWNER_IDS="your_user_id_here,another_user_id"

# Deploy
git push heroku main

# Scale the worker
heroku ps:scale web=1
```

### 3. Environment Variables

Set these in your Heroku app dashboard under **Settings > Config Vars**:

| Variable | Description | Example |
|----------|-------------|---------|
| `API_ID` | Telegram API ID | `12345678` |
| `API_HASH` | Telegram API Hash | `abcdef1234567890` |
| `BOT_TOKEN` | Bot token from BotFather | `123456:ABC-DEF...` |
| `OWNER_IDS` | Your Telegram User ID | `987654321` |

#### Optional Variables:
| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_VOLUME` | `600` | Maximum volume (1-600%) |
| `JOIN_DELAY` | `2` | Delay between joins (seconds) |
| `LEAVE_DELAY` | `1` | Delay between leaves (seconds) |
| `MAX_ACCOUNTS` | `50` | Maximum number of accounts |

### 4. Using the Bot

1. **Start the bot**: Send `/start` to your bot
2. **Add accounts**: Use the "👥 Accounts" menu to add Telegram accounts
3. **Join voice chats**: Use "🎤 Voice Chat" → "🎤 Join Voice Chat"
4. **Play media**: Use "🎵 Play Audio" or "🎬 Play Video"

## Features

✅ **Auto-installing dependencies**
✅ **Modern PyTgCalls 2.2.5 support**
✅ **Enhanced audio processing with 600% volume boost**
✅ **Multiple account management**
✅ **Queue management**
✅ **Performance monitoring**
✅ **Automatic reconnection**

## Troubleshooting

### Common Issues

1. **Bot not responding**
   - Check logs: `heroku logs --tail`
   - Ensure all environment variables are set correctly

2. **FFmpeg errors**
   - FFmpeg is automatically installed via Aptfile
   - Check if the app is using the correct buildpacks

3. **Voice chat join failures**
   - Ensure the account has permission to join the voice chat
   - Check if there's an active voice chat in the target group

4. **Session issues**
   - User sessions may be lost on dyno restart (Heroku limitation)
   - Re-add accounts if needed

### Monitoring

```bash
# View logs
heroku logs --tail

# Check app status
heroku ps

# Restart app
heroku restart

# Scale workers
heroku ps:scale web=1
```

## Limitations on Heroku

- **Ephemeral filesystem**: User sessions may be lost on dyno restart
- **30-second request timeout**: Long operations may timeout
- **Sleep mode**: Free dynos sleep after 30 minutes of inactivity

## Upgrading

For better reliability, consider upgrading to a paid Heroku plan:
- **Hobby**: $7/month - No sleeping, SSL certificates
- **Standard**: $25/month - Better performance, autoscaling

## Support

If you encounter issues:
1. Check the logs first: `heroku logs --tail`
2. Ensure all environment variables are correctly set
3. Verify that your Telegram credentials are valid
4. Check if the target voice chat exists and is active

## Security Notes

- Never commit your `.env` file or session files to Git
- Use environment variables for all sensitive data
- Regularly rotate your bot token if compromised
- Only authorize trusted users in `OWNER_IDS`
