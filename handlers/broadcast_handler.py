from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.supabase import db
import os

ADMIN_ID = int(os.getenv("ADMIN_ID", 7836675446))
failed_broadcast_users = []

async def broadcast_task(context, admin_id, message, active_users):
    """Run broadcast"""
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
        
        if i % 30 == 0:
            import asyncio
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
            "Wait for it to complete.",
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
    
    context.job_queue.run_once(
        broadcast_task,
        0,
        data={'admin_id': update.effective_user.id, 'message': message, 'active_users': active_users},
        name=f"broadcast_{update.effective_user.id}"
    )

async def cleanup_task(context, admin_id):
    """Delete failed users"""
    global failed_broadcast_users
    
    try:
        total_to_delete = len(failed_broadcast_users)
        deleted_count = 0
        
        await context.bot.send_message(
            admin_id,
            f"🧹 <b>Deleting {total_to_delete} blocked users...</b>",
            parse_mode='HTML'
        )
        
        for i, user_id in enumerate(failed_broadcast_users, 1):
            try:
                if await db.delete_user(user_id):
                    deleted_count += 1
            except:
                pass
            
            if i % 20 == 0:
                import asyncio
                await asyncio.sleep(0.5)
        
        all_users = await db.get_all_user_ids()
        remaining = len(all_users)
        
        await context.bot.send_message(
            admin_id,
            f"✅ <b>CLEANUP COMPLETE!</b>\n\n"
            f"<b>Deleted:</b> {deleted_count}\n"
            f"<b>Remaining:</b> {remaining}",
            parse_mode='HTML'
        )
        
        failed_broadcast_users = []
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
    finally:
        context.bot_data['cleanup_running'] = False

async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start cleanup"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only!", parse_mode='HTML')
        return
    
    if not failed_broadcast_users or len(failed_broadcast_users) == 0:
        await update.message.reply_text(
            "❌ No failed users!\n\n"
            "Run /broadcast first, then /cleanup.",
            parse_mode='HTML'
        )
        return
    
    if context.bot_data.get('cleanup_running'):
        await update.message.reply_text(
            "⚠️ Cleanup already running!",
            parse_mode='HTML'
        )
        return
    
    context.bot_data['cleanup_running'] = True
    total = len(failed_broadcast_users)
    
    await update.message.reply_text(
        f"✅ <b>Cleanup STARTED!</b>\n\n"
        f"Removing {total} users...",
        parse_mode='HTML'
    )
    
    context.job_queue.run_once(
        cleanup_task,
        0,
        data={'admin_id': update.effective_user.id},
        name=f"cleanup_{update.effective_user.id}"
    )

broadcast_handler = CommandHandler("broadcast", broadcast)
cleanup_handler = CommandHandler("cleanup", cleanup)
