import random
from datetime import datetime, timedelta, timezone

import bot as B
import db
import game_data as G


def new_player(uid=1, name="Ana", username="ana"):
    db.ensure_player(uid, name, username)
    return uid


# ---------- players and currency
def test_player_is_created_once():
    new_player(1)
    new_player(1)
    assert db.player(1)["first_name"] == "Ana"


def test_spend_refuses_overdraft():
    new_player(1)
    db.give(1, yens=100)
    assert db.spend(1, "yens", 60) is True
    assert db.spend(1, "yens", 60) is False
    assert db.player(1)["yens"] == 40


def test_crystals_are_spendable():
    new_player(1)
    db.give(1, crystals=5)
    assert db.spend(1, "crystals", 5) is True


def test_level_from_exp():
    assert db.level_of(0) == 1
    assert db.level_of(250) == 3


def test_rank_order_by_exp():
    new_player(1)
    new_player(2, "Bo", "bo")
    db.give(2, exp=900)
    assert db.rank_of(2) == 1
    assert db.rank_of(1) == 2


# ---------- give
def test_give_currency_moves_it():
    new_player(1); new_player(2, "Bo", "bo")
    db.give(1, gems=10)
    assert db.spend(1, "gems", 4) is True
    db.give(2, gems=4)
    assert db.player(2)["gems"] == 4


def test_give_character_moves_it_and_unequips():
    new_player(1); new_player(2, "Bo", "bo")
    db.add_character(1, "Goku", "legendary")
    db.set_field(1, "equipped_char", "Goku")
    assert db.transfer_character(1, 2, "Goku") is True
    assert db.has_character(2, "Goku") and not db.has_character(1, "Goku")
    assert db.player(1)["equipped_char"] is None


def test_give_character_refused_if_target_owns_it():
    new_player(1); new_player(2, "Bo", "bo")
    db.add_character(1, "Goku", "legendary")
    db.add_character(2, "Goku", "legendary")
    assert db.transfer_character(1, 2, "Goku") is False


def test_give_skill_moves_it():
    new_player(1); new_player(2, "Bo", "bo")
    db.add_skill(1, "Ki Blast")
    assert db.transfer_skill(1, 2, "Ki Blast") is True
    assert "Ki Blast" in db.skills(2)


def test_give_items_and_dragon_balls():
    new_player(1); new_player(2, "Bo", "bo")
    db.add_item(1, "Iron Sword", 2)
    assert db.remove_item(1, "Iron Sword", 1) is True
    db.add_item(2, "Iron Sword", 1)
    assert db.remove_item(1, "Iron Sword", 5) is False
    db.add_dragon_ball(1, 3, 2)
    assert db.remove_dragon_ball(1, 3, 2) is True
    assert db.remove_dragon_ball(1, 3, 1) is False


def test_username_lookup_is_case_insensitive():
    new_player(2, "Bo", "bo")
    assert db.player_by_username("BO")["user_id"] == 2


# ---------- wish
def test_wish_needs_all_seven_stars():
    new_player(1)
    for s in G.DRAGON_BALL_STARS:
        db.add_dragon_ball(1, s)
    assert db.take_one_of_each_dragon_ball(1) is True
    assert db.take_one_of_each_dragon_ball(1) is False


# ---------- rankup costs and names
def test_rank_costs_and_names():
    assert G.RANKUP_CRYSTALS == {1: 500, 2: 4000, 3: 20000, 4: 70000}
    assert G.RANKS[1] == "Beginner" and G.RANKS[6] == "Immortal"


# ---------- daily and weekly
def test_daily_once_per_day_and_streak_grows():
    new_player(1)
    streak, rewards = db.claim_daily(1)
    assert streak == 1 and "yens" in rewards
    assert db.claim_daily(1) is None
    with db.conn() as c:
        c.execute("UPDATE players SET daily_day=? WHERE user_id=1",
                  ((datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat(),))
    assert db.claim_daily(1)[0] == 2


def test_daily_missed_day_resets_streak():
    new_player(1)
    with db.conn() as c:
        c.execute("UPDATE players SET daily_day=?, daily_streak=5 WHERE user_id=1",
                  ((datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat(),))
    assert db.claim_daily(1)[0] == 1


def test_weekly_once_per_week():
    new_player(1)
    rewards, star = db.claim_weekly(1)
    assert rewards["yens"] == 5000 and 1 <= star <= 3
    assert db.claim_weekly(1) is None


# ---------- battle
def test_weak_player_loses_to_strong_boss():
    won, _, _ = B.auto_battle(10, 1, 10_000, 500)
    assert won is False


def test_strong_player_beats_weak_mob():
    random.seed(1)
    won, _, _ = B.auto_battle(500, 100, 50, 5)
    assert won is True


def test_enrage_only_hits_harder_late():
    random.seed(2)
    _, hp_plain, _ = B.auto_battle(1000, 5, 400, 40, enrage=False)
    random.seed(2)
    _, hp_enraged, _ = B.auto_battle(1000, 5, 400, 40, enrage=True)
    assert hp_enraged <= hp_plain


# ---------- raid
def test_raid_damage_and_defeat():
    new_player(1); new_player(2, "Bo", "bo")
    db.raid_start()
    hp_left, defeated, _ = db.raid_hit(1, 1000)
    assert hp_left == G.RAID["hp"] - 1000 and defeated is False
    _, defeated, dmg_by = db.raid_hit(2, G.RAID["hp"])
    assert defeated is True and "1" in dmg_by and "2" in dmg_by


def test_raid_cooldown_enforced():
    new_player(1)
    db.mark_raid_hit(1)
    assert db.cooldown_ok(1, G.RAID["attack_cooldown_s"]) > 0


# ---------- crown and art
def test_upload_name_resolution():
    assert B._resolve_art_name("goku") == ("hero", "Goku")
    assert B._resolve_art_name("Map") == ("map", "Map")
    assert B._resolve_art_name("Nobody") == (None, None)


def test_crown_marks_uploaded_art():
    db.set_art("hero", "Goku", "FILE")
    text = B._crown_text("hero", db.all_art())
    assert "✅ Goku" in text
    assert "1/20" in text.splitlines()[0]


# ---------- help and text safety
def test_help_fits_telegram_limit():
    assert len(B.HELP_TEXT) < 4096


def test_every_shop_entry_has_a_valid_kind():
    kinds = {"item", "ticket", "crystal", "key_elite", "key_boss"}
    assert all(v[3] in kinds for v in G.SHOP.values())
