from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # KEYBOARD WITH Watch Ads BUTTON
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    welcome_text = (
        "🎉 Watch ads and earn money!\n"
        "💰 Get paid for every ad you watch!"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Keyboard Watch Ads → Shows Inline WebApp button"""
    MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-mini-app.pages.dev")
    
    # INLINE WebApp button below text
    inline_keyboard = [[InlineKeyboardButton("📺 Watch Ad Now (3-5 Rs) 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "🎥 Watch the ad below to earn money!\n"
        "⏳ Please watch complete ad for reward.",
        reply_markup=inline_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIXED: Proper reward handling"""
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🌐 WebApp data received: {data}")  # Debug log
    
    if '"ad_completed":true' in data or "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        await update.message.reply_text(
            f"✅🎉 Ad watched successfully!\n"
            f"💰 You earned: **+{reward:.1f} Rs**\n"
            f"💳 **Total balance: {balance:.1f} Rs**\n\n"
            f"👇 Watch more ads!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Ad failed or cancelled.\n"
            "👇 Try watching again!",
            reply_markup=get_main_keyboard()
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**\n\n"
        f"📺 Watch ads to earn more!",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
