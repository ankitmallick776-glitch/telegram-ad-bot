from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from utils.supabase import db

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    top_users = await db.get_leaderboard(5)
    if not top_users:
        await update.message.reply_text("🏆 No users yet!")
        return

    message = "🏆 **TOP 5 RICHEST**\n\n"
    for i, user in enumerate(top_users, 1):
        username = user['username'] or f"User #{user['user_id']}"
        message += f"{i}. {username}\n💰 ₹{user.get('balance', 0):.1f}\n\n"

    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 Refresh", callback_data="leaderboard")]])
    await update.message.reply_text(message, reply_markup=keyboard, parse_mode='Markdown')

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await leaderboard(update, context)

leaderboard_handler = CommandHandler("leaderboard", leaderboard)
leaderboard_callback_handler = CallbackQueryHandler(leaderboard_callback, pattern="^leaderboard$")
