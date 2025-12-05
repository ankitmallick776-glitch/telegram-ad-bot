from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.supabase import db
import os
from datetime import date, timedelta

ADMIN_ID = int(os.getenv("ADMIN_ID", "7836675446"))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin broadcast to all active users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ **Admin only!**")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 **BROADCAST USAGE:**\n\n"
            "`/broadcast Hello everyone!`"
        )
        return
    
    active_users = await db.get_active_users()
    total_users = len(active_users)
    
    if total_users == 0:
        await update.message.reply_text("❌ No active users!")
        return
    
    message = " ".join(context.args)
    await update.message.reply_text(f"📤 **Starting broadcast...**\n👥 **Active users:** {total_users}")
    
    success_count = 0
    failed_count = 0
    
    for i, user_id in enumerate(active_users, 1):
        try:
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
            success_count += 1
        except:
            failed_count += 1
        
        if i % 100 == 0 or i == total_users:
            progress = f"📊 **Progress:** {i}/{total_users}\n✅ **Sent:** {success_count}\n❌ **Failed:** {failed_count}"
            await update.message.reply_text(progress)
    
    await update.message.reply_text(
        f"✅ **Broadcast COMPLETE!**\n\n"
        f"👥 **Total:** {total_users}\n"
        f"✅ **Delivered:** {success_count}\n"
        f"❌ **Failed:** {failed_count}\n"
        f"📈 **Success Rate:** {(success_count/total_users*100):.1f}%"
    )

async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin cleanup - remove blocked/deleted users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ **Admin only!**")
        return
    
    await update.message.reply_text("🔍 **Scanning users...**")
    
    all_user_ids = await db.get_all_user_ids()
    total_users = len(all_user_ids)
    
    if total_users == 0:
        await update.message.reply_text("❌ No users found!")
        return
    
    await update.message.reply_text(f"🔍 **Found {total_users} users... Testing connections**")
    
    deleted_count = 0
    alive_count = 0
    
    for i, user_id in enumerate(all_user_ids, 1):
        try:
            await context.bot.send_chat_action(chat_id=user_id, action="typing")
            alive_count += 1
        except:
            if await db.delete_user(user_id):
                deleted_count += 1
        
        if i % 50 == 0 or i == total_users:
            progress = (
                f"🔄 **Cleanup Progress:** {i}/{total_users}\n"
                f"🧹 **Deleted:** {deleted_count}\n"
                f"✅ **Alive:** {alive_count}"
            )
            status_msg = await update.message.reply_text(progress)
            await asyncio.sleep(0.1)  # Prevent spam
    
    await update.message.reply_text(
        f"✅ **CLEANUP COMPLETE!**\n\n"
        f"📊 **Total Scanned:** {total_users}\n"
        f"🧹 **Deleted:** {deleted_count}\n"
        f"✅ **Kept:** {alive_count}\n"
        f"📉 **Cleaned:** {(deleted_count/total_users*100):.1f}%"
    )

# Export handlers
broadcast_handler = CommandHandler("broadcast", broadcast)
cleanup_handler = CommandHandler("cleanup", cleanup)
