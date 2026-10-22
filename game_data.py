"""Game tables. Edit these freely: prices, rarities, NPCs, drops and boss numbers."""

# NPCs for /explore: (name, hp, damage, yens reward)
NPCS = [
    ("Bandit Rookie", 60, 6, 120),
    ("Wild Wolf", 90, 9, 200),
    ("Rogue Ninja", 130, 12, 320),
    ("Iron Golem", 180, 14, 450),
    ("Shadow Sorcerer", 240, 18, 650),
    ("Dark Knight", 320, 22, 900),
]
NPC_STREAK_FOR_BOSS = 15          # every 15 NPC wins, a boss appears on the next explore
BOSS = {"name": "Frieza Force Commander", "hp": 1200, "dmg": 45,
        "yens": 5000, "gems": 60, "crystals": 6, "tickets": 3, "skill_points": 6}

# Dragon Ball Super characters: (name, rarity)
CHARACTERS = [
    ("Goku", "legendary"), ("Vegeta", "legendary"), ("Gohan", "epic"), ("Piccolo", "epic"),
    ("Trunks", "rare"), ("Krillin", "rare"), ("Android 18", "rare"), ("Beerus", "mythical"),
    ("Whis", "mythical"), ("Goku Black", "mythical"), ("Jiren", "legendary"), ("Frieza", "epic"),
    ("Cell", "epic"), ("Majin Buu", "legendary"), ("Broly", "mythical"), ("Hit", "rare"),
    ("Toppo", "rare"), ("Goten", "common"), ("Bulma", "common"), ("Master Roshi", "common"),
]
RARITY_ATK = {"common": 3, "rare": 6, "epic": 10, "legendary": 15, "mythical": 22}
RARITY_HP = {"common": 5, "rare": 10, "epic": 18, "legendary": 28, "mythical": 40}
GACHA_RATES = [("common", 45), ("rare", 30), ("epic", 15), ("legendary", 8), ("mythical", 2)]

# Equipment: name -> (kind, bonus)
EQUIPMENT = {
    "Wooden Sword": ("weapon", 4), "Iron Sword": ("weapon", 9), "Saiyan Blade": ("weapon", 16),
    "Leather Vest": ("armor", 8), "Steel Armor": ("armor", 18), "Saiyan Armor": ("armor", 30),
}

# Shop: id -> (name, price, currency, kind, amount)  kind: item|ticket|crystal|key
SHOP = {
    1: ("Wooden Sword", 500, "yens", "item", 1),
    2: ("Iron Sword", 2000, "yens", "item", 1),
    3: ("Saiyan Blade", 12000, "yens", "item", 1),
    4: ("Leather Vest", 600, "yens", "item", 1),
    5: ("Steel Armor", 2200, "yens", "item", 1),
    6: ("Saiyan Armor", 13000, "yens", "item", 1),
    7: ("Gacha Ticket", 50, "gems", "ticket", 1),
    8: ("Crystal", 30, "gems", "crystal", 1),
    9: ("Elite Key", 800, "yens", "key_elite", 1),
    10: ("Boss Key", 2500, "yens", "key_boss", 1),
}

# Skill shop (paid in skill points)
SKILLS = {"Ki Blast": 3, "Kaioken": 6, "Instant Transmission": 10, "Spirit Bomb": 18}
SKILL_ATK = {"Ki Blast": 3, "Kaioken": 6, "Instant Transmission": 4, "Spirit Bomb": 12}

DRAGON_BALL_STARS = range(1, 8)   # collect one of each 1 to 7 star for a wish

# Summon: key -> (boss name, hp, dmg, reward multiplier, key column)
SUMMONS = {
    "elite": ("Elite Ginyu Force", 2000, 80, 3, "keys_elite"),
    "mythical": ("Mythical Perfect Cell", 5000, 150, 5, "keys_boss"),
}

RAID = {"hp": 60000, "dmg": 300, "reward_mult": 50, "attack_cooldown_s": 600}

# Ranks: (number, name). Rankup costs in crystals. Rank 5 -> 6 needs every gacha character.
RANKS = {1: "Beginner", 2: "Novice", 3: "King", 4: "Emperor", 5: "Demigod", 6: "Immortal"}
RANKUP_CRYSTALS = {1: 500, 2: 4000, 3: 20000, 4: 70000}
