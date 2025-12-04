from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
from datetime import date

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generic /start - no referral"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    await db.create_user_if_not_exists(user_id, username)
    
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

async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start with referral code - NOTIFY REFERRER, NOT NEW USER"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User_{user_id}"
    
    print(f"🔗 REFERRAL: User {user_id} ({username}) joined with args: {context.args}")
    
    # Create user first
    await db.create_user_if_not_exists(user_id, username)
    
    # Process referral if args provided
    if context.args:
        referrer_code = context.args[0]
        print(f"📌 Referral code: {referrer_code}")
        
        # Get referrer user_id from code
        referrer_info = await db.get_referrer_by_code(referrer_code)
        if referrer_info:
            referrer_id = referrer_info["user_id"]
            referrer_username = referrer_info.get("username", f"User_{referrer_id}")
            
            if await db.process_referral(user_id, referrer_code):
                print(f"✅ Referral processed: {user_id} → {referrer_id}")
                
                # NOTIFY REFERRER - NOT NEW USER!
                # FIXED: Escape @ symbol and use plain text format
                try:
                    notification_text = (
                        f"🎉 Someone joined via your referral!\n\n"
                        f"👤 User: {username}\n"
                        f"💰 You earned: 40 Rs\n"
                        f"💳 Check balance for details!"
                    )
                    await context.bot.send_message(
                        referrer_id,
                        notification_text,
                        parse_mode=None  # NO MARKDOWN - plain text only
                    )
                    print(f"📬 Notification sent to referrer {referrer_id}")
                except Exception as e:
                    print(f"⚠️ Could not send notification: {e}")
            else:
                print(f"❌ Referral failed for code: {referrer_code}")
        else:
            print(f"❌ Referrer not found for code: {referrer_code}")
    
    # Show welcome to NEW USER (no special notification)
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
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ User not found!", reply_markup=get_main_keyboard())
        return
    
    referral_code = user.get("referral_code", "")
    bot_username = os.getenv("BOT_USERNAME", "Cashyads_bot")
    link = f"https://t.me/{bot_username}?start={referral_code}"
    referrals = int(user.get("referrals", 0))
    
    keyboard = [[InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}&text=Join%20Cashyads2%20and%20earn%20money%20watching%20ads%20%F0%9F%92%B0")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    print(f"📌 REFER: User {user_id} referral code: {referral_code}")
    
    await update.message.reply_text(
        f"👥 **Your Referral Link:**\n\n"
        f"`{link}`\n\n"
        f"👫 **Referrals: {referrals}**\n\n"
        f"💰 **Earnings:**\n"
        f"• **40 Rs per referral**\n"
        f"• **5% commission on their ad earnings**\n\n"
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
            f"📅 {date.today()}",
            parse_mode='Markdown'
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
