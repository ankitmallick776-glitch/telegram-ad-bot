from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.supabase import db
import os
import asyncio
from datetime import date, timedelta

ADMIN_ID = int(os.getenv("ADMIN_ID", "7836675446"))

# Global variable to store failed users from broadcast
failed_broadcast_users = []

async def broadcast_task(context, admin_id, message, active_users):
    """Run broadcast in background and track failed users"""
    global failed_broadcast_users
    
    success_count = 0
    failed_count = 0
    total_users = len(active_users)
    failed_broadcast_users = []  # Reset before broadcast
    
    for i, user_id in enumerate(active_users, 1):
        try:
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            success_count += 1
        except:
            failed_count += 1
            failed_broadcast_users.append(user_id)  # Store failed user
        
        # Delay every 30 messages to avoid rate limit
        if i % 30 == 0:
            await asyncio.sleep(1)
    
    # Send final report to admin
    try:
        await context.bot.send_message(
            admin_id,
            f"✅ <b>Broadcast COMPLETE!</b>\n\n"
            f"👥 <b>Total:</b> {total_users}\n"
            f"✅ <b>Delivered:</b> {success_count}\n"
            f"❌ <b>Failed:</b> {failed_count}\n"
            f"📈 <b>Success Rate:</b> {(success_count/total_users*100):.1f}%\n\n"
            f"💡 Run /cleanup to remove the {failed_count} failed users",
            parse_mode='HTML'
        )
    except:
        pass

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast in background"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ <b>Admin only!</b>", parse_mode='HTML')
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 <b>BROADCAST USAGE:</b>\n\n"
            "<code>/broadcast Hello everyone!</code>",
            parse_mode='HTML'
        )
        return
    
    active_users = await db.get_active_users()
    total_users = len(active_users)
    
    if total_users == 0:
        await update.message.reply_text("❌ <b>No active users!</b>", parse_mode='HTML')
        return
    
    message = " ".join(context.args)
    
    # Check if broadcast already running
    if 'broadcast_running' in context.bot_data and context.bot_data['broadcast_running']:
        await update.message.reply_text(
            "⚠️ <b>Broadcast already running!</b>\n\n"
            "Wait for it to complete before starting another.",
            parse_mode='HTML'
        )
        return
    
    # Mark broadcast as running
    context.bot_data['broadcast_running'] = True
    
    await update.message.reply_text(
        f"📤 <b>Broadcast STARTED in background!</b>\n\n"
        f"👥 <b>Active users:</b> {total_users}\n"
        f"📨 <b>Message:</b> {message[:50]}...\n\n"
        f"⏳ You can use other features while broadcasting!\n"
        f"Final report will be sent when complete.",
        parse_mode='HTML'
    )
    
    # Run broadcast in background (non-blocking)
    asyncio.create_task(broadcast_task_wrapper(context, update.effective_user.id, message, active_users))

async def broadcast_task_wrapper(context, admin_id, message, active_users):
    """Wrapper to handle background task"""
    try:
        await broadcast_task(context, admin_id, message, active_users)
    finally:
        context.bot_data['broadcast_running'] = False

async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete users who failed during last broadcast"""
    global failed_broadcast_users
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ <b>Admin only!</b>", parse_mode='HTML')
        return
    
    if 'cleanup_running' in context.bot_data and context.bot_data['cleanup_running']:
        await update.message.reply_text(
            "⚠️ <b>Cleanup already running!</b>\n\n"
            "Wait for it to complete.",
            parse_mode='HTML'
        )
        return
    
    # Check if we have failed users from broadcast
    if not failed_broadcast_users or len(failed_broadcast_users) == 0:
        await update.message.reply_text(
            "ℹ️ <b>No failed users to cleanup!</b>\n\n"
            "Run /broadcast first, then /cleanup to remove blocked users.",
            parse_mode='HTML'
        )
        return
    
    context.bot_data['cleanup_running'] = True
    
    total_to_delete = len(failed_broadcast_users)
    await update.message.reply_text(
        f"🧹 <b>Cleanup STARTED!</b>\n\n"
        f"Removing {total_to_delete} blocked users from broadcast..."
    )
    
    asyncio.create_task(cleanup_task_wrapper(context, update.effective_user.id))

async def cleanup_task_wrapper(context, admin_id):
    """Background cleanup - delete users who failed broadcast"""
    global failed_broadcast_users
    
    try:
        total_to_delete = len(failed_broadcast_users)
        deleted_count = 0
        
        await context.bot.send_message(
            admin_id,
            f"🧹 <b>Deleting {total_to_delete} blocked users from database...</b>",
            parse_mode='HTML'
        )
        
        for i, user_id in enumerate(failed_broadcast_users, 1):
            try:
                if await db.delete_user(user_id):
                    deleted_count += 1
            except:
                pass
            
            # Delay every 20 deletes
            if i % 20 == 0:
                await asyncio.sleep(0.5)
            
            # Send progress every 50 deletes
            if i % 50 == 0 or i == total_to_delete:
                progress = (
                    f"🔄 <b>Cleanup Progress:</b> {i}/{total_to_delete}\n"
                    f"🗑️ <b>Deleted:</b> {deleted_count}"
                )
                try:
                    await context.bot.send_message(admin_id, progress, parse_mode='HTML')
                except:
                    pass
        
        # Get new total user count
        all_users = await db.get_all_user_ids()
        remaining_users = len(all_users)
        
        await context.bot.send_message(
            admin_id,
            f"✅ <b>CLEANUP COMPLETE!</b>\n\n"
            f"🗑️ <b>Deleted:</b> {deleted_count}\n"
            f"👥 <b>Remaining Active Users:</b> {remaining_users}\n"
            f"📉 <b>Removed:</b> {(deleted_count/total_to_delete*100):.1f}% of failed users\n\n"
            f"💡 Database cleaned! Ready for next broadcast.",
            parse_mode='HTML'
        )
        
        # Clear failed users list after cleanup
        failed_broadcast_users = []
        
    finally:
        context.bot_data['cleanup_running'] = False

broadcast_handler = CommandHandler("broadcast", broadcast)
cleanup_handler = CommandHandler("cleanup", cleanup)
