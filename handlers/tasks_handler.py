# handlers/tasks_handler.py

from telegram import Update
from telegram.ext import ContextTypes

async def tasks_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Temporary placeholder for Tasks feature."""
    await update.message.reply_text(
        "<b>📋 Tasks Coming Soon!</b>\n\n"
        "🚧 Our new tasks system is under development.\n"
        "✅ Watch ads and use referrals to keep earning in the meantime!",
        parse_mode="HTML"
    )

# Dummy placeholders so imports from main.py do not fail
code_command = None
code_submit = None
