from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from src.vanya.core.config_loader import CONFIG
from src.vanya.model.account import Account
from src.vanya.telegram.commands import stats_cmd, accounts_cmd, solo_hunt_cmd, say_cmd, train_cmd, phantom_halls_cmd, \
    boss_cmd


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    pass


def start_telegram(accounts: list[Account]):
    application = ApplicationBuilder().token(CONFIG.telegram.token).build()
    application.bot_data["accounts"] = accounts

    application.add_error_handler(error_handler)

    application.add_handler(CommandHandler("accounts", accounts_cmd))
    application.add_handler(CommandHandler("boss", boss_cmd))
    application.add_handler(CommandHandler("phantom_halls", phantom_halls_cmd))
    application.add_handler(CommandHandler("say", say_cmd))
    application.add_handler(CommandHandler("solo_hunt", solo_hunt_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("train", train_cmd))

    application.run_polling()
