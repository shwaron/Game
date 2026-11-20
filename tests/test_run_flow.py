import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from game.core.app import Game


class FakeInput:
    """只实现出口判定会用到的最小接口。"""

    def __init__(self, pressed=()):
        self.pressed = set(pressed)

    def is_action_just_pressed(self, action: str) -> bool:
        return action in self.pressed


@pytest.fixture(scope="module")
def game() -> Game:
    app = Game()
    app.start_run()
    return app


@pytest.fixture()
def run(game: Game):
    game.start_run()
    return game.scenes.current


def test_room_enemies_are_not_respawned(run):
    run._enter_room("bamboo_path", "start")
    first = list(run.enemies)
    assert first

    run._enter_room("shrine", "from_path")
    run._enter_room("bamboo_path", "start")

    assert [id(enemy) for enemy in run.enemies] == [id(enemy) for enemy in first]


def test_damaged_enemy_keeps_hp_between_visits(run):
    run._enter_room("bamboo_path", "start")
    target = run.enemies[0]
    target.health.take_damage(7)
    hp = target.health.hp
    assert hp == target.health.max_hp - 7

    run._enter_room("shrine", "from_path")
    run._enter_room("bamboo_path", "start")

    assert run.enemies[0] is target
    assert run.enemies[0].health.hp == hp


def test_cleared_room_stays_empty(run):
    run._enter_room("bamboo_path", "start")
    run.room_enemies.pop("bamboo_path")
    run.cleared.add("bamboo_path")

    run._enter_room("shrine", "from_path")
    run._enter_room("bamboo_path", "start")

    assert run.enemies == []


def test_new_run_clears_enemy_cache(run):
    run._enter_room("bamboo_path", "start")
    assert run.room_enemies

    run._start_run()

    assert "bamboo_path" not in run.room_enemies
    assert run.room_enemies["shrine"] == []
    assert run.room.room_id == "shrine"


def test_exit_requires_interact_key(run):
    run._enter_room("shrine", "from_path")
    exit_ = run.room.exits[0]
    body = run.player.body
    body.x = float(exit_.rect.x + 4)
    body.y = float(exit_.rect.bottom - body.h)
    run.exit_cooldown = 0.0
    run.focus_exit = run._exit_under_player()

    assert run.focus_exit is exit_
    assert run._try_use_exit(FakeInput()) is False
    assert run.transition is None

    assert run._try_use_exit(FakeInput(["interact"])) is True
    assert run.transition is not None
    assert run.transition["target"] == exit_.target


def test_exit_blocked_during_entry_cooldown(run):
    run._enter_room("shrine", "from_path")
    exit_ = run.room.exits[0]
    body = run.player.body
    body.x = float(exit_.rect.x + 4)
    body.y = float(exit_.rect.bottom - body.h)
    run.exit_cooldown = 0.55
    run.focus_exit = run._exit_under_player()

    assert run._try_use_exit(FakeInput(["interact"])) is False
    assert run.transition is None


def test_no_exit_when_standing_away(run):
    run._enter_room("shrine", "from_path")
    body = run.player.body
    body.x = 120.0
    body.y = 208.0
    run.exit_cooldown = 0.0
    run.focus_exit = run._exit_under_player()

    assert run.focus_exit is None
    assert run._try_use_exit(FakeInput(["interact"])) is False
