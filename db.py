"""SQLite storage. One file (game.sqlite) in this folder. Works on Termux/phones."""
import json
import os
import random
import sqlite3
import time

import game_data as G

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "game.sqlite"))


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS players(
            user_id INTEGER PRIMARY KEY, first_name TEXT, username TEXT,
            exp INTEGER DEFAULT 0, yens INTEGER DEFAULT 0, gems INTEGER DEFAULT 0,
            crystals INTEGER DEFAULT 0, tickets INTEGER DEFAULT 0, skill_points INTEGER DEFAULT 0,
            keys_elite INTEGER DEFAULT 0, keys_boss INTEGER DEFAULT 0,
            npc_streak INTEGER DEFAULT 0, equipped_char TEXT, weapon TEXT, armor TEXT,
            last_raid_hit INTEGER DEFAULT 0, rank INTEGER DEFAULT 1);
        CREATE TABLE IF NOT EXISTS items(user_id INTEGER, item TEXT, qty INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, item));
        CREATE TABLE IF NOT EXISTS characters(user_id INTEGER, name TEXT, rarity TEXT,
            PRIMARY KEY(user_id, name));
        CREATE TABLE IF NOT EXISTS skills(user_id INTEGER, name TEXT, PRIMARY KEY(user_id, name));
        CREATE TABLE IF NOT EXISTS dragon_balls(user_id INTEGER, star INTEGER, qty INTEGER DEFAULT 0,
            PRIMARY KEY(user_id, star));
        CREATE TABLE IF NOT EXISTS art(kind TEXT, name TEXT, file_id TEXT, PRIMARY KEY(kind, name));
        CREATE TABLE IF NOT EXISTS raid(id INTEGER PRIMARY KEY CHECK(id = 1), active INTEGER,
            hp INTEGER, max_hp INTEGER, damage_json TEXT);
        """)
        cols = [r[1] for r in c.execute("PRAGMA table_info(players)")]
        for col, ddl in [("rank", "INTEGER DEFAULT 1"), ("daily_day", "TEXT"),
                         ("daily_streak", "INTEGER DEFAULT 0"), ("weekly_week", "TEXT")]:
            if col not in cols:  # migrate older databases
                c.execute(f"ALTER TABLE players ADD COLUMN {col} {ddl}")


# ---------------- players
def ensure_player(uid: int, first: str, username: str | None) -> None:
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO players(user_id, first_name, username) VALUES (?,?,?)",
                  (uid, first or "", username or ""))
        c.execute("UPDATE players SET first_name=?, username=? WHERE user_id=?",
                  (first or "", username or "", uid))


def player(uid: int):
    with conn() as c:
        return c.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()


def level_of(exp: int) -> int:
    return 1 + int(exp) // 100


def rank_of(uid: int) -> int:
    with conn() as c:
        mine = c.execute("SELECT exp FROM players WHERE user_id=?", (uid,)).fetchone()
        if mine is None:
            return 0
        above = c.execute("SELECT COUNT(*) FROM players WHERE exp > ?", (mine["exp"],)).fetchone()[0]
        return above + 1


def give(uid: int, **amounts) -> None:
    """Add currency: yens, gems, crystals, tickets, skill_points, keys_elite, keys_boss, exp."""
    allowed = {"yens", "gems", "crystals", "tickets", "skill_points", "keys_elite", "keys_boss", "exp"}
    for k, v in amounts.items():
        if k not in allowed or not v:
            continue
        with conn() as c:
            c.execute(f"UPDATE players SET {k} = {k} + ? WHERE user_id=?", (int(v), uid))


def spend(uid: int, column: str, amount: int) -> bool:
    allowed = {"yens", "gems", "crystals", "tickets", "skill_points", "keys_elite", "keys_boss"}
    if column not in allowed:
        raise ValueError("bad currency")
    with conn() as c:
        cur = c.execute(f"UPDATE players SET {column} = {column} - ? WHERE user_id=? AND {column} >= ?",
                        (amount, uid, amount))
        return cur.rowcount == 1


def set_field(uid: int, field: str, value) -> None:
    if field not in {"equipped_char", "weapon", "armor", "npc_streak", "last_raid_hit", "rank"}:
        raise ValueError("bad field")
    with conn() as c:
        c.execute(f"UPDATE players SET {field}=? WHERE user_id=?", (value, uid))


# ---------------- inventory
def add_item(uid: int, item: str, qty: int = 1) -> None:
    with conn() as c:
        c.execute("INSERT INTO items(user_id,item,qty) VALUES(?,?,?) "
                  "ON CONFLICT(user_id,item) DO UPDATE SET qty = qty + excluded.qty", (uid, item, qty))


def items(uid: int) -> list:
    with conn() as c:
        return c.execute("SELECT item, qty FROM items WHERE user_id=? AND qty>0 ORDER BY item", (uid,)).fetchall()


def add_character(uid: int, name: str, rarity: str) -> bool:
    with conn() as c:
        cur = c.execute("INSERT OR IGNORE INTO characters(user_id,name,rarity) VALUES(?,?,?)", (uid, name, rarity))
        return cur.rowcount == 1


def characters(uid: int) -> list:
    with conn() as c:
        return c.execute("SELECT name, rarity FROM characters WHERE user_id=? ORDER BY rarity DESC, name",
                         (uid,)).fetchall()


def has_character(uid: int, name: str) -> bool:
    with conn() as c:
        return c.execute("SELECT 1 FROM characters WHERE user_id=? AND name=?", (uid, name)).fetchone() is not None


def add_skill(uid: int, name: str) -> bool:
    with conn() as c:
        return c.execute("INSERT OR IGNORE INTO skills(user_id,name) VALUES(?,?)", (uid, name)).rowcount == 1


def skills(uid: int) -> list:
    with conn() as c:
        return [r["name"] for r in c.execute("SELECT name FROM skills WHERE user_id=? ORDER BY name", (uid,))]


def add_dragon_ball(uid: int, star: int, qty: int = 1) -> None:
    with conn() as c:
        c.execute("INSERT INTO dragon_balls(user_id,star,qty) VALUES(?,?,?) "
                  "ON CONFLICT(user_id,star) DO UPDATE SET qty = qty + excluded.qty", (uid, star, qty))


def dragon_balls(uid: int) -> dict:
    with conn() as c:
        return {r["star"]: r["qty"] for r in c.execute(
            "SELECT star, qty FROM dragon_balls WHERE user_id=? AND qty>0", (uid,))}


def take_one_of_each_dragon_ball(uid: int) -> bool:
    """Consume one of each 1 to 7 star ball for a wish. Returns False if incomplete."""
    have = dragon_balls(uid)
    if any(have.get(s, 0) < 1 for s in G.DRAGON_BALL_STARS):
        return False
    with conn() as c:
        for s in G.DRAGON_BALL_STARS:
            c.execute("UPDATE dragon_balls SET qty = qty - 1 WHERE user_id=? AND star=?", (uid, s))
    return True


# ---------------- raid
def raid_state():
    with conn() as c:
        return c.execute("SELECT * FROM raid WHERE id=1").fetchone()


def raid_start() -> None:
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO raid(id, active, hp, max_hp, damage_json) VALUES(1,1,?,?,?)",
                  (G.RAID["hp"], G.RAID["hp"], json.dumps({})))


def raid_hit(uid: int, damage: int):
    """Apply damage to the global raid boss. Returns (hp_left, defeated_now, damage_by_user)."""
    st = raid_state()
    if st is None or not st["active"]:
        return None
    dmg_by = json.loads(st["damage_json"] or "{}")
    dmg_by[str(uid)] = dmg_by.get(str(uid), 0) + damage
    hp = max(0, st["hp"] - damage)
    defeated = hp == 0
    with conn() as c:
        c.execute("UPDATE raid SET hp=?, damage_json=?, active=? WHERE id=1",
                  (hp, json.dumps(dmg_by), 0 if defeated else 1))
    return hp, defeated, dmg_by


def cooldown_ok(uid: int, seconds: int) -> int:
    """Returns 0 when the user may attack now, else seconds to wait."""
    p = player(uid)
    left = seconds - (int(time.time()) - int(p["last_raid_hit"] or 0))
    return max(0, left)


def mark_raid_hit(uid: int) -> None:
    with conn() as c:
        c.execute("UPDATE players SET last_raid_hit=? WHERE user_id=?", (int(time.time()), uid))


def roll_rarity() -> str:
    total = sum(w for _, w in G.GACHA_RATES)
    r = random.uniform(0, total)
    acc = 0
    for name, w in G.GACHA_RATES:
        acc += w
        if r <= acc:
            return name
    return "common"


# ---------------- give / rank helpers
def player_by_username(username: str):
    with conn() as c:
        return c.execute("SELECT * FROM players WHERE lower(username)=lower(?)", (username,)).fetchone()


def remove_item(uid: int, item: str, qty: int) -> bool:
    with conn() as c:
        cur = c.execute("UPDATE items SET qty = qty - ? WHERE user_id=? AND item=? AND qty >= ?",
                        (qty, uid, item, qty))
        return cur.rowcount == 1


def remove_dragon_ball(uid: int, star: int, qty: int) -> bool:
    with conn() as c:
        cur = c.execute("UPDATE dragon_balls SET qty = qty - ? WHERE user_id=? AND star=? AND qty >= ?",
                        (qty, uid, star, qty))
        return cur.rowcount == 1


def transfer_character(giver: int, target: int, name: str) -> bool:
    """Move a character. Returns False if the giver doesn't own it or the target already does."""
    with conn() as c:
        row = c.execute("SELECT rarity FROM characters WHERE user_id=? AND name=?", (giver, name)).fetchone()
        if row is None or c.execute("SELECT 1 FROM characters WHERE user_id=? AND name=?",
                                    (target, name)).fetchone():
            return False
        c.execute("DELETE FROM characters WHERE user_id=? AND name=?", (giver, name))
        c.execute("INSERT INTO characters(user_id,name,rarity) VALUES(?,?,?)", (target, name, row["rarity"]))
        c.execute("UPDATE players SET equipped_char=NULL WHERE user_id=? AND equipped_char=?", (giver, name))
        return True


def transfer_skill(giver: int, target: int, name: str) -> bool:
    with conn() as c:
        if c.execute("SELECT 1 FROM skills WHERE user_id=? AND name=?", (giver, name)).fetchone() is None:
            return False
        if c.execute("SELECT 1 FROM skills WHERE user_id=? AND name=?", (target, name)).fetchone():
            return False
        c.execute("DELETE FROM skills WHERE user_id=? AND name=?", (giver, name))
        c.execute("INSERT INTO skills(user_id,name) VALUES(?,?)", (target, name))
        return True


def rank_of_player(uid: int) -> int:
    p = player(uid)
    return int(p["rank"] or 1) if p else 1


# ---------------- artwork (admin uploads, shown in /crown)
def set_art(kind: str, name: str, file_id: str) -> None:
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO art(kind, name, file_id) VALUES(?,?,?)", (kind, name, file_id))


def all_art() -> dict:
    with conn() as c:
        return {(r["kind"], r["name"]): r["file_id"] for r in c.execute("SELECT kind, name, file_id FROM art")}


# ---------------- daily and weekly rewards
def claim_daily(uid: int):
    """Once per UTC day. Streak counts consecutive days. Returns (streak, rewards) or None if already claimed."""
    from datetime import datetime, timedelta, timezone
    p = player(uid)
    now = datetime.now(timezone.utc).date()
    today = now.isoformat()
    if p["daily_day"] == today:
        return None
    yesterday = (now - timedelta(days=1)).isoformat()
    streak = (int(p["daily_streak"] or 0) + 1) if p["daily_day"] == yesterday else 1
    rewards = {"yens": 300 + min(streak, 15) * 100, "gems": min(1 + streak // 5, 5)}
    if streak % 3 == 0:
        rewards["tickets"] = 1
    if streak % 7 == 0:
        rewards["crystals"] = 1
    with conn() as c:
        c.execute("UPDATE players SET daily_day=?, daily_streak=? WHERE user_id=?", (today, streak, uid))
    give(uid, **rewards)
    return streak, rewards


def claim_weekly(uid: int):
    """Once per ISO week. Returns (rewards, star_ball) or None if already claimed this week."""
    import random
    from datetime import datetime, timezone
    p = player(uid)
    year, week, _ = datetime.now(timezone.utc).date().isocalendar()
    key = f"{year}-W{week:02d}"
    if p["weekly_week"] == key:
        return None
    with conn() as c:
        c.execute("UPDATE players SET weekly_week=? WHERE user_id=?", (key, uid))
    rewards = {"yens": 5000, "gems": 50, "crystals": 5, "tickets": 3, "skill_points": 5}
    give(uid, **rewards)
    star = random.randint(1, 3)
    add_dragon_ball(uid, star)
    return rewards, star
