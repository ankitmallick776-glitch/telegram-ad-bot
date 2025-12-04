from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("TEST REWARD 💰")]  # TEMP TEST BUTTON
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎉 Watch ads and earn money!\n💰 Get paid for every ad you watch!",
        reply_markup=reply_markup
    )

async def watch_ads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📺 Mini App coming soon! 👇 Use TEST REWARD button")

async def test_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FORCE REWARD TEST - No Mini App needed"""
    user_id = update.effective_user.id
    reward = generate_reward()
    
    print(f"🧪 TEST REWARD: User {user_id} +{reward}")
    await db.add_balance(user_id, reward)
    balance = await db.get_balance(user_id)
    
    await update.message.reply_text(
        f"🧪 **TEST PASSED!**\n"
        f"💰 **+{reward:.1f} Rs ADDED**\n"
        f"💳 **Balance: {balance:.1f} Rs**",
        reply_markup=get_main_keyboard()
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    print(f"💳 BALANCE CHECK: User {user_id} = {balance}")
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**",
        reply_markup=get_main_keyboard()
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("📺 Watch Ads 💰")],
        [KeyboardButton("Balance 💳"), KeyboardButton("TEST REWARD 💰")],
        [KeyboardButton("Bonus 🎁")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
