from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    welcome_text = "🎉 Watch ads and earn money!\n💰 Get paid for every ad you watch!"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Keyboard button → Text + INLINE WebApp button"""
    MINI_APP_URL = os.getenv("MINI_APP_URL")
    
    # TEXT MESSAGE
    await update.message.reply_text(
        "📺 **Open Mini App to watch rewarded ad!**\n\n"
        "💰 **Reward: 3.0 - 5.0 Rs**\n"
        "⏳ Watch complete ad → Auto reward!",
        parse_mode='Markdown'
    )
    
    # INLINE WEAPP BUTTON
    inline_keyboard = [[InlineKeyboardButton("🎥 WATCH REWARDED AD NOW 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "👇 **Click the button below:**",
        reply_markup=inline_markup,
        parse_mode='Markdown'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🌐 WEBDATA: {data}")  # DEBUG LOG
    
    if "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        print(f"💰 REWARD: +{reward} = {balance}")  # DEBUG LOG
        
        await update.message.reply_text(
            f"✅ **Ad watched successfully!**\n\n"
            f"💰 **You earned: {reward:.1f} Rs**\n"
            f"💳 **New balance: {balance:.1f} Rs**\n\n"
            f"👇 Watch more ads!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        print(f"❌ NO REWARD: {data}")  # DEBUG LOG
        await update.message.reply_text(
            "❌ Ad cancelled. Watch complete ad!\n👇 Try again:",
            reply_markup=get_main_keyboard()
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 **Your current balance: {balance:.1f} Rs**\n\n👇 Watch more ads to earn!",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

def get_main_keyboard():
    from telegram import ReplyKeyboardMarkup, KeyboardButton
    keyboard = [
        [KeyboardButton("Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
