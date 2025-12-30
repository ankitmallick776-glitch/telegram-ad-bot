from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.supabase import db
from datetime import datetime, timedelta
import os

TASK_REWARD = 80.0
TASK_DURATION = 30
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
    
    # Start first task
    context.user_data['tasks_completed'] = 0
    context.user_data['task_start_time'] = datetime.now()
    context.user_data['current_task'] = 1
    
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
        f"3️⃣ Return here and click next task\n\n"
        f"⚠️ <b>You must wait 30 seconds!</b>\n\n"
        f"👇 <b>Start Task 1:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    context.user_data['task_start_time'] = datetime.now()
    context.user_data['current_task'] = 1

async def show_task_2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Task 2"""
    user_id = update.effective_user.id
    link = os.getenv("TASK_LINK_2", "https://adsterra.com")
    keyboard = [[InlineKeyboardButton("🔗 Open Task 2 (Stay 30s)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ <b>Task 1 Complete!</b>\n\n"
        f"📋 <b>TASK 2/4</b>\n\n"
        f"💰 <b>Reward so far: 0 Rs</b>\n\n"
        f"⏱️ <b>Stay 30 seconds on link</b>\n\n"
        f"👇 <b>Continue:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    context.user_data['task_start_time'] = datetime.now()
    context.user_data['current_task'] = 2

async def show_task_3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Task 3"""
    user_id = update.effective_user.id
    link = os.getenv("TASK_LINK_3", "https://monetag.com")
    keyboard = [[InlineKeyboardButton("🔗 Open Task 3 (Stay 30s)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ <b>Task 2 Complete!</b>\n\n"
        f"📋 <b>TASK 3/4</b>\n\n"
        f"💰 <b>Reward so far: 0 Rs</b>\n\n"
        f"⏱️ <b>Stay 30 seconds on link</b>\n\n"
        f"👇 <b>Continue:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    context.user_data['task_start_time'] = datetime.now()
    context.user_data['current_task'] = 3

async def show_task_4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show Task 4 - Final"""
    user_id = update.effective_user.id
    link = os.getenv("TASK_LINK_4", "https://adsterra.com")
    keyboard = [[InlineKeyboardButton("🔗 Open Task 4 (Stay 30s)", url=link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ <b>Task 3 Complete!</b>\n\n"
        f"📋 <b>TASK 4/4 - FINAL!</b>\n\n"
        f"💰 <b>Reward so far: 0 Rs</b>\n\n"
        f"⏱️ <b>Stay 30 seconds on link</b>\n\n"
        f"After this, you get +80 Rs! 🎉\n\n"
        f"👇 <b>Complete:</b>",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    context.user_data['task_start_time'] = datetime.now()
    context.user_data['current_task'] = 4

async def check_task_completion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manual check - user clicks button to verify task"""
    user_id = update.effective_user.id
    current_task = context.user_data.get('current_task', 1)
    start_time = context.user_data.get('task_start_time')
    
    if not start_time:
        await update.message.reply_text("⚠️ Please start task first!", parse_mode='HTML')
        return
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    if elapsed < TASK_DURATION:
        remaining = int(TASK_DURATION - elapsed)
        await update.message.reply_text(
            f"⏳ <b>Please wait {remaining} more seconds...</b>\n\n"
            f"⏰ Timer: {int(elapsed)}/{TASK_DURATION}s",
            parse_mode='HTML'
        )
        return
    
    # Task completed
    if current_task >= MAX_TASKS:
        await give_final_reward(update, context, user_id)
    else:
        if current_task == 1:
            await show_task_2(update, context)
        elif current_task == 2:
            await show_task_3(update, context)
        elif current_task == 3:
            await show_task_4(update, context)

async def give_final_reward(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
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
        
        await update.message.reply_text(
            f"🎉 <b>ALL 4 TASKS COMPLETED!</b>\n\n"
            f"💰 <b>+80 Rs added to balance!</b>\n"
            f"💳 <b>New balance: ₹{new_balance:.1f}</b>\n\n"
            f"⏳ <b>Next tasks in 3 hours</b>\n\n"
            f"🔥 Share with friends for more!",
            parse_mode='HTML'
        )
        print(f"✅ User {user_id}: +80 Rs - ALL TASKS DONE!")
        
        # Clear task data
        context.user_data.clear()
        
    except Exception as e:
        print(f"❌ Reward error: {e}")
        await update.message.reply_text("❌ Reward error!", parse_mode='HTML')

# Handler
tasks_handler = MessageHandler(filters.Regex("^(Tasks 📋)$"), tasks_menu)
