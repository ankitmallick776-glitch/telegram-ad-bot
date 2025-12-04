from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    # Check for referral
    args = context.args
    if args and args[0].startswith("ref_"):
        referrer_code = args[0].split("_")[1]
        await db.process_referral(user_id, referrer_code)
        await update.message.reply_text("🎉 Welcome! You joined via referral!")
    
    await db.create_user(user_id, username)
    
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🎉 **Welcome to Cashyads2!**\n\n"
        "💰 **Watch ads → Earn 3-5 Rs each**\n"
        "👥 **Refer → Earn 40 Rs + 5% commission**\n"
        "🎁 **Daily bonus available!**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await db.give_daily_bonus(user_id):
        await update.message.reply_text(
            "🎉 **Daily Bonus Claimed!**\n💰 **+5 Rs added to balance!**\n👇 Check your balance!",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ **Daily bonus already claimed today!**\n⏳ Try again tomorrow!",
            reply_markup=get_main_keyboard()
        )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = await db.get_referral_link(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📤 Share Referral Link", url=link)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👥 **Your Referral Link:**\n\n"
        f"`{link}`\n\n"
        f"💰 **Earnings:**\n"
        f"• 40 Rs per referral\n"
        f"• 5% commission on their ad earnings\n\n"
        f"📱 Click below to share!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    check = await db.can_withdraw(user_id)
    
    if check["can"]:
        keyboard = [
            [InlineKeyboardButton("💳 Paytm", callback_data="withdraw_paytm")],
            [InlineKeyboardButton("💸 UPI", callback_data="withdraw_upi")],
            [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
            [InlineKeyboardButton("💵 Paypal", callback_data="withdraw_paypal")],
            [InlineKeyboardButton("₿ USDT TRC20", callback_data="withdraw_usdt")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"💳 **Withdraw {check['balance']:.1f} Rs**\n\n"
            f"✅ Minimum met ✓\n"
            f"👥 Referrals: {check['referrals']}\n\n"
            f"💰 **Choose method:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ **Cannot withdraw!**\n\n"
            f"{check['reason']}\n\n"
            f"💡 **Requirements:**\n• 380 Rs minimum\n• 12 referrals",
            reply_markup=get_main_keyboard()
        )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🌐 WEBDATA: {data}")
    
    if "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        await update.message.reply_text(
            f"✅ **Ad watched successfully!**\n💰 **You earned: {reward:.1f} Rs**\n💳 **New balance: {balance:.1f} Rs**",
            reply_markup=get_main_keyboard()
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**\n\n"
        f"👇 Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
