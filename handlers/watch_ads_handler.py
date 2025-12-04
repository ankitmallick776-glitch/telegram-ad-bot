from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
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
    MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-mini-app.pages.dev")
    keyboard = [[KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📺 Open the Mini App to watch an ad and earn money!\n💰 Reward: 3.0 - 5.0 Rs",
        reply_markup=reply_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    if "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        await update.message.reply_text(
            f"✅ Ad watched successfully!\n💰 You earned: {reward:.1f} Rs\n💳 New balance: {balance:.1f} Rs",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text("❌ Something went wrong. Try again!", reply_markup=get_main_keyboard())

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 Your current balance: {balance:.1f} Rs\n👇 Watch more ads to earn!",
        reply_markup=get_main_keyboard()
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
