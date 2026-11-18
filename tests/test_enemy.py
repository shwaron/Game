from types import SimpleNamespace

import pygame

from game.components.health import Health
from game.core.animation import AnimationClip
from game.entities.enemy import ChaserEnemy, ShooterEnemy

DT = 1 / 60

ENEMY_ANIM_NAMES = [
    "idle",
    "walk",
    "windup",
    "active",
    "recovery",
    "stagger",
    "death",
]


def make_enemy_anims():
    return {name: AnimationClip(name, "", 2, 10, True) for name in ENEMY_ANIM_NAMES}

CRAWLER = {
    "hp": 30,
    "damage": 8,
    "armor": 0,
    "speed": 60,
    "detect_range": 150,
    "attacks": [
        {
            "id": "bite",
            "windup_ms": 350,
            "active_ms": 100,
            "recovery_ms": 500,
            "hitbox": [26, 24],
            "range": 28,
            "knockback": 140,
            "cooldown": 1.2,
        }
    ],
    "loot_table": "wine_imp",
}

ARCHER = {
    "hp": 22,
    "damage": 6,
    "armor": 0,
    "speed": 45,
    "detect_range": 210,
    "keep_distance": 90,
    "attacks": [
        {
            "id": "shoot",
            "windup_ms": 400,
            "active_ms": 60,
            "recovery_ms": 600,
            "cooldown": 1.8,
            "projectile": {"speed": 160, "size": [6, 3], "life": 3.0},
        }
    ],
    "loot_table": "paper_runner",
}


def make_room():
    return SimpleNamespace(
        solids=[pygame.Rect(0, 246, 480, 24)], one_ways=[]
    )


def make_player(x, y=208):
    return SimpleNamespace(
        health=Health(100), rect=pygame.Rect(x, y, 18, 38)
    )


def test_chaser_moves_toward_player():
    room = make_room()
    enemy = ChaserEnemy("wine_imp", 300, 200, CRAWLER, room)
    player = make_player(200)
    start_x = enemy.rect.x
    for _ in range(60):
        enemy.update(DT, player)
    assert enemy.rect.x < start_x
    assert enemy.facing == -1


def test_chaser_attacks_in_range():
    room = make_room()
    enemy = ChaserEnemy("wine_imp", 230, 200, CRAWLER, room)
    player = make_player(200)
    enemy.cooldown = 0.0
    for _ in range(20):
        enemy.update(DT, player)
        if enemy.state == "windup":
            break
    assert enemy.state == "windup"
    for _ in range(30):
        enemy.update(DT, player)
    assert enemy.state in ("active", "recovery")
    assert enemy.swing_id >= 1


def test_hit_staggers_and_interrupts():
    room = make_room()
    enemy = ChaserEnemy("wine_imp", 230, 200, CRAWLER, room)
    player = make_player(200)
    enemy._start_attack()
    enemy.on_hit(5, (220, 208), 100)
    assert enemy.state == "stagger"
    assert enemy.attack_hitbox is None


def test_archer_fires_projectile():
    room = make_room()
    enemy = ShooterEnemy("paper_runner", 400, 200, ARCHER, room)
    player = make_player(250)
    enemy.cooldown = 0.0
    fired = False
    for _ in range(90):
        enemy.update(DT, player)
        if enemy.pending_projectile:
            fired = True
            break
    assert fired
    assert enemy.pending_projectile["speed"] == 160


def test_enemy_dies_at_zero_hp():
    room = make_room()
    enemy = ChaserEnemy("wine_imp", 230, 200, CRAWLER, room)
    enemy.on_hit(999, (220, 208), 0)
    assert not enemy.health.alive
    assert enemy.state == "dead"


def test_enemy_animation_follows_states():
    room = make_room()
    enemy = ChaserEnemy(
        "wine_imp", 300, 200, CRAWLER, room, make_enemy_anims()
    )
    player = make_player(200)
    for _ in range(5):
        enemy.update(DT, player)
    assert enemy.anim.current == "walk"
    enemy._start_attack()
    enemy.update(DT, player)
    assert enemy.anim.current == "windup"
    enemy.on_hit(5, (220, 208), 0)
    enemy.update(DT, player)
    assert enemy.anim.current == "stagger"
    enemy.on_hit(999, (220, 208), 0)
    enemy.update(DT, player)
    assert enemy.anim.current == "death"