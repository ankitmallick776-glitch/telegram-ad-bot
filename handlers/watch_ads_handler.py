from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from utils.supabase import db
import os

# States for withdrawal conversation
WITHDRAW_METHOD, PAYMENT_DETAILS, CONFIRM = range(3)

async def get_main_keyboard():
    """Get main menu keyboard"""
    return ReplyKeyboardMarkup([
        [KeyboardButton("Watch Ads 💰"), KeyboardButton("Balance 💳")],
        [KeyboardButton("Bonus 🎁"), KeyboardButton("Refer and Earn 👥")],
        [KeyboardButton("Tasks 📋"), KeyboardButton("Extra ➡️")]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    
    await db.create_user_if_not_exists(user_id, username)
    
    await update.message.reply_text(
        "👋 <b>Welcome to Cashyads2!</b>\n\n"
        "💰 <b>Earn money by:</b>\n"
        "✅ Watching ads\n"
        "✅ Completing tasks\n"
        "✅ Referring friends\n\n"
        "👇 Choose an option:",
        reply_markup=await get_main_keyboard(),
        parse_mode='HTML'
    )

async def start_referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start with referral code"""
    user_id = update.effective_user.id
    username = update.effective_user.username or ""
    args = context.args
    
    await db.create_user_if_not_exists(user_id, username)
    
    if args:
        referral_code = args[0]
        result = await db.process_referral(user_id, referral_code)
        if result:
            await update.message.reply_text(
                "🎉 <b>Referral bonus activated!</b>\n\n"
                "💰 <b>+40 Rs added to your balance</b>",
                reply_markup=await get_main_keyboard(),
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "❌ <b>Invalid referral code!</b>",
                reply_markup=await get_main_keyboard(),
                parse_mode='HTML'
            )
    else:
        await update.message.reply_text(
            "👋 <b>Welcome to Cashyads2!</b>\n\n"
            "💰 <b>Earn money by:</b>\n"
            "✅ Watching ads\n"
            "✅ Completing tasks\n"
            "✅ Referring friends\n\n"
            "👇 Choose an option:",
            reply_markup=await get_main_keyboard(),
            parse_mode='HTML'
        )

async def web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle web app data (ad completion)"""
    user_id = update.effective_user.id
    web_app = update.message.web_app_data
    
    if web_app and web_app.data:
        reward = 10.0  # 10 Rs per ad
        await db.add_balance(user_id, reward)
        
        # Add commission to referrer
        await db.add_referral_commission(user_id, reward)
        
        await update.message.reply_text(
            f"✅ <b>Ad completed!</b>\n\n"
            f"💰 <b>+{reward} Rs earned</b>\n"
            f"👇 Watch more ads:",
            reply_markup=await get_main_keyboard(),
            parse_mode='HTML'
        )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user balance"""
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ User not found")
        return
    
    balance = float(user.get("balance", 0))
    referrals = int(user.get("referrals", 0))
    
    await update.message.reply_text(
        f"💳 <b>Your Balance</b>\n\n"
        f"💰 <b>Main Balance: {balance:.1f} Rs</b>\n"
        f"👥 <b>Referrals: {referrals}</b>\n\n"
        f"📋 <b>Withdrawal Requirements:</b>\n"
        f"✅ Min 380 Rs balance\n"
        f"✅ Min 12 referrals\n\n"
        f"👇 Options:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton("👈 Back", callback_data="back_balance")]
        ]),
        parse_mode='HTML'
    )

async def bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Give daily bonus"""
    user_id = update.effective_user.id
    
    result = await db.give_daily_bonus(user_id)
    
    if result:
        await update.message.reply_text(
            "🎁 <b>Daily bonus claimed!</b>\n\n"
            "💰 <b>+5 Rs added</b>\n"
            "⏰ <b>Come back tomorrow for more!</b>",
            reply_markup=await get_main_keyboard(),
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text(
            "❌ <b>Already claimed today!</b>\n\n"
            "⏰ <b>Come back tomorrow</b>",
            reply_markup=await get_main_keyboard(),
            parse_mode='HTML'
        )

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral link"""
    user_id = update.effective_user.id
    user = await db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ User not found")
        return
    
    referral_code = user.get("referral_code", "")
    bot_username = (await context.bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    await update.message.reply_text(
        f"👥 <b>Refer & Earn</b>\n\n"
        f"💰 <b>+40 Rs per referral</b>\n"
        f"🔗 <b>Your link:</b>\n"
        f"<code>{referral_link}</code>\n\n"
        f"👥 <b>Referrals: {user.get('referrals', 0)}</b>",
        reply_markup=await get_main_keyboard(),
        parse_mode='HTML'
    )

async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show withdrawal methods"""
    user_id = update.effective_user.id
    
    can_withdraw = await db.can_withdraw(user_id)
    
    if not can_withdraw.get("can"):
        await update.query.answer()
        await update.callback_query.edit_message_text(
            f"❌ <b>Cannot withdraw!</b>\n\n"
            f"❌ {can_withdraw.get('reason')}\n\n"
            f"📋 <b>Requirements:</b>\n"
            f"• Min 380 Rs balance\n"
            f"• Min 12 referrals",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👈 Back", callback_data="back_balance")]
            ]),
            parse_mode='HTML'
        )
        return
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "💸 <b>Select Payment Method</b>\n\n"
        "Choose how you want to receive payment:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇳 UPI", callback_data="withdraw_upi")],
            [InlineKeyboardButton("📱 Phone Pay", callback_data="withdraw_phonepe")],
            [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
            [InlineKeyboardButton("👈 Back", callback_data="back_balance")]
        ]),
        parse_mode='HTML'
    )

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal method selection"""
    query = update.callback_query
    await query.answer()
    
    method = query.data.replace("withdraw_", "")
    context.user_data['withdrawal_method'] = method
    
    method_names = {
        "upi": "UPI",
        "phonepe": "Phone Pay",
        "bank": "Bank Transfer"
    }
    
    await query.edit_message_text(
        f"💸 <b>{method_names.get(method)}</b>\n\n"
        f"Please provide your {method_names.get(method)} details:\n\n",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👈 Back", callback_data="back_methods")]
        ]),
        parse_mode='HTML'
    )
    
    # Set flag to expect payment details
    context.user_data['waiting_for_payment'] = True
    
    # Send message asking for details
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text=f"📝 <b>Enter your {method_names.get(method)} details:</b>\n\n"
             f"Type your {method_names.get(method)} here:",
        parse_mode='HTML'
    )

async def handle_payment_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment details submission"""
    user_id = update.effective_user.id
    user_input = update.message.text
    
    # ============================================
    # CRITICAL: Check if waiting for payment
    # ============================================
    if not context.user_data.get('waiting_for_payment'):
        # Not waiting for payment - ignore
        return
    
    # Get withdrawal method
    withdrawal_method = context.user_data.get('withdrawal_method')
    
    if not withdrawal_method:
        await update.message.reply_text(
            "❌ <b>Error: No withdrawal method selected!</b>\n\n"
            "Please select a method and try again.",
            reply_markup=await get_main_keyboard(),
            parse_mode='HTML'
        )
        context.user_data['waiting_for_payment'] = False
        return
    
    # Get user balance
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ User not found")
        context.user_data['waiting_for_payment'] = False
        return
    
    balance = float(user.get("balance", 0))
    referrals = int(user.get("referrals", 0))
    
    # Store payment details
    context.user_data['payment_details'] = user_input
    context.user_data['withdrawal_amount'] = balance
    
    method_names = {
        "upi": "UPI",
        "phonepe": "Phone Pay",
        "bank": "Bank Transfer"
    }
    
    # Ask for confirmation
    await update.message.reply_text(
        f"✅ <b>Confirm Your Withdrawal</b>\n\n"
        f"💰 <b>Amount: {balance:.1f} Rs</b>\n"
        f"💳 <b>Method: {method_names.get(withdrawal_method)}</b>\n"
        f"📝 <b>Details: {user_input}</b>\n\n"
        f"✅ Click button to confirm:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Confirm & Withdraw", callback_data=f"confirm_withdraw_{withdrawal_method}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_methods")]
        ]),
        parse_mode='HTML'
    )
    
    # Clear waiting flag
    context.user_data['waiting_for_payment'] = False

async def confirm_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and process withdrawal"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    withdrawal_method = query.data.replace("confirm_withdraw_", "")
    payment_details = context.user_data.get('payment_details', 'N/A')
    withdrawal_amount = context.user_data.get('withdrawal_amount', 0)
    
    # Get user
    user = await db.get_user(user_id)
    if not user:
        await query.edit_message_text("❌ User not found")
        return
    
    # Deduct balance
    new_balance = float(user.get("balance", 0)) - withdrawal_amount
    db.client.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
    
    # Store withdrawal request (for admin to process)
    try:
        db.client.table("withdrawals").insert({
            "user_id": user_id,
            "amount": withdrawal_amount,
            "method": withdrawal_method,
            "details": payment_details,
            "status": "pending"
        }).execute()
        print(f"💸 Withdrawal request: {user_id} - {withdrawal_amount} Rs via {withdrawal_method}")
    except Exception as e:
        print(f"⚠️ Withdrawal storage error: {e}")
    
    method_names = {
        "upi": "UPI",
        "phonepe": "Phone Pay",
        "bank": "Bank Transfer"
    }
    
    # Send confirmation
    await query.edit_message_text(
        f"✅ <b>Withdrawal Confirmed!</b>\n\n"
        f"💰 <b>Amount: {withdrawal_amount:.1f} Rs</b>\n"
        f"💳 <b>Method: {method_names.get(withdrawal_method)}</b>\n\n"
        f"⏳ <b>Processing...</b>\n"
        f"✅ Money will be sent within 24 hours\n\n"
        f"📝 <b>Admin will verify and process your request</b>",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👈 Back to Balance", callback_data="back_balance")]
        ]),
        parse_mode='HTML'
    )
    
    # Notify admin
    admin_id = int(os.getenv("ADMIN_ID", "7836675446"))
    try:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"💸 <b>NEW WITHDRAWAL REQUEST</b>\n\n"
                 f"👤 <b>User ID:</b> {user_id}\n"
                 f"💰 <b>Amount:</b> {withdrawal_amount:.1f} Rs\n"
                 f"💳 <b>Method:</b> {method_names.get(withdrawal_method)}\n"
                 f"📝 <b>Details:</b> {payment_details}\n\n"
                 f"⏳ <b>Status: Pending</b>",
            parse_mode='HTML'
        )
    except Exception as e:
        print(f"⚠️ Admin notification error: {e}")
    
    # Clear context
    context.user_data.pop('withdrawal_method', None)
    context.user_data.pop('payment_details', None)
    context.user_data.pop('withdrawal_amount', None)
    context.user_data.pop('waiting_for_payment', None)

async def back_to_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to balance"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.user_id
    user = await db.get_user(user_id)
    
    if not user:
        await query.edit_message_text("❌ User not found")
        return
    
    balance = float(user.get("balance", 0))
    referrals = int(user.get("referrals", 0))
    
    await query.edit_message_text(
        f"💳 <b>Your Balance</b>\n\n"
        f"💰 <b>Main Balance: {balance:.1f} Rs</b>\n"
        f"👥 <b>Referrals: {referrals}</b>\n\n"
        f"📋 <b>Withdrawal Requirements:</b>\n"
        f"✅ Min 380 Rs balance\n"
        f"✅ Min 12 referrals\n\n"
        f"👇 Options:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")],
            [InlineKeyboardButton("👈 Back", callback_data="back_balance")]
        ]),
        parse_mode='HTML'
    )
    
    # Clear payment flags
    context.user_data.pop('waiting_for_payment', None)
    context.user_data.pop('withdrawal_method', None)

async def back_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Go back to withdrawal methods"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    can_withdraw = await db.can_withdraw(user_id)
    
    if not can_withdraw.get("can"):
        await query.edit_message_text(
            f"❌ <b>Cannot withdraw!</b>\n\n"
            f"❌ {can_withdraw.get('reason')}\n\n"
            f"📋 <b>Requirements:</b>\n"
            f"• Min 380 Rs balance\n"
            f"• Min 12 referrals",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👈 Back", callback_data="back_balance")]
            ]),
            parse_mode='HTML'
        )
        return
    
    await query.edit_message_text(
        "💸 <b>Select Payment Method</b>\n\n"
        "Choose how you want to receive payment:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🇮🇳 UPI", callback_data="withdraw_upi")],
            [InlineKeyboardButton("📱 Phone Pay", callback_data="withdraw_phonepe")],
            [InlineKeyboardButton("🏦 Bank Transfer", callback_data="withdraw_bank")],
            [InlineKeyboardButton("👈 Back", callback_data="back_balance")]
        ]),
        parse_mode='HTML'
    )
    
    # Clear payment flags
    context.user_data.pop('waiting_for_payment', None)
    context.user_data.pop('withdrawal_method', None)
