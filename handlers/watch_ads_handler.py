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
        "🎉 Watch ads and earn money!\n💰 Get paid for every ad you watch!",
        reply_markup=reply_markup
    )

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    MINI_APP_URL = os.getenv("MINI_APP_URL")
    
    inline_keyboard = [[InlineKeyboardButton("📺 Watch Ad Now (3-5 Rs) 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "🎥 Watch the ad → Reward automatic!\n⏳ Complete ad = money!",
        reply_markup=inline_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """CAPTURE EVERYTHING - NO FILTERS"""
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print("\n" + "="*50)
    print(f"🆔 USER: {user_id}")
    print(f"📦 RAW DATA: {repr(data)}")
    print(f"📏 LENGTH: {len(data)}")
    print(f"🔤 LOWER: {data.lower()}")
    print("="*50)
    
    # SHOW RAW DATA TO USER TOO
    await update.message.reply_text(
        f"📦 **DEBUG DATA RECEIVED:**\n`{data}`\n\n⏳ Processing...",
        parse_mode='Markdown'
    )
    
    # TRY EVERY POSSIBLE FORMAT
    success = False
    
    # 1. JSON parsing
    try:
        parsed = json.loads(data)
        print(f"📄 PARSED JSON: {parsed}")
        if parsed.get("ad_completed") or parsed.get("success") or parsed.get("completed"):
            success = True
    except:
        pass
    
    # 2. String contains
    if any(word in data.lower() for word in ['ad_completed', 'success', 'completed', 'reward', 'done', 'finish']):
        print("✅ STRING MATCH!")
        success = True
    
    if success:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        print(f"💰 REWARD: +{reward} = {balance}")
        await update.message.reply_text(
            f"✅🎉 **AD SUCCESS!**\n"
            f"💰 **+{reward:.1f} Rs EARNED**\n"
            f"💳 **BALANCE: {balance:.1f} Rs**",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        print("❌ NO REWARD TRIGGER")
        await update.message.reply_text(
            "❌ No reward trigger found\n"
            "👇 Try again or check logs!",
            reply_markup=get_main_keyboard()
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
