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
        referrer_code = args[0][4:]
        await db.process_referral(user_id, referrer_code)
        await update.message.reply_text("✅ Referral bonus credited! +₹40 + 5% commission activated!")
        return
    
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

async def balance_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main button handler - dispatches to specific functions"""
    text = update.message.text
    
    if text == "Balance 💳":
        await balance(update, context)
    elif text == "Bonus 🎁":
        await bonus(update, context)
    elif text == "Refer 👥":
        await refer(update, context)
    elif text == "Leaderboard 🏆":
        from handlers.leaderboard_handler import leaderboard
        await leaderboard(update, context)
    elif text == "Withdraw 💸":
        await withdraw_menu(update, context)
    else:
        await start(update, context)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    keyboard = [
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"💳 **Your Balance: ₹{user['balance']:.1f}**\n\n"
    text += f"👥 Referrals: {user.get('referrals', 0)}\n"
    text += f"**Withdraw min:** ₹380 + 12 referrals"
    
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    success = await db.claim_daily_bonus(user_id)
    
    keyboard = get_main_keyboard()
    if success:
        await update.message.reply_text("🎁 **+₹5 Daily Bonus Claimed!**\nCome back tomorrow!", reply_markup=keyboard)
    else:
        await update.message.reply_text("🎁 Daily bonus already claimed today!", reply_markup=keyboard)

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    ref_code = user['referral_code']
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{ref_code}"
    
    keyboard = get_main_keyboard()
    message = f"👥 **YOUR REFERRAL LINK**\n\n"
    message += f"`{ref_link}`\n\n"
    message += f"💰 **EARNINGS:**\n"
    message += f"• ₹40 per referral\n"
    message += f"• 5% commission on their ads FOREVER\n"
    message += f"• **Your referrals: {user.get('referrals', 0)}**\n\n"
    message += f"**Withdraw min:** ₹380 + 12 referrals"
    
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Create utils/rewards.py if missing
    try:
        from utils.rewards import generate_reward
        reward = generate_reward()
    except:
        reward = round(3.0 + random.uniform(0, 2.0), 1)
    
    await db.add_balance(user_id, reward)
    
    # Commission to referrer
    user = await db.get_user(user_id)
    if user.get('referrer_id'):
        comm = reward * 0.05
        await db.add_balance(user['referrer_id'], comm)
    
    keyboard = get_main_keyboard()
    await update.message.reply_text(
        f"✅ **Ad watched successfully!**\n"
        f"💰 **+₹{reward:.1f}** added to balance!\n\n"
        "🔄 Watch more ads?",
        reply_markup=keyboard
    )

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdraw button (will check conditions in callback)"""
    query = update.callback_query
    if query:
        await query.answer()
    
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    keyboard = get_main_keyboard()
    text = f"💸 **Withdraw ₹{user['balance']:.1f}**\n\n"
    text += f"👥 Referrals: {user.get('referrals', 0)}\n"
    text += "**Min: ₹380 + 12 referrals**"
    
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_balance")],
        [InlineKeyboardButton("🏆 Leaderboard", callback_data="leaderboard")]
    ])

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.upper()
    user = await db.get_user(user_id)
    
    if user['balance'] < 380 or user.get('referrals', 0) < 12:
        await query.edit_message_text(
            "❌ **Withdraw Failed**\n\n"
            "💰 Min balance: ₹380\n"
            "👥 Min referrals: 12\n\n"
            f"**Current:** ₹{user['balance']:.1f} | {user.get('referrals', 0)} refs"
        )
        return
    
    await db.process_withdrawal(user_id, method)
    await db.notify_admin(user_id, method, user['balance'])
    
    await query.edit_message_text("✅ **Withdrawal Requested!**\nAdmin will process within 24h")

async def back_to_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(query.message, context)
