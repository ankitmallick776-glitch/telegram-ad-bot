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
                f"⏰ Next available: {hours}h {mins}m",
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
        f"1️⃣ Click button\n"
        f"2️⃣ Wait 30 seconds\n"
        f"3️⃣ Return here\n"
        f"4️⃣ Type: done\n\n"
        f"👇 <b>Start:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )

async def verify_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify task completion when user types 'done'"""
    user_id = update.effective_user.id
    message = update.message.text.strip().lower()
    
    if message != "done":
        return  # Not a task completion
    
    start_time = context.user_data.get('task_start_time')
    if not start_time:
        await update.message.reply_text("⚠️ No active task!", parse_mode='HTML')
        return
    
    elapsed = (datetime.now() - start_time).total_seconds()
    if elapsed < 30:
        remaining = int(30 - elapsed)
        await update.message.reply_text(
            f"⏳ Wait {remaining} more seconds...",
            parse_mode='HTML'
        )
        return
    
    # Task complete - give reward
    try:
        user = await db.get_user(user_id)
        current_balance = float(user.get("balance", 0))
        new_balance = current_balance + TASK_REWARD
        
        db.client.table("users").update({
            "balance": new_balance,
            "last_task_completion": datetime.now().isoformat()
        }).eq("user_id", user_id).execute()
        
        await update.message.reply_text(
            f"🎉 <b>TASK COMPLETE!</b>\n\n"
            f"💰 <b>+80 Rs added!</b>\n"
            f"💳 <b>Balance: ₹{new_balance:.1f}</b>\n\n"
            f"⏳ Next in 3 hours",
            parse_mode='HTML'
        )
        
        context.user_data.clear()
        
    except Exception as e:
        print(f"❌ Task error: {e}")
        await update.message.reply_text("❌ Error!", parse_mode='HTML')

tasks_handler = MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks_menu)
task_verify = MessageHandler(filters.TEXT & ~filters.COMMAND, verify_task)
