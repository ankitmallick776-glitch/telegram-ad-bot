from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler
from utils.supabase import db
from datetime import datetime, timedelta
import asyncio
import os

TASK_REWARD = 80.0
TASK_DURATION = 30  # 30 seconds per task
COOLDOWN_HOURS = 3
MAX_TASKS = 4

async def tasks_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main tasks menu"""
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
    
    # Set task state
    context.user_data['current_task'] = 1
    context.user_data['tasks_completed'] = 0
    await show_task(update, context, 1)

async def show_task(update: Update, context: ContextTypes.DEFAULT_TYPE, task_num: int):
    """Show specific task with timer"""
    links = {
        1: os.getenv("TASK_LINK_1", "https://monetag.com"),
        2: os.getenv("TASK_LINK_2", "https://adsterra.com"),
        3: os.getenv("TASK_LINK_3", "https://monetag.com"),
        4: os.getenv("TASK_LINK_4", "https://adsterra.com")
    }
    
    keyboard = [[InlineKeyboardButton(f"🔗 Open Task {task_num}", url=links[task_num])]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Start timer
    context.user_data['task_start_time'] = datetime.now()
    context.user_data['current_task'] = task_num
    
    await update.callback_query.edit_message_text(
        f"📋 <b>TASK {task_num}/4</b>\n\n"
        f"💰 <b>Reward: +80 Rs (after all 4 tasks)</b>\n\n"
        f"⏱️ <b>Instructions:</b>\n"
        f"1️⃣ Click button below\n"
        f"2️⃣ Stay on website for <b>30 seconds</b>\n"
        f"3️⃣ Return here automatically\n\n"
        f"⚠️ <b>Leave early = Task fails!</b>\n\n"
        f"👇 <b>Start Task {task_num}:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    # Auto-check after 35 seconds (buffer)
    context.job_queue.run_once(check_task_completion, 35, data={'user_id': update.effective_user.id, 'task_num': task_num}, name=f'task_{task_num}')

async def check_task_completion(context: ContextTypes.DEFAULT_TYPE):
    """Auto-check if user completed task (stayed 30s)"""
    job = context.job
    user_id = job.data['user_id']
    task_num = job.data['task_num']
    
    # Get user data
    user_data = context.bot_data.get(user_id, {})
    start_time = user_data.get('task_start_time')
    
    if start_time:
        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed >= TASK_DURATION:
            # Task completed! Move to next
            tasks_completed = user_data.get('tasks_completed', 0) + 1
            context.bot_data[user_id] = {
                'tasks_completed': tasks_completed,
                'current_task': task_num + 1
            }
            
            if tasks_completed >= MAX_TASKS:
                # ALL TASKS COMPLETE - GIVE REWARD
                await give_task_reward(context.bot, user_id)
            else:
                # Next task
                await show_task_auto(context.bot, user_id, task_num + 1)
        else:
            # Task failed - reset
            await context.bot.send_message(user_id, "❌ Task failed! Stayed less than 30s. Click Tasks to retry.")

async def show_task_auto(bot, user_id: int, task_num: int):
    """Show next task automatically"""
    try:
        links = {
            1: os.getenv("TASK_LINK_1", "https://monetag.com"),
            2: os.getenv("TASK_LINK_2", "https://adsterra.com"),
            3: os.getenv("TASK_LINK_3", "https://monetag.com"),
            4: os.getenv("TASK_LINK_4", "https://adsterra.com")
        }
        
        keyboard = [[InlineKeyboardButton(f"🔗 Open Task {task_num}", url=links[task_num])]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        bot_data = bot.bot_data.get(user_id, {})
        bot_data['task_start_time'] = datetime.now()
        bot_data['current_task'] = task_num
        bot.bot_data[user_id] = bot_data
        
        bot.send_message(
            user_id,
            f"✅ <b>Task {task_num-1} Complete!</b>\n\n"
            f"📋 <b>Next: Task {task_num}/4</b>\n\n"
            f"⏱️ Stay 30s on link → Auto next task\n\n"
            f"👇 Click to continue:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        # Schedule next check
        from telegram.ext import Application
        app = Application.builder().token(os.getenv("BOT_TOKEN")).build()
        app.job_queue.run_once(check_task_completion, 35, data={'user_id': user_id, 'task_num': task_num})
        
    except Exception as e:
        print(f"Auto task error: {e}")

async def give_task_reward(bot, user_id: int):
    """Give 80 Rs reward after all tasks"""
    try:
        user = await db.get_user(user_id)
        current_balance = float(user.get("balance", 0))
        new_balance = current_balance + TASK_REWARD
        
        # Update balance
        db.client.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
        
        # Record completion time
        db.client.table("users").update({"last_task_completion": datetime.now().isoformat()}).eq("user_id", user_id).execute()
        
        bot.send_message(
            user_id,
            f"🎉 <b>ALL 4 TASKS COMPLETED!</b>\n\n"
            f"💰 <b>+80 Rs added to balance!</b>\n"
            f"💳 <b>New balance: ₹{new_balance:.1f}</b>\n\n"
            f"⏳ <b>Next tasks available in 3 hours</b>\n\n"
            f"🔥 Share with friends for more earnings!",
            parse_mode='HTML'
        )
        print(f"✅ User {user_id} completed tasks! +80 Rs")
        
    except Exception as e:
        print(f"Reward error: {e}")
        bot.send_message(user_id, "❌ Reward error! Contact admin.")

# Supabase functions needed
async def get_user_task_time(user_id: int):
    """Get last task completion time"""
    user = await db.get_user(user_id)
    return user.get("last_task_completion")

# Handlers
tasks_handler = MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks_menu)
task_callback = CallbackQueryHandler(lambda u, c: show_task(u, c, c.user_data.get('current_task', 1)), pattern="^task_")
