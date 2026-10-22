# Telegram RPG Starter

An open-source Telegram bot RPG: profiles, NPC fights, bosses, gacha with Dragon Ball
Super characters, a shop, skills, Dragon Ball wishes, key-based summons, and a global raid.
Everything runs from one Python file and one SQLite file, so you can host it on a phone.

## Features

| Command | What it does |
|---|---|
| `/start`, `/help` | Welcome and command list |
| `/profile` | Photo, name, username, user ID, EXP, level, rank, equipped character |
| `/explore` | Fight one of 6 NPCs. Drops yens, gems, crystals, skill points, tickets, dragon balls, gear. Every 15 NPC wins, a boss appears. |
| `/myinventory` | Currency, keys, gear, dragon balls, skills |
| `/shop`, `/buy <id> [qty]` | Weapons, armor, gacha tickets, crystals, keys |
| `/gacha` | Spend a ticket for a random Dragon Ball Super character |
| `/mycharacters`, `/myteam`, `/equip <name>` | Characters and gear |
| `/skills`, `/learn <skill>` | Skill shop, paid in skill points |
| `/wish` | Uses one of each 1★ to 7★ ball for a wish |
| `/summon elite` or `/summon mythical` | Spend a key to fight a strong key boss |
| `/raid`, `/raid_start`, `/raid_attack` | Global raid. Only the owner or admins start it. Winners get 50x rewards. |

The numbers (prices, drop rates, NPC stats, boss stats, raid HP) are in `game_data.py`.
Change them there. No code edits needed.

## What you need

- A Telegram account
- A bot token from **@BotFather** (send `/newbot`, copy the token)
- Your numeric Telegram user ID (ask **@userinfobot**). This becomes `OWNER_ID`.
- Python 3.10+

## Run it on your Android phone (Termux)

1. Install **Termux** from F-Droid (the Play Store version is outdated).
2. In Termux:
   ```bash
   pkg update && pkg upgrade -y
   pkg install -y python git
   git clone https://github.com/YOUR-NAME/telegame.git
   cd telegame
   pip install -r requirements.txt
   cp .env.example .env
   nano .env          # paste BOT_TOKEN and OWNER_ID, then Ctrl+O, Enter, Ctrl+X
   ```
3. Start the bot. Load the variables first:
   ```bash
   export $(grep -v '^#' .env | xargs)
   python bot.py
   ```
4. Keep it running when the screen is off:
   ```bash
   termux-wake-lock     # needs the Termux:API app; optional
   ```
   Also turn off battery optimisation for Termux in Android settings.

The bot only runs while Termux is open or running in the background. Phone hosting is fine
for testing and small groups. For 24/7 use a PC, a Raspberry Pi, or a small VPS (see below).

## Run it on a PC or Linux server

```bash
git clone https://github.com/YOUR-NAME/telegame.git
cd telegame
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # edit BOT_TOKEN and OWNER_ID
export $(grep -v '^#' .env | xargs)
python bot.py
```

To keep it alive on a Linux server, run it under systemd or `tmux`.

## Make your group play with it

Add the bot to a Telegram group. Disable its privacy mode in @BotFather
(`/setprivacy` → Disable) if you want it to read every message. Commands work either way.

## Files

- `bot.py`: all commands and the battle loop
- `db.py`: SQLite storage (creates `game.sqlite` on first run)
- `game_data.py`: all tunable numbers (NPCs, shop, rarities, boss, raid)
- `.env.example`: settings template. Your real `.env` is ignored by git.

## Safety

- Keep `BOT_TOKEN` secret. If it leaks, revoke it in @BotFather.
- Only `OWNER_ID` and `ADMIN_IDS` can start raids.
- Back up `game.sqlite` to keep player progress.

## Contributing

Pull requests welcome. Keep changes small and tune numbers in `game_data.py`.

## License

MIT. See `LICENSE`.
