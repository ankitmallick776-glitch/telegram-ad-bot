from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎉 **CashyAds2** - Earn Instantly!\n\n"
        "💰 **3-5 Rs per claim**\n"
        "📱 Click → Claim Reward → Money Added!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    MINI_APP_URL = os.getenv("MINI_APP_URL")
    
    inline_keyboard = [[InlineKeyboardButton("📺 Claim Reward Now 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "🎁 **Instant Reward Available!**\n\n"
        "👇 Click → Claim 3-5 Rs Instantly!",
        reply_markup=inline_markup,
        parse_mode='Markdown'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ALWAYS GIVE REWARD ON CLAIM BUTTON CLICK"""
    user_id = update.effective_user.id
    
    print(f"🎁 CLAIM CLICKED by user {user_id}")
    
    # ANY WebAppData = Reward! (No verification)
    reward = generate_reward()
    await db.add_balance(user_id, reward)
    balance = await db.get_balance(user_id)
    
    print(f"💰 REWARD: User {user_id} +{reward} = {balance}")
    
    await update.message.reply_text(
        f"🎉 **REWARD CLAIMED!**\n\n"
        f"💰 **+{reward:.1f} Rs EARNED**\n"
        f"💳 **NEW BALANCE: {balance:.1f} Rs**\n\n"
        f"📺 Claim more rewards!",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**\n\n"
        "📺 Claim more rewards to earn!",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
