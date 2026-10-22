import pytest

import clans as CL
import db
import game_data as G


def player(uid, name=None, crystals=1000):
    db.ensure_player(uid, name or f"P{uid}", f"p{uid}")
    db.give(uid, crystals=crystals)
    return uid


def test_create_costs_100_crystals():
    player(1, crystals=150)
    CL.create(1, "Dragon Hunters")
    assert db.player(1)["crystals"] == 50
    assert CL.membership(1)["role"] == "leader"


def test_create_refused_without_crystals():
    player(1, crystals=99)
    with pytest.raises(CL.ClanError):
        CL.create(1, "Poor Clan")


def test_name_rules_and_uniqueness():
    player(1); player(2)
    with pytest.raises(CL.ClanError):
        CL.create(1, "ab")                     # too short
    with pytest.raises(CL.ClanError):
        CL.create(1, "bad-name!")              # symbols not allowed
    CL.create(1, "Alpha")
    with pytest.raises(CL.ClanError):
        CL.create(2, "alpha")                  # names are case-insensitive


def test_one_clan_per_player():
    player(1); player(2)
    CL.create(1, "Alpha")
    with pytest.raises(CL.ClanError):
        CL.create(1, "Beta")
    CL.join(2, "Alpha")
    with pytest.raises(CL.ClanError):
        CL.join(2, "Alpha")


def test_clans_have_no_member_limit():
    for u in range(1, 41):
        player(u)
    CL.create(1, "Alpha")
    for u in range(2, 41):
        CL.join(u, "Alpha")
    assert len(CL.members(CL.membership(1)["clan_id"])) == 40


def test_leader_adds_and_officer_adds():
    for u in (1, 2, 3, 4):
        player(u)
    CL.create(1, "Alpha")
    CL.add(1, 2)
    CL.promote(1, 2)
    CL.add(2, 3)                               # officers can add
    assert CL.membership(3)["role"] == "member"
    with pytest.raises(CL.ClanError):
        CL.add(3, 4)                           # members cannot add


def test_promote_and_demote_are_leader_only():
    for u in (1, 2, 3):
        player(u)
    CL.create(1, "Alpha")
    CL.add(1, 2); CL.add(1, 3)
    with pytest.raises(CL.ClanError):
        CL.promote(2, 3)                       # officer can't promote (2 isn't officer yet anyway)
    CL.promote(1, 2)
    with pytest.raises(CL.ClanError):
        CL.promote(1, 2)                       # already officer
    CL.demote(1, 2)
    assert CL.membership(2)["role"] == "member"


def test_remove_rules():
    for u in (1, 2, 3, 4):
        player(u)
    CL.create(1, "Alpha")
    CL.add(1, 2); CL.add(1, 3); CL.add(1, 4)
    CL.promote(1, 2); CL.promote(1, 3)
    with pytest.raises(CL.ClanError):
        CL.remove(2, 3)                        # officer can't remove officer
    with pytest.raises(CL.ClanError):
        CL.remove(2, 1)                        # nobody removes the leader
    CL.remove(2, 4)                            # officer removes a member
    assert CL.membership(4) is None
    CL.remove(1, 3)                            # leader removes an officer
    assert CL.membership(3) is None


def test_leader_must_transfer_before_leaving():
    player(1); player(2)
    CL.create(1, "Alpha")
    CL.add(1, 2)
    with pytest.raises(CL.ClanError):
        CL.leave(1)
    CL.transfer(1, 2)
    assert CL.membership(2)["role"] == "leader"
    assert CL.membership(1)["role"] == "officer"
    assert CL.leave(1) == "left"


def test_last_member_leaving_closes_the_clan():
    player(1)
    CL.create(1, "Alpha")
    assert CL.leave(1) == "disbanded"
    assert CL.clan_by_name("Alpha") is None


def test_only_leader_disbands():
    player(1); player(2)
    CL.create(1, "Alpha")
    CL.add(1, 2)
    with pytest.raises(CL.ClanError):
        CL.disband(2)
    CL.disband(1)
    assert CL.clan_by_name("Alpha") is None
    assert CL.membership(2) is None


def test_clan_list_orders_by_size():
    for u in (1, 2, 3):
        player(u)
    CL.create(1, "Small"); CL.create(2, "Big")
    CL.add(2, 3)
    rows = CL.top_clans()
    assert rows[0]["name"] == "Big" and rows[0]["n"] == 2
