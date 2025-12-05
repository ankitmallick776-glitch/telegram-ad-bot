import asyncio
import logging
import os
import signal
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from handlers.watch_ads_handler import (
    start, start_referral, web_app_data, balance, bonus, refer,
    withdraw_menu, process_withdrawal, back_to_balance, get_main_keyboard
)
from handlers.broadcast_handler import broadcast_handler, cleanup_handler
from handlers.leaderboard_handler import leaderboard_handler

load_dotenv()
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing!")

class CashyBot:
    def __init__(self):
        self.app = None

    async def run(self):
        from utils.supabase import db
        await db.init_table()
        print("✅ Cashyads2 Ready!")
        
        self.app = Application.builder().token(BOT_TOKEN).build()
        
        # ⚠️ CRITICAL: REFERRAL HANDLER FIRST
        self.app.add_handler(CommandHandler("start", start_referral, filters.Regex(".*"), has_args=True))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.Regex("^(Balance 💳)$"), balance))
        self.app.add_handler(MessageHandler(filters.Regex("^(Bonus 🎁)$"), bonus))
        self.app.add_handler(MessageHandler(filters.Regex("^(Refer and Earn 👥)$"), refer))
        self.app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
        
        # Callback handlers
        self.app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw$"))
        self.app.add_handler(CallbackQueryHandler(process_withdrawal, pattern="^withdraw_"))
        self.app.add_handler(CallbackQueryHandler(back_to_balance, pattern="^back_balance$"))
        
        # Leaderboard
        self.app.add_handler(leaderboard_handler)
        
        # ADMIN COMMANDS
        self.app.add_handler(broadcast_handler)
        self.app.add_handler(cleanup_handler)
        
        # Generic /start (no args) - LAST
        self.app.add_handler(CommandHandler("start", start))
        
        # Unknown handler
        async def unknown(update: Update, context):
            await update.message.reply_text("👇 <b>Use the buttons!</b>", reply_markup=get_main_keyboard(), parse_mode='HTML')
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
        
        print("🤖 Cashyads2 FULLY LIVE! (Broadcast + Cleanup + HTML)")
        
        # Start bot
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)
        
        print("🚀 Bot polling started - Press Ctrl+C to stop")
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
    
    async def stop(self):
        print("🔄 Stopping...")
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        print("✅ Clean shutdown complete!")

async def main():
    bot = CashyBot()
    try:
        await bot.run()
    except KeyboardInterrupt:
        print("🛑 Keyboard interrupt")
    finally:
        await bot.stop()
        print("👋 Cashyads2 offline - Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())
