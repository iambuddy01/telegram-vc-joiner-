#!/usr/bin/env python3
"""
Simple web server wrapper for Heroku deployment
This starts both the web server (for PORT binding) and the Telegram bot
"""

import os
import sys
import asyncio
import logging
from aiohttp import web

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint for Heroku"""
    return web.Response(text="✅ Telegram VC Bot is running!", status=200)

async def start_web_server():
    """Start the web server for Heroku PORT binding"""
    port = int(os.getenv('PORT', 8000))
    
    # Create aiohttp app
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/status', health_check)
    
    # Start web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    logger.info(f"🌐 Web server started on port {port}")
    return runner

async def start_telegram_bot():
    """Import and start the main bot"""
    try:
        # Import the main bot components
        from main import dp, bot, load_users
        
        await load_users()
        logger.info("🤖 Starting Telegram bot...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main function - starts both web server and bot"""
    logger.info("🚀 Starting Telegram VC Bot on Heroku...")
    
    # Start web server first (required for Heroku)
    runner = await start_web_server()
    
    # Start bot in background task
    bot_task = asyncio.create_task(start_telegram_bot())
    
    try:
        # Keep both running
        await bot_task
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Shutting down...")
        await runner.cleanup()
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
