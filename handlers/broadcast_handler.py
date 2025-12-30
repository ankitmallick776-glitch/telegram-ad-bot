from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.supabase import db
import os
import asyncio

ADMIN_ID = int(os.getenv("ADMIN_ID", 7836675446))

# Store failed users from broadcast
failed_broadcast_users = []

async def broadcast_task(context, admin_id, message, active_users):
    """Run broadcast in background"""
    global failed_broadcast_users
    success_count = 0
    failed_count = 0
    total_users = len(active_users)
    failed_broadcast_users = []
    
    for i, user_id in enumerate(active_users, 1):
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            success_count += 1
        except:
            failed_count += 1
            failed_broadcast_users.append(user_id)
        
        # Rate limit - delay every 30 messages
        if i % 30 == 0:
            await asyncio.sleep(1)
    
    try:
        await context.bot.send_message(
            admin_id,
            f"✅ <b>Broadcast COMPLETE!</b>\n\n"
            f"<b>Total:</b> {total_users}\n"
            f"<b>Delivered:</b> {success_count}\n"
            f"<b>Failed:</b> {failed_count}\n"
            f"<b>Success Rate:</b> {success_count/total_users*100:.1f}%",
            parse_mode='HTML'
        )
    except:
        pass
    
    context.bot_data['broadcast_running'] = False

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start broadcast"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!", parse_mode='HTML')
        return
    
    if not context.args:
        await update.message.reply_text(
            "<b>BROADCAST USAGE</b>\n\n"
            "`/broadcast Hello everyone!`",
            parse_mode='HTML'
        )
        return
    
    active_users = await db.get_active_users()
    total_users = len(active_users)
    
    if total_users == 0:
        await update.message.reply_text("❌ No active users!", parse_mode='HTML')
        return
    
    if context.bot_data.get('broadcast_running'):
        await update.message.reply_text(
            "⚠️ Broadcast already running!\n\n"
            "Wait for it to complete before starting another.",
            parse_mode='HTML'
        )
        return
    
    message = ' '.join(context.args)
    context.bot_data['broadcast_running'] = True
    
    await update.message.reply_text(
        f"✅ <b>Broadcast STARTED in background!</b>\n\n"
        f"<b>Active users:</b> {total_users}\n"
        f"<b>Message:</b> {message[:50]}...\n\n"
        f"You can use other features while broadcasting!\n"
        f"Final report will be sent when complete.",
        parse_mode='HTML'
    )
    
    # Use job_queue to run broadcast without blocking
    context.job_queue.run_once(
        lambda ctx: asyncio.create_task(broadcast_task(ctx, update.effective_user.id, message, active_users)),
        0
    )

async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete users who failed during broadcast"""
    global failed_broadcast_users
    
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!", parse_mode='HTML')
        return
    
    if context.bot_data.get('cleanup_running'):
        await update.message.reply_text(
            "⚠️ Cleanup already running!\n\n"
            "Wait for it to complete.",
            parse_mode='HTML'
        )
        return
    
    if not failed_broadcast_users or len(failed_broadcast_users) == 0:
        await update.message.reply_text(
            "❌ No failed users to cleanup!\n\n"
            "Run /broadcast first, then /cleanup to remove blocked users.",
            parse_mode='HTML'
        )
        return
    
    total_to_delete = len(failed_broadcast_users)
    context.bot_data['cleanup_running'] = True
    
    await update.message.reply_text(
        f"✅ <b>Cleanup STARTED!</b>\n\n"
        f"Removing {total_to_delete} blocked users from database...",
        parse_mode='HTML'
    )
    
    # Run cleanup in background
    context.job_queue.run_once(
        lambda ctx: cleanup_task(ctx, update.effective_user.id),
        0
    )

async def cleanup_task(context, admin_id):
    """Background cleanup - delete failed users"""
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
                progress = f"🧹 <b>Cleanup Progress</b>\n\n<b>Deleted:</b> {i}/{total_to_delete}"
                try:
                    await context.bot.send_message(admin_id, progress, parse_mode='HTML')
                except:
                    pass
        
        all_users = await db.get_all_user_ids()
        remaining_users = len(all_users)
        
        await context.bot.send_message(
            admin_id,
            f"✅ <b>CLEANUP COMPLETE!</b>\n\n"
            f"<b>Deleted:</b> {deleted_count}\n"
            f"<b>Remaining Active Users:</b> {remaining_users}\n"
            f"<b>Removed:</b> {deleted_count/total_to_delete*100:.1f}% of failed users\n\n"
            f"Database cleaned! Ready for next broadcast.",
            parse_mode='HTML'
        )
        
        failed_broadcast_users = []
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    finally:
        context.bot_data['cleanup_running'] = False

# Handlers
broadcast_handler = CommandHandler("broadcast", broadcast)
cleanup_handler = CommandHandler("cleanup", cleanup)
