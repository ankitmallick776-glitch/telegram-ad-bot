from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.supabase import db
from datetime import datetime, timedelta
import os

TASK_REWARD = 80.0
COOLDOWN_HOURS = 3

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tasks menu"""
    user_id = update.effective_user.id
    
    # Check cooldown
    last_completion = await db.get_user_task_time(user_id)
    if last_completion:
        last_time = datetime.fromisoformat(last_completion)
        time_left = (last_time + timedelta(hours=COOLDOWN_HOURS)) - datetime.now()
        if time_left.total_seconds() > 0:
            hours = int(time_left.total_seconds() / 3600)
            mins = int((time_left.total_seconds() % 3600) / 60)
            await update.message.reply_text(
                f"⏳ <b>Tasks on cooldown!</b>\n\n"
                f"⏰ Next available: {hours}h {mins}m\n"
                f"💡 Complete tasks every 3 hours for max earnings!",
                parse_mode='HTML'
            )
            return
    
    link = os.getenv("TASK_LINK_1", "https://monetag.com")
    keyboard = [[InlineKeyboardButton("🔗 Open Task (30s stay)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['task_start_time'] = datetime.now()
    
    await update.message.reply_text(
        f"📋 <b>TASK AVAILABLE</b>\n\n"
        f"💰 <b>Reward: +80 Rs</b>\n\n"
        f"⏱️ <b>Instructions:</b>\n"
        f"1️⃣ Click button below\n"
        f"2️⃣ Wait 30 seconds\n"
        f"3️⃣ Return here\n"
        f"4️⃣ Type: done\n\n"
        f"⚠️ <b>You must wait 30 seconds!</b>\n\n"
        f"👇 <b>Start:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def verify_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify task completion"""
    user_id = update.effective_user.id
    message = update.message.text.strip().lower()
    
    if message != "done":
        return
    
    start_time = context.user_data.get('task_start_time')
    if not start_time:
        await update.message.reply_text("⚠️ No active task!", parse_mode='HTML')
        return
    
    elapsed = (datetime.now() - start_time).total_seconds()
    if elapsed < 30:
        remaining = int(30 - elapsed)
        await update.message.reply_text(
            f"⏳ Please wait {remaining} more seconds...",
            parse_mode='HTML'
        )
        return
    
    # Task complete
    try:
        user = await db.get_user(user_id)
        current_balance = float(user.get("balance", 0))
        new_balance = current_balance + TASK_REWARD
        
        db.client.table("users").update({
            "balance": new_balance,
            "last_task_completion": datetime.now().isoformat()
        }).eq("user_id", user_id).execute()
        
        # Check referrer
        referral_response = db.client.table("referral_history").select("referrer_id").eq("new_user_id", user_id).execute()
        if referral_response.data:
            referrer_id = referral_response.data[0]["referrer_id"]
            commission = TASK_REWARD * 0.05
            referrer = await db.get_user(referrer_id)
            referrer_balance = float(referrer.get("balance", 0))
            new_referrer_balance = referrer_balance + commission
            db.client.table("users").update({
                "balance": new_referrer_balance
            }).eq("user_id", referrer_id).execute()
            print(f"🤝 Commission: {referrer_id} +{commission:.1f}")
        
        await update.message.reply_text(
            f"🎉 <b>TASK COMPLETE!</b>\n\n"
            f"💰 <b>+80 Rs added to balance!</b>\n"
            f"💳 <b>New balance: ₹{new_balance:.1f}</b>\n\n"
            f"⏳ <b>Next tasks in 3 hours</b>\n\n"
            f"🔥 Invite friends for more rewards!",
            parse_mode='HTML'
        )
        print(f"✅ User {user_id}: +80 Rs!")
        
        context.user_data.clear()
        
    except Exception as e:
        print(f"❌ Task error: {e}")
        await update.message.reply_text("❌ Task error! Try again.", parse_mode='HTML')

tasks_handler = MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks_menu)
task_verify = MessageHandler(filters.TEXT & ~filters.COMMAND, verify_task)
