#!/usr/bin/env python3
import logging
import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from handlers.watch_ads_handler import (
    start, web_app_data, balance_menu, bonus, refer, withdraw_menu, 
    process_withdrawal, back_to_balance
)
from handlers.leaderboard_handler import leaderboard, leaderboard_callback

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env")

def main():
    """Main bot - NO DB INIT (manual SQL done)"""
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    
    # Keyboard buttons
    app.add_handler(MessageHandler(filters.Regex("^(Balance|Bonus|Refer|Leaderboard|Withdraw)$"), balance_menu))
    app.add_handler(MessageHandler(filters.Regex("^Watch Ads$"), web_app_data))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(leaderboard_callback, pattern="^leaderboard$"))
    app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(process_withdrawal, pattern="^paytm|upi|bank|paypal|usdt$"))
    app.add_handler(CallbackQueryHandler(back_to_balance, pattern="^back_balance$"))
    
    logger.info("🤖 Cashyads2 LIVE - No DB init!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
