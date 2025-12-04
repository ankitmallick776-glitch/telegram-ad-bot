import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.watch_ads_handler import (
    start, web_app_data, balance, bonus, refer, 
    withdraw_menu, process_withdrawal, back_to_balance, get_main_keyboard
)

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Message handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^(Balance 💳)$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^(Bonus 🎁)$"), bonus))
    app.add_handler(MessageHandler(filters.Regex("^(Refer and Earn 👥)$"), refer))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(process_withdrawal, pattern="^withdraw_"))
    app.add_handler(CallbackQueryHandler(back_to_balance, pattern="^back_balance$"))
    
    # Unknown handler
    async def unknown(update, context):
        await update.message.reply_text("👇 Use the buttons!", reply_markup=get_main_keyboard())
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    print("🤖 Cashyads2 LIVE!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import asyncio
    
    async def init_db():
        from utils.supabase import db
        await db.init_table()
        print("✅ Cashyads2 Ready!")
    
    # Initialize DB only
    asyncio.run(init_db())
    
    # Start bot (handles its own event loop)
    main()
