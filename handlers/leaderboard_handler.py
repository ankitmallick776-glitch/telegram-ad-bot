from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.supabase import db

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = await db.get_leaderboard(5)
    
    if not top_users:
        await update.message.reply_text("🏆 No users yet! Be the first!")
        return
    
    message = "🏆 **TOP 5 RICHEST USERS**\n\n"
    for i, user in enumerate(top_users, 1):
        username = user['username'] or f"User #{user['user_id']}"
        message += f"{i}. {username}\n💰 **₹{user['balance']:.1f}**\n\n"
    
    keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="leaderboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await leaderboard(update, context)
