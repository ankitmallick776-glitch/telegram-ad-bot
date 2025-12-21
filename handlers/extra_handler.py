from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.supabase import db

async def extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extra info page - FAST & COMPACT with total users"""
    user_id = update.effective_user.id
    
    # Fetch user stats (no logs)
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text(
            "❌ <b>User not found!</b>",
            parse_mode='HTML'
        )
        return
    
    balance = float(user.get("balance", 0))
    referrals = int(user.get("referrals", 0))
    
    # Get total users count (fast, no logs)
    all_users = await db.get_all_user_ids()
    total_users = len(all_users)
    
    keyboard = [
        [InlineKeyboardButton("📢 Channel", url="https://t.me/CashyAds")],
        [InlineKeyboardButton("💬 Support", url="https://t.me/CashyadsSupportBot")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"➡️ <b>EXTRA INFO</b>\n\n"
        f"👤 <b>Your Stats:</b>\n"
        f"💰 Balance: ₹{balance:.1f}\n"
        f"👥 Referrals: {referrals}\n\n"
        f"📊 <b>Bot Stats:</b>\n"
        f"👥 Total Users: {total_users:,}\n\n"
        f"📢 <b>Official Links:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# Export handler
extra_handler = MessageHandler(filters.Regex("^(Extra ➡️)$"), extra)
