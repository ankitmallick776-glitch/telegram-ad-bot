from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
import json

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎉 **CashyAds2** - Watch ads & earn!\n\n"
        "💰 **3-5 Rs per ad**\n"
        "📱 Watch → Claim Reward → Money added!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    MINI_APP_URL = os.getenv("MINI_APP_URL")
    
    inline_keyboard = [[InlineKeyboardButton("📺 Watch Ad Now 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "🎥 **Watch the ad below:**\n\n"
        "✅ Watch complete → **CLAIM REWARD** button appears\n"
        "🎁 Click Claim → **3-5 Rs INSTANT**",
        reply_markup=inline_markup,
        parse_mode='Markdown'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"\n🚀 WEBDATA: {repr(data)}")
    
    # PERFECT MATCH: Claim Reward clicked
    if '"claimed":true' in data or '"ad_completed":true' in data or data == '{"ad_completed":true,"claimed":true}':
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        print(f"💰 REWARD: User {user_id} +{reward} = {balance}")
        
        await update.message.reply_text(
            f"🎉 **CLAIM SUCCESS!**\n\n"
            f"💰 **+{reward:.1f} Rs EARNED**\n"
            f"💳 **NEW BALANCE: {balance:.1f} Rs**\n\n"
            f"📺 Watch more ads to earn!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ Ad cancelled. Watch complete ad → Claim Reward!",
            reply_markup=get_main_keyboard()
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**\n\n"
        "📺 Watch ads to earn more!",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
