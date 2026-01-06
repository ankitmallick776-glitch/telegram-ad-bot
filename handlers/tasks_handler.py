from telegram import Update
from telegram.ext import ContextTypes

async def tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>📋 Tasks Coming Soon!</b>\n\n"
        "🚧 Our new tasks system is under development.\n"
        "✅ Watch ads and use referrals to keep earning in the meantime!",
        parse_mode="HTML"
    )

# For compatibility if main.py uses taskshandler.callback
taskshandler = type("Obj", (), {"callback": tasks_handler})
