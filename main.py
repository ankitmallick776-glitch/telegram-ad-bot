import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.watch_ads_handler import start, watch_ads, web_app_data
from utils.db import init_db

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from @BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your bot token

async def main():
    """Start the bot"""
    await init_db()
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^(Watch Ads 💰)$"), watch_ads))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # Handle other buttons ( Balance, Bonus, etc. - add later)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: u.message.reply_text(
        "Use the buttons below 👇", reply_markup=watch_ads_handler.get_main_keyboard()
    )))
    
    print("🤖 Bot started! Press Ctrl+C to stop.")
    await application.run_polling(allowed_updates=["message", "web_app_data"])

if __name__ == "__main__":
    asyncio.run(main())
