from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os

BOT_USERNAME = "@CashyAds_bot"
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-mini-app.pages.dev")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    # Check/create user
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, username)
        user = await db.get_user(user_id)
    
    # Referral check
    args = context.args
    if args and len(args) > 0 and args[0].startswith('ref_'):
        referrer_code = args[0][4:]  # ref_REF123 → REF123
        await db.process_referral(user_id, referrer_code)
        await update.message.reply_text("✅ Referral bonus credited! +₹40 + 5% commission activated!")
    
    # MAIN KEYBOARD with Leaderboard
    keyboard = [
        [KeyboardButton("Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer 👥"), KeyboardButton("Leaderboard 🏆")],
        [KeyboardButton("Withdraw 💸")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"🤖 **Welcome {username}!**\n\n"
        "💰 Watch ads → Earn ₹3-5\n"
        "👥 Refer friends → ₹40 + 5% lifetime\n"
        "🎁 Daily bonus → ₹5\n\n"
        f"💳 **Current: ₹{user['balance']:.1f}**",
        reply_markup=reply_markup, parse_mode='Markdown'
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    keyboard = get_main_keyboard()
    text = f"💳 **Your Balance: ₹{user['balance']:.1f}**\n\n"
    text += f"👥 Referrals: {user.get('referrals', 0) or 0}\n"
    text += f"**Withdraw min:** ₹380 + 12 referrals"
    
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    success = await db.claim_daily_bonus(user_id)
    
    if success:
        await update.message.reply_text("🎁 **+₹5 Daily Bonus Claimed!**\nCome back tomorrow!")
    else:
        await update.message.reply_text("🎁 Daily bonus already claimed today!")

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    ref_code = user['referral_code']
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}"
    
    message = f"👥 **YOUR REFERRAL LINK**\n\n"
    message += f"`{ref_link}`\n\n"
    message += f"💰 **EARNINGS:**\n"
    message += f"• ₹40 per referral\n"
    message += f"• 5% commission on their ads FOREVER\n"
    message += f"• **Your referrals: {user.get('referrals', 0) or 0}**\n\n"
    message += f"**Withdraw min:** ₹380 + 12 referrals"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    reward = generate_reward()
    await db.add_balance(user_id, reward)
    
    # Commission to referrer
    user = await db.get_user(user_id)
    if user.get('referrer_id'):
        comm = reward * 0.05
        await db.add_balance(user['referrer_id'], comm)
    
    await update.message.reply_text(
        f"✅ **Ad watched successfully!**\n"
        f"💰 **+₹{reward:.1f}** added to balance!\n\n"
        "🔄 Watch more ads?"
    )

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("💳 Balance", callback_data="balance")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_balance")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await db.get_user(user_id)
    
    if user['balance'] < 380 or user.get('referrals', 0) < 12:
        await query.edit_message_text(
            "❌ **Withdraw Failed**\n\n"
            "💰 Min balance: ₹380\n"
            "👥 Min referrals: 12\n\n"
            f"**Current:** ₹{user['balance']:.1f} | {user.get('referrals', 0)} refs"
        )
        return
    
    keyboard = [
        [InlineKeyboardButton("💳 Paytm", callback_data="paytm")],
        [InlineKeyboardButton("💸 UPI", callback_data="upi")],
        [InlineKeyboardButton("🏦 Bank", callback_data="bank")],
        [InlineKeyboardButton("💰 Paypal", callback_data="paypal")],
        [InlineKeyboardButton("₿ USDT TRC20", callback_data="usdt")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💸 **Withdraw ₹{user['balance']:.1f}**\n\n"
        "Choose method:",
        reply_markup=reply_markup
    )

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.upper()
    user = await db.get_user(user_id)
    
    await db.process_withdrawal(user_id, method)
    await db.notify_admin(user_id, method, user['balance'])
    
    await query.edit_message_text("✅ **Withdrawal Requested!**\nAdmin will process within 24h")

async def back_to_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await balance(query.message, context)
