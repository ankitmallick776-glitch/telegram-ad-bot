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
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ➡️")]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎉 <b>Welcome to Cashyads2!</b>\n\n"
        "💰 <b>Watch ads → Earn 3-5 Rs each</b>\n"
        "👥 <b>Refer → Earn 40 Rs + 5% commission</b>\n"
        "🎁 <b>Daily bonus: 5 Rs (once/day)</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start with referral code - ONLY WORKS ONCE PER USER!"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User_{user_id}"
    
    print(f"🔗 REFERRAL: User {user_id} ({username}) joined with args: {context.args}")
    
    # Create user first
    await db.create_user_if_not_exists(user_id, username)
    
    # Process referral if args provided
    if context.args:
        referrer_code = context.args[0]
        print(f"📌 Referral code: {referrer_code}")
        
        # Check if already referred
        already_referred = await db.user_already_referred(user_id)
        if already_referred:
            print(f"⚠️ User {user_id} already has a referrer! Blocking duplicate...")
        else:
            # Get referrer user_id from code
            referrer_info = await db.get_referrer_by_code(referrer_code)
            if referrer_info:
                referrer_id = referrer_info["user_id"]
                referrer_username = referrer_info.get("username", f"User_{referrer_id}")
                
                if await db.process_referral(user_id, referrer_code):
                    print(f"✅ Referral processed: {user_id} → {referrer_id}")
                    # NOTIFY REFERRER
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
                            parse_mode='HTML'
                        )
                        print(f"📬 Notification sent to referrer {referrer_id}")
                    except Exception as e:
                        print(f"⚠️ Could not send notification: {e}")
                else:
                    print(f"❌ Referral failed for code: {referrer_code}")
            else:
                print(f"❌ Referrer not found for code: {referrer_code}")
    
    # Show welcome (same for all)
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Extra ➡️")]
    ]
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        "🎉 <b>Welcome to Cashyads2!</b>\n\n"
        "💰 <b>Watch ads → Earn 3-5 Rs each</b>\n"
        "👥 <b>Refer → Earn 40 Rs + 5% commission</b>\n"
        "🎁 <b>Daily bonus: 5 Rs (once/day)</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mini app ad completion"""
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"🌐 WEBDATA: {data}")
    
    if "ad_completed" in data:
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        balance = await db.get_balance(user_id)
        
        print(f"💰 REWARD: +{reward} = {balance}")
        
        # ADD 5% COMMISSION TO REFERRER!
        await db.add_commission(user_id, reward)
        
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
        await update.message.reply_text("❌ <b>User not found!</b>", reply_markup=get_main_keyboard(), parse_mode='HTML')
        return
    
    referral_code = user.get("referral_code", "")
    bot_username = os.getenv("BOT_USERNAME", "Cashyads_bot")
    link = f"https://t.me/{bot_username}?start={referral_code}"
    referrals = int(user.get("referrals", 0))
    
    keyboard = [[InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}&text=Join%20Cashyads2%20and%20earn%20money%20watching%20ads%20%F0%9F%92%B0")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    print(f"📌 REFER: User {user_id} referral code: {referral_code}")
    
    await update.message.reply_text(
        f"👥 <b>Your Referral Link:</b>\n\n"
        f"<code>{link}</code>\n\n"
        f"👫 <b>Referrals: {referrals}</b>\n\n"
        f"💰 <b>Earnings:</b>\n"
        f"• <b>40 Rs per referral</b>\n"
        f"• <b>5% commission on their ad earnings</b>\n\n"
        f"📱 Click to share!",
        reply_markup=reply_markup,
        parse_mode='HTML'
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
            f"💳 <b>Withdraw {check['balance']:.1f} Rs</b>\n\n"
            f"✅ <b>Minimum met ✓</b>\n"
            f"👥 Referrals: {check['referrals']}\n\n"
            f"💰 <b>Choose method:</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_balance")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"❌ <b>Cannot withdraw!</b>\n\n"
            f"{check['reason']}\n\n"
            f"💡 <b>Requirements:</b>\n"
            f"• 380 Rs minimum\n"
            f"• 12 referrals",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[1].upper()
    bal = await db.get_balance(user_id)
    
    # Deduct balance
    await db.add_balance(user_id, -bal)
    
    await query.edit_message_text(
        f"✅ <b>Withdrawal Requested!</b>\n\n"
        f"💰 <b>Amount:</b> {bal:.1f} Rs\n"
        f"💳 <b>Method:</b> {method}\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n\n"
        f"⏳ <b>Status:</b> Processing...\n"
        f"📧 Admin will contact within 24h\n\n"
        f"💳 <b>New Balance:</b> 0.0 Rs",
        parse_mode='HTML'
    )
    
    # Notify admin
    admin_id = int(os.getenv("ADMIN_ID", "7836675446"))
    try:
        await context.bot.send_message(
            admin_id,
            f"💳 <b>NEW WITHDRAWAL!</b>\n\n"
            f"👤 User: {user_id}\n"
            f"💰 Amount: {bal:.1f} Rs\n"
            f"💳 Method: {method}\n"
            f"📅 {date.today()}",
            parse_mode='HTML'
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
        f"💳 <b>Your balance: {bal:.1f} Rs</b>\n\n"
        "👇 Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Leaderboard 🏆")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
