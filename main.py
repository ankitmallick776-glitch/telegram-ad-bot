import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.watch_ads_handler import start, watch_ads, web_app_data, balance, get_main_keyboard
from utils.supabase import db

load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file")

async def main():
    """Start the bot"""
    # Initialize Supabase
    await db.init_table()
    print("✅ Supabase connected and table ready!")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^(Watch Ads 💰)$"), watch_ads))
    application.add_handler(MessageHandler(filters.Regex("^(Balance 💳)$"), balance))
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # Handle other buttons - FIXED LAMBDA
    async def handle_unknown(update, context):
        await update.message.reply_text(
            "👇 Use the buttons below!", 
            reply_markup=get_main_keyboard()
        )
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_unknown))
    
    print("🤖 Bot started! Press Ctrl+C to stop.")
    
    # FIXED: Use proper polling method
    await application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    try:
        # FIXED: Use nest_asyncio for VPS environments
        import nest_asyncio
        nest_asyncio.apply()
        
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
