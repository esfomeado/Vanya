# Vanya

Multi-account automation framework for a browser-based RPG, controlled through a Telegram bot.

Each configured account runs in its own thread under a central scheduler, with services for hunting, training, bosses, market, guilds, inventory, and more. All control is exposed via Telegram commands so you can manage many accounts from your phone.

## Features

- **Multi-account scheduler** — every account runs independently with per-mode tick intervals
- **Hunting modes** — Solo Hunt, Phantom Halls, Deep Dragon, Dual Hunt
- **Combat** — boss attack/kill, automatic boss farming, auto-heal and resume
- **Progression** — skill training, house training, daily tasks, reconciliation
- **Economy** — dark market buy/sell, auto-fill buy orders, vault, bank withdrawals, pub regen
- **Social** — guild join/leave, chat messages, lounge likes/dislikes
- **Cosmetics** — visages (list/equip/spin), outfits (list/equip/random), flags
- **Telegram bot** — single-account and bulk (`/auto_*`) commands with ACL
- **Proxy support** — per-account HTTP proxy

## Requirements

- Python 3.11+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- Optional: HTTP proxies if you want to route accounts separately

## Installation

```bash
git clone <your-fork-url> vanya
cd vanya
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy and edit `accounts.yaml` in the project root:

```yaml
accounts:
  - username: your_username
    password: your_password
    proxy: "host:port:user:pass"   # optional, format: host:port:user:pass

telegram:
  token: your_telegram_bot_token
  allowed_users:
    - 123456789                    # Telegram user IDs allowed to control the bot
```

Add as many accounts as you want under `accounts:`. Only Telegram user IDs listed in `allowed_users` can issue commands.

## Running

```bash
python main.py
```

The scheduler starts a worker thread per account and the Telegram bot begins polling. Send `/help` to your bot to see the full command list.

## Telegram commands

Single-account commands operate on one account by username. Bulk commands prefixed with `/auto_` operate on every configured account.

| Command                                                   | Description                                                           |
|-----------------------------------------------------------|-----------------------------------------------------------------------|
| `/accounts`                                               | List configured accounts and their modes                              |
| `/stats <account>`                                        | Detailed stats for one account                                        |
| `/auto_stats`                                             | Stats summary for all accounts                                        |
| `/solo_hunt <account> <start\|stop> [area_id]`            | Solo Hunt control                                                     |
| `/phantom_halls <account> <start\|stop> [area_id]`        | Phantom Halls control                                                 |
| `/deep_dragon <account> <start\|stop>`                    | Deep Dragon control                                                   |
| `/dual_hunt <account> <start\|stop> [area_id]`            | Dual Hunt control                                                     |
| `/auto_hunt <start\|stop> [area_id]`                      | Auto-hunt all accounts (Solo Hunt < lvl 300, Phantom Halls otherwise) |
| `/boss <account> <attack\|kill\|list> [boss_id]`          | Per-account boss action                                               |
| `/auto_boss <attack\|kill\|list\|farm on\|off> [boss_id]` | Boss action across all accounts                                       |
| `/train <account> <skill>`                                | Start training a skill                                                |
| `/guild <account> join <guild_id>`                        | Join a guild                                                          |
| `/auto_guild <join\|leave> [guild_id]`                    | Bulk guild join/leave                                                 |
| `/market <account> <buy\|sell> [args]`                    | Buy or list on the market                                             |
| `/auto_sell <item_name> <price_per_item>`                 | List all units of an item from every account                          |
| `/auto_fill <item_name> <order_id>`                       | Fill a buy order from inventory across all accounts                   |
| `/auto_items`                                             | Export every account's inventory as collapsible HTML                  |
| `/auto_coupon <code>`                                     | Redeem a coupon on every account                                      |
| `/auto_regenerate`                                        | Send idle accounts to the pub to regenerate                           |
| `/auto_pub`                                               | Buy accumulated pub regen on every account                            |
| `/auto_gold`                                              | Withdraw all bank gold on every account                               |
| `/auto_flag <flag_code>`                                  | Change pub flag on every account                                      |
| `/auto_house <generate\|join> [friend_code]`              | Manage house friend codes                                             |
| `/auto_outfit <list\|random\|equip> [filename]`           | Manage outfits                                                        |
| `/auto_lounge <like\|dislike> <topic_id> <post_id>`       | Bulk like/dislike a forum post                                        |
| `/auto_vault open_box <season>`                           | Open vault box on every account                                       |
| `/visage <account> <list\|equip\|spin> [filename]`        | Manage visages for one account                                        |
| `/auto_visage <list\|free_spin>`                          | List visages or use free spin on every account                        |
| `/say <account> <message>`                                | Post a chat message                                                   |
| `/ritual <account> <target_user_id>`                      | Perform the dead-inside ritual                                        |
| `/help`                                                   | Show the full command list                                            |

## Project structure

```
src/vanya/
  core/         # session, config loader, logging, constants, demona shield
  model/        # pydantic models: account, stats, hunt, boss, item, ...
  scheduler/    # main scheduler loop and per-mode dispatch
  service/     # one service per game subsystem (hunt, boss, market, ...)
  telegram/     # bot, commands, ACL
main.py         # entrypoint: load config, start scheduler, start bot
accounts.yaml   # account credentials and bot config (gitignored in your fork)
```

## Notes

- **Keep `accounts.yaml` out of version control.** It contains credentials. The committed file is a placeholder; your real config should not be pushed.
- Mode tick intervals are tuned per mode in `Scheduler.MODE_TICK_INTERVAL`. Adjust there if you need different cadences.
- Errors during a tick are caught and reported to the Telegram chat via `TelegramService`.

## Disclaimer

This project is provided for educational purposes. Automating accounts may violate the terms of service of the target game. You are solely responsible for how you use this software.
