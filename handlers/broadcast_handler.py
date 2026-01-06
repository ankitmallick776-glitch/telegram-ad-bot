from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.supabase import db
import os
import asyncio
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

ADMIN_ID = int(os.getenv("ADMIN_ID", "7836675446"))

# Thread-safe storage for failed users (better than global)
failed_broadcast_users = []

async def broadcast_task(context, admin_id: int, message: str, active_users: list):
    """Run broadcast in background and track failed users"""
    global failed_broadcast_users
    
    success_count = 0
    failed_count = 0
    total_users = len(active_users)
    
    # Reset failed list
    failed_broadcast_users = []
    
    for i, user_id in enumerate(active_users, 1):
        try:
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            success_count += 1
        except Exception as e:
            failed_count += 1
            failed_broadcast_users.append(user_id)
            logger.warning(f"Broadcast failed for {user_id}: {e}")
        
        # Rate limit: 30 msg/sec
        if i % 30 == 0:
            await asyncio.sleep(1)
    
    # Final report
    try:
        success_rate = (success_count / total_users * 100) if total_users > 0 else 0
        await context.bot.send_message(
            admin_id,
            f"✅ <b>Broadcast COMPLETE!</b>\n\n"
            f"👥 <b>Total:</b> {total_users:,}\n"
            f"✅ <b>Delivered:</b> {success_count:,}\n"
            f"❌ <b>Failed:</b> {failed_count:,}\n"
            f"📈 <b>Success Rate:</b> {success_rate:.1f}%\n\n"
            f"💡 Run <code>/cleanup</code> to remove {failed_count:,} failed users",
            parse_mode='HTML'
        )
        logger.info(f"Broadcast complete: {success_count}/{total_users} ({success_rate:.1f}%)")
    except Exception as e:
        logger.error(f"Final report error: {e}")

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
    
    # Check running status
    if context.bot_data.get('broadcast_running', False):
        await update.message.reply_text(
            "⚠️ <b>Broadcast already running!</b>\n\n"
            "Wait for it to complete before starting another.",
            parse_mode='HTML'
        )
        return
    
    # Mark as running
    context.bot_data['broadcast_running'] = True
    
    await update.message.reply_text(
        f"📤 <b>Broadcast STARTED</b> (background)\n\n"
        f"👥 Active users: {total_users:,}\n"
        f"📨 Message: <i>{message[:50]}...</i>\n\n"
        f"⏳ You can use other features!\n"
        f"📊 Final report when complete.",
        parse_mode='HTML'
    )
    
    # Non-blocking background task
    asyncio.create_task(broadcast_task_wrapper(context, update.effective_user.id, message, active_users))

async def broadcast_task_wrapper(context, admin_id: int, message: str, active_users: list):
    """Wrapper to clean up running flag"""
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
    
    if context.bot_data.get('cleanup_running', False):
        await update.message.reply_text(
            "⚠️ <b>Cleanup already running!</b>\n\n"
            "Wait for it to complete.",
            parse_mode='HTML'
        )
        return
    
    if not failed_broadcast_users or len(failed_broadcast_users) == 0:
        await update.message.reply_text(
            "ℹ️ <b>No failed users to cleanup!</b>\n\n"
            "Run <code>/broadcast</code> first, then <code>/cleanup</code>.",
            parse_mode='HTML'
        )
        return
    
    context.bot_data['cleanup_running'] = True
    total_to_delete = len(failed_broadcast_users)
    
    await update.message.reply_text(
        f"🧹 <b>Cleanup STARTED!</b>\n\n"
        f"Removing {total_to_delete:,} blocked users..."
    )
    
    asyncio.create_task(cleanup_task_wrapper(context, update.effective_user.id))

async def cleanup_task_wrapper(context, admin_id: int):
    """Background cleanup task"""
    global failed_broadcast_users
    
    try:
        total_to_delete = len(failed_broadcast_users)
        deleted_count = 0
        
        await context.bot.send_message(
            admin_id,
            f"🧹 Deleting {total_to_delete:,} blocked users...",
            parse_mode='HTML'
        )
        
        for i, user_id in enumerate(failed_broadcast_users, 1):
            try:
                if await db.delete_user(user_id):
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Cleanup delete {user_id} failed: {e}")
            
            # Rate limit deletes
            if i % 20 == 0:
                await asyncio.sleep(0.5)
            
            # Progress updates
            if i % 50 == 0 or i == total_to_delete:
                progress = f"🔄 <b>Cleanup Progress:</b> {i:,}/{total_to_delete:,}\n🗑️ <b>Deleted:</b> {deleted_count:,}"
                try:
                    await context.bot.send_message(admin_id, progress, parse_mode='HTML')
                except:
                    pass
        
        # Final stats
        all_users = await db.get_all_user_ids()
        remaining_users = len(all_users)
        removal_rate = (deleted_count / total_to_delete * 100) if total_to_delete > 0 else 0
        
        await context.bot.send_message(
            admin_id,
            f"✅ <b>CLEANUP COMPLETE!</b>\n\n"
            f"🗑️ <b>Deleted:</b> {deleted_count:,}\n"
            f"👥 <b>Remaining Users:</b> {remaining_users:,}\n"
            f"📉 <b>Removed:</b> {removal_rate:.1f}% of failed\n\n"
            f"💡 Database cleaned! Ready for next broadcast.",
            parse_mode='HTML'
        )
        
        # Clear list
        failed_broadcast_users = []
        logger.info(f"Cleanup complete: {deleted_count}/{total_to_delete}")
        
    except Exception as e:
        logger.error(f"Cleanup task error: {e}")
    finally:
        context.bot_data['cleanup_running'] = False

# Export handlers
broadcast_handler = CommandHandler("broadcast", broadcast)
cleanup_handler = CommandHandler("cleanup", cleanup)
