from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters, CommandHandler
from utils.supabase import db
from datetime import date, datetime, timedelta
import os
import asyncio

TASK_REWARD_PER_TASK = 25.0
TOTAL_REWARD = 100.0
MAX_TASKS = 4

async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tasks menu"""
    user_id = update.effective_user.id
    
    # Get or create daily tasks
    user_tasks = await db.get_user_daily_tasks(user_id)
    
    if not user_tasks:
        await db.create_or_update_daily_task(user_id, 0, 0)
        user_tasks = await db.get_user_daily_tasks(user_id)
    
    # Safety check - if still None, create default dict
    if not user_tasks:
        await db.create_or_update_daily_task(user_id, 0, 0)
        user_tasks = {"tasks_completed": 0, "pending_reward": 0}
    
    tasks_done = user_tasks.get("tasks_completed", 0)
    pending = user_tasks.get("pending_reward", 0)
    
    # Check if all tasks done
    if tasks_done >= MAX_TASKS:
        await update.message.reply_text(
            f"❌ <b>No tasks available!</b>\n\n"
            f"✅ You have completed all tasks for today.\n"
            f"💰 Come back tomorrow for more tasks!",
            parse_mode='HTML'
        )
        return
    
    # Show next task
    next_task = tasks_done + 1
    
    if next_task <= 3:
        # Code-based tasks
        url_key = f"MONETAG_AD_URL_{next_task}"
        task_url = os.getenv(url_key, "https://monetag.com")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🔗 Open Task {next_task}", url=task_url)]
        ])
        
        # Set flag that user is expecting code
        context.user_data['waiting_for_code'] = True
        context.user_data['current_task'] = next_task
        
        await update.message.reply_text(
            f"📋 <b>Task {next_task}/4</b>\n\n"
            f"💰 <b>Reward:</b> +25 Rs\n"
            f"🔑 <b>Find the secret code in the ad</b>\n"
            f"📝 <b>Type the code here to complete task</b>\n\n"
            f"👇 Click to open ad:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    
    else:  # Task 4 - Final task (no code needed)
        final_url = os.getenv("MONETAG_FINAL_TASK_URL", "https://monetag.com")
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Complete Final Task", url=final_url)]
        ])
        
        # Mark task 4 as in progress
        context.user_data['waiting_for_final_task'] = True
        context.user_data['final_task_start_time'] = datetime.now()
        
        await update.message.reply_text(
            f"📋 <b>Final Task 4/4</b>\n\n"
            f"💰 <b>Reward:</b> +25 Rs\n"
            f"⏰ <b>Click below to complete</b>\n"
            f"⏱️ <b>Wait 1 minute, then type 'done' in chat</b>\n\n"
            f"👇 Click to complete:",
            reply_markup=keyboard,
            parse_mode='HTML'
        )

async def submit_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /code command - show daily codes to admin"""
    user_id = update.effective_user.id
    admin_id = int(os.getenv("ADMIN_ID", "7836675446"))
    
    # Admin only
    if user_id != admin_id:
        await update.message.reply_text(
            "❌ <b>Admin only command!</b>",
            parse_mode='HTML'
        )
        return
    
    # Generate codes if not exist
    codes = await db.get_daily_codes()
    
    if not codes or len(codes) < 3:
        await db.generate_daily_codes()
        codes = await db.get_daily_codes()
    
    if not codes:
        await update.message.reply_text("❌ Error generating codes!")
        return
    
    # Format message for admin
    msg = f"📋 <b>TODAY'S TASK CODES ({date.today().isoformat()})</b>\n\n"
    
    for code_data in codes:
        task_num = code_data.get("task_number")
        secret = code_data.get("secret_code")
        url_key = f"MONETAG_AD_URL_{task_num}"
        task_url = os.getenv(url_key, "https://monetag.com")
        
        msg += f"<b>Task {task_num}:</b> <code>{secret}</code>\n"
        msg += f"Link: <a href='{task_url}'>Open Link {task_num}</a>\n"
        msg += f"👉 <b>Add code to this link</b>\n\n"
    
    msg += f"ℹ️ <b>Instructions:</b>\n"
    msg += f"• Add codes to Monetag links above\n"
    msg += f"• Users will find codes in ads\n"
    msg += f"• Each user can use each code ONCE\n"
    msg += f"• Multiple users can use same code\n"
    msg += f"• Codes valid for 24 hours\n"
    msg += f"• Tomorrow new codes will be generated"
    
    await update.message.reply_text(msg, parse_mode='HTML')

async def verify_task_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify code from user - ONLY IF WAITING FOR CODE/TASK"""
    user_id = update.effective_user.id
    user_input = update.message.text.strip().upper()
    
    # ============================================
    # CRITICAL: Only process if waiting for code or task
    # ============================================
    # If not waiting for code or final task, skip (let payment handler catch it)
    if not context.user_data.get('waiting_for_code') and not context.user_data.get('waiting_for_final_task'):
        return  # ← EXIT - not a task/code message, pass to next handler
    
    # ============================================
    # Check if waiting for code (Task 1-3)
    # ============================================
    if context.user_data.get('waiting_for_code'):
        current_task = context.user_data.get('current_task', 1)
        
        # Verify code (includes user_id for per-user tracking)
        code_check = await db.check_task_code(user_input, user_id)
        
        if not code_check.get("valid"):
            await update.message.reply_text(
                f"❌ <b>Invalid code!</b>\n\n"
                f"❌ {code_check.get('reason')}\n\n"
                f"💡 Make sure you copied the code correctly from the ad.",
                parse_mode='HTML'
            )
            return
        
        # Code valid - mark as used BY THIS USER
        code_id = code_check.get("code_id")
        task_number = code_check.get("task_number")
        
        await db.mark_code_used(code_id, user_id)
        
        # Update user progress
        user_tasks = await db.get_user_daily_tasks(user_id)
        if user_tasks:
            tasks_done = user_tasks.get("tasks_completed", 0) + 1
        else:
            tasks_done = 1
        
        pending = tasks_done * TASK_REWARD_PER_TASK
        
        await db.create_or_update_daily_task(user_id, tasks_done, pending)
        
        # Clear waiting flag
        context.user_data['waiting_for_code'] = False
        
        # Show completion message
        total_completed = tasks_done
        total_progress = f"{total_completed * TASK_REWARD_PER_TASK:.0f}/{TOTAL_REWARD:.0f} Rs"
        
        if total_completed < MAX_TASKS:
            await update.message.reply_text(
                f"✅ <b>Task {total_completed}/4 completed!</b>\n\n"
                f"💰 <b>+25 Rs earned with this task</b>\n"
                f"📊 <b>Total progress: {total_progress}</b>\n\n"
                f"💡 <b>Complete all tasks to get rewarded!</b>\n\n"
                f"👇 Click Tasks button for next task:",
                parse_mode='HTML'
            )
        
        return
    
    # ============================================
    # Check if waiting for final task completion
    # ============================================
    if context.user_data.get('waiting_for_final_task'):
        if user_input == 'DONE':
            # Check if 1 minute has passed
            start_time = context.user_data.get('final_task_start_time')
            if not start_time:
                await update.message.reply_text(
                    "❌ <b>Please click the task link first!</b>",
                    parse_mode='HTML'
                )
                return
            
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed < 60:
                remaining = 60 - int(elapsed)
                await update.message.reply_text(
                    f"⏳ <b>Please wait {remaining} more seconds...</b>",
                    parse_mode='HTML'
                )
                return
            
            # ============================================
            # 1 minute passed - complete all tasks
            # ============================================
            try:
                # Get user current balance
                user = await db.get_user(user_id)
                current_balance = float(user.get("balance", 0))
                new_balance = current_balance + TOTAL_REWARD
                
                # Update balance in database (NO AWAIT - direct Supabase call)
                db.client.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
                print(f"💰 User {user_id}: Task reward +{TOTAL_REWARD} = {new_balance}")
                
                # Add 5% commission to referrer (if exists)
                referral_response = db.client.table("referral_history").select("referrer_id").eq("new_user_id", user_id).execute()
                if referral_response.data:
                    referrer_id = referral_response.data[0]["referrer_id"]
                    commission = TOTAL_REWARD * 0.05
                    referrer = await db.get_user(referrer_id)
                    referrer_balance = float(referrer.get("balance", 0))
                    new_referrer_balance = referrer_balance + commission
                    db.client.table("users").update({"balance": new_referrer_balance}).eq("user_id", referrer_id).execute()
                    print(f"🤝 COMMISSION: {user_id} earned {TOTAL_REWARD} → {referrer_id} gets {commission:.2f} Rs")
                
                # Reset daily tasks to completed
                await db.create_or_update_daily_task(user_id, MAX_TASKS, 0)
                
                # Clear flags
                context.user_data['waiting_for_final_task'] = False
                context.user_data['final_task_start_time'] = None
                
                await update.message.reply_text(
                    f"🎉 <b>ALL TASKS COMPLETED!</b>\n\n"
                    f"💰 <b>+100 Rs added to main balance!</b>\n"
                    f"💳 <b>Your new balance: {new_balance:.1f} Rs</b>\n\n"
                    f"✨ <b>Come back tomorrow for more tasks!</b>",
                    parse_mode='HTML'
                )
                
                print(f"✅ User {user_id} completed all 4 tasks! Balance: {new_balance}")
                
            except Exception as e:
                print(f"❌ Task completion error: {e}")
                await update.message.reply_text(
                    f"❌ <b>Error completing task!</b>\n\n"
                    f"Please try again.",
                    parse_mode='HTML'
                )
        else:
            await update.message.reply_text(
                "⏱️ <b>Task is running...</b>\n\n"
                "Type 'done' when you finish the task.",
                parse_mode='HTML'
            )
        return

# Handler for tasks button
tasks_handler = MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks)

# Handler for /code command (admin)
code_command = CommandHandler("code", submit_code)

# Handler for code/task submission - checks context internally
code_submit = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    verify_task_code
)
