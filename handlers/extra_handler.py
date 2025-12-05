from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.supabase import db

async def extra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extra info page with links and stats"""
    user_id = update.effective_user.id
    user_stats = await db.get_user_stats(user_id)
    
    total_earned = user_stats["total_earned"]
    total_withdrawn = user_stats["total_withdrawn"]
    referrals = user_stats.get("referrals", 0)
    
    # Global stats
    global_stats = await db.get_global_stats()
    
    keyboard = [
        [InlineKeyboardButton("📢 Channel", url="https://t.me/CashyAds")],
        [InlineKeyboardButton("💬 Support", url="https://t.me/CashyadsSupportBot")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"➡️ <b>EXTRA INFO</b>\n\n"
        f"👤 <b>Your Stats:</b>\n"
        f"💰 <b>Current Balance:</b> ₹{total_earned:.1f}\n"        # ✅ Shows balance
        f"👥 <b>Referrals:</b> {referrals}\n"                       # ✅ Referral count
        f"💸 <b>Total Withdrawn:</b> ₹{total_withdrawn:.1f}\n\n"   # ✅ Withdrawal tracking
        
        f"📊 <b>Bot Stats:</b>\n"
        f"👥 <b>Total Users:</b> {global_stats['total_users']:,}\n"
        f"💎 <b>Total Balance:</b> ₹{global_stats['total_balance']:.1f}\n\n"
        f"📢 <b>Official Links:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# Export handler
extra_handler = MessageHandler(filters.Regex("^(Extra ➡️)$"), extra)
