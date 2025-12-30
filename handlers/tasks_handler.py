from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.supabase import db
from datetime import datetime, timedelta
import os
import asyncio

TASK_REWARD = 80.0
TASK_DURATION = 30
COOLDOWN_HOURS = 3
MAX_TASKS = 4

# Global task timers
task_timers = {}

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
    
    # Start first task
    context.user_data['tasks_completed'] = 0
    context.user_data['task_start_time'] = datetime.now()
    
    await show_task_1(update, context)

async def show_task_1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Task 1"""
    user_id = update.effective_user.id
    link = os.getenv("TASK_LINK_1", "https://monetag.com")
    keyboard = [[InlineKeyboardButton("🔗 Open Task 1 (Stay 30s)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📋 <b>TASK 1/4</b>\n\n"
        f"💰 <b>Total Reward: +80 Rs (after all 4 tasks)</b>\n\n"
        f"⏱️ <b>Instructions:</b>\n"
        f"1️⃣ Click button below\n"
        f"2️⃣ <b>Stay on website 30 seconds</b>\n"
        f"3️⃣ Return here automatically\n\n"
        f"⚠️ <b>Leave early = FAIL!</b>\n\n"
        f"👇 <b>Start Task 1:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    # Schedule check
    await schedule_task_check(update.get_bot(), user_id, 1, context)

async def schedule_task_check(bot, user_id: int, task_num: int, context: ContextTypes.DEFAULT_TYPE):
    """Schedule task completion check"""
    # Cancel previous task if exists
    if user_id in task_timers:
        task_timers[user_id].cancel()
    
    # Create new task
    task = asyncio.create_task(
        check_task_completion(bot, user_id, task_num, context)
    )
    task_timers[user_id] = task

async def check_task_completion(bot, user_id: int, task_num: int, context: ContextTypes.DEFAULT_TYPE):
    """Check if task completed after 35 seconds"""
    try:
        await asyncio.sleep(35)
        
        user_context = context.user_data.get(user_id, {})
        start_time = user_context.get('task_start_time')
        
        if start_time:
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed >= TASK_DURATION:
                # Task success
                current_tasks = user_context.get('tasks_completed', 0) + 1
                context.user_data[user_id]['tasks_completed'] = current_tasks
                
                if current_tasks >= MAX_TASKS:
                    await give_final_reward(bot, user_id, context)
                else:
                    await show_next_task(bot, user_id, current_tasks + 1, context)
            else:
                # Task failed
                await bot.send_message(
                    user_id,
                    "❌ <b>Task Failed!</b>\n\n"
                    f"⏱️ Stayed less than 30 seconds.\n"
                    "💡 Click <b>Tasks</b> to retry.",
                    parse_mode='HTML'
                )
    except asyncio.CancelledError:
        pass
    except Exception as e:
        print(f"⚠️ Task check error: {e}")
    finally:
        # Clean up
        if user_id in task_timers:
            del task_timers[user_id]

async def show_next_task(bot, user_id: int, task_num: int, context: ContextTypes.DEFAULT_TYPE):
    """Show next task"""
    links = {
        2: os.getenv("TASK_LINK_2", "https://adsterra.com"),
        3: os.getenv("TASK_LINK_3", "https://monetag.com"),
        4: os.getenv("TASK_LINK_4", "https://adsterra.com")
    }
    
    link = links.get(task_num, "https://monetag.com")
    keyboard = [[InlineKeyboardButton(f"🔗 Open Task {task_num} (Stay 30s)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await bot.send_message(
        user_id,
        f"✅ <b>Task {task_num-1} Complete!</b>\n\n"
        f"📋 <b>TASK {task_num}/4</b>\n\n"
        f"⏱️ <b>Stay 30 seconds on link</b>\n\n"
        f"👇 <b>Continue:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    # Update context
    if user_id not in context.user_data:
        context.user_data[user_id] = {}
    
    context.user_data[user_id]['task_start_time'] = datetime.now()
    
    # Schedule next check
    await schedule_task_check(bot, user_id, task_num, context)

async def give_final_reward(bot, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Give 80 Rs reward"""
    try:
        user = await db.get_user(user_id)
        current_balance = float(user.get("balance", 0))
        new_balance = current_balance + TASK_REWARD
        
        # Update balance
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
            print(f"🤝 Commission: {user_id} → {referrer_id} +₹{commission:.1f}")
        
        await bot.send_message(
            user_id,
            f"🎉 <b>ALL 4 TASKS COMPLETED!</b>\n\n"
            f"💰 <b>+80 Rs added to balance!</b>\n"
            f"💳 <b>New balance: ₹{new_balance:.1f}</b>\n\n"
            f"⏳ <b>Next tasks in 3 hours</b>\n\n"
            f"🔥 Share with friends for more!",
            parse_mode='HTML'
        )
        print(f"✅ User {user_id}: +80 Rs")
        
    except Exception as e:
        print(f"❌ Reward error: {e}")
        await bot.send_message(user_id, "❌ Reward error!")

# Handler
tasks_handler = MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks_menu)
