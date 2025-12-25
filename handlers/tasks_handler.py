from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler
from utils.supabase import db
from datetime import datetime, timedelta
import os
import asyncio

TASK_REWARD = 80.0
TASK_DURATION = 30  # 30 seconds per task
COOLDOWN_HOURS = 3
MAX_TASKS = 4

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main tasks menu - triggered by button"""
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
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Main Menu", callback_data="back_main")]])
            )
            return
    
    # Set task state and show first task
    context.user_data['current_task'] = 1
    context.user_data['tasks_completed'] = 0
    await show_task_1(update, context)

async def show_task_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Task 1"""
    link = os.getenv("TASK_LINK_1", "https://monetag.com")
    keyboard = [[InlineKeyboardButton("🔗 Open Task 1 (Stay 30s)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    context.user_data['task_start_time'] = datetime.now()
    
    await update.message.reply_text(
        f"📋 <b>TASK 1/4</b>\n\n"
        f"💰 <b>Total Reward: +80 Rs (after all 4 tasks)</b>\n\n"
        f"⏱️ <b>Instructions:</b>\n"
        f"1️⃣ Click button below\n"
        f"2️⃣ <b>Stay on website 30 seconds</b>\n"
        f"3️⃣ Return here\n\n"
        f"⚠️ <b>Leave early = FAIL!</b>\n\n"
        f"👇 <b>Start Task 1:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    # Auto-check after 35 seconds
    context.job_queue.run_once(auto_check_task, 35, data={
        'user_id': update.effective_user.id, 
        'task_num': 1,
        'chat_id': update.effective_chat.id,
        'message_id': update.message.message_id
    }, name=f"task_check_1")

async def auto_check_task(context: ContextTypes.DEFAULT_TYPE):
    """Auto-check task completion after timer"""
    job = context.job
    data = job.data
    user_id = data['user_id']
    task_num = data['task_num']
    
    # Get user data
    user_tasks = context.user_data.get(user_id, {})
    start_time = user_tasks.get('task_start_time')
    
    if start_time:
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed >= TASK_DURATION:
            # ✅ TASK SUCCESS - Next task or reward
            current_tasks = user_tasks.get('tasks_completed', 0) + 1
            
            if current_tasks >= MAX_TASKS:
                # ALL TASKS COMPLETE
                await give_final_reward(context.bot, user_id)
            else:
                # Next task
                await show_next_task(context.bot, user_id, current_tasks + 1)
        else:
            # Task failed
            await context.bot.send_message(
                user_id, 
                "❌ <b>Task Failed!</b>\n\n"
                f"⏱️ Stayed less than 30 seconds.\n"
                "💡 Click <b>Tasks</b> to retry.",
                parse_mode='HTML'
            )

async def show_next_task(bot, user_id: int, task_num: int):
    """Show next task automatically"""
    links = {
        2: os.getenv("TASK_LINK_2", "https://adsterra.com"),
        3: os.getenv("TASK_LINK_3", "https://monetag.com"),
        4: os.getenv("TASK_LINK_4", "https://adsterra.com")
    }
    
    link = links.get(task_num, "https://monetag.com")
    keyboard = [[InlineKeyboardButton(f"🔗 Open Task {task_num} (Stay 30s)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    bot.send_message(
        user_id,
        f"✅ <b>Task {task_num-1} Complete!</b>\n\n"
        f"📋 <b>TASK {task_num}/4</b>\n\n"
        f"⏱️ <b>Stay 30 seconds on link</b>\n\n"
        f"👇 <b>Continue:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    # Start timer for next task
    context.user_data[user_id] = context.user_data.get(user_id, {})
    context.user_data[user_id]['task_start_time'] = datetime.now()
    context.user_data[user_id]['tasks_completed'] = task_num - 1
    
    # Auto-check
    context.job_queue.run_once(auto_check_task, 35, data={
        'user_id': user_id, 
        'task_num': task_num
    }, name=f"task_check_{task_num}")

async def give_final_reward(bot, user_id: int):
    """Give 80 Rs reward after all tasks"""
    try:
        user = await db.get_user(user_id)
        current_balance = float(user.get("balance", 0))
        new_balance = current_balance + TASK_REWARD
        
        # Update balance & completion time
        db.client.table("users").update({
            "balance": new_balance,
            "last_task_completion": datetime.now().isoformat()
        }).eq("user_id", user_id).execute()
        
        # Referral commission
        referral_response = db.client.table("referral_history").select("referrer_id").eq("new_user_id", user_id).execute()
        if referral_response.data:
            referrer_id = referral_response.data[0]["referrer_id"]
            commission = TASK_REWARD * 0.05
            referrer = await db.get_user(referrer_id)
            referrer_balance = float(referrer.get("balance", 0))
            new_referrer_balance = referrer_balance + commission
            db.client.table("users").update({"balance": new_referrer_balance}).eq("user_id", referrer_id).execute()
            print(f"🤝 Task commission: {user_id} → {referrer_id} +₹{commission:.1f}")
        
        bot.send_message(
            user_id,
            f"🎉 <b>ALL 4 TASKS COMPLETED!</b>\n\n"
            f"💰 <b>+80 Rs added to balance!</b>\n"
            f"💳 <b>New balance: ₹{new_balance:.1f}</b>\n\n"
            f"⏳ <b>Next tasks in 3 hours</b>\n\n"
            f"🔥 Share with friends for more!",
            parse_mode='HTML'
        )
        print(f"✅ User {user_id}: +80 Rs tasks complete!")
        
    except Exception as e:
        print(f"❌ Reward error: {e}")
        bot.send_message(user_id, "❌ Reward error! Contact admin.")

# Handlers
tasks_handler = MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks_menu)

# Export for main.py
def get_handlers():
    return [tasks_handler]
