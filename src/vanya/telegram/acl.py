from telegram import Update

from src.vanya.core.config_loader import CONFIG


def allowed(update: Update) -> bool:
    user = update.effective_user
    return user is not None and user.id in CONFIG.telegram.allowed_users
