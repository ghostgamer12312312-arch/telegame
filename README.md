# Telegram RPG Bot

A Telegram game bot. Players fight, collect things, rank up, and more.
This guide is written for complete beginners. Follow the steps in order.

---

## Part 1: Make your bot (5 minutes, on your phone)

1. Open Telegram. Search for **@BotFather** and open it.
2. Send: `/newbot`
3. It asks for a name. Type anything, for example: `My Game Bot`
4. It asks for a username. It must end in `bot`, for example: `mygame_rpg_bot`
5. BotFather replies with a long code like `123456:ABCdef...`.
   **Copy it and keep it safe.** This is your **BOT_TOKEN**.

Next, find your own Telegram number:

6. Search for **@userinfobot** and open it.
7. Send any message. It replies with a number like `123456789`.
   **Copy it.** This is your **OWNER_ID**.

---

## Part 2A: Run it on your Android phone (Termux)

**Step 1.** Install **Termux** from **F-Droid** (https://f-droid.org). Do not use the Play Store version.

**Step 2.** Open Termux. Copy and paste these lines, one at a time, pressing Enter after each one:

```
pkg update -y
pkg upgrade -y
pkg install -y python git
```

If it asks a question, type `y` and press Enter.

**Step 3.** Download this game:

```
git clone https://github.com/mrandi-art/telegame.git
cd telegame
```

**Step 4.** Install the game's parts:

```
pip install -r requirements.txt
```

If this step shows an error, run `pkg install -y rust clang` and then run the line above again.

**Step 5.** Make your settings file:

```
cp .env.example .env
nano .env
```

A text editor opens. Change two lines:
- `BOT_TOKEN=` → paste your token from Part 1 (after the `=` sign, no spaces)
- `OWNER_ID=` → paste your number from Part 1

To save: press **Ctrl + O**, then **Enter**, then **Ctrl + X**.

**Step 6.** Start the bot:

```
sh start.sh
```

If you see lines of text and no red error, it's running. Leave Termux open.

To stop it: press **Ctrl + C**.

To start it again later: open Termux, type `cd telegame` then `sh start.sh`.

---

## Part 2B: Run it on a computer (Windows, Mac, or Linux)

1. Install **Python 3.10 or newer** from https://www.python.org/downloads/
   (on Windows, tick "Add Python to PATH" during install).
2. Install **Git** from https://git-scm.com
3. Open a terminal (Command Prompt, Terminal, or PowerShell) and run:

```
git clone https://github.com/mrandi-art/telegame.git
cd telegame
pip install -r requirements.txt
```

4. Make the settings file. Copy `.env.example` to a new file called `.env`,
   open it in Notepad, and paste your **BOT_TOKEN** and **OWNER_ID**. Save it.
5. Start the bot:
   - Mac or Linux: `sh start.sh`
   - Windows: `python bot.py` (after setting the two values in `.env`, or type them in first)

---

## Part 3: Try it in Telegram

1. Open your bot in Telegram (search for its username from Part 1).
2. Press **Start**, or send `/start`.
3. Send `/explore` to fight an enemy and collect rewards.
4. Send `/profile` to see your stats.

**Want a group?** Add your bot to a group chat. Everyone in the group can play.

---

## The commands, in plain words

| Type this | What happens |
|---|---|
| `/start` | Begin your game |
| `/profile` | See your name, level, rank, and equipped character |
| `/explore` | Fight an enemy. You get money and items. |
| `/myinventory` | See everything you own |
| `/shop` | See things to buy |
| `/buy 1` | Buy item number 1 from the shop (use any number from /shop) |
| `/gacha` | Use a ticket to get a random character |
| `/mycharacters` | See your characters |
| `/equip Goku` | Put a character on your team (or any character name) |
| `/equip Iron Sword` | Wear a weapon or armor |
| `/myteam` | See your team and how strong it is |
| `/skills` | See skills you can learn |
| `/learn Ki Blast` | Learn a skill |
| `/wish` | Use all seven dragon balls for a wish |
| `/summon elite` | Fight a strong boss (uses an elite key) |
| `/give` | Send money, items, or characters to a friend (see below) |
| `/rankup` | Rank up using crystals |
| `/raid_start` | Owner or admin only: start a big group boss fight |
| `/raid_attack` | Hit the big boss |

**How to give something to a friend:**
- Reply to their message, then type: `/give 50 gems`
- Or type their username: `/give @friend 50 gems`
- Things you can give: gems, yens, crystals, tickets, weapons, armor, characters, skills, dragon balls.

**How to rank up:** type `/rankup`. It tells you what you still need.

---

## Problems?

| Problem | Fix |
|---|---|
| "Set BOT_TOKEN first" | Your `.env` file is missing the token. Do Step 5 again. |
| Bot doesn't answer | Check the token has no spaces. Make sure the program is still running. |
| `pip install` fails with `pydantic-core` or `maturin` / "Rust not found" on phone | Type `pkg install -y rust clang`, then `pip install -r requirements.txt` again. Takes several minutes. |
| You want to start over | Delete the file `game.sqlite` (this erases all player progress) |

---

## Safety

- **Never share your BOT_TOKEN.** Anyone with it can control your bot.
  If it leaks, open @BotFather, send `/revoke`, and pick your bot to make a new one.
- Keep a copy of `game.sqlite`. It holds all player progress.

## Files

- `bot.py`: the game
- `game_data.py`: prices, enemies, and rates. Change numbers here.
- `db.py`: saves progress to `game.sqlite`
- `start.sh`: starts the bot
- `.env.example`: settings template

## License

MIT. See `LICENSE`.
