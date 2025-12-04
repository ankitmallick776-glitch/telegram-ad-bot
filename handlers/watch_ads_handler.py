from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # MAIN KEYBOARD with DIRECT WebApp on Watch Ads!
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    welcome_text = "🎉 Watch ads and earn money!\n💰 Get paid for every ad you watch!"
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Optional fallback - not needed anymore"""
    await update.message.reply_text("👇 Use the Watch Ads button from keyboard!", reply_markup=get_main_keyboard())

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🌐 WEBDATA: {data}")
    
    if "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        print(f"💰 REWARD: +{reward} = {balance}")
        
        await update.message.reply_text(
            f"✅ **Ad watched successfully!**\n💰 **You earned: {reward:.1f} Rs**\n💳 **New balance: {balance:.1f} Rs**",
            reply_markup=get_main_keyboard()
        )
    else:
        print(f"❌ NO REWARD: {data}")
        await update.message.reply_text("❌ Ad cancelled. Try again!", reply_markup=get_main_keyboard())

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**\n👇 Watch more ads!",
        reply_markup=get_main_keyboard()
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
