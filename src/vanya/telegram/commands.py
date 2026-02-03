import asyncio
from html import escape
from io import BytesIO

from telegram import Update
from telegram.ext import ContextTypes

from src.vanya.model.account import Account
from src.vanya.model.mode import Mode
from src.vanya.service.boss_service import BossService
from src.vanya.service.chat_service import ChatService
from src.vanya.service.coupon_service import CouponService
from src.vanya.service.dark_market_service import DarkMarketService
from src.vanya.service.deep_dragon_service import DeepDragonService
from src.vanya.service.guild_service import GuildService
from src.vanya.service.inventory_service import InventoryService
from src.vanya.service.lounge_service import LoungeService
from src.vanya.service.phantom_halls_service import PhantomHallsService
from src.vanya.service.pub_service import PubService
from src.vanya.service.service_registry import service_registry
from src.vanya.service.solo_hunt_service import SoloHuntService
from src.vanya.service.training_service import TrainingService
from src.vanya.service.visage_service import VisageService
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
        f"Drako: {stats.drako}",
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
            "/auto_hunt start [area_id]\n"
            "/auto_hunt stop"
        )
        return

    action = context.args[0]
    area_id = context.args[1] if len(context.args) > 1 else None

    accounts: list[Account] = context.application.bot_data["accounts"]
    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    lines: list[str] = []

    if action == "stop":
        def stop_one(account: Account):
            if account.mode == Mode.SOLO_HUNT:
                service_registry.get(SoloHuntService, account).stop_hunt()
                lines.append(f"⏹️ {account.username} stopped Solo Hunt")
            elif account.mode == Mode.PHANTOM_HALLS:
                service_registry.get(PhantomHallsService, account).stop_hunt()
                lines.append(f"⏹️ {account.username} stopped Phantom Halls")
            elif account.mode == Mode.DEEP_DRAGON:
                service_registry.get(DeepDragonService, account).stop_hunt()
                lines.append(f"⏹️ {account.username} stopped Deep Dragon")
            else:
                lines.append(f"⏭️ {account.username} not hunting")

        await asyncio.gather(
            *(asyncio.to_thread(stop_one, account) for account in accounts)
        )

        await update.message.reply_text(
            "🛑 Auto Hunt Stop\n\n" + "\n".join(lines)
        )
        return

    if action != "start":
        await update.message.reply_text(
            "Usage:\n"
            "/auto_hunt start [area_id]\n"
            "/auto_hunt stop"
        )
        return

    def start_one(account: Account):
        if account.mode in {Mode.SOLO_HUNT, Mode.PHANTOM_HALLS, Mode.DEEP_DRAGON}:
            lines.append(
                f"⏭️ {account.username} already hunting ({account.mode.value})"
            )
            return

        try:
            level = account.stats.level

            if level < 300:
                service_registry.get(SoloHuntService, account).hunt(area_id)
                hunt = account.hunt
                lines.append(
                    f"🗡️ {account.username} → Solo Hunt "
                    f"({hunt.name}, max hit {hunt.max_hit})"
                )
            else:
                service_registry.get(PhantomHallsService, account).hunt(area_id)
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

    await asyncio.gather(
        *(asyncio.to_thread(start_one, account) for account in accounts)
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
    """
    Attacks or kills a boss with a specific account.
    """

    if not allowed(update):
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/boss <account> attack <boss_id>\n"
            "/boss <account> kill <boss_id>\n"
            "/boss <account> list"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]

    name = context.args[0]
    action = context.args[1].lower()

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    boss_service = service_registry.get(BossService, account)

    try:
        # List available bosses
        if action == "list":
            bosses = boss_service.list_available_bosses()

            if not bosses:
                await update.message.reply_text(
                    f"👹 No available bosses for {name}"
                )
                return

            lines = [f"👹 Available bosses for {name}:"]
            for boss in bosses:
                boost_icon = "⚡" if boss.boosted else ""
                lines.append(
                    f"{boost_icon}Stage {boss.stage}: {boss.name}\n"
                    f"  ID: {boss.boss_id}\n"
                    f"  Life: {boss.life:,} | XP: {boss.xp:,}\n"
                    f"  Required Level: {boss.required_level}"
                )

            await update.message.reply_text("\n\n".join(lines))
            return

        # Attack or kill boss
        if action not in {"attack", "kill"}:
            await update.message.reply_text(
                f"Unknown action: {action}\n\n"
                "Available actions:\n"
                "- attack\n"
                "- kill\n"
                "- list"
            )
            return

        if len(context.args) < 3:
            await update.message.reply_text(
                f"Usage: /boss <account> {action} <boss_id>"
            )
            return

        try:
            boss_id = int(context.args[2])
        except ValueError:
            await update.message.reply_text("boss_id must be an integer")
            return

        if action == "kill":
            boss_service.kill_boss(boss_id)
            await update.message.reply_text(
                f"👹 {name} started killing boss {boss_id}"
            )
        else:  # attack
            result = boss_service.attack_boss_once(boss_id)

            if not result:
                await update.message.reply_text(
                    f"👹 Boss {boss_id} is already dead"
                )
                return

            await update.message.reply_text(
                f"👹 Boss attack for {name}\n\n"
                f"Boss: {result.get('boss_name', 'Unknown')}\n"
                f"Damage dealt: {result.get('player_damage', 0):.1f}\n"
                f"Boss HP: {result.get('new_boss_life', 0):.0f}/{result.get('boss_max_life', 0):.0f}\n"
                f"Your HP: {result.get('new_player_life', 0)}/{result.get('player_max_life', 0)}\n"
                f"Stamina: {result.get('new_stamina', 0)}"
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
            f"📊 Stats: Level {stats.level}, Gold {stats.gold}, Drako {stats.drako} Health {stats.health}/{stats.max_health}, Stamina {stats.stamina}",
            f"⚔️ Skills: Sword {stats.sword}, Bow {stats.bow}, Magic {stats.magic}, Defence {stats.defence}, Fishing {stats.fishing}"
        ]

        if hunt:
            acc_lines.append(f"🗡️ Hunting: {hunt.name}, Max hit {hunt.max_hit}")

        lines.append("\n".join(acc_lines))

    batch_size = 15
    for i in range(0, len(lines), batch_size):
        batch = lines[i:i + batch_size]
        await update.message.reply_text("\n\n".join(batch))


async def auto_boss_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Attacks or kills a specific boss for all configured accounts.
    """
    if not allowed(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/auto_boss attack <boss_id>\n"
            "/auto_boss kill <boss_id>\n"
            "/auto_boss list"
        )
        return

    action = context.args[0].lower()

    if action not in {"attack", "kill", "list"}:
        await update.message.reply_text(
            f"Unknown action: {action}\n\n"
            "Available actions:\n"
            "- attack <boss_id>\n"
            "- kill <boss_id>\n"
            "- list"
        )
        return

    accounts: list[Account] = context.application.bot_data.get("accounts", [])
    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    # List mode doesn't need boss_id
    if action == "list":
        results = []
        for account in accounts:
            boss_service: BossService = service_registry.get(BossService, account)
            try:
                bosses = boss_service.list_available_bosses()

                if not bosses:
                    results.append(f"⏭️ {account.username}: no available bosses")
                    continue

                lines = [f"👹 {account.username}:"]
                for boss in bosses:
                    boost_icon = "⚡" if boss.boosted else ""
                    lines.append(
                        f"  {boost_icon}Stage {boss.stage}: {boss.name} "
                        f"(ID: {boss.boss_id}, HP: {boss.life:,}, XP: {boss.xp:,})"
                    )
                results.append("\n".join(lines))

            except Exception as e:
                results.append(f"❌ {account.username}: {e}")

        if not results:
            await update.message.reply_text("No results to display")
            return

        await update.message.reply_text("\n\n".join(results))
        return

    # Attack and kill modes require boss_id
    if len(context.args) < 2:
        await update.message.reply_text(
            f"Usage: /auto_boss {action} <boss_id>"
        )
        return

    try:
        boss_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("boss_id must be an integer")
        return

    results = []

    for account in accounts:
        if account.mode == Mode.SOLO_HUNT:
            service_registry.get(SoloHuntService, account).stop_hunt()
        elif account.mode == Mode.PHANTOM_HALLS:
            service_registry.get(PhantomHallsService, account).stop_hunt()
        elif account.mode == Mode.DEEP_DRAGON:
            service_registry.get(DeepDragonService, account).stop_hunt()

        boss_service: BossService = service_registry.get(BossService, account)
        try:
            if action == "kill":
                boss_service.kill_boss(boss_id)
                results.append(f"☠️ {account.username} started killing boss {boss_id}")
            else:  # attack
                result = boss_service.attack_boss_once(boss_id)

                if not result:
                    results.append(f"💀 {account.username}: boss {boss_id} is already dead")
                    continue

                hp_percent = (result.get('new_boss_life', 0) / result.get('boss_max_life', 1)) * 100
                results.append(
                    f"🗡️ {account.username}: {result.get('boss_name', 'Unknown')}\n"
                    f"   Damage: -{result.get('player_damage', 0):.0f} | "
                    f"Boss HP: {result.get('new_boss_life', 0):,.0f}/{result.get('boss_max_life', 0):,.0f} ({hp_percent:.0f}%)\n"
                    f"   Your HP: {result.get('new_player_life', 0)}/{result.get('player_max_life', 0)} | "
                    f"Stamina: {result.get('new_stamina', 0)}"
                )

        except Exception as e:
            results.append(f"❌ {account.username}: {e}")

    if not results:
        await update.message.reply_text("No results to display")
        return

    await update.message.reply_text("\n\n".join(results))


async def auto_items_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    accounts: list[Account] = context.application.bot_data.get("accounts", [])

    sections: list[str] = []

    for account in accounts:
        service = service_registry.get(InventoryService, account)
        try:
            items = service.list_items()
        except Exception as e:
            sections.append(
                f"<details open>"
                f"<summary>❌ {escape(account.username)} – inventory fetch failed</summary>"
                f"<pre>{escape(str(e))}</pre>"
                f"</details>"
            )
            continue

        if not items:
            sections.append(
                f"<details>"
                f"<summary>📦 {escape(account.username)} – empty inventory</summary>"
                f"</details>"
            )
            continue

        body_lines = []
        for item in items:
            line = f"- {item.name}"
            if item.quantity > 1:
                line += f" x{item.quantity}"
            if item.equipped:
                line += " [E]"
            body_lines.append(escape(line))

        body = "\n".join(body_lines)

        sections.append(
            f"<details>"
            f"<summary>📦 {escape(account.username)} ({len(items)} items)</summary>"
            f"<pre>{body}</pre>"
            f"</details>"
        )

    if not sections:
        await update.message.reply_text("No accounts found")
        return

    html = (
        "<!DOCTYPE html>"
        "<html>"
        "<head>"
        "<meta charset='utf-8'>"
        "<title>Inventory</title>"
        "<style>"
        "body{font-family:monospace;background:#fff;color:#000}"
        "details{margin-bottom:12px}"
        "summary{cursor:pointer;font-weight:bold}"
        "pre{margin:6px 0 0 0;white-space:pre-wrap}"
        "</style>"
        "</head>"
        "<body>"
        + "".join(sections) +
        "</body>"
        "</html>"
    )

    buf = BytesIO(html.encode("utf-8"))
    buf.name = "inventory.html"

    await update.message.reply_document(
        document=buf,
        caption="Inventory items"
    )


async def market_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Buy or sell items on the market.

    Usage:
    /market buy <account> <item_name>
    /market sell <account> <item_name> <amount> <price>
    """
    if not allowed(update):
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage:\n"
            "/market <account> buy <item_id>\n"
            "/market <account> sell <item_name> <amount> <price>"
        )
        return

    account_name = context.args[0]
    action = context.args[1].lower()

    accounts: list[Account] = context.application.bot_data["accounts"]
    account = _find_account(accounts, account_name)
    if not account:
        await update.message.reply_text(f"Unknown account: {account_name}")
        return

    market = service_registry.get(DarkMarketService, account)

    try:
        if action == "buy":
            item_id = int(context.args[2])

            market.buy_item(item_id)
            await update.message.reply_text(f"✅ Bought {item_id}")

        elif action == "sell":
            if len(context.args) < 5:
                await update.message.reply_text("Usage: /market <account> sell <item_name> <amount> <price>")
                return

            item_name = " ".join(context.args[2:-2])
            amount = int(context.args[-2])
            price = int(context.args[-1])
            market.sell_item(item_name, amount, price)
            await update.message.reply_text(f"✅ Listed {amount}x {item_name} for {price} GOLD each")

        else:
            await update.message.reply_text("Invalid action. Use buy or sell.")

    except Exception as e:
        await update.message.reply_text(f"❌ Market action failed: {str(e)}")


async def auto_coupon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    accounts: list[Account] = context.application.bot_data.get("accounts", [])

    results = []

    for account in accounts:
        service = service_registry.get(CouponService, account)
        try:
            coupon_code = context.args[0]
            service.redeem(coupon_code)
            results.append(f"✅ {account.username}: Coupon redeemed successfully")
        except Exception as e:
            results.append(f"❌ {account.username}: {str(e)}")

    if results:
        await update.message.reply_text("\n".join(results))


async def auto_regenerate_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    accounts: list[Account] = context.application.bot_data.get("accounts", [])

    results = []

    for account in accounts:
        if account.mode in {Mode.SOLO_HUNT, Mode.PHANTOM_HALLS, Mode.DEEP_DRAGON}:
            results.append(f"⏭️ {account.username}: currently hunting, skipped")
            continue

        service = service_registry.get(PubService, account)
        try:
            service.go_to_pub()
            service.regenerate(sleep=False)
            results.append(f"✅ {account.username}: regenerated successfully")
        except Exception as e:
            results.append(f"❌ {account.username}: {str(e)}")

    if results:
        await update.message.reply_text("\n".join(results))


async def visage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/visage <account> list\n"
            "/visage <account> equip <filename>\n"
            "/visage <account> spin"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]
    name = context.args[0]
    action = context.args[1].lower()

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    visage_service = service_registry.get(VisageService, account)

    try:
        if action == "list":
            visages = visage_service.list()
            if not visages:
                await update.message.reply_text(f"🖼️ {name} owns no visages.")
                return

            lines = [f"🖼️ Owned Visages for {name}:"]
            for v in visages:
                status = "✅" if v.is_equipped else "❌"
                lines.append(f"{status} {v.name}\n   Bonus: {v.bonus}\n   File: {v.filename}")

            await update.message.reply_text("\n\n".join(lines))

        elif action == "equip":
            if len(context.args) < 3:
                await update.message.reply_text(f"Usage: /visage <account> equip <filename>")
                return

            filename = context.args[2]
            visage_service.equip(filename)
            await update.message.reply_text(f"✅ {name} equipped visage: {filename}")

        elif action == "spin":
            result = visage_service.spin()
            if result.get("status") == "ok":
                won = result.get("won")
                rarity = result.get("rarity", "common").upper()
                dup = " (DUPLICATE)" if result.get("duplicate") else " (NEW!)"

                msg = (
                    f"🎰 Spin Result for {name}:\n\n"
                    f"Portrait: {won}{dup}\n"
                    f"Rarity: {rarity}\n"
                    f"Gold remaining: {result.get('gold', 0):,}"
                )
                await update.message.reply_text(msg)
            else:
                await update.message.reply_text(f"❌ Spin failed: {result.get('message', 'Unknown error')}")

        else:
            await update.message.reply_text("Invalid action. Use list, equip, or spin.")

    except Exception as e:
        await update.message.reply_text(f"❌ Visage command failed for {name}: {str(e)}")


async def auto_visage_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not allowed(update):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage:\n"
            "/auto_visage list\n"
            "/auto_visage free_spin"
        )
        return

    action = context.args[0].lower()
    accounts: list[Account] = context.application.bot_data.get("accounts", [])

    if not accounts:
        await update.message.reply_text("No accounts configured")
        return

    if action == "list":
        sections = []
        for account in accounts:
            try:
                service = service_registry.get(VisageService, account)
                visages = service.list()

                if not visages:
                    sections.append(
                        f"<details><summary>🖼️ {escape(account.username)} (0)</summary>"
                        f"<p style='margin-left:1em'>No visages owned.</p></details>"
                    )
                    continue

                rows = []
                for v in visages:
                    status = "<b>[EQUIPPED]</b> " if v.is_equipped else ""
                    rows.append(
                        f"<div>"
                        f"{status}{escape(v.name)} <span style='color:#666'>({escape(v.bonus)})</span>"
                        f"<br><small>{escape(v.filename)}</small>"
                        f"</div>"
                    )

                body = "<div style='margin-left:1em; display:grid; gap:8px;'>" + "".join(rows) + "</div>"

                sections.append(
                    f"<details><summary>🖼️ {escape(account.username)} ({len(visages)})</summary>"
                    f"{body}</details>"
                )
            except Exception as e:
                sections.append(
                    f"<details><summary>❌ {escape(account.username)} - Error</summary>"
                    f"<pre>{escape(str(e))}</pre></details>"
                )

        html = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<style>body{font-family:sans-serif; background:#fff; color:#000}"
            "details{margin-bottom:12px; border-bottom:1px solid #eee; padding-bottom:8px}"
            "summary{cursor:pointer; font-weight:bold; margin-bottom:6px}"
            "</style></head><body>"
            + "".join(sections) +
            "</body></html>"
        )

        buf = BytesIO(html.encode("utf-8"))
        buf.name = "visages.html"
        await update.message.reply_document(document=buf, caption="All Accounts Visages")

    elif action == "free_spin":
        results = []
        for account in accounts:
            try:
                service = service_registry.get(VisageService, account)
                service.free_spin()

                results.append(f"✅ {account.username}: spun successfully")
            except Exception as e:
                results.append(f"❌ {account.username}: {str(e)}")

        await update.message.reply_text("\n".join(results))

    else:
        await update.message.reply_text("Invalid action. Use list or free_spin.")


async def deep_dragon_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Starts or stops the Deep Dragon hunt for a specific account.
    Usage: /deep_dragon <account> <start|stop>
    """
    if not allowed(update):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage:\n"
            "/deep_dragon <account> start\n"
            "/deep_dragon <account> stop"
        )
        return

    accounts: list[Account] = context.application.bot_data["accounts"]
    name = context.args[0]
    action = context.args[1].lower()

    account = _find_account(accounts, name)
    if not account:
        await update.message.reply_text(f"Unknown account: {name}")
        return

    service = service_registry.get(DeepDragonService, account)

    try:
        if action == "start":
            if account.mode == Mode.DEEP_DRAGON:
                await update.message.reply_text(f"🐉 {name} is already hunting Deep Dragon.")
                return

            if account.mode == Mode.SOLO_HUNT:
                service_registry.get(SoloHuntService, account).stop_hunt()
            elif account.mode == Mode.PHANTOM_HALLS:
                service_registry.get(PhantomHallsService, account).stop_hunt()

            service.hunt()
            hunt = account.hunt
            await update.message.reply_text(
                f"🐉 {name} started Deep Dragon hunt.\n"
                f"Max Hit: {hunt.max_hit}"
            )

        elif action == "stop":
            if account.mode != Mode.DEEP_DRAGON:
                await update.message.reply_text(f"{name} is not in Deep Dragon mode.")
                return

            service.stop_hunt()
            await update.message.reply_text(f"🛑 {name} stopped Deep Dragon hunt.")

        else:
            await update.message.reply_text("Invalid action. Use 'start' or 'stop'.")

    except Exception as e:
        await update.message.reply_text(f"❌ Deep Dragon command failed for {name}:\n{e}")


async def auto_lounge_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Mass like or dislike a post using all accounts.
    Usage: /auto_lounge <like|dislike> <topic_id> <post_id>
    """
    if not allowed(update):
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage:\n"
            "/auto_lounge like <topic_id> <post_id>\n"
            "/auto_lounge dislike <topic_id> <post_id>"
        )
        return

    action = context.args[0].lower()
    topic_id = context.args[1]
    post_id = context.args[2]

    if not topic_id.isdigit() or not post_id.isdigit():
        await update.message.reply_text("❌ Topic ID and Post ID must be numbers.")
        return

    accounts: list[Account] = context.application.bot_data.get("accounts", [])
    if not accounts:
        await update.message.reply_text("No accounts configured.")
        return

    if action not in ["like", "dislike"]:
        await update.message.reply_text("Invalid action. Use 'like' or 'dislike'.")
        return

    await update.message.reply_text(
        f"🚀 Starting {action} for Topic {topic_id}, Post {post_id} on {len(accounts)} accounts...")

    results = []
    for account in accounts:
        try:
            service = service_registry.get(LoungeService, account)
            if action == "like":
                service.like(int(topic_id), int(post_id))
                results.append(f"✅ {account.username}: Liked")
            elif action == "dislike":
                service.dislike(int(topic_id), int(post_id))
                results.append(f"✅ {account.username}: Disliked")
        except Exception as e:
            results.append(f"❌ {account.username}: {str(e)}")

    response_text = "\n".join(results)
    if len(response_text) > 4000:
        response_text = response_text[:4000] + "\n...(truncated)"

    await update.message.reply_text(response_text)
