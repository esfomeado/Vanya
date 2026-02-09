from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

from src.vanya.core.config_loader import CONFIG
from src.vanya.model.account import Account
from src.vanya.telegram.commands import stats_cmd, accounts_cmd, solo_hunt_cmd, say_cmd, train_cmd, phantom_halls_cmd, \
    boss_cmd, auto_hunt_cmd, guild_cmd, auto_guild_cmd, auto_stats_cmd, auto_boss_cmd, auto_items_cmd, market_cmd, \
    auto_coupon_cmd, auto_regenerate_cmd, visage_cmd, deep_dragon_cmd, auto_visage_cmd, auto_lounge_cmd, auto_pub_cmd, \
    auto_sell_cmd


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    pass


async def unknown_cmd(update: object, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Unknown command")


def start_telegram(accounts: list[Account]):
    application = ApplicationBuilder().token(CONFIG.telegram.token).build()
    application.bot_data["accounts"] = accounts

    application.add_error_handler(error_handler)

    application.add_handler(CommandHandler("accounts", accounts_cmd))
    application.add_handler(CommandHandler("auto_boss", auto_boss_cmd))
    application.add_handler(CommandHandler("auto_coupon", auto_coupon_cmd))
    application.add_handler(CommandHandler("auto_guild", auto_guild_cmd))
    application.add_handler(CommandHandler("auto_hunt", auto_hunt_cmd))
    application.add_handler(CommandHandler("auto_items", auto_items_cmd))
    application.add_handler(CommandHandler("auto_lounge", auto_lounge_cmd))
    application.add_handler(CommandHandler("auto_pub", auto_pub_cmd))
    application.add_handler(CommandHandler("auto_regenerate", auto_regenerate_cmd))
    application.add_handler(CommandHandler("auto_regen", auto_regenerate_cmd))
    application.add_handler(CommandHandler("auto_sell", auto_sell_cmd))
    application.add_handler(CommandHandler("auto_stats", auto_stats_cmd))
    application.add_handler(CommandHandler("auto_visage", auto_visage_cmd))
    application.add_handler(CommandHandler("boss", boss_cmd))
    application.add_handler(CommandHandler("deep_dragon", deep_dragon_cmd))
    application.add_handler(CommandHandler("guild", guild_cmd))
    application.add_handler(CommandHandler("market", market_cmd))
    application.add_handler(CommandHandler("phantom_halls", phantom_halls_cmd))
    application.add_handler(CommandHandler("say", say_cmd))
    application.add_handler(CommandHandler("solo_hunt", solo_hunt_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("train", train_cmd))
    application.add_handler(CommandHandler("visage", visage_cmd))

    application.add_handler(MessageHandler(filters.COMMAND, unknown_cmd))

    application.run_polling(bootstrap_retries=-1)
