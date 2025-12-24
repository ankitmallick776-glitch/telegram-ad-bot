import asyncio
import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.error import BadRequest

# Import all handlers
from handlers.watch_ads_handler import (
    start, start_referral, web_app_data, balance, bonus, refer,
    withdraw_menu, process_withdrawal, confirm_withdrawal,
    handle_payment_details, back_to_balance, back_methods,
    get_main_keyboard
)
from handlers.broadcast_handler import broadcast_handler, cleanup_handler
from handlers.extra_handler import extra_handler
from handlers.tasks_handler import tasks_handler, code_command, code_submit

load_dotenv()
logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN missing!")

async def error_handler(update: Update, context):
    """Log errors with full details"""
    logging.error(f"Update {update} caused error {context.error}")
    if isinstance(context.error, BadRequest):
        logging.error(f"BadRequest: {context.error}")

async def unknown(update: Update, context):
    """Handle unknown commands"""
    await update.message.reply_text(
        "👇 Use the buttons!",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def main():
    from utils.supabase import db
    await db.init_table()
    print("✅ Cashyads2 Ready!")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    
    # ============================================
    # COMMAND HANDLERS (FIRST)
    # ============================================
    app.add_handler(CommandHandler("start", start_referral, filters.Regex(".*"), has_args=True))
    app.add_handler(code_command)
    app.add_handler(CommandHandler("start", start))
    
    # ============================================
    # MAIN BUTTONS (SECOND)
    # ============================================
    app.add_handler(MessageHandler(filters.Regex("^(Balance 💳)$"), balance))
    app.add_handler(MessageHandler(filters.Regex("^(Bonus 🎁)$"), bonus))
    app.add_handler(MessageHandler(filters.Regex("^(Refer and Earn 👥)$"), refer))
    app.add_handler(MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks_handler.callback))
    app.add_handler(MessageHandler(filters.Regex("^(Extra ➡️)$"), extra_handler.callback))
    
    # Web app data
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data))
    
    # ============================================
    # TASK CODE HANDLER (THIRD - BEFORE PAYMENT)
    # ============================================
    app.add_handler(code_submit)
    
    # ============================================
    # PAYMENT HANDLER (FOURTH)
    # ============================================
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~filters.Regex("^(Watch Ads 💰|Balance 💳|Bonus 🎁|Refer and Earn 👥|Tasks 📋|Extra ➡️)$"),
        handle_payment_details
    ))
    
    # ============================================
    # CALLBACK HANDLERS
    # ============================================
    app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(process_withdrawal, pattern="^withdraw_"))
    app.add_handler(CallbackQueryHandler(confirm_withdrawal, pattern="^confirm_withdraw_"))
    app.add_handler(CallbackQueryHandler(back_methods, pattern="^back_methods$"))
    app.add_handler(CallbackQueryHandler(back_to_balance, pattern="^back_balance$"))
    
    # Admin handlers
    app.add_handler(broadcast_handler)
    app.add_handler(cleanup_handler)
    
    # ============================================
    # UNKNOWN (LAST - CATCH-ALL)
    # ============================================
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))
    
    print("🤖 Cashyads2 FULLY LIVE! ✅")
    print("🎯 PERFECT HANDLER ORDER:")
    print("1️⃣ Commands → 2️⃣ Buttons → 3️⃣ Task Codes → 4️⃣ Payment → 5️⃣ Unknown")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
