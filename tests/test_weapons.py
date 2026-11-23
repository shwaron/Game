from types import SimpleNamespace

import pygame
import pytest

from game.components.health import Health
from game.components.resources import ResourcePool
from game.entities.player import Player
from game.systems.weapons import (
    level_multiplier,
    scaling_bonus,
    weapon_damage,
    weapon_level,
)


class FakeStats:
    def __init__(self, hp: int = 100, stamina: float = 100, mana: float = 100):
        self.health = Health(100)
        self.health.hp = hp
        self.stamina = ResourcePool(100)
        self.stamina.value = stamina
        self.mana = ResourcePool(100)
        self.mana.value = mana


class FakeInput:
    def __init__(self, *pressed: str):
        self._pressed = set(pressed)

    def get_axis(self, axis: str) -> float:
        return 0.0

    def is_action_pressed(self, action: str) -> bool:
        return action in self._pressed

    def is_action_just_pressed(self, action: str) -> bool:
        return action in self._pressed


def test_level_multiplier_scales_and_clamps():
    weapon = {"base_damage": 10, "level": 3, "level_scale": 0.1, "max_level": 5}
    assert weapon_level(weapon) == 3
    assert level_multiplier(weapon) == pytest.approx(1.2)
    weapon["level"] = 99
    assert weapon_level(weapon) == 5
    assert level_multiplier(weapon) == pytest.approx(1.4)
    weapon["level"] = 0
    assert weapon_level(weapon) == 1
    assert level_multiplier(weapon) == pytest.approx(1.0)


def test_plain_weapon_ignores_level_and_scaling():
    stats = FakeStats()
    assert weapon_damage({"base_damage": 12}, stats) == pytest.approx(12.0)
    assert scaling_bonus({"base_damage": 12}, stats) == 0.0


def test_missing_hp_scaling_rises_as_hp_drops():
    weapon = {
        "base_damage": 9,
        "scaling": [{"stat": "missing_hp", "max_bonus": 0.8}],
    }
    full = FakeStats(hp=100)
    low = FakeStats(hp=10)
    assert weapon_damage(weapon, full) == pytest.approx(9.0)
    assert weapon_damage(weapon, low) == pytest.approx(9 * (1 + 0.8 * 0.9))


def test_level_and_scaling_stack_multiplicatively():
    weapon = {
        "base_damage": 10,
        "level": 3,
        "level_scale": 0.1,
        "max_level": 5,
        "scaling": [{"stat": "missing_hp", "max_bonus": 0.8}],
    }
    stats = FakeStats(hp=50)
    assert weapon_damage(weapon, stats) == pytest.approx(10 * 1.2 * 1.4)


def test_stamina_and_mana_scaling_add_up():
    weapon = {
        "base_damage": 10,
        "scaling": [
            {"stat": "stamina", "max_bonus": 0.35},
            {"stat": "mana", "max_bonus": 0.5},
        ],
    }
    stats = FakeStats(stamina=50, mana=0)
    assert scaling_bonus(weapon, stats) == pytest.approx(0.175)
    assert weapon_damage(weapon, stats) == pytest.approx(10 * 1.175)


def test_wuxia_trio_keeps_design_tradeoffs():
    import json
    from pathlib import Path

    data = json.loads(
        Path(__file__).resolve().parent.parent.joinpath("game/data/weapons.json").read_text(encoding="utf-8")
    )["weapons"]
    tachi, longsword, zhanmadao = (data[k] for k in ("tachi", "longsword", "zhanmadao"))
    assert tachi["hitbox"][0] < longsword["hitbox"][0] < zhanmadao["hitbox"][0]
    assert tachi["base_damage"] < longsword["base_damage"] < zhanmadao["base_damage"]
    cycle = lambda w: w["windup_ms"] + w["active_ms"] + w["recovery_ms"]
    assert cycle(tachi) < cycle(longsword) < cycle(zhanmadao)


def test_shield_and_bow_special_rules():
    import json
    from pathlib import Path

    data = json.loads(
        Path(__file__).resolve().parent.parent.joinpath("game/data/weapons.json").read_text(encoding="utf-8")
    )["weapons"]
    shield, bow = data["shield"], data["bow"]
    assert shield["parry_scale"] == 2.0
    assert "projectile" not in shield
    assert shield["base_damage"] == 4
    assert shield["base_damage"] * shield["counter_multiplier"] == pytest.approx(
        8 * 1.5
    )
    assert bow["parry_scale"] == 0.0
    assert bow["projectile"]["speed"] > 0
    assert bow["projectile"]["life"] > 0
    from game import config

    assert bow["projectile"]["speed"] * bow["projectile"]["life"] == pytest.approx(
        config.INTERNAL_WIDTH / 2
    )
    for key in ("tachi", "longsword", "zhanmadao"):
        assert data[key].get("parry_scale", 1.0) == 1.0


def test_player_attack_uses_weapon_damage():
    weapon = {
        "base_damage": 10,
        "hitbox": [30, 26],
        "windup_ms": 50,
        "active_ms": 80,
        "recovery_ms": 140,
        "knockback": 0,
        "level": 2,
        "level_scale": 0.1,
        "max_level": 5,
        "scaling": [{"stat": "missing_hp", "max_bonus": 0.8}],
    }
    room = SimpleNamespace(
        solids=[pygame.Rect(0, 60, 480, 8)],
        one_ways=[],
    )
    player = Player(40, 20, weapon)
    player.health.hp = 10
    player.update(0.0, FakeInput("attack"), room)
    assert player.attack_power == pytest.approx(10 * 1.1 * (1 + 0.8 * 0.9))