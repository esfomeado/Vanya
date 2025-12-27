from telegram import Update
from telegram.ext import ContextTypes

from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.boss_service import BossService
from src.vanya.service.chat_service import ChatService
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.solo_hunt_service import SoloHuntService
from src.vanya.service.training_service import TrainingService
from src.vanya.telegram.acl import allowed


def _find_account(accounts: list[Account], username: str) -> Account | None:
    for account in accounts:
        if account.username == username:
            return account
    return None


async def accounts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Lists all configured accounts and their current operation modes.
    """
    if not allowed(update):
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    lines = ["👥 Accounts"]
    for account in accounts:
        lines.append(f"- {account.username} ({account.mode.value})")

    await update.message.reply_text("\n".join(lines))


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Displays detailed character statistics for a specific account.

    Usage: /stats <account_username>

    Shows level, gold, health, skill levels (Sword, Bow, Magic, etc.),
    and current hunting area information if applicable.
    """
    if not allowed(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /stats <account>")
        return

    accounts: list[Account] = context.application.bot_data["accounts"]
    name = context.args[0]

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    stats = account.stats
    hunt = account.hunt

    lines = [
        f"👤 Account: {account.username}",
        f"🧭 Mode: {account.mode.value}",
        "",
        "📊 Stats",
        f"Level: {stats.level}",
        f"Gold: {stats.gold}",
        f"Health: {stats.health}/{stats.max_health}",
        "",
        "⚔️ Skills",
        f"Sword: {stats.sword}",
        f"Bow: {stats.bow}",
        f"Magic: {stats.magic}",
        f"Defence: {stats.defence}",
        f"Fishing: {stats.fishing}",
    ]

    if hunt:
        lines.extend([
            "",
            "🗡️ Hunting",
            f"Area: {hunt.name}",
            f"Max hit: {hunt.max_hit}",
        ])

    await update.message.reply_text("\n".join(lines))


async def solo_hunt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/solo_hunt <account> start [area_id]\n"
            "/solo_hunt <account> stop"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    name = context.args[0]
    action = context.args[1]
    area_id = context.args[2] if len(context.args) > 2 else None

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    if action == "stop":
        if account.mode != Mode.SOLO_HUNT:
            await update.message.reply_text(f"{name} is not solo hunting")
            return

        service_registry.get(SoloHuntService, account).stop_hunt()

        await update.message.reply_text(f"{name} stopped solo hunting")
        return

    if action != "start":
        await update.message.reply_text(
            "Usage:\n"
            "/solo_hunt <account> start [area_id]\n"
            "/solo_hunt <account> stop"
        )
        return

    if account.mode == Mode.SOLO_HUNT:
        hunt = account.hunt
        await update.message.reply_text(
            f"{name} already hunting\n{hunt.name}"
        )
        return

    if account.mode == Mode.PHANTOM_HALLS:
        service_registry.get(PhantomHallsService, account).stop_hunt()

    try:
        service_registry.get(SoloHuntService, account).hunt(area_id=area_id)
        hunt = account.hunt

        await update.message.reply_text(
            f"🗡️ {name} started solo hunting\n\n"
            f"Area: {hunt.name}\n"
            f"Max hit: {hunt.max_hit}"
        )

    except Exception as e:
        account.hunt = None
        account.mode = Mode.IDLE
        await update.message.reply_text(
            f"Failed to start solo hunt for {name}:\n{e}"
        )


async def phantom_halls_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/phantom_halls <account> start [area_id]\n"
            "/phantom_halls <account> stop"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    name = context.args[0]
    action = context.args[1]
    area_id = context.args[2] if len(context.args) > 2 else None

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    if action == "stop":
        if account.mode != Mode.PHANTOM_HALLS:
            await update.message.reply_text(f"{name} is not on phantom halls")
            return

        service_registry.get(PhantomHallsService, account).stop_hunt()

        await update.message.reply_text(f"{name} stopped phantom halls")
        return

    if action != "start":
        await update.message.reply_text(
            "Usage:\n"
            "/phantom_halls <account> start [area_id]\n"
            "/phantom_halls <account> stop"
        )
        return

    if account.mode == Mode.PHANTOM_HALLS:
        hunt = account.hunt
        await update.message.reply_text(
            f"{name} already hunting\n{hunt.name}"
        )
        return

    if account.mode == Mode.SOLO_HUNT:
        service_registry.get(SoloHuntService, account).stop_hunt()

    try:
        service_registry.get(PhantomHallsService, account).hunt(area_id=area_id)
        hunt = account.hunt

        await update.message.reply_text(
            f"🗡️ {name} started Phantom Halls\n\n"
            f"Area: {hunt.name}\n"
            f"Max hit: {hunt.max_hit}"
        )

    except Exception as e:
        account.hunt = None
        account.mode = Mode.IDLE
        await update.message.reply_text(
            f"Failed to start phantom Halls for {name}:\n{e}"
        )


async def say_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Sends a message to the chat.
    """
    if not allowed(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /say <account> <message>"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    name = context.args[0]
    message = " ".join(context.args[1:]).strip()

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    if not message:
        await update.message.reply_text("Message cannot be empty")
        return

    try:
        service_registry.get(ChatService, account).post_message(message)
        await update.message.reply_text(
            f"💬 Message sent as {name}"
        )

    except Exception as e:
        await update.message.reply_text(
            f"Failed to send message as {name}:\n{e}"
        )


async def train_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /train <account> <skill>"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    name = context.args[0]
    skill = context.args[1]

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    if account.mode not in {Mode.IDLE, Mode.TRAINING}:
        await update.message.reply_text(
            f"{name} cannot train while in mode {account.mode.value}"
        )
        return

    try:
        service_registry.get(TrainingService, account).train(skill=skill)

        await update.message.reply_text(
            f"🛡️ {name} started training {skill}"
        )

    except Exception as e:
        await update.message.reply_text(
            f"Failed to start training for {name}:\n{e}"
        )


async def boss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /boss <account> [full]"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    name = context.args[0]
    mode = context.args[1] if len(context.args) > 1 else None

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    boss_service = service_registry.get(BossService, account)

    try:
        bosses = boss_service.list_available_bosses()
        if not bosses:
            await update.message.reply_text(f"{name}: no available bosses")
            return

        lines = []
        for boss in bosses:
            if mode == "full":
                boss_service.kill_boss(boss.boss_id)
                lines.append(f"☠️ {boss.name} killed")
            else:
                result = boss_service.attack_boss_once(boss.boss_id)
                lines.append(
                    f"🗡️ {boss.name}: "
                    f"-{result['player_damage']} dmg "
                    f"(boss {result['new_boss_life']}/{result['boss_max_life']})"
                )

        await update.message.reply_text(
            f"👹 Boss run for {name}\n\n" + "\n".join(lines)
        )

    except Exception as e:
        await update.message.reply_text(
            f"Boss command failed for {name}:\n{e}"
        )
