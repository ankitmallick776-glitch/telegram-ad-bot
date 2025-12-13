from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
from datetime import date

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ➡️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    await db.create_user_if_not_exists(user_id, username)
    
    await update.message.reply_text(
        "🎉 <b>Welcome to CashyAds!</b>\n\n"
        "💰 <b>Watch ads → Earn 3-5 Rs each</b>\n"
        "👥 <b>Refer → Earn 40 Rs + 5% commission</b>\n"
        "🎁 <b>Daily bonus: 5 Rs (once/day)</b>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start with referral code - INSTANT REWARD"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User_{user_id}"
    
    print(f"🔗 REFERRAL: User {user_id} ({username}) joined with args: {context.args}")
    
    await db.create_user_if_not_exists(user_id, username)
    
    if context.args:
        referrer_code = context.args[0]
        print(f"📌 Referral code: {referrer_code}")
        
        already_referred = await db.user_already_referred(user_id)
        if already_referred:
            print(f"⚠️ User {user_id} already has a referrer! Blocking duplicate...")
        else:
            if await db.process_referral(user_id, referrer_code):
                print(f"✅ Referral processed with INSTANT reward!")
                try:
                    # Get referrer info for notification
                    referrer_info = await db.get_referrer_by_code(referrer_code)
                    if referrer_info:
                        referrer_id = referrer_info["user_id"]
                        await context.bot.send_message(
                            referrer_id,
                            f"🎉 <b>REFERRAL SUCCESS!</b>\n\n"
                            f"👤 New user: {username}\n"
                            f"💰 <b>You earned: 40 Rs INSTANTLY!</b>\n"
                            f"💳 Check your balance!",
                            parse_mode='HTML'
                        )
                        print(f"📬 Instant reward notification sent to {referrer_id}")
                except Exception as e:
                    print(f"⚠️ Notification error: {e}")
    
    await update.message.reply_text(
        "🎉 <b>Welcome to CashyAds!</b>\n\n"
        "💰 <b>Watch ads → Earn 3-5 Rs each</b>\n"
        "👥 <b>Refer → Earn 40 Rs + 5% commission</b>\n"
        "🎁 <b>Daily bonus: 5 Rs (once/day)</b>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mini app ad completion - SIMPLE"""
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🌐 WEBDATA: {data}")
    
    if "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        # Add 5% commission to referrer (if exists)
        await db.add_referral_commission(user_id, reward)
        
        await update.message.reply_text(
            f"✅ <b>Ad watched successfully!</b>\n"
            f"💰 <b>You earned: +{reward:.1f} Rs</b>\n"
            f"💳 <b>New balance: {balance:.1f} Rs</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Ad cancelled!</b>\n👇 Try again:",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance_amt = await db.get_balance(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💳 <b>Your balance: {balance_amt:.1f} Rs</b>\n\n"
        "👇 Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if await db.give_daily_bonus(user_id):
        await update.message.reply_text(
            "🎉 <b>Daily Bonus Claimed!</b>\n"
            "💰 <b>+5 Rs added!</b>\n"
            "👇 Check balance!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Already claimed today!</b>\n"
            "⏳ Try tomorrow!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            "❌ <b>User not found!</b>", 
            reply_markup=get_main_keyboard(), 
            parse_mode='HTML'
        )
        return
    
    referral_code = user.get("referral_code", "")
    bot_username = os.getenv("BOT_USERNAME", "Cashyads_bot")
    link = f"https://t.me/{bot_username}?start={referral_code}"
    referrals = int(user.get("referrals", 0))
    
    keyboard = [[InlineKeyboardButton(
        "📤 Share Link", 
        url=f"https://t.me/share/url?url={link}&text=Join%20Cashyads2%20and%20earn%20money%20watching%20ads%20%F0%9F%92%B0"
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👥 <b>Your Referral Link:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"👫 <b>Referrals: {referrals}</b>\n\n"
        f"💰 <b>Earnings:</b>\n"
        f"• <b>40 Rs INSTANT per referral</b>\n"
        f"• <b>5% commission on their ad earnings</b>\n\n"
        f"📱 Click to share!",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

# [Keep all withdrawal functions exactly the same - no changes needed]
# withdraw_menu, process_withdrawal, confirm_withdrawal, handle_payment_details, 
# back_to_balance, back_methods - ALL SAME AS BEFORE
