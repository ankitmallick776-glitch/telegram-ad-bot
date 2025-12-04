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
    MINI_APP_URL = os.getenv("MINI_APP_URL")
    if not MINI_APP_URL or MINI_APP_URL == "https://your-mini-app.pages.dev":
        await update.message.reply_text("❌ Deploy Mini App to Cloudflare first!\n👇 Use Balance to check rewards work")
        return
    
    inline_keyboard = [[InlineKeyboardButton("📺 Watch Ad Now (3-5 Rs) 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    inline_markup = InlineKeyboardMarkup(inline_keyboard)
    
    await update.message.reply_text(
        "🎥 Watch the ad below to earn money!\n⏳ Complete ad = reward!",
        reply_markup=inline_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🌐 RAW WebAppData: {repr(data)}")
    
    # FIXED: Handle ALL JSON formats
    try:
        parsed = json.loads(data)
        if parsed.get("ad_completed") == True:
            print("✅ AD SUCCESS!")
            reward = generate_reward()
            await db.add_balance(user_id, reward)
            balance = await db.get_balance(user_id)
            
            await update.message.reply_text(
                f"✅🎉 **Ad watched successfully!**\n"
                f"💰 **You earned: +{reward:.1f} Rs**\n"
                f"💳 **Total balance: {balance:.1f} Rs**",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
            return
    except:
        pass
    
    # Fallback string check
    if 'ad_completed' in data.lower():
        print("✅ AD SUCCESS (string match)!")
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        await update.message.reply_text(
            f"✅🎉 **Ad watched successfully!**\n"
            f"💰 **You earned: +{reward:.1f} Rs**\n"
            f"💳 **Total balance: {balance:.1f} Rs**",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        print("❌ No reward trigger")
        await update.message.reply_text(
            f"❌ Ad cancelled. Data: `{data}`",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    print(f"💳 BALANCE: User {user_id} = {balance}")
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
