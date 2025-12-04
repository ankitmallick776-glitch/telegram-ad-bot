from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # MAIN KEYBOARD (without Watch Ads)
    keyboard = [
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    welcome_text = (
        "🎉 Watch ads and earn money!\n"
        "💰 Get paid for every ad you watch!"
    )
    
    # INLINE Watch Ads button below text
    inline_keyboard = [[InlineKeyboardButton("📺 Watch Ads Now 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL", "https://your-mini-app.pages.dev")))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)
    await update.message.reply_text("👇 Click below to start earning!", reply_markup=inline_markup)

async def watch_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline Watch Ads button"""
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📱 Opening Mini App...", reply_markup=None)

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    if "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        await update.message.reply_text(
            f"✅ Ad watched successfully!\n"
            f"💰 You earned: +{reward:.1f} Rs\n"
            f"💳 Total balance: {balance:.1f} Rs",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ad failed. Try again!", 
            reply_markup=get_main_keyboard()
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 Your current balance: {balance:.1f} Rs\n"
        "👇 Watch more ads to earn!",
        reply_markup=get_main_keyboard()
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
