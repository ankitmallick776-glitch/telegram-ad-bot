from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
from datetime import date
import json

def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL", "https://example.com")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Tasks 📋")],
        [KeyboardButton("Extra ➡️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generic start handler - no referral"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User{user_id}"
    
    await db.create_user_if_not_exists(user_id, username)
    
    await update.message.reply_text(
        f"👋 <b>Welcome to Cashyads2!</b>\n\n"
        f"💰 <b>Watch Ads</b> - Earn 3-5 Rs each\n"
        f"👥 <b>Refer</b> - Earn 40 Rs + 5% commission\n"
        f"🎁 <b>Daily Bonus</b> - 5 Rs once/day\n"
        f"📋 <b>Tasks</b> - 80 Rs every 3 hours\n\n"
        f"📌 <b>Withdrawal Requirements:</b>\n"
        f"• Minimum 380 Rs balance\n"
        f"• Minimum 12 referrals\n\n"
        f"Let's earn! 💸",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle start with referral code - INSTANT REWARD"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User{user_id}"
    
    print(f"👥 Referral: User {user_id} ({username}) joined with args {context.args}")
    
    await db.create_user_if_not_exists(user_id, username)
    
    if context.args:
        referrer_code = context.args[0]
        print(f"🔗 Referral code: {referrer_code}")
        
        already_referred = await db.user_already_referred(user_id)
        if already_referred:
            print(f"❌ User {user_id} already has a referrer! Blocking duplicate...")
        else:
            if await db.process_referral(user_id, referrer_code):
                print(f"✅ Referral processed with INSTANT reward!")
                
                try:
                    referrer_info = await db.get_referrer_by_code(referrer_code)
                    if referrer_info:
                        referrer_id = referrer_info["user_id"]
                        await context.bot.send_message(
                            referrer_id,
                            f"🎉 <b>REFERRAL SUCCESS!</b>\n\n"
                            f"👤 <b>New user:</b> {username}\n"
                            f"💰 <b>You earned: 40 Rs INSTANTLY!</b>\n\n"
                            f"💳 Check your balance!",
                            parse_mode='HTML'
                        )
                        print(f"✅ Instant reward notification sent to {referrer_id}")
                except Exception as e:
                    print(f"⚠️ Notification error: {e}")
    
    await update.message.reply_text(
        f"👋 <b>Welcome to Cashyads2!</b>\n\n"
        f"💰 <b>Watch Ads</b> - Earn 3-5 Rs each\n"
        f"👥 <b>Refer</b> - Earn 40 Rs + 5% commission\n"
        f"🎁 <b>Daily Bonus</b> - 5 Rs once/day\n"
        f"📋 <b>Tasks</b> - 80 Rs every 3 hours\n\n"
        f"📌 <b>Withdrawal Requirements:</b>\n"
        f"• Minimum 380 Rs balance\n"
        f"• Minimum 12 referrals\n\n"
        f"Let's earn! 💸",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mini app ad completion"""
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"📱 Web App Data: {data}")
    
    try:
        data_json = json.loads(data)
    except:
        data_json = {}
    
    if data_json.get("ad_completed"):
        reward = generate_reward()
        await db.add_balance(user_id, reward)
        await db.add_referral_commission(user_id, reward)
        
        balance = await db.get_balance(user_id)
        
        await update.message.reply_text(
            f"✅ <b>Ad watched successfully!</b>\n\n"
            f"💰 <b>You earned: {reward:.1f} Rs</b>\n"
            f"💳 <b>New balance: ₹{balance:.1f}</b>\n\n"
            f"🔥 Keep earning!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        print(f"✅ User {user_id}: +{reward:.1f} Rs!")
    else:
        await update.message.reply_text(
            f"❌ <b>Ad cancelled!</b>\n\n"
            f"Try again to earn money.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance"""
    user_id = update.effective_user.id
    balance_amt = await db.get_balance(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💳 <b>Your Balance</b>\n\n"
        f"💸 <b>₹{balance_amt:.2f}</b>\n\n"
        f"Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claim daily bonus"""
    user_id = update.effective_user.id
    
    if await db.give_daily_bonus(user_id):
        balance = await db.get_balance(user_id)
        await update.message.reply_text(
            f"🎁 <b>Daily Bonus Claimed!</b>\n\n"
            f"💰 <b>+5 Rs added!</b>\n"
            f"💳 <b>New balance: ₹{balance:.2f}</b>\n\n"
            f"⏰ Come back tomorrow!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        print(f"🎁 User {user_id}: +5 Rs bonus!")
    else:
        await update.message.reply_text(
            f"⚠️ <b>Already claimed today!</b>\n\n"
            f"Try tomorrow! 🗓️",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral info"""
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text(
            f"❌ User not found!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    referral_code = user.get("referral_code", "")
    bot_username = os.getenv("BOT_USERNAME", "Cashyads2bot")
    link = f"https://t.me/{bot_username}?start={referral_code}"
    referrals = int(user.get("referrals", 0))
    
    keyboard = [
        [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={link}&text=Join%20Cashyads2%20and%20earn%20money%20watching%20ads!%20💰")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"👥 <b>Your Referral Program</b>\n\n"
        f"🔗 <b>Your Link:</b>\n"
        f"`{link}`\n\n"
        f"👨‍👩‍👦 <b>Referrals:</b> {referrals}\n\n"
        f"💰 <b>Earnings:</b>\n"
        f"• 40 Rs INSTANT per referral\n"
        f"• 5% commission on their ads\n\n"
        f"📤 Share and earn!",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdrawal payment methods"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🟩 Paytm", callback_data="withdraw_paytm")],
        [InlineKeyboardButton("💳 UPI", callback_data="withdraw_upi")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
        [InlineKeyboardButton("🌐 PayPal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("💵 USDT TRC20", callback_data="withdraw_usdt")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💰 <b>Choose Payment Method</b>\n\n"
        f"Select your preferred withdrawal method below:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process withdrawal request"""
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
            f"💵 <b>Amount:</b> ₹{bal:.2f}\n"
            f"🔑 <b>Method:</b> {method}\n"
            f"👥 <b>Referrals:</b> {check['referrals']}\n\n"
            f"✅ All requirements met!\n\n"
            f"Click confirm to proceed.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_methods")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"❌ <b>Cannot Withdraw!</b>\n\n"
            f"🔑 <b>Method Selected:</b> {method}\n\n"
            f"❌ <b>Why you can't withdraw:</b>\n"
            f"{check['reason']}\n\n"
            f"📌 <b>Requirements:</b>\n"
            f"• Minimum balance: 380 Rs\n"
            f"• Minimum referrals: 12\n\n"
            f"💪 Keep earning to unlock withdrawals!",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

async def confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm withdrawal and ask for payment details"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[3].upper()
    bal = await db.get_balance(user_id)
    
    context.user_data["withdrawal_method"] = method
    context.user_data["withdrawal_amount"] = bal
    context.user_data["withdrawal_user_id"] = user_id
    
    if method == "PAYTM":
        await query.edit_message_text(
            f"📱 <b>Enter Your Paytm Number</b>\n\n"
            f"💵 <b>Amount:</b> ₹{bal:.2f}\n"
            f"🔑 <b>Method:</b> PAYTM\n\n"
            f"Please reply with your <b>10-digit Paytm number</b>.\n\n"
            f"<b>Example:</b> 9876543210",
            parse_mode='HTML'
        )
    
    elif method == "UPI":
        await query.edit_message_text(
            f"💳 <b>Enter Your UPI ID</b>\n\n"
            f"💵 <b>Amount:</b> ₹{bal:.2f}\n"
            f"🔑 <b>Method:</b> UPI\n\n"
            f"Please reply with your <b>UPI ID</b>.\n\n"
            f"<b>Example:</b> username@paytm or name@okhdfcbank",
            parse_mode='HTML'
        )
    
    elif method == "BANK":
        await query.edit_message_text(
            f"🏦 <b>Enter Your Bank Details</b>\n\n"
            f"💵 <b>Amount:</b> ₹{bal:.2f}\n"
            f"🔑 <b>Method:</b> BANK TRANSFER\n\n"
            f"Please reply with your details in this format:\n\n"
            f"`Account Number`\n"
            f"`IFSC Code`\n"
            f"`Account Holder Name`\n\n"
            f"<b>Example:</b>\n"
            f"1234567890\n"
            f"HDFC0000123\n"
            f"John Doe",
            parse_mode='HTML'
        )
    
    elif method == "PAYPAL":
        await query.edit_message_text(
            f"💵 <b>Enter Your PayPal Email</b>\n\n"
            f"💵 <b>Amount:</b> ₹{bal:.2f}\n"
            f"🔑 <b>Method:</b> PAYPAL\n\n"
            f"Please reply with your <b>PayPal email address</b>.\n\n"
            f"<b>Example:</b> john@gmail.com",
            parse_mode='HTML'
        )
    
    elif method == "USDT":
        await query.edit_message_text(
            f"💵 <b>Enter Your USDT TRC20 Wallet</b>\n\n"
            f"💵 <b>Amount:</b> ₹{bal:.2f}\n"
            f"🔑 <b>Method:</b> USDT TRC20\n\n"
            f"Please reply with your <b>TRC20 wallet address</b>.\n\n"
            f"<b>Example:</b> TQCp8xxxxxxxxxxxxxxxxxxxxxxxxxxx",
            parse_mode='HTML'
        )

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process payment details and complete withdrawal"""
    user_id = update.effective_user.id
    payment_details = update.message.text
    
    if "withdrawal_method" not in context.user_data:
        await update.message.reply_text(
            f"⚠️ <b>Session expired!</b>\n\n"
            f"Please start withdrawal again from Balance button.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    method = context.user_data["withdrawal_method"]
    amount = context.user_data["withdrawal_amount"]
    
    await db.add_balance(user_id, -amount)
    
    await update.message.reply_text(
        f"✅ <b>Withdrawal Processed!</b>\n\n"
        f"💵 <b>Amount:</b> ₹{amount:.2f}\n"
        f"🔑 <b>Method:</b> {method}\n"
        f"📝 <b>Payment Details Received</b>\n\n"
        f"⏳ <b>Status:</b> Processing...\n"
        f"Admin will contact within 24h\n\n"
        f"💳 <b>New Balance:</b> ₹0.00",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    await update.message.reply_text(
        f"🎉 <b>WITHDRAWAL CONFIRMATION</b>\n\n"
        f"Your withdrawal request has been <b>SUCCESSFULLY SUBMITTED</b> ✅\n\n"
        f"⏱️ <b>Processing Details:</b>\n"
        f"• Processing time: 5-7 working days\n"
        f"• Excludes weekends & public holidays\n"
        f"• Depends on your bank/payment service\n\n"
        f"❓ <b>Why it takes time:</b>\n"
        f"1️⃣ Bank verification & KYC checks\n"
        f"2️⃣ Payment gateway processing\n"
        f"3️⃣ Fraud prevention & security\n"
        f"4️⃣ Weekend/holiday delays\n\n"
        f"📝 <b>What happens next:</b>\n"
        f"1️⃣ Our admin verifies your request\n"
        f"2️⃣ Amount transferred to your account\n"
        f"3️⃣ Bank processes the payment\n"
        f"4️⃣ Money appears in your account\n\n"
        f"📞 <b>Need Help?</b>\n"
        f"Contact CashyadsSupportBot\n\n"
        f"⚠️ We <b>NEVER</b> charge for withdrawals!",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    admin_id = int(os.getenv("ADMIN_ID", 7836675446))
    
    try:
        escaped_details = payment_details.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        await context.bot.send_message(
            admin_id,
            f"🆕 <b>NEW WITHDRAWAL!</b>\n\n"
            f"👤 <b>User ID:</b> {user_id}\n"
            f"💵 <b>Amount:</b> ₹{amount:.2f}\n"
            f"🔑 <b>Method:</b> {method}\n"
            f"📝 <b>Payment Details:</b>\n"
            f"`{escaped_details}`\n\n"
            f"📅 {date.today()}",
            parse_mode='HTML'
        )
        print(f"✅ Admin notified with payment details")
    except Exception as e:
        print(f"⚠️ Admin notification failed: {e}")
    
    context.user_data.clear()

async def back_to_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to balance"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    bal = await db.get_balance(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💳 <b>Your Balance</b>\n\n"
        f"💸 <b>₹{bal:.2f}</b>\n\n"
        f"Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def back_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to payment methods"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🟩 Paytm", callback_data="withdraw_paytm")],
        [InlineKeyboardButton("💳 UPI", callback_data="withdraw_upi")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
        [InlineKeyboardButton("🌐 PayPal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("💵 USDT TRC20", callback_data="withdraw_usdt")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"💰 <b>Choose Payment Method</b>\n\n"
        f"Select your preferred withdrawal method below:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
