from telegram import Update
from telegram.ext import ContextTypes

from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.boss_service import BossService
from src.vanya.service.chat_service import ChatService
from src.vanya.service.guild_service import GuildService
from src.vanya.service.inventory_service import InventoryService
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
        f"🏰 Guild: {account.guild}"
        "",
        "📊 Stats",
        f"Level: {stats.level}",
        f"Gold: {stats.gold}",
        f"Health: {stats.health}/{stats.max_health}",
        f"Stamina: {stats.stamina}",
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


async def auto_hunt_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/auto_hunt start\n"
            "/auto_hunt stop"
        )
        return

    action = context.args[0]

    accounts: list[Account] = context.application.bot_data["accounts"]
    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    lines: list[str] = []

    if action == "stop":
        for account in accounts:
            if account.mode == Mode.SOLO_HUNT:
                service_registry.get(SoloHuntService, account).stop_hunt()
                lines.append(f"⏹️ {account.username} stopped Solo Hunt")
            elif account.mode == Mode.PHANTOM_HALLS:
                service_registry.get(PhantomHallsService, account).stop_hunt()
                lines.append(f"⏹️ {account.username} stopped Phantom Halls")
            elif account.mode == Mode.DEEP_DRAGON:
                lines.append(f"⏹️ {account.username} stopped Deep Dragon")
            else:
                lines.append(f"⏭️ {account.username} not hunting")

        await update.message.reply_text(
            "🛑 Auto Hunt Stop\n\n" + "\n".join(lines)
        )
        return

    if action != "start":
        await update.message.reply_text(
            "Usage:\n"
            "/auto_hunt start\n"
            "/auto_hunt stop"
        )
        return

    for account in accounts:
        if account.mode in {Mode.SOLO_HUNT, Mode.PHANTOM_HALLS, Mode.DEEP_DRAGON}:
            lines.append(
                f"⏭️ {account.username} already hunting ({account.mode.value})"
            )
            continue

        try:
            level = account.stats.level

            if level < 300:
                service_registry.get(SoloHuntService, account).hunt()
                hunt = account.hunt
                lines.append(
                    f"🗡️ {account.username} → Solo Hunt "
                    f"({hunt.name}, max hit {hunt.max_hit})"
                )
            else:
                service_registry.get(PhantomHallsService, account).hunt()
                hunt = account.hunt
                lines.append(
                    f"🌀 {account.username} → Phantom Halls "
                    f"({hunt.name}, max hit {hunt.max_hit})"
                )

        except Exception as e:
            account.hunt = None
            account.mode = Mode.IDLE
            lines.append(
                f"❌ {account.username} auto_hunt failed: {e}"
            )

    await update.message.reply_text(
        "🤖 Auto Hunt Start\n\n" + "\n".join(lines)
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


async def guild_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/guild <account> join <guild_id>"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    name = context.args[0]
    action = context.args[1]

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    if action == "join":
        if len(context.args) < 3:
            await update.message.reply_text(
                "Usage:\n"
                "/guild <account> join <guild_id>"
            )
            return

        try:
            guild_id = int(context.args[2])
        except ValueError:
            await update.message.reply_text("guild_id must be an integer")
            return

        try:
            service_registry.get(GuildService, account).join(guild_id)
            await update.message.reply_text(
                f"🏰 {name} applied to guild {guild_id}"
            )
        except Exception as e:
            await update.message.reply_text(
                f"Guild join failed for {name}:\n{e}"
            )
        return

    await update.message.reply_text(
        f"Unknown guild action: {action}\n\n"
        "Available actions:\n"
        "- join"
    )


async def auto_guild_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if not context.args:
        await update.message.reply_text("Usage: /auto_guild <join|leave> [guild_id]")
        return

    action = context.args[0].lower()
    guild_id = int(context.args[1]) if len(context.args) > 1 else None

    accounts: list[Account] = context.application.bot_data["accounts"]
    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    results = []

    for account in accounts:
        try:
            if action == "join":
                if not account.guild:
                    if guild_id is not None:
                        service_registry.get(GuildService, account).join(guild_id)
                        results.append(f"{account.username} joined guild {guild_id}")
                    else:
                        results.append(f"{account.username} not in a guild, no guild_id provided")
                else:
                    results.append(f"{account.username} already in guild {account.guild}")
            elif action == "leave":
                if account.guild:
                    service_registry.get(GuildService, account).leave()
                    results.append(f"{account.username} left guild {account.guild}")
                else:
                    results.append(f"{account.username} not in a guild")
            else:
                results.append(f"Invalid action {action}")
        except Exception as e:
            results.append(f"Error for {account.username}: {e}")

    await update.message.reply_text("\n".join(results))


async def auto_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    accounts: list[Account] = context.application.bot_data.get("accounts", [])
    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    lines = []

    for account in accounts:
        stats = account.stats
        hunt = account.hunt
        guild = account.guild or "None"

        acc_lines = [
            f"👤 {account.username} | Guild: {guild} | Mode: {account.mode.value}",
            f"📊 Stats: Level {stats.level}, Gold {stats.gold}, Health {stats.health}/{stats.max_health}, Stamina {stats.stamina}",
            f"⚔️ Skills: Sword {stats.sword}, Bow {stats.bow}, Magic {stats.magic}, Defence {stats.defence}, Fishing {stats.fishing}"
        ]

        if hunt:
            acc_lines.append(f"🗡️ Hunting: {hunt.name}, Max hit {hunt.max_hit}")

        lines.append("\n".join(acc_lines))

    await update.message.reply_text("\n\n".join(lines))


async def auto_boss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    mode_arg = context.args[0].lower() if context.args else None
    full_mode = mode_arg == "full"

    accounts: list[Account] = context.application.bot_data.get("accounts", [])
    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    results = []

    for account in accounts:
        boss_service: BossService = service_registry.get(BossService, account)
        try:
            bosses = boss_service.list_available_bosses()
            if not bosses:
                results.append(f"{account.username}: no available bosses")
                continue

            lines = []
            for boss in bosses:
                if full_mode:
                    boss_service.kill_boss(boss.boss_id)
                    lines.append(f"☠️ {boss.name} killed")
                else:
                    result = boss_service.attack_boss_once(boss.boss_id)
                    lines.append(
                        f"🗡️ {boss.name}: -{result['player_damage']} dmg "
                        f"(boss {result['new_boss_life']}/{result['boss_max_life']})"
                    )

            results.append(f"👹 Boss run for {account.username}\n" + "\n".join(lines))

        except Exception as e:
            results.append(f"❌ Boss command failed for {account.username}: {e}")

    await update.message.reply_text("\n\n".join(results))


async def auto_items_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    accounts: list[Account] = context.application.bot_data.get("accounts", [])

    lines: list[str] = []

    for account in accounts:
        service = service_registry.get(InventoryService, account)
        try:
            items = service.list_items()
        except Exception as e:
            lines.append(f"❌ {account.username}: inventory fetch failed ({e})")
            continue

        if not items:
            lines.append(f"📦 {account.username}: empty inventory")
            continue

        lines.append(f"📦 {account.username}")
        for item in items:
            line = f"- {item.name}"

            if item.quantity > 1:
                line += f" x{item.quantity}"

            if item.equipped:
                line += " [E]"

            if item.stats:
                line += f" ({item.stats})"

            lines.append(line)

        lines.append("")  # spacer

    if not lines:
        await update.message.reply_text("No accounts found")
        return

    await update.message.reply_text("\n".join(lines))
