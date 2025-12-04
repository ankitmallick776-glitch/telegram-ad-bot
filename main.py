import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from handlers.watch_ads_handler import start, web_app_data, balance, get_main_keyboard

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing!")

async def main():
    from utils.supabase import db
    await db.init_table()
    print("✅ Cashyads2 Direct WebApp Ready!")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    app.add_handler(MessageHandler(filters.Regex("^(Balance 💳)$"), balance))
    
    async def unknown(update, context):
        await update.message.reply_text("👇 Use the Watch Ads button!", reply_markup=get_main_keyboard())
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    print("🤖 Cashyads2 PERFECT!")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
