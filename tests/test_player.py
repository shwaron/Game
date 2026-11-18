from types import SimpleNamespace

import pygame

from game import config
from game.core.animation import AnimationClip
from game.entities.player import Player

DT = config.DT

ANIM_NAMES = [
    "idle",
    "run",
    "jump",
    "fall",
    "dash",
    "attack_windup",
    "attack_active",
    "attack_recovery",
    "parry",
    "skill",
    "hurt",
    "death",
]


def make_anim_clips():
    return {name: AnimationClip(name, "", 2, 10, True) for name in ANIM_NAMES}


class FakeInput:
    def __init__(self):
        self.pressed = set()
        self.just = set()

    def press(self, action):
        self.pressed.add(action)
        self.just.add(action)

    def release(self, action):
        self.pressed.discard(action)

    def is_action_pressed(self, action):
        return action in self.pressed

    def is_action_just_pressed(self, action):
        return action in self.just

    def get_axis(self, axis):
        assert axis == "move_x"
        return float("move_right" in self.pressed) - float(
            "move_left" in self.pressed
        )


def make_room(ground=None):
    return SimpleNamespace(
        solids=[ground or pygame.Rect(0, 246, 480, 24)],
        one_ways=[pygame.Rect(120, 190, 96, 8)],
    )


def step(player, inp, room, n=1):
    for _ in range(n):
        player.update(DT, inp, room)
        inp.just = set()


def test_jump_buffer_triggers_on_landing():
    player = Player(100, 205)
    inp = FakeInput()
    room = make_room()
    inp.press("jump")
    step(player, inp, room, 12)
    assert player.body.vel_y < 0
    assert player.rect.y < 205


def test_coyote_time_allows_late_jump():
    room = make_room(ground=pygame.Rect(0, 246, 100, 24))
    player = Player(70, 208)
    inp = FakeInput()
    step(player, inp, room, 2)
    assert player.body.on_ground
    inp.press("move_right")
    for _ in range(60):
        step(player, inp, room)
        if not player.body.on_ground:
            break
    assert not player.body.on_ground
    inp.press("jump")
    step(player, inp, room)
    assert player.body.vel_y == config.JUMP_VELOCITY


def test_dash_cooldown_blocks_second_dash():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    inp.press("dash")
    step(player, inp, room)
    assert player.dash_time > 0
    step(player, inp, room, 12)
    assert player.dash_time <= 0
    inp.press("dash")
    step(player, inp, room)
    assert player.dash_time <= 0
    assert player.dash_cooldown > 0


def test_variable_jump_height_cut():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    inp.press("jump")
    step(player, inp, room)
    assert player.body.vel_y < config.JUMP_CUT_VELOCITY
    inp.release("jump")
    step(player, inp, room)
    assert player.body.vel_y == config.JUMP_CUT_VELOCITY


def test_attack_hitbox_only_in_active_phase():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    inp.press("attack")
    step(player, inp, room)
    assert player.attack_phase == "windup"
    assert player.attack_hitbox is None
    step(player, inp, room, 4)
    assert player.attack_phase == "active"
    hitbox = player.attack_hitbox
    assert hitbox is not None
    assert hitbox.left == player.rect.right


def test_parry_window_and_cooldown():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    inp.press("offhand")
    step(player, inp, room)
    assert player.is_parrying
    assert player.parry_cooldown > 0
    step(player, inp, room, 10)
    assert not player.is_parrying


def test_parry_counter_buffs_next_attack():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    player.parry_success()
    assert player.counter_timer > 0
    inp.press("attack")
    step(player, inp, room)
    assert player.attack_power == player.weapon["base_damage"] * 1.5
    assert player.counter_timer == 0


def test_take_hit_applies_iframes_and_knockback():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    assert player.take_hit(10, (200, 208), 100)
    assert player.health.hp == 90
    assert player.invuln > 0
    assert player.body.vel_y < 0
    assert not player.take_hit(10, (200, 208), 100)
    assert player.health.hp == 90


def test_dash_and_parry_spend_stamina():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    assert player.stamina.value == config.STAMINA_MAX
    inp.press("dash")
    step(player, inp, room)
    assert player.dash_time > 0
    assert player.stamina.value == config.STAMINA_MAX - config.DASH_STAMINA_COST
    step(player, inp, room, 14)
    inp.press("offhand")
    step(player, inp, room)
    assert player.is_parrying
    expected = config.STAMINA_MAX - config.DASH_STAMINA_COST - config.PARRY_STAMINA_COST
    assert player.stamina.value <= expected
    assert player.stamina.value > expected - 3


def test_no_dash_when_stamina_insufficient():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    player.stamina.value = 5.0
    inp.press("dash")
    step(player, inp, room)
    assert player.dash_time <= 0


def test_fall_damage_on_hard_landing():
    player = Player(100, 0)
    inp = FakeInput()
    room = make_room()
    for _ in range(120):
        step(player, inp, room)
        if player.body.on_ground:
            break
    assert player.body.on_ground
    assert player.health.hp < player.health.max_hp


def test_normal_jump_landing_has_no_fall_damage():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    inp.press("jump")
    step(player, inp, room)
    for _ in range(90):
        step(player, inp, room)
        if player.body.on_ground:
            break
    assert player.body.on_ground
    assert player.health.hp == player.health.max_hp


def test_poison_dot_accumulates_fractional_damage():
    player = Player(100, 208)
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    player.status.apply("poison", 2.0, 4.0, max_stacks=1)
    step(player, inp, room, 60)
    assert player.health.hp < player.health.max_hp


def test_animation_follows_movement_and_dash():
    player = Player(100, 208, anim_clips=make_anim_clips())
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    assert player.anim.current == "idle"
    inp.press("move_right")
    step(player, inp, room, 3)
    assert player.anim.current == "run"
    inp.press("dash")
    step(player, inp, room)
    assert player.anim.current == "dash"


def test_animation_follows_attack_phases_and_death():
    player = Player(100, 208, anim_clips=make_anim_clips())
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    inp.press("attack")
    step(player, inp, room)
    assert player.anim.current == "attack_windup"
    for _ in range(10):
        step(player, inp, room)
        if player.attack_phase == "active":
            break
    assert player.anim.current == "attack_active"
    player.health.take_damage(999)
    step(player, inp, room)
    assert player.anim.current == "death"


def test_animation_follows_hurt_and_parry():
    player = Player(100, 208, anim_clips=make_anim_clips())
    inp = FakeInput()
    room = make_room()
    step(player, inp, room, 2)
    inp.press("offhand")
    step(player, inp, room)
    assert player.anim.current == "parry"
    step(player, inp, room, 20)
    player.take_hit(5, (200, 208), 0)
    step(player, inp, room)
    assert player.anim.current == "hurt"