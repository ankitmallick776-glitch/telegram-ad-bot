from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from utils.supabase import db
import os
import asyncio
from datetime import date, timedelta

ADMIN_ID = int(os.getenv("ADMIN_ID", "7836675446"))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(
        f"📤 <b>Starting broadcast...</b>\n👥 <b>Active users:</b> {total_users}",
        parse_mode='HTML'
    )
    
    success_count = 0
    failed_count = 0
    
    for i, user_id in enumerate(active_users, 1):
        try:
            await context.bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
            success_count += 1
        except:
            failed_count += 1
        
        if i % 100 == 0 or i == total_users:
            progress = (
                f"📊 <b>Progress:</b> {i}/{total_users}\n"
                f"✅ <b>Sent:</b> {success_count}\n"
                f"❌ <b>Failed:</b> {failed_count}"
            )
            await update.message.reply_text(progress, parse_mode='HTML')
    
    await update.message.reply_text(
        f"✅ <b>Broadcast COMPLETE!</b>\n\n"
        f"👥 <b>Total:</b> {total_users}\n"
        f"✅ <b>Delivered:</b> {success_count}\n"
        f"❌ <b>Failed:</b> {failed_count}\n"
        f"📈 <b>Success Rate:</b> {(success_count/total_users*100):.1f}%",
        parse_mode='HTML'
    )

async def cleanup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ <b>Admin only!</b>", parse_mode='HTML')
        return
    
    await update.message.reply_text("🔍 <b>Scanning users...</b>", parse_mode='HTML')
    
    all_user_ids = await db.get_all_user_ids()
    total_users = len(all_user_ids)
    
    if total_users == 0:
        await update.message.reply_text("❌ <b>No users found!</b>", parse_mode='HTML')
        return
    
    await update.message.reply_text(
        f"🔍 <b>Found {total_users} users...</b> Testing connections",
        parse_mode='HTML'
    )
    
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
                f"🔄 <b>Cleanup Progress:</b> {i}/{total_users}\n"
                f"🧹 <b>Deleted:</b> {deleted_count}\n"
                f"✅ <b>Alive:</b> {alive_count}"
            )
            await update.message.reply_text(progress, parse_mode='HTML')
            await asyncio.sleep(0.1)
    
    await update.message.reply_text(
        f"✅ <b>CLEANUP COMPLETE!</b>\n\n"
        f"📊 <b>Total Scanned:</b> {total_users}\n"
        f"🧹 <b>Deleted:</b> {deleted_count}\n"
        f"✅ <b>Kept:</b> {alive_count}\n"
        f"📉 <b>Cleaned:</b> {(deleted_count/total_users*100):.1f}%",
        parse_mode='HTML'
    )

broadcast_handler = CommandHandler("broadcast", broadcast)
cleanup_handler = CommandHandler("cleanup", cleanup)
