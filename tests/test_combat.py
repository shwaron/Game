import random

import pygame

from game.components.health import Health
from game.systems.combat import CombatSystem, roll_damage


class FakeEntity:
    def __init__(self, x, y, team, hp=30, armor=0):
        self.rect = pygame.Rect(x, y, 18, 38)
        self.team = team
        self.health = Health(hp, armor)
        self.hits = []

    def on_hit(self, amount, source_pos, knockback):
        self.health.take_damage(amount)
        self.hits.append(amount)


def test_damage_formula_armor_and_min():
    assert roll_damage(12, 4, crit_chance=0) == (8, False)
    assert roll_damage(1, 10, crit_chance=0) == (1, False)


def test_crit_doubles_with_seeded_rng():
    amount, crit = roll_damage(12, 0, crit_chance=1.0, rng=random.Random(1))
    assert crit
    assert amount == 18


def test_hit_once_per_swing():
    combat = CombatSystem()
    target = FakeEntity(50, 50, "enemy")
    combat.register(target)
    rect = pygame.Rect(40, 40, 40, 40)
    first = combat.resolve_melee("player:1", rect, "player", 10)
    second = combat.resolve_melee("player:1", rect, "player", 10)
    third = combat.resolve_melee("player:2", rect, "player", 10)
    assert len(first) == 1
    assert len(second) == 0
    assert len(third) == 1
    assert target.health.hp == 10


def test_team_filter_and_dead_targets():
    combat = CombatSystem()
    ally = FakeEntity(50, 50, "player")
    dead = FakeEntity(50, 50, "enemy", hp=1)
    dead.health.take_damage(1)
    combat.register(ally)
    combat.register(dead)
    rect = pygame.Rect(40, 40, 40, 40)
    assert combat.resolve_melee("swing", rect, "player", 10) == []


def test_unregister_removes_hurtbox():
    combat = CombatSystem()
    target = FakeEntity(50, 50, "enemy")
    combat.register(target)
    combat.unregister(target)
    rect = pygame.Rect(40, 40, 40, 40)
    assert combat.resolve_melee("swing", rect, "player", 10) == []