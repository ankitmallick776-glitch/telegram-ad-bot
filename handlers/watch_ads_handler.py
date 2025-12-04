from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
import random

BOT_USERNAME = "@CashyAds_bot"

MAIN_KEYBOARD = ReplyKeyboardMarkup([
    [KeyboardButton("Watch Ads 💰")],
    [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
    [KeyboardButton("Refer 👥"), KeyboardButton("Leaderboard 🏆")],
    [KeyboardButton("Withdraw 💸")]
], resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    # Check/create user
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, username)
        user = await db.get_user(user_id)
    
    # Referral check
    args = context.args
    if args and len(args) > 0 and args[0].startswith('ref_'):
        referrer_code = args[0][4:]
        await db.process_referral(user_id, referrer_code)
        await update.message.reply_text("✅ Referral bonus credited!", reply_markup=MAIN_KEYBOARD)
        return
    
    text = f"🤖 **Welcome {username}!**\n\n💰 Watch ads → Earn ₹3-5\n👥 Refer → ₹40 + 5%\n🎁 Daily bonus → ₹5\n\n💳 **Balance: ₹{user.get('balance', 0):.1f}**"
    await update.message.reply_text(text, reply_markup=MAIN_KEYBOARD, parse_mode='Markdown')

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="back_balance")]
    ])
    
    text = f"💳 **Your Balance: ₹{user.get('balance', 0):.1f}**\n\n👥 Referrals: {user.get('referrals', 0)}\n⚠️ Min withdraw: ₹380 + 12 referrals"
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode='Markdown')

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    success = await db.claim_daily_bonus(user_id)
    
    if success:
        await update.message.reply_text("🎁 **+₹5 Daily Bonus Claimed!**\nTomorrow again!", reply_markup=MAIN_KEYBOARD)
    else:
        await update.message.reply_text("🎁 Daily bonus already claimed today!", reply_markup=MAIN_KEYBOARD)

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user.get('referral_code', 'XXXXX')}"
    
    text = f"👥 **YOUR REFERRAL LINK:**\n\n`{ref_link}`\n\n💰 **Earnings:**\n• ₹40 per referral\n• 5% commission FOREVER\n• Your refs: {user.get('referrals', 0)}"
    await update.message.reply_text(text, reply_markup=MAIN_KEYBOARD, parse_mode='Markdown')

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        reward = generate_reward()
    except:
        reward = round(random.uniform(3.0, 5.0), 1)
    
    await db.add_balance(user_id, reward)
    
    # 5% commission to referrer
    user = await db.get_user(user_id)
    if user.get('referrer_id'):
        comm = reward * 0.05
        await db.add_balance(user['referrer_id'], comm)
    
    text = f"✅ **Ad completed!**\n💰 **+₹{reward:.1f}** added!\n\n🔄 Watch more?"
    await update.message.reply_text(text, reply_markup=MAIN_KEYBOARD)

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user = await db.get_user(user_id)
    
    if user.get('balance', 0) < 380 or user.get('referrals', 0) < 12:
        await query.edit_message_text(
            f"❌ **Cannot withdraw**\n\n"
            f"💰 Balance: ₹{user.get('balance', 0):.1f} (need ₹380)\n"
            f"👥 Referrals: {user.get('referrals', 0)} (need 12)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="back_balance")]])
        )
        return
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Paytm", callback_data="paytm")],
        [InlineKeyboardButton("💸 UPI", callback_data="upi")],
        [InlineKeyboardButton("🏦 Bank", callback_data="bank")],
        [InlineKeyboardButton("💰 Paypal", callback_data="paypal")],
        [InlineKeyboardButton("₿ USDT", callback_data="usdt")],
        [InlineKeyboardButton("🔙 Cancel", callback_data="back_balance")]
    ])
    
    await query.edit_message_text(
        f"💸 **Withdraw ₹{user.get('balance', 0):.1f}**\n\nChoose method:",
        reply_markup=keyboard
    )

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = query.data.upper()
    user_id = query.from_user.id
    user = await db.get_user(user_id)
    
    await db.process_withdrawal(user_id, method)
    await db.notify_admin(user_id, method, user.get('balance', 0))
    
    await query.edit_message_text("✅ **Withdrawal requested!**\nAdmin will process in 24h", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main", callback_data="back_balance")]]))

async def back_to_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(query.message, context)

async def leaderboard_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Leaderboard button handler"""
    from handlers.leaderboard_handler import leaderboard
    await leaderboard(update, context)
