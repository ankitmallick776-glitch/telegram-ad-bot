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
        "🎉 <b>Welcome to Cashyads2!</b>\n\n"
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
        "🎉 <b>Welcome to Cashyads2!</b>\n\n"
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

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💳 Paytm", callback_data="withdraw_paytm")],
        [InlineKeyboardButton("💸 UPI", callback_data="withdraw_upi")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
        [InlineKeyboardButton("💵 Paypal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("₿ USDT TRC20", callback_data="withdraw_usdt")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💳 <b>Choose Payment Method:</b>\n\n"
        f"Select your preferred withdrawal method below:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[1].upper()
    
    check = await db.can_withdraw(user_id)
    
    if check["can"]:
        bal = await db.get_balance(user_id)
        keyboard = [
            [InlineKeyboardButton("✅ Confirm Withdrawal", callback_data=f"confirm_withdraw_{method}")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_methods")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ <b>Withdrawal Ready!</b>\n\n"
            f"💰 <b>Amount:</b> ₹{bal:.1f}\n"
            f"💳 <b>Method:</b> {method}\n"
            f"👥 <b>Referrals:</b> {check['referrals']}\n\n"
            f"✅ <b>All requirements met!</b>\n"
            f"Click confirm to proceed.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_methods")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ <b>Cannot Withdraw!</b>\n\n"
            f"💳 <b>Method Selected:</b> {method}\n\n"
            f"<b>Why you can't withdraw:</b>\n"
            f"{check['reason']}\n\n"
            f"💡 <b>Requirements:</b>\n"
            f"• Minimum balance: ₹380\n"
            f"• Minimum referrals: 12\n\n"
            f"Keep earning to unlock withdrawals! 💰",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[2].upper()
    bal = await db.get_balance(user_id)
    
    context.user_data['withdrawal_method'] = method
    context.user_data['withdrawal_amount'] = bal
    context.user_data['withdrawal_user_id'] = user_id
    
    if method == "PAYTM":
        await query.edit_message_text(
            f"📱 <b>Enter Your Paytm Number:</b>\n\n"
            f"💰 Amount: ₹{bal:.1f}\n"
            f"💳 Method: PAYTM\n\n"
            f"Please reply with your 10-digit Paytm number.\n"
            f"Example: 9876543210",
            parse_mode='HTML'
        )
    elif method == "UPI":
        await query.edit_message_text(
            f"💸 <b>Enter Your UPI ID:</b>\n\n"
            f"💰 Amount: ₹{bal:.1f}\n"
            f"💳 Method: UPI\n\n"
            f"Please reply with your UPI ID.\n"
            f"Example: username@paytm or name@okhdfcbank",
            parse_mode='HTML'
        )
    elif method == "BANK":
        await query.edit_message_text(
            f"🏦 <b>Enter Your Bank Details:</b>\n\n"
            f"💰 Amount: ₹{bal:.1f}\n"
            f"💳 Method: BANK TRANSFER\n\n"
            f"Please reply with your details in this format:\n"
            f"<code>Account Number\nIFSC Code\nAccount Holder Name</code>\n\n"
            f"Example:\n"
            f"1234567890\n"
            f"HDFC0000123\n"
            f"John Doe",
            parse_mode='HTML'
        )
    elif method == "PAYPAL":
        await query.edit_message_text(
            f"💵 <b>Enter Your PayPal Email:</b>\n\n"
            f"💰 Amount: ₹{bal:.1f}\n"
            f"💳 Method: PAYPAL\n\n"
            f"Please reply with your PayPal email address.\n"
            f"Example: john@gmail.com",
            parse_mode='HTML'
        )
    elif method == "USDT":
        await query.edit_message_text(
            f"₿ <b>Enter Your USDT TRC20 Wallet:</b>\n\n"
            f"💰 Amount: ₹{bal:.1f}\n"
            f"💳 Method: USDT TRC20\n\n"
            f"Please reply with your TRC20 wallet address.\n"
            f"Example: TQCp8xxxxxxxxxxxxxxxxxxxxxxxxxxx",
            parse_mode='HTML'
        )

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process payment details and complete withdrawal"""
    user_id = update.effective_user.id
    payment_details = update.message.text
    
    if 'withdrawal_method' not in context.user_data:
        await update.message.reply_text(
            "❌ <b>Session expired!</b>\n\n"
            "Please start withdrawal again from Balance button.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    method = context.user_data['withdrawal_method']
    amount = context.user_data['withdrawal_amount']
    
    await db.add_balance(user_id, -amount)
    
    await update.message.reply_text(
        f"✅ <b>Withdrawal Processed!</b>\n\n"
        f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
        f"💳 <b>Method:</b> {method}\n"
        f"👤 <b>Payment Details Received</b>\n\n"
        f"⏳ <b>Status:</b> Processing...\n"
        f"📧 Admin will contact within 24h\n\n"
        f"💳 <b>New Balance:</b> ₹0.0",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    await update.message.reply_text(
        f"📋 <b>WITHDRAWAL CONFIRMATION</b>\n\n"
        f"✅ Your withdrawal request has been <b>SUCCESSFULLY SUBMITTED</b>\n\n"
        f"<b>Processing Details:</b>\n"
        f"⏱️ Processing time: <b>5-7 working days</b>\n"
        f"📅 Excludes weekends & public holidays\n"
        f"🏦 Depends on your bank/payment service\n\n"
        f"<b>Why it takes time:</b>\n"
        f"• Bank verification & KYC checks\n"
        f"• Payment gateway processing\n"
        f"• Fraud prevention security\n"
        f"• Weekend/holiday delays\n\n"
        f"<b>What happens next:</b>\n"
        f"1️⃣ Our admin verifies your request\n"
        f"2️⃣ Amount transferred to your account\n"
        f"3️⃣ Bank processes the payment\n"
        f"4️⃣ Money appears in your account\n\n"
        f"<b>Need Help?</b>\n"
        f"📧 Contact: @CashyadsSupportBot\n"
        f"⚠️ We never charge for withdrawals!\n\n"
        f"💰 Keep earning more! Watch ads & refer friends.",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    admin_id = int(os.getenv("ADMIN_ID", "7836675446"))
    try:
        await context.bot.send_message(
            admin_id,
            f"💳 <b>NEW WITHDRAWAL!</b>\n\n"
            f"👤 <b>User ID:</b> {user_id}\n"
            f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
            f"💳 <b>Method:</b> {method}\n"
            f"📄 <b>Payment Details:</b>\n"
            f"<code>{payment_details}</code>\n\n"
            f"📅 {date.today()}",
            parse_mode='HTML'
        )
        print(f"✅ Admin notified with payment details")
    except Exception as e:
        print(f"⚠️ Admin notification failed: {e}")
    
    context.user_data.clear()

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

async def back_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💳 Paytm", callback_data="withdraw_paytm")],
        [InlineKeyboardButton("💸 UPI", callback_data="withdraw_upi")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
        [InlineKeyboardButton("💵 Paypal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("₿ USDT TRC20", callback_data="withdraw_usdt")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💳 <b>Choose Payment Method:</b>\n\n"
        f"Select your preferred withdrawal method below:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
