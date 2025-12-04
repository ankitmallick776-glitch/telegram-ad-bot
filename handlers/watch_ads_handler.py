from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
import json

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎉 Watch ads and earn money!\n💰 Get paid for every ad you watch!",
        reply_markup=reply_markup
    )

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    MINI_APP_URL = os.getenv("MINI_APP_URL", "https://your-mini-app.pages.dev")
    
    inline_keyboard = [[InlineKeyboardButton("📺 Watch Ad Now (3-5 Rs) 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "🎥 Watch the ad below to earn money!\n⏳ Please watch complete ad for reward.",
        reply_markup=inline_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """MAX DEBUG VERSION"""
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🔍 RAW DATA: {repr(data)}")
    print(f"🔍 DATA TYPE: {type(data)}")
    print(f"🔍 LEN DATA: {len(data)}")
    
    # TRY ALL POSSIBLE FORMATS
    if 'ad_completed' in data.lower() or data == '{"ad_completed":true}' or '"ad_completed":true' in data:
        print("✅ AD COMPLETED DETECTED!")
        reward = generate_reward()
        print(f"🎲 Generated reward: {reward}")
        
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        print(f"💾 DB UPDATED: User {user_id} balance = {balance}")
        
        await update.message.reply_text(
            f"✅🎉 **Ad watched successfully!**\n"
            f"💰 **You earned: +{reward:.1f} Rs**\n"
            f"💳 **Total balance: {balance:.1f} Rs**\n\n"
            f"👇 Watch more ads!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        print("❌ NO REWARD - Data doesn't match")
        await update.message.reply_text(
            f"❌ Ad failed. Raw data: `{data}`\n👇 Try again!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    print(f"💳 Balance check: User {user_id} = {balance}")
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**\n\n📺 Watch ads to earn more!",
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
