from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from telegram.ext import ContextTypes
from utils.supabase import db
from utils.rewards import generate_reward
import os
from datetime import date
import json

def get_main_keyboard():
    """Get main menu keyboard with all buttons"""
    keyboard = [
        [KeyboardButton("Watch Ads 💰", web_app=WebAppInfo(url=os.getenv("MINI_APP_URL")))],
        [KeyboardButton("Balance 💳"), KeyboardButton("Bonus 🎁")],
        [KeyboardButton("Refer and Earn 👥"), KeyboardButton("Tasks 📋")],
        [KeyboardButton("Extra ➡️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generic start handler (no referral)"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User{user_id}"
    
    await db.create_user_if_not_exists(user_id, username)
    
    await update.message.reply_text(
        f"<b>👋 Welcome to Cashyads2!</b>\n\n"
        f"💰 <b>Watch ads</b> - Earn 3-5 Rs each\n"
        f"👥 <b>Refer</b> - Earn 40 Rs + 5% commission\n"
        f"🎁 <b>Daily bonus</b> - 5 Rs once/day\n"
        f"📋 <b>Daily tasks</b> - 100 Rs (4 tasks)\n\n"
        f"<i>Start earning now! 🚀</i>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start with referral code - INSTANT REWARD"""
    user_id = update.effective_user.id
    username = update.effective_user.username or f"User{user_id}"
    
    print(f"🔗 REFERRAL: User {user_id} ({username}) joined with args: {context.args}")
    
    await db.create_user_if_not_exists(user_id, username)
    
    if context.args:
        referrer_code = context.args[0]
        print(f"Referral code: {referrer_code}")
        
        already_referred = await db.user_already_referred(user_id)
        if already_referred:
            print(f"❌ EXPLOIT BLOCKED: User {user_id} already has a referrer!")
        else:
            if await db.process_referral(user_id, referrer_code):
                print(f"✅ Referral processed with INSTANT reward!")
                
                try:
                    referrer_info = await db.get_referrer_by_code(referrer_code)
                    if referrer_info:
                        referrer_id = referrer_info["user_id"]
                        await context.bot.send_message(
                            referrer_id,
                            f"<b>🎉 REFERRAL SUCCESS!</b>\n\n"
                            f"👤 New user: {username}\n"
                            f"<b>💰 You earned 40 Rs INSTANTLY!</b>\n\n"
                            f"💳 Check your balance!",
                            parse_mode='HTML'
                        )
                        print(f"✅ Instant reward notification sent to {referrer_id}")
                except Exception as e:
                    print(f"⚠️ Notification error: {e}")
    
    await update.message.reply_text(
        f"<b>👋 Welcome to Cashyads2!</b>\n\n"
        f"💰 <b>Watch ads</b> - Earn 3-5 Rs each\n"
        f"👥 <b>Refer</b> - Earn 40 Rs + 5% commission\n"
        f"🎁 <b>Daily bonus</b> - 5 Rs once/day\n"
        f"📋 <b>Daily tasks</b> - 100 Rs (4 tasks)\n\n"
        f"<i>Start earning now! 🚀</i>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )


async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mini app ad completion"""
    user_id = update.effective_user.id
    data = update.effective_message.web_app_data.data
    
    print(f"📱 WEB_APP_DATA: {data}")
    
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
            f"<b>✅ Ad watched successfully!</b>\n\n"
            f"💰 <b>You earned {reward:.1f} Rs</b>\n"
            f"💳 New balance: <b>{balance:.1f} Rs</b>",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        print(f"✅ Ad reward: {user_id} +{reward:.1f} Rs = {balance:.1f}")
    else:
        await update.message.reply_text(
            f"❌ Ad cancelled!\n\n"
            f"Try again! 🔄",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show balance with withdraw button"""
    user_id = update.effective_user.id
    balance_amt = await db.get_balance(user_id)
    
    keyboard = [[InlineKeyboardButton("💰 Withdraw", callback_data="withdraw")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"💳 <b>Your Balance</b>\n\n"
        f"💵 <b>{balance_amt:.1f} Rs</b>\n\n"
        f"Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    print(f"💳 Balance shown to {user_id}: {balance_amt:.1f} Rs")


async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Claim daily bonus - 5 Rs once per day"""
    user_id = update.effective_user.id
    
    try:
        if await db.give_daily_bonus(user_id):
            await update.message.reply_text(
                f"<b>🎁 Daily Bonus Claimed!</b>\n\n"
                f"✅ <b>5 Rs added</b> to your balance!\n\n"
                f"💳 Check your balance now!",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            print(f"✅ Daily bonus given to user {user_id}")
        else:
            await update.message.reply_text(
                f"<b>⏳ Already Claimed Today!</b>\n\n"
                f"⏰ Come back tomorrow for another 5 Rs bonus!",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            print(f"⏸️ User {user_id} already claimed bonus today")
            
    except Exception as e:
        print(f"❌ Bonus error: {e}")
        await update.message.reply_text(
            "❌ Error processing bonus. Try again!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )


async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral info and share link"""
    user_id = update.effective_user.id
    
    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ User not found!",
                reply_markup=get_main_keyboard(),
                parse_mode='HTML'
            )
            return
        
        referral_code = user.get("referral_code", "")
        bot_username = os.getenv("BOT_USERNAME", "Cashyadsbot")
        link = f"https://t.me/{bot_username}?start={referral_code}"
        share_url = f"https://t.me/share/url?url={link}&text=Join%20Cashyads2%20and%20earn%20money%20watching%20ads%20%F0%9F%92%B0"
        
        referrals = int(user.get("referrals", 0))
        
        keyboard = [[InlineKeyboardButton("📲 Share Link", url=share_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"<b>👥 Referral Program</b>\n\n"
            f"<code>{link}</code>\n\n"
            f"<b>Your Stats:</b>\n"
            f"👥 Referrals: <b>{referrals}</b>\n\n"
            f"<b>💰 Earnings:</b>\n"
            f"💵 <b>40 Rs INSTANT</b> per referral\n"
            f"💵 <b>5% commission</b> on their ad earnings\n\n"
            f"👇 Click to share!",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        print(f"📊 Referral info shown to {user_id}: {referrals} referrals")
        
    except Exception as e:
        print(f"❌ Referral error: {e}")
        await update.message.reply_text(
            "❌ Error loading referral info!",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )


async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdrawal payment methods"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💳 Paytm", callback_data="withdraw_paytm")],
        [InlineKeyboardButton("📱 UPI", callback_data="withdraw_upi")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
        [InlineKeyboardButton("💵 Paypal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("₿ USDT (TRC20)", callback_data="withdraw_usdt")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"<b>💳 Choose Payment Method</b>\n\n"
        f"<i>Select your preferred withdrawal method below:</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    print(f"💸 Withdrawal menu shown to {query.from_user.id}")


async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process withdrawal request - show confirmation"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[1].upper()
    
    check = await db.can_withdraw(user_id)
    
    if check["can"]:
        bal = await db.get_balance(user_id)
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirm Withdrawal", callback_data=f"confirm_withdraw_{method}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_methods")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"<b>💳 Withdrawal Ready!</b>\n\n"
            f"<b>💰 Amount:</b> ₹{bal:.1f}\n"
            f"<b>📌 Method:</b> {method}\n"
            f"<b>👥 Referrals:</b> {check['referrals']}\n\n"
            f"✅ <i>All requirements met!</i>\n"
            f"<b>Click confirm to proceed.</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        print(f"✅ Withdrawal ready for {user_id}: {bal:.1f} Rs via {method}")
    else:
        keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_methods")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"<b>❌ Cannot Withdraw!</b>\n\n"
            f"<b>📌 Method Selected:</b> {method}\n\n"
            f"<b>❌ Why you can't withdraw:</b>\n"
            f"<i>{check['reason']}</i>\n\n"
            f"<b>📋 Requirements:</b>\n"
            f"💵 Minimum balance: <b>380 Rs</b>\n"
            f"👥 Minimum referrals: <b>12</b>\n\n"
            f"<i>Keep earning to unlock withdrawals!</i>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        print(f"❌ Cannot withdraw: {user_id} - {check['reason']}")


async def confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm withdrawal and ask for payment details"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    method = query.data.split("_")[2].upper()
    
    bal = await db.get_balance(user_id)
    
    # Store withdrawal details in context
    context.user_data['withdrawal_method'] = method
    context.user_data['withdrawal_amount'] = bal
    context.user_data['withdrawal_user_id'] = user_id
    
    if method == "PAYTM":
        await query.edit_message_text(
            f"<b>💳 Enter Your Paytm Number</b>\n\n"
            f"💰 <b>Amount:</b> ₹{bal:.1f}\n"
            f"📌 <b>Method:</b> PAYTM\n\n"
            f"<i>Please reply with your 10-digit Paytm number.</i>\n"
            f"<b>Example:</b> <code>9876543210</code>",
            parse_mode='HTML'
        )
        
    elif method == "UPI":
        await query.edit_message_text(
            f"<b>📱 Enter Your UPI ID</b>\n\n"
            f"💰 <b>Amount:</b> ₹{bal:.1f}\n"
            f"📌 <b>Method:</b> UPI\n\n"
            f"<i>Please reply with your UPI ID.</i>\n"
            f"<b>Examples:</b>\n"
            f"<code>username@paytm</code>\n"
            f"<code>name@okhdfcbank</code>",
            parse_mode='HTML'
        )
        
    elif method == "BANK":
        await query.edit_message_text(
            f"<b>🏦 Enter Your Bank Details</b>\n\n"
            f"💰 <b>Amount:</b> ₹{bal:.1f}\n"
            f"📌 <b>Method:</b> BANK TRANSFER\n\n"
            f"<i>Please reply with your details in this format:</i>\n"
            f"<code>Account Number\nIFSC Code\nAccount Holder Name</code>\n\n"
            f"<b>Example:</b>\n"
            f"<code>1234567890\nHDFC0000123\nJohn Doe</code>",
            parse_mode='HTML'
        )
        
    elif method == "PAYPAL":
        await query.edit_message_text(
            f"<b>💵 Enter Your PayPal Email</b>\n\n"
            f"💰 <b>Amount:</b> ₹{bal:.1f}\n"
            f"📌 <b>Method:</b> PAYPAL\n\n"
            f"<i>Please reply with your PayPal email address.</i>\n"
            f"<b>Example:</b> <code>john@gmail.com</code>",
            parse_mode='HTML'
        )
        
    elif method == "USDT":
        await query.edit_message_text(
            f"<b>₿ Enter Your USDT (TRC20) Wallet</b>\n\n"
            f"💰 <b>Amount:</b> ₹{bal:.1f}\n"
            f"📌 <b>Method:</b> USDT (TRC20)\n\n"
            f"<i>Please reply with your TRC20 wallet address.</i>\n"
            f"<b>Example:</b>\n"
            f"<code>TQCp8xxxxxxxxxxxxxxxxxxxxxxxxxxx</code>",
            parse_mode='HTML'
        )
    
    print(f"📝 Waiting for payment details from {user_id} for {method}")


async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process payment details and complete withdrawal"""
    user_id = update.effective_user.id
    payment_details = update.message.text
    
    # Check if user is in withdrawal context
    if 'withdrawal_method' not in context.user_data:
        await update.message.reply_text(
            "❌ Session expired!\n\n"
            "Please start withdrawal again from Balance button.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return
    
    method = context.user_data['withdrawal_method']
    amount = context.user_data['withdrawal_amount']
    
    # Deduct balance
    await db.add_balance(user_id, -amount)
    
    await update.message.reply_text(
        f"<b>✅ Withdrawal Processed!</b>\n\n"
        f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
        f"📌 <b>Method:</b> {method}\n"
        f"<b>✓ Payment Details Received</b>\n\n"
        f"<b>⏳ Status:</b> <i>Processing...</i>\n"
        f"<i>Admin will contact within 24h</i>\n\n"
        f"<b>💳 New Balance:</b> 0.0 Rs",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    await update.message.reply_text(
        f"<b>🎉 WITHDRAWAL CONFIRMATION</b>\n\n"
        f"<i>Your withdrawal request has been</i> <b>SUCCESSFULLY SUBMITTED</b>\n\n"
        f"<b>📌 Processing Details:</b>\n"
        f"⏱️ Processing time: <b>5-7 working days</b>\n"
        f"<i>(Excludes weekends & public holidays)</i>\n"
        f"<i>Depends on your bank/payment service</i>\n\n"
        f"<b>❓ Why it takes time:</b>\n"
        f"🔐 Bank verification & KYC checks\n"
        f"🔄 Payment gateway processing\n"
        f"🛡️ Fraud prevention & security\n"
        f"📅 Weekend/holiday delays\n\n"
        f"<b>📋 What happens next:</b>\n"
        f"1️⃣ Our admin verifies your request\n"
        f"2️⃣ Amount transferred to your account\n"
        f"3️⃣ Bank processes the payment\n"
        f"4️⃣ Money appears in your account\n\n"
        f"<b>💬 Need Help?</b>\n"
        f"📞 Contact @CashyadsSupportBot\n"
        f"⚠️ <i>We never charge for withdrawals!</i>\n"
        f"💡 <i>Keep earning more! Watch ads & refer friends.</i>",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    
    # Notify admin
    admin_id = int(os.getenv("ADMIN_ID", "7836675446"))
    try:
        # Escape HTML characters
        escaped_details = payment_details.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        if method == "PAYTM":
            await context.bot.send_message(
                admin_id,
                f"<b>📱 NEW WITHDRAWAL - PAYTM</b>\n\n"
                f"👤 <b>User ID:</b> {user_id}\n"
                f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
                f"📌 <b>Method:</b> PAYTM\n\n"
                f"<b>Paytm Number:</b>\n"
                f"<code>{escaped_details}</code>\n\n"
                f"📅 {date.today()}",
                parse_mode='HTML'
            )
        elif method == "UPI":
            await context.bot.send_message(
                admin_id,
                f"<b>📱 NEW WITHDRAWAL - UPI</b>\n\n"
                f"👤 <b>User ID:</b> {user_id}\n"
                f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
                f"📌 <b>Method:</b> UPI\n\n"
                f"<b>UPI ID:</b>\n"
                f"<code>{escaped_details}</code>\n\n"
                f"📅 {date.today()}",
                parse_mode='HTML'
            )
        elif method == "BANK":
            await context.bot.send_message(
                admin_id,
                f"<b>🏦 NEW WITHDRAWAL - BANK TRANSFER</b>\n\n"
                f"👤 <b>User ID:</b> {user_id}\n"
                f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
                f"📌 <b>Method:</b> BANK TRANSFER\n\n"
                f"<b>Bank Details:</b>\n"
                f"<code>{escaped_details}</code>\n\n"
                f"📅 {date.today()}",
                parse_mode='HTML'
            )
        elif method == "PAYPAL":
            await context.bot.send_message(
                admin_id,
                f"<b>💵 NEW WITHDRAWAL - PAYPAL</b>\n\n"
                f"👤 <b>User ID:</b> {user_id}\n"
                f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
                f"📌 <b>Method:</b> PAYPAL\n\n"
                f"<b>PayPal Email:</b>\n"
                f"<code>{escaped_details}</code>\n\n"
                f"📅 {date.today()}",
                parse_mode='HTML'
            )
        elif method == "USDT":
            await context.bot.send_message(
                admin_id,
                f"<b>₿ NEW WITHDRAWAL - USDT (TRC20)</b>\n\n"
                f"👤 <b>User ID:</b> {user_id}\n"
                f"💰 <b>Amount:</b> ₹{amount:.1f}\n"
                f"📌 <b>Method:</b> USDT (TRC20)\n\n"
                f"<b>TRC20 Wallet:</b>\n"
                f"<code>{escaped_details}</code>\n\n"
                f"📅 {date.today()}",
                parse_mode='HTML'
            )
        
        print(f"✅ Admin notified with payment details")
        
    except Exception as e:
        print(f"⚠️ Admin notification failed: {e}")
    
    # Clear context data
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
        f"💵 <b>{bal:.1f} Rs</b>\n\n"
        f"Ready to withdraw?",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )


async def back_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to payment methods"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("💳 Paytm", callback_data="withdraw_paytm")],
        [InlineKeyboardButton("📱 UPI", callback_data="withdraw_upi")],
        [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
        [InlineKeyboardButton("💵 Paypal", callback_data="withdraw_paypal")],
        [InlineKeyboardButton("₿ USDT (TRC20)", callback_data="withdraw_usdt")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_balance")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"<b>💳 Choose Payment Method</b>\n\n"
        f"<i>Select your preferred withdrawal method below:</i>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
