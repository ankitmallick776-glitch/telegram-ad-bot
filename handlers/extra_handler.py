from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.supabase import db
import logging

logger = logging.getLogger(__name__)

async def extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extra info page - shows user/bot stats"""
    user_id = update.effective_user.id
    
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text(
            "❌ <b>User not found!</b>",
            parse_mode='HTML'
        )
        logger.warning(f"Extra info: user {user_id} not found")
        return
    
    balance = float(user.get("balance", 0))
    referrals = int(user.get("referrals", 0))
    
    # Fast stats lookup
    total_users = await db.get_total_user_count()
    
    keyboard = [
        [InlineKeyboardButton("📢 Channel", url="https://t.me/CashyAds")],
        [InlineKeyboardButton("💬 Support", url="https://t.me/CashyadsSupportBot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"➡️ <b>EXTRA INFO</b>\n\n"
        f"👤 <b>Your Stats:</b>\n"
        f"💰 <b>Balance:</b> ₹{balance:.1f}\n"
        f"👥 <b>Referrals:</b> {referrals}\n\n"
        f"📊 <b>Bot Stats:</b>\n"
        f"👥 <b>Total Users:</b> {total_users:,}\n\n"
        f"📢 <b>Official Links:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    logger.info(f"Extra info viewed by {user_id}: bal={balance}, refs={referrals}")

# Export handler (matches main.py expectation)
extra_handler = MessageHandler(filters.Regex("^(Extra ➡️)$"), extra)
