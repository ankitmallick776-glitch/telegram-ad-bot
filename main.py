import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from handlers.watch_ads_handler import (
    start, start_referral, web_app_data, balance, bonus, refer,
    withdraw_menu, process_withdrawal, back_to_balance, back_methods, confirm_withdrawal, 
    handle_payment_details, get_main_keyboard
)
from handlers.broadcast_handler import broadcast_handler, cleanup_handler
from handlers.extra_handler import extra_handler

load_dotenv()
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing!")

async def main():
    from utils.supabase import db
    await db.init_table()
    print("✅ Cashyads2 Ready!")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # ⚠️ CRITICAL: REFERRAL HANDLER FIRST
    app.add_handler(CommandHandler("start", start_referral, filters.Regex(".*"), has_args=True))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.Regex("^(Balance 💳)$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^(Bonus 🎁)$"), bonus))
    app.add_handler(MessageHandler(filters.Regex("^(Refer and Earn 👥)$"), refer))
    app.add_handler(MessageHandler(filters.Regex("^(Extra ➡️)$"), extra_handler.callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # Payment details handler (captures user text during withdrawal)
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(Watch Ads 💰|Balance 💳|Bonus 🎁|Refer and Earn 👥|Extra ➡️)$"),
        handle_payment_details
    ))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(process_withdrawal, pattern="^withdraw_"))
    app.add_handler(CallbackQueryHandler(confirm_withdrawal, pattern="^confirm_withdraw_"))
    app.add_handler(CallbackQueryHandler(back_methods, pattern="^back_methods$"))
    app.add_handler(CallbackQueryHandler(back_to_balance, pattern="^back_balance$"))
    
    # ADMIN COMMANDS
    app.add_handler(broadcast_handler)
    app.add_handler(cleanup_handler)
    
    # Generic /start (no args) - LAST
    app.add_handler(CommandHandler("start", start))
    
    async def unknown(update: Update, context):
        await update.message.reply_text("👇 <b>Use the buttons!</b>", reply_markup=get_main_keyboard(), parse_mode='HTML')
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    print("🤖 Cashyads2 FULLY LIVE! (Background + Smart Cleanup + Unlimited Users)")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
