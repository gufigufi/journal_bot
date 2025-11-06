import asyncio
import logging
import os
from dotenv import load_dotenv
from aiohttp import web
from database import Database
from bot import TelegramBot
from notifications import NotificationService
from webhook import create_webhook_app


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    load_dotenv()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    db_path = os.getenv('DATABASE_PATH', './data/grades.db')
    
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not set in environment")
        return
    
    db = Database(db_path)
    await db.init_db()
    logger.info("Database initialized")
    
    telegram_bot = TelegramBot(bot_token, db)
    notification_service = NotificationService(db, telegram_bot)
    
    webhook_app = await create_webhook_app(db, notification_service)
    
    runner = web.AppRunner(webhook_app)
    await runner.setup()
    
    webhook_port = int(os.getenv('WEBHOOK_PORT', 8080))
    site = web.TCPSite(runner, '0.0.0.0', webhook_port)
    await site.start()
    
    logger.info(f"Webhook server started on port {webhook_port}")
    
    try:
        await telegram_bot.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await telegram_bot.stop()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
