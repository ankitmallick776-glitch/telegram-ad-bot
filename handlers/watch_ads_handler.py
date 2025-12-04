from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.db import get_balance, add_balance
from utils.rewards import generate_reward

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command and show persistent keyboard"""
    keyboard = [
        [KeyboardButton("Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)
    
    welcome_text = (
        "🎉 Watch ads and earn money!\n"
        "💰 Get paid for every ad you watch!"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Watch Ads button - open Mini App"""
    # Replace with your Cloudflare Pages URL after deployment
    MINI_APP_URL = "https://your-mini-app.pages.dev"  # UPDATE THIS
    
    keyboard = [[KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=MINI_APP_URL))]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "📺 Open the Mini App to watch an ad and earn money!\n"
        "💰 Reward: 3.0 - 5.0 Rs",
        reply_markup=reply_markup
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data sent from Mini App after ad completion"""
    user_id = update.effective_user.id
    
    # Verify it's an ad completion signal
    data = update.effective_message.web_app_data.data
    if "ad_completed" in data:
        reward = generate_reward()
        await add_balance(user_id, reward)
        balance = await get_balance(user_id)
        
        await update.message.reply_text(
            f"✅ Ad watched successfully!\n"
            f"💰 You earned: {reward:.1f} Rs\n"
            f"💳 New balance: {balance:.1f} Rs",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Something went wrong. Try again!",
            reply_markup=get_main_keyboard()
        )

def get_main_keyboard():
    """Return main persistent keyboard"""
    from telegram import ReplyKeyboardMarkup, KeyboardButton
    keyboard = [
        [KeyboardButton("Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ⚡")],
        [KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, persistent=True)
