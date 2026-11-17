from types import SimpleNamespace

import pygame

from game import config
from game.entities.player import Player

DT = config.DT


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