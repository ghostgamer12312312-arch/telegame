"""Telegram RPG starter: profile, explore, boss, gacha, shop, skills, dragon balls, summons, raid.

Run locally:  BOT_TOKEN=123:abc python bot.py
"""
import asyncio
import json
import logging
import os
import random
from html import escape

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import db
import game_data as G

logging.basicConfig(level=logging.INFO)
router = Router(name="game")
OWNER_ID = int(os.getenv("OWNER_ID", "0") or 0)
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x.isdigit()} | {OWNER_ID}


def is_staff(uid: int) -> bool:
    return uid in ADMIN_IDS


# ---------------- stats and battle
def equipped_char_bonus(uid: int) -> tuple[int, int]:
    p = db.player(uid)
    name = p["equipped_char"]
    if not name:
        return 0, 0
    row = next((c for c in db.characters(uid) if c["name"] == name), None)
    if row is None:
        return 0, 0
    return G.RARITY_ATK[row["rarity"]], G.RARITY_HP[row["rarity"]]


def player_stats(uid: int) -> tuple[int, int]:
    """(attack, max_hp) from level, gear, equipped character and learned skills."""
    p = db.player(uid)
    lvl = db.level_of(p["exp"])
    atk = 10 + lvl * 3
    hp = 100 + lvl * 10
    ca, ch = equipped_char_bonus(uid)
    atk += ca
    hp += ch
    if p["weapon"] in G.EQUIPMENT:
        atk += G.EQUIPMENT[p["weapon"]][1]
    if p["armor"] in G.EQUIPMENT:
        hp += G.EQUIPMENT[p["armor"]][1] * 2
    atk += sum(G.SKILL_ATK.get(s, 0) for s in db.skills(uid))
    return atk, hp


def auto_battle(p_hp: int, p_atk: int, e_hp: int, e_dmg: int, enrage: bool = False) -> tuple[bool, int, list[str]]:
    """Simple turn fight. Returns (won, player_hp_left, log lines).

    enrage: bosses hit 30% harder once they are at half HP or lower.
    """
    log = []
    e_max = e_hp
    for rnd in range(1, 41):
        hit = max(1, int(p_atk * random.uniform(0.8, 1.2)))
        e_hp -= hit
        if e_hp <= 0:
            log.append(f"Round {rnd}: you hit for {hit}. Victory!")
            return True, max(1, p_hp), log
        mult = 1.3 if enrage and e_hp <= e_max // 2 else 1.0
        taken = max(1, int(e_dmg * mult * random.uniform(0.8, 1.2)))
        p_hp -= taken
        log.append(f"Round {rnd}: you hit {hit}, take {taken}.")
        if p_hp <= 0:
            return False, 0, log
    return False, max(0, p_hp), log + ["The fight dragged on and you backed off."]


# ---------------- basics
@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    u = message.from_user
    db.ensure_player(u.id, u.first_name, u.username)
    await message.answer(
        "🐉 <b>Welcome to the RPG</b>\n\n"
        "/profile  your stats\n/explore  fight NPCs (boss every 15 wins)\n"
        "/myinventory  yens, gems, items, balls\n/shop  buy gear, tickets, keys, crystals\n"
        "/buy &lt;id&gt; [qty]  buy from /shop\n/gacha  spend a ticket on a DBS character\n"
        "/mycharacters  your characters\n/myteam  your active team\n/equip &lt;name&gt;  equip gear or a character\n"
        "/skills  skill shop\n/learn &lt;skill&gt;  learn a skill\n/wish  use all 1 to 7 star dragon balls\n"
        "/summon elite or /summon mythical  fight a key boss\n/give  send gems, yens, crystals, items or characters\n"
        "/rankup  rank up with crystals\n/raid  global raid (status)\n"
        "/raid_start  start raid (owner/admin only)\n/raid_attack  hit the raid boss")


@router.message(Command("profile"))
async def cmd_profile(message: Message) -> None:
    u = message.from_user
    db.ensure_player(u.id, u.first_name, u.username)
    p = db.player(u.id)
    lvl = db.level_of(p["exp"])
    caption = (f"👤 <b>{escape(p['first_name'] or 'Unknown')}</b>\n"
               f"Username: @{escape(p['username'] or '-')}\nUser ID: <code>{u.id}</code>\n"
               f"EXP: {p['exp']:,} · Level: {lvl} · Leaderboard: #{db.rank_of(u.id)}\n"
               f"Rank: {G.RANKS[db.rank_of_player(u.id)]}\n"
               f"Equipped character: {escape(p['equipped_char'] or 'none')}\n"
               f"Clan: {escape(CL.membership(u.id)['name']) + ' (' + CL.membership(u.id)['role'] + ')' if CL.membership(u.id) else 'none'}")
    photos = await message.bot.get_user_profile_photos(u.id, limit=1)
    if photos.total_count:
        await message.answer_photo(photos.photos[0][-1].file_id, caption=caption, parse_mode="HTML")
    else:
        await message.answer(caption, parse_mode="HTML")


# ---------------- explore and boss
@router.message(Command("explore"))
async def cmd_explore(message: Message) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    p = db.player(uid)
    atk, hp = player_stats(uid)
    if p["npc_streak"] >= G.NPC_STREAK_FOR_BOSS:
        b = G.BOSS
        won, left, log = auto_battle(hp, atk, b["hp"], b["dmg"], enrage=True)
        if not won:
            # the boss stays due: the streak is kept, so the next /explore tries again
            db.set_field(uid, "npc_streak", p["npc_streak"])
            await message.answer(f"💀 <b>{b['name']}</b> beat you. Heal and try again.\n" + "\n".join(log[-3:]),
                                 parse_mode="HTML")
            return
        db.set_field(uid, "npc_streak", 0)
        db.give(uid, yens=b["yens"], gems=b["gems"], crystals=b["crystals"],
                tickets=b["tickets"], skill_points=b["skill_points"], exp=200)
        extra = []
        for _ in range(random.randint(1, 3)):
            star = random.choice(list(G.DRAGON_BALL_STARS))
            db.add_dragon_ball(uid, star)
            extra.append(f"{star}★ Dragon Ball")
        if random.random() < 0.5:
            name = random.choice(list(G.EQUIPMENT))
            db.add_item(uid, name)
            extra.append(name)
        if random.random() < 0.2:
            learnable = [s for s in G.SKILLS if s not in db.skills(uid)]
            if learnable:
                s = random.choice(learnable)
                db.add_skill(uid, s)
                extra.append(f"skill {s}")
        await message.answer(
            f"🏆 <b>Boss defeated: {b['name']}!</b>\n+{b['yens']:,} yens, +{b['gems']} gems, "
            f"+{b['crystals']} crystals, +{b['tickets']} gacha tickets, +{b['skill_points']} skill points, +200 EXP\n"
            + (f"Bonus: {', '.join(extra)}" if extra else ""), parse_mode="HTML")
        return

    name, npc_hp, npc_dmg, yens = random.choice(G.NPCS)
    won, left, log = auto_battle(hp, atk, npc_hp, npc_dmg)
    if not won:
        await message.answer(f"😵 {name} beat you this time. No rewards.\n" + "\n".join(log[-2:]), parse_mode="HTML")
        return
    rewards = {"yens": yens, "exp": 20 + G.NPCS.index((name, npc_hp, npc_dmg, yens)) * 5}
    notes = [f"+{yens} yens"]
    if random.random() < 0.30:
        g = random.randint(1, 3); rewards["gems"] = g; notes.append(f"+{g} gems")
    if random.random() < 0.10:
        rewards["crystals"] = 1; notes.append("+1 crystal")
    if random.random() < 0.25:
        rewards["skill_points"] = 1; notes.append("+1 skill point")
    if random.random() < 0.05:
        rewards["tickets"] = 1; notes.append("+1 gacha ticket")
    if random.random() < 0.05:
        star = random.choice(list(G.DRAGON_BALL_STARS)); db.add_dragon_ball(uid, star); notes.append(f"{star}★ Dragon Ball")
    if random.random() < 0.05:
        it = random.choice(list(G.EQUIPMENT)); db.add_item(uid, it); notes.append(it)
    db.give(uid, **rewards)
    db.set_field(uid, "npc_streak", p["npc_streak"] + 1)
    left_to_boss = G.NPC_STREAK_FOR_BOSS - (p["npc_streak"] + 1)
    tail = f"\n⚠ A boss is coming in {left_to_boss} more win(s)!" if left_to_boss > 0 else \
        "\n⚠ A boss has appeared. Use /explore to face it!"
    await message.answer(f"⚔ You defeated <b>{name}</b>!\n" + ", ".join(notes) + tail, parse_mode="HTML")


HELP_TEXT = (
    "📖 <b>How to play</b>\n\n"
    "<b>Step 1. Get started</b>\n"
    "Send /start, then /daily to collect your first reward.\n\n"
    "<b>Step 2. Get stronger</b>\n"
    "/explore fights an enemy. Win to get yens, items and EXP.\n"
    "Every 15 wins, a boss appears. Beat it for big rewards.\n\n"
    "<b>Step 3. Get characters</b>\n"
    "/gacha uses one ticket for a random character. Get tickets from /daily, /weekly, bosses, or /shop.\n"
    "/equip Goku puts a character on your team. /myteam shows your strength.\n\n"
    "<b>Step 4. Gear up</b>\n"
    "/shop shows things to buy. /buy 1 buys item 1.\n"
    "/equip Iron Sword wears a weapon. Armor works the same way.\n\n"
    "<b>Step 5. Rank up</b>\n"
    "/rankup uses crystals. Crystals are rare, so save them.\n\n"
    "<b>Rewards</b>\n"
    "/daily: once a day. Keep it going for bigger rewards.\n"
    "/weekly: once a week. A bigger bundle plus a dragon ball.\n\n"
    "<b>Dragon balls</b>\n"
    "Collect one of each 1★ to 7★. Then /wish.\n\n"
    "<b>Friends</b>\n"
    "/give 50 gems (reply to a friend) sends items or money.\n\n"
    "<b>All commands</b>\n"
    "/profile, /explore, /daily, /weekly, /myinventory, /shop, /buy, /gacha, /mycharacters, "
    "/myteam, /equip, /skills, /learn, /wish, /summon, /give, /rankup, /raid, /raid_attack\n\n"
    "<i>Stuck? Ask in the group. Tip: /explore has no cost, so play often.</i>"
)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    u = message.from_user
    db.ensure_player(u.id, u.first_name, u.username)
    await message.answer(HELP_TEXT, parse_mode="HTML", reply_to_message_id=message.message_id,
                         allow_sending_without_reply=True)


@router.message(Command("daily"))
async def cmd_daily(message: Message) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    res = db.claim_daily(uid)
    if res is None:
        await message.answer("✅ You already took today's reward. Come back tomorrow.")
        return
    streak, rw = res
    parts = [f"{v:,} {k}" for k, v in rw.items()]
    await message.answer(f"🎁 <b>Daily reward</b> (day {streak} in a row)\n+ " + ", ".join(parts) +
                         "\nKeep the streak going for bigger rewards.", parse_mode="HTML")


@router.message(Command("weekly"))
async def cmd_weekly(message: Message) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    res = db.claim_weekly(uid)
    if res is None:
        await message.answer("✅ You already took this week's bundle. It resets every Monday.")
        return
    rw, star = res
    parts = [f"{v:,} {k}" for k, v in rw.items()] + [f"1 × {star}★ Dragon Ball"]
    await message.answer("🎁 <b>Weekly bundle</b>\n+ " + ", ".join(parts), parse_mode="HTML")


# ---------------- inventory and shop
@router.message(Command("myinventory"))
async def cmd_inventory(message: Message) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    p = db.player(uid)
    items = db.items(uid)
    balls = db.dragon_balls(uid)
    lines = [
        "🎒 <b>Inventory</b>",
        f"Yens: {p['yens']:,} · Gems: {p['gems']} · Crystals: {p['crystals']}",
        f"Gacha tickets: {p['tickets']} · Skill points: {p['skill_points']}",
        f"Elite keys: {p['keys_elite']} · Boss keys: {p['keys_boss']}",
        f"Weapon: {escape(p['weapon'] or 'none')} · Armor: {escape(p['armor'] or 'none')}",
        "", "<b>Items</b>: " + (", ".join(f"{escape(r['item'])} x{r['qty']}" for r in items) or "none"),
        "<b>Dragon balls</b>: " + (", ".join(f"{s}★ x{q}" for s, q in sorted(balls.items())) or "none"),
        "<b>Skills</b>: " + (", ".join(db.skills(uid)) or "none"),
    ]
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("shop"))
async def cmd_shop(message: Message) -> None:
    lines = ["🛒 <b>Shop</b>  (buy with /buy &lt;id&gt; [qty])"]
    for sid, (name, price, cur, kind, _) in G.SHOP.items():
        lines.append(f"{sid}. {escape(name)} — {price:,} {cur}")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("buy"))
async def cmd_buy(message: Message, command: CommandObject) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    parts = (command.args or "").split()
    if not parts or not parts[0].isdigit() or int(parts[0]) not in G.SHOP:
        await message.answer("Use <code>/buy &lt;id&gt; [qty]</code>. See /shop.", parse_mode="HTML")
        return
    qty = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 1
    qty = max(1, min(qty, 50))
    name, price, cur, kind, amount = G.SHOP[int(parts[0])]
    total = price * qty
    if not db.spend(uid, cur, total):
        await message.answer(f"Not enough {cur}. {name} x{qty} costs {total:,} {cur}.")
        return
    if kind == "item":
        db.add_item(uid, name, qty)
    elif kind == "ticket":
        db.give(uid, tickets=amount * qty)
    elif kind == "crystal":
        db.give(uid, crystals=amount * qty)
    elif kind == "key_elite":
        db.give(uid, keys_elite=amount * qty)
    elif kind == "key_boss":
        db.give(uid, keys_boss=amount * qty)
    await message.answer(f"✅ Bought {name} x{qty} for {total:,} {cur}.")


@router.message(Command("equip"))
async def cmd_equip(message: Message, command: CommandObject) -> None:
    uid = message.from_user.id
    name = (command.args or "").strip()
    if not name:
        await message.answer("Use <code>/equip &lt;name&gt;</code>. Example: /equip Goku or /equip Iron Sword",
                             parse_mode="HTML")
        return
    if name in G.EQUIPMENT:
        kind = G.EQUIPMENT[name][0]
        if name not in [r["item"] for r in db.items(uid)]:
            await message.answer("You don't own that item.")
            return
        db.set_field(uid, "weapon" if kind == "weapon" else "armor", name)
        await message.answer(f"Equipped {name}.")
        return
    if not db.has_character(uid, name):
        await message.answer("You don't own that character. Try /gacha or /mycharacters.")
        return
    db.set_field(uid, "equipped_char", name)
    await message.answer(f"{name} joins your team.")


@router.message(Command("myteam"))
async def cmd_myteam(message: Message) -> None:
    uid = message.from_user.id
    p = db.player(uid)
    atk, hp = player_stats(uid)
    await message.answer(
        f"🧩 <b>Your team</b>\nCharacter: {escape(p['equipped_char'] or 'none')}\n"
        f"Weapon: {escape(p['weapon'] or 'none')}\nArmor: {escape(p['armor'] or 'none')}\n"
        f"Attack: {atk} · Max HP: {hp}", parse_mode="HTML")


@router.message(Command("mycharacters"))
async def cmd_mycharacters(message: Message) -> None:
    rows = db.characters(message.from_user.id)
    if not rows:
        await message.answer("No characters yet. Try /gacha.")
        return
    await message.answer("🐲 <b>Your characters</b>\n" +
                         "\n".join(f"• {escape(r['name'])} ({r['rarity']})" for r in rows), parse_mode="HTML")


# ---------------- gacha, skills, dragon balls
@router.message(Command("gacha"))
async def cmd_gacha(message: Message) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    if not db.spend(uid, "tickets", 1):
        await message.answer("You need a gacha ticket. Buy one in /shop (id 7) or win boss fights.")
        return
    rarity = db.roll_rarity()
    pool = [n for n, r in G.CHARACTERS if r == rarity]
    name = random.choice(pool)
    if db.add_character(uid, name, rarity):
        await message.answer(f"🎰 You pulled <b>{escape(name)}</b> ({rarity})!", parse_mode="HTML")
    else:
        db.give(uid, gems=2)
        await message.answer(f"🎰 {escape(name)} ({rarity}) again. Converted to 2 gems.", parse_mode="HTML")


@router.message(Command("skills"))
async def cmd_skills(message: Message) -> None:
    owned = set(db.skills(message.from_user.id))
    lines = ["📜 <b>Skill shop</b>  (learn with /learn &lt;name&gt;, paid in skill points)"]
    for s, cost in G.SKILLS.items():
        lines.append(f"{'✅' if s in owned else '•'} {escape(s)} — {cost} points, +{G.SKILL_ATK[s]} attack")
    await message.answer("\n".join(lines), parse_mode="HTML")


@router.message(Command("learn"))
async def cmd_learn(message: Message, command: CommandObject) -> None:
    uid = message.from_user.id
    name = (command.args or "").strip()
    if name not in G.SKILLS:
        await message.answer("Use <code>/learn &lt;skill&gt;</code>. See /skills.", parse_mode="HTML")
        return
    if name in db.skills(uid):
        await message.answer("You already know that skill.")
        return
    if not db.spend(uid, "skill_points", G.SKILLS[name]):
        await message.answer(f"Not enough skill points. {name} costs {G.SKILLS[name]}.")
        return
    db.add_skill(uid, name)
    await message.answer(f"📘 Learned {name}!")


@router.message(Command("wish"))
async def cmd_wish(message: Message) -> None:
    uid = message.from_user.id
    if not db.take_one_of_each_dragon_ball(uid):
        await message.answer("You need one of each 1★ to 7★ Dragon Ball to make a wish.")
        return
    roll = random.random()
    if roll < 0.10:
        rarity = "mythical"
        name = random.choice([n for n, r in G.CHARACTERS if r == rarity])
        db.add_character(uid, name, rarity)
        result = f"a mythical character: <b>{escape(name)}</b>"
    elif roll < 0.25:
        db.add_item(uid, "Saiyan Blade"); result = "a mythical weapon: <b>Saiyan Blade</b>"
    elif roll < 0.40:
        db.add_skill(uid, "Spirit Bomb"); result = "the best skill: <b>Spirit Bomb</b>"
    elif roll < 0.70:
        db.give(uid, yens=100000); result = "100,000 yens"
    elif roll < 0.85:
        db.give(uid, gems=500); result = "500 gems"
    else:
        db.give(uid, crystals=50); result = "50 crystals"
    await message.answer(f"🐉 Shenron grants your wish: {result}!", parse_mode="HTML")


# ---------------- summons
@router.message(Command("summon"))
async def cmd_summon(message: Message, command: CommandObject) -> None:
    uid = message.from_user.id
    key = (command.args or "").strip().lower()
    if key not in G.SUMMONS:
        await message.answer("Use <code>/summon elite</code> or <code>/summon mythical</code>.", parse_mode="HTML")
        return
    boss, hp, dmg, mult, column = G.SUMMONS[key]
    if not db.spend(uid, column, 1):
        await message.answer(f"You need a {'elite' if key == 'elite' else 'boss'} key. Buy in /shop.")
        return
    atk, pl_hp = player_stats(uid)
    won, left, log = auto_battle(pl_hp, atk, hp, dmg)
    if not won:
        await message.answer(f"💀 {boss} was too strong. The key is gone.")
        return
    db.give(uid, yens=3000 * mult, gems=50 * mult, crystals=5 * mult, skill_points=4 * mult,
            tickets=2 * mult, exp=100 * mult)
    if random.random() < 0.5:
        db.add_item(uid, random.choice(list(G.EQUIPMENT)))
    if random.random() < 0.25:
        learnable = [s for s in G.SKILLS if s not in db.skills(uid)]
        if learnable:
            db.add_skill(uid, random.choice(learnable))
    await message.answer(f"🏆 You beat <b>{boss}</b>! Big rewards: {3000*mult:,} yens, {50*mult} gems, "
                         f"{5*mult} crystals, {4*mult} skill points, {2*mult} tickets.", parse_mode="HTML")


# ---------------- raid
@router.message(Command("raid"))
async def cmd_raid(message: Message) -> None:
    st = db.raid_state()
    if st is None or not st["active"]:
        await message.answer("No raid right now. The owner or an admin can start one with /raid_start.")
        return
    dmg_by = json.loads(st["damage_json"] or "{}")
    await message.answer(f"🌋 <b>Global raid</b>\nBoss HP: {st['hp']:,} / {st['max_hp']:,}\n"
                         f"Hitters: {len(dmg_by)}\nHit it with /raid_attack.", parse_mode="HTML")


@router.message(Command("raid_start"))
async def cmd_raid_start(message: Message) -> None:
    if not is_staff(message.from_user.id):
        await message.answer("Only the owner or an admin can start a raid.")
        return
    db.raid_start()
    await message.answer(f"🌋 A global raid has begun! Boss HP {G.RAID['hp']:,}. Hit it with /raid_attack. "
                         f"Defeat it to earn {G.RAID['reward_mult']}x rewards.")


@router.message(Command("raid_attack"))
async def cmd_raid_attack(message: Message) -> None:
    uid = message.from_user.id
    st = db.raid_state()
    if st is None or not st["active"]:
        await message.answer("No raid is active.")
        return
    wait = db.cooldown_ok(uid, G.RAID["attack_cooldown_s"])
    if wait:
        await message.answer(f"Wait {wait // 60}m {wait % 60}s before the next raid hit.")
        return
    atk, _ = player_stats(uid)
    damage = max(1, int(atk * random.uniform(1.5, 2.5)))
    res = db.raid_hit(uid, damage)
    db.mark_raid_hit(uid)
    if res is None:
        return
    hp_left, defeated, dmg_by = res
    if not defeated:
        await message.answer(f"💥 You hit the raid boss for {damage:,}. Boss HP left: {hp_left:,}.")
        return
    mult = G.RAID["reward_mult"]
    for hitter in dmg_by:
        db.give(int(hitter), yens=5000 * mult, gems=60 * mult, crystals=6 * mult,
                tickets=3 * mult, skill_points=6 * mult, exp=200 * mult)
    await message.answer(f"🏆 The raid boss is defeated! {len(dmg_by)} hitters each earned "
                         f"{mult}x boss rewards.")



# ---------------- give
CURRENCY_NAMES = {
    "yen": "yens", "yens": "yens", "gem": "gems", "gems": "gems",
    "crystal": "crystals", "crystals": "crystals", "ticket": "tickets", "tickets": "tickets",
    "skill point": "skill_points", "skill points": "skill_points",
    "elite key": "keys_elite", "elite keys": "keys_elite", "boss key": "keys_boss", "boss keys": "keys_boss",
}


def _find_name(thing: str, names) -> str | None:
    low = thing.lower()
    return next((n for n in names if n.lower() == low), None)


@router.message(Command("give"))
async def cmd_give(message: Message, command: CommandObject) -> None:
    giver = message.from_user.id
    db.ensure_player(giver, message.from_user.first_name, message.from_user.username)
    args = (command.args or "").split()
    usage = ("Use <code>/give &lt;amount&gt; &lt;thing&gt;</code> by replying to someone, or "
             "<code>/give @username &lt;thing&gt; [amount]</code>.\n"
             "Things: yens, gems, crystals, tickets, skill points, elite keys, boss keys, "
             "dragon ball 3, any weapon/armor, any skill, or a character name.")
    reply = message.reply_to_message
    if reply and reply.from_user and not reply.from_user.is_bot:
        target_id = reply.from_user.id
        db.ensure_player(target_id, reply.from_user.first_name, reply.from_user.username)
    else:
        if not args:
            await message.answer(usage, parse_mode="HTML")
            return
        tok = args.pop(0)
        if tok.startswith("@"):
            row = db.player_by_username(tok[1:])
            if row is None:
                await message.answer("I haven't seen that player yet. They need to send /start.")
                return
            target_id = row["user_id"]
        elif tok.isdigit():
            if db.player(int(tok)) is None:
                await message.answer("That player hasn't started yet (they need /start).")
                return
            target_id = int(tok)
        else:
            await message.answer(usage, parse_mode="HTML")
            return
    if target_id == giver:
        await message.answer("You can't give to yourself.")
        return
    qty = 1
    if args and args[-1].isdigit():
        qty = int(args.pop())
    qty = max(1, min(qty, 100000))
    thing = " ".join(args).strip()
    if not thing:
        await message.answer(usage, parse_mode="HTML")
        return

    # currency
    cur = CURRENCY_NAMES.get(thing.lower())
    if cur:
        if not db.spend(giver, cur, qty):
            await message.answer(f"You don't have {qty:,} {thing}.")
            return
        db.give(target_id, **{cur: qty})
        await message.answer(f"🎁 Sent {qty:,} {thing} to {target_id}.")
        return
    # dragon ball
    if thing.lower().startswith("dragon ball"):
        digits = [c for c in thing if c.isdigit()]
        if not digits or int(digits[0]) not in G.DRAGON_BALL_STARS:
            await message.answer("Use e.g. <code>/give @user dragon ball 3</code>.", parse_mode="HTML")
            return
        star = int(digits[0])
        if not db.remove_dragon_ball(giver, star, qty):
            await message.answer(f"You don't have {qty} of the {star}★ ball.")
            return
        db.add_dragon_ball(target_id, star, qty)
        await message.answer(f"🎁 Sent {qty} × {star}★ Dragon Ball.")
        return
    # equipment items (weapons and armor)
    item = _find_name(thing, G.EQUIPMENT)
    if item:
        owned = {r["item"]: r["qty"] for r in db.items(giver)}
        gp = db.player(giver)
        if gp["weapon"] == item or gp["armor"] == item:
            if owned.get(item, 0) - qty < 1:
                await message.answer("Unequip that item first (equip something else in its slot).")
                return
        if not db.remove_item(giver, item, qty):
            await message.answer(f"You don't have {qty} × {item}.")
            return
        db.add_item(target_id, item, qty)
        await message.answer(f"🎁 Sent {qty} × {item}.")
        return
    # characters and skills move (qty must be 1)
    char = _find_name(thing, [n for n, _ in G.CHARACTERS])
    if char:
        if db.transfer_character(giver, target_id, char):
            await message.answer(f"🎁 Sent <b>{char}</b> to the other player.", parse_mode="HTML")
        else:
            await message.answer("They already have that character, or you don't own it.")
        return
    skill = _find_name(thing, list(G.SKILLS))
    if skill:
        if db.transfer_skill(giver, target_id, skill):
            await message.answer(f"🎁 Sent the {skill} skill.")
        else:
            await message.answer("They already know that skill, or you don't know it.")
        return
    await message.answer(f"I don't know <i>{escape(thing)}</i>. " + "See /help for things you can give.",
                         parse_mode="HTML")


# ---------------- rankup
@router.message(Command("rankup"))
async def cmd_rankup(message: Message) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    rank = db.rank_of_player(uid)
    if rank >= 6:
        await message.answer("👑 You are already <b>Immortal</b>, the highest rank.", parse_mode="HTML")
        return
    if rank < 5:
        cost = G.RANKUP_CRYSTALS[rank]
        if not db.spend(uid, "crystals", cost):
            p = db.player(uid)
            await message.answer(f"Rank {G.RANKS[rank]} → {G.RANKS[rank + 1]} needs {cost:,} crystals. "
                                 f"You have {p['crystals']:,}.")
            return
        db.set_field(uid, "rank", rank + 1)
        await message.answer(f"⬆ Ranked up to <b>{G.RANKS[rank + 1]}</b>! (−{cost:,} crystals)", parse_mode="HTML")
        return
    total = len(G.CHARACTERS)
    have = len(db.characters(uid))
    if have < total:
        await message.answer(f"To become <b>Immortal</b> you need every gacha character: {have}/{total} owned.",
                             parse_mode="HTML")
        return
    db.set_field(uid, "rank", 6)
    await message.answer("👑 You own every character. You are now <b>Immortal</b>!", parse_mode="HTML")


# ---------------- artwork: /upload and /crown (admins only, same idea as the Veil bot)
def _art_targets() -> dict:
    """Every name that can have art: kind -> list of names."""
    return {
        "hero": [n for n, _ in G.CHARACTERS],
        "npc": [n for n, *_ in G.NPCS],
        "boss": [G.BOSS["name"]],
        "summon": [v[0] for v in G.SUMMONS.values()],
        "map": ["Map"],
    }


def _resolve_art_name(query: str):
    low = query.strip().lower()
    if low == "map":
        return "map", "Map"
    for kind, names in _art_targets().items():
        for n in names:
            if n.lower() == low:
                return kind, n
    return None, None


@router.message(Command("upload"))
async def cmd_upload(message: Message, command: CommandObject) -> None:
    if not is_staff(message.from_user.id):
        return  # silent for non-admins, like the Veil bot
    query = (command.args or "").strip()
    src = message.reply_to_message
    if not query or src is None or not src.photo:
        await message.answer("Reply to a photo with <code>/upload NAME</code>, e.g. <code>/upload Goku</code> "
                             "or <code>/upload Map</code>.", parse_mode="HTML")
        return
    kind, name = _resolve_art_name(query)
    if kind is None:
        await message.answer("I don't know that name. Check /crown for the list.")
        return
    db.set_art(kind, name, src.photo[-1].file_id)
    await message.answer(f"✅ Art saved for <b>{escape(name)}</b>.", parse_mode="HTML")


def _crown_text(tab: str, art: dict) -> str:
    targets = _art_targets()
    names = targets[tab]
    have = sum(1 for n in names if (tab, n) in art)
    lines = [f"👑 <b>Crown · {tab.title()}</b> — {have}/{len(names)} have art"]
    for n in names:
        lines.append(f"{'✅' if (tab, n) in art else '❌'} {escape(n)}")
    lines.append("<i>Upload: reply to a photo with /upload NAME</i>")
    return "\n".join(lines)


def _crown_kb() -> InlineKeyboardMarkup:
    tabs = [("hero", "Heroes"), ("npc", "NPCs"), ("boss", "Boss"), ("summon", "Summons"), ("map", "Map")]
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=f"crown:{k}")
                                                  for k, t in tabs]])


@router.message(Command("crown"))
async def cmd_crown(message: Message) -> None:
    if not is_staff(message.from_user.id):
        return
    await message.answer("👑 <b>Crown</b>: pick a category.", reply_markup=_crown_kb(), parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^crown:(hero|npc|boss|summon|map)$"))
async def cb_crown(callback: CallbackQuery) -> None:
    if not is_staff(callback.from_user.id):
        await callback.answer()
        return
    tab = callback.data.split(":")[1]
    try:
        await callback.message.edit_text(_crown_text(tab, db.all_art()), reply_markup=_crown_kb(),
                                         parse_mode="HTML")
    except Exception:
        pass  # same screen tapped again
    await callback.answer()


# ---------------- clans
import clans as CL  # noqa: E402

CLAN_HELP = (
    "🏰 <b>Clans</b>\n"
    "/clan create NAME  make a clan (costs 100 crystals)\n"
    "/clan join NAME  join a clan\n"
    "/clan info  your clan and its roles\n"
    "/clan members  list members\n"
    "/clan add @user  add a player (leader or officer). Or reply to them.\n"
    "/clan remove @user  remove a member (leader or officer)\n"
    "/clan promote @user  member → officer (leader)\n"
    "/clan demote @user  officer → member (leader)\n"
    "/clan transfer @user  hand leadership to someone (leader)\n"
    "/clan leave  leave your clan\n"
    "/clan disband  close the clan (leader)\n"
    "/clan list  top clans"
)


def _clan_target(message: Message, args: list[str]):
    """Target user id from a reply or @username, or None."""
    if message.reply_to_message and message.reply_to_message.from_user and not message.reply_to_message.from_user.is_bot:
        u = message.reply_to_message.from_user
        db.ensure_player(u.id, u.first_name, u.username)
        return u.id
    if args and args[0].startswith("@"):
        row = db.player_by_username(args[0][1:])
        return row["user_id"] if row else None
    return None


@router.message(Command("clan"))
async def cmd_clan(message: Message, command: CommandObject) -> None:
    uid = message.from_user.id
    db.ensure_player(uid, message.from_user.first_name, message.from_user.username)
    args = (command.args or "").split()
    sub = args[0].lower() if args else "help"
    rest = args[1:]
    reply = lambda t: message.answer(t, parse_mode="HTML", reply_to_message_id=message.message_id,
                                     allow_sending_without_reply=True)
    try:
        if sub in ("help", ""):
            await reply(CLAN_HELP)
        elif sub == "create":
            name = " ".join(rest)
            CL.create(uid, name)
            await reply(f"🏰 Clan <b>{escape(CL.clan_by_name(name)['name'])}</b> created! You are the leader.")
        elif sub == "join":
            CL.join(uid, " ".join(rest))
            await reply(f"🏰 You joined <b>{escape(' '.join(rest))}</b>.")
        elif sub == "leave":
            outcome = CL.leave(uid)
            await reply("You left the clan." if outcome == "left" else "You left and the empty clan closed.")
        elif sub == "info":
            m = CL.membership(uid)
            if m is None:
                await reply("You are not in a clan. Use /clan create NAME or /clan join NAME.")
                return
            mem = CL.members(m["clan_id"])
            roles = {"leader": 0, "officer": 0, "member": 0}
            for r in mem:
                roles[r["role"]] += 1
            await reply(f"🏰 <b>{escape(m['name'])}</b>\nYour role: {m['role']}\n"
                        f"Leaders {roles['leader']} · Officers {roles['officer']} · Members {roles['member']} "
                        f"({len(mem)}/{CL.MAX_MEMBERS})")
        elif sub == "members":
            m = CL.membership(uid)
            if m is None:
                await reply("You are not in a clan.")
                return
            lines = [f"{'👑' if r['role']=='leader' else '⭐' if r['role']=='officer' else '•'} "
                     f"{escape(r['first_name'] or 'Unknown')} ({r['role']})" for r in CL.members(m["clan_id"])]
            await reply(f"🏰 <b>{escape(m['name'])}</b> members\n" + "\n".join(lines))
        elif sub in ("add", "remove", "promote", "demote", "transfer"):
            target = _clan_target(message, rest)
            if target is None:
                await reply(f"Reply to the player's message, or use <code>/clan {sub} @username</code>.")
                return
            if db.player(target) is None:
                await reply("That player hasn't started the game yet (they need /start).")
                return
            {"add": CL.add, "remove": CL.remove, "promote": CL.promote,
             "demote": CL.demote, "transfer": CL.transfer}[sub](uid, target)
            done = {"add": "added to", "remove": "removed from", "promote": "promoted to officer in",
                    "demote": "demoted to member in", "transfer": "made the new leader of"}[sub]
            await reply(f"✅ Player {done} your clan.")
        elif sub == "disband":
            if not rest or rest[0].lower() != "confirm":
                await reply("This closes the clan for everyone. Send <code>/clan disband confirm</code> to do it.")
                return
            CL.disband(uid)
            await reply("🏰 Clan disbanded.")
        elif sub == "list":
            rows = CL.top_clans()
            if not rows:
                await reply("No clans yet. Be the first: /clan create NAME")
                return
            await reply("🏰 <b>Clans</b>\n" + "\n".join(f"{i}. {escape(r['name'])} ({r['n']} members)"
                                                       for i, r in enumerate(rows, 1)))
        else:
            await reply(CLAN_HELP)
    except CL.ClanError as exc:
        await reply(f"😕 {escape(str(exc))}")


# ---------------- run
async def main() -> None:
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise SystemExit("Set BOT_TOKEN first (see README).")
    db.init()
    bot = Bot(token=token, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
