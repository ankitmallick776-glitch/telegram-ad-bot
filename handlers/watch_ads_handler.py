from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
from datetime import date

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    args = context.args
    if args and args[0].startswith("ref_"):
        referrer_code = args[0][4:]
        await db.process_referral(user_id, referrer_code)
    
    await db.create_user(user_id, username)
    
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Leaderboard 🏆")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎉 **Welcome to Cashyads2!**\n\n"
        "💰 **Watch ads → Earn 3-5 Rs each**\n"
        "👥 **Refer → Earn 40 Rs + 5% commission**\n"
        "🎁 **Daily bonus: 5 Rs (once/day)**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

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
            f"✅ **Ad watched successfully!**\n"
            f"💰 **You earned: +{reward:.1f} Rs**\n"
            f"💳 **New balance: {balance:.1f} Rs**",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "❌ **Ad cancelled!**\n👇 Try again:",
            reply_markup=get_main_keyboard()
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = await db.get_balance(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💳 **Your balance: {balance:.1f} Rs**\n\n👇 Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if await db.give_daily_bonus(user_id):
        await update.message.reply_text(
            "🎉 **Daily Bonus Claimed!**\n💰 **+5 Rs added!**\n👇 Check balance!",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ **Already claimed today!**\n⏳ Try tomorrow!",
            reply_markup=get_main_keyboard()
        )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = await db.get_referral_link(user_id)
    
    keyboard = [[InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}&text=Join%20Cashyads2%20%F0%9F%92%B0")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👥 **Your Referral Link:**\n\n"
        f"`{link}`\n\n"
        f"💰 **Earnings:**\n"
        f"• 40 Rs per referral\n"
        f"• 5% commission on their earnings\n\n"
        f"📱 Click to share!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
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
        
        await query.edit_message_text(
            f"💳 **Withdraw {check['balance']:.1f} Rs**\n\n"
            f"✅ Minimum met ✓\n"
            f"👥 Referrals: {check['referrals']}\n\n"
            f"💰 **Choose method:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_balance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ **Cannot withdraw!**\n\n"
            f"{check['reason']}\n\n"
            f"💡 **Requirements:**\n• 380 Rs minimum\n• 12 referrals",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[1].upper()
    bal = await db.get_balance(user_id)
    
    await db.add_balance(user_id, -bal)
    
    await query.edit_message_text(
        f"✅ **Withdrawal Requested!**\n\n"
        f"💰 **Amount:** {bal:.1f} Rs\n"
        f"💳 **Method:** {method}\n"
        f"👤 **User ID:** `{user_id}`\n\n"
        f"⏳ **Status:** Processing...\n"
        f"📧 Admin will contact within 24h\n\n"
        f"💳 **New Balance:** 0.0 Rs",
        parse_mode='Markdown'
    )
    
    admin_id = int(os.getenv("ADMIN_ID", "7836675446"))
    try:
        await context.bot.send_message(
            admin_id,
            f"💳 **NEW WITHDRAWAL!**\n\n"
            f"👤 User: {user_id}\n"
            f"💰 Amount: {bal:.1f} Rs\n"
            f"💳 Method: {method}\n"
            f"📅 {date.today()}"
        )
    except:
        pass

async def back_to_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bal = await db.get_balance(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💳 **Your balance: {bal:.1f} Rs**\n\n👇 Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
