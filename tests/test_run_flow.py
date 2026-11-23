import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
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


def test_r_after_death_opens_weapon_select(run):
    from game.scenes.weapon_select import WeaponSelectScene

    run.player.health.take_damage(999)
    run.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))

    assert isinstance(run.game.scenes.current, WeaponSelectScene)


def test_r_while_alive_quick_restarts(run):
    run._enter_room("bamboo_path", "start")
    run.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_r))

    assert run.game.scenes.current is run
    assert run.room.room_id == "shrine"


def test_consecutive_arrows_each_hit(run):
    from game.systems.combat import TEAM_PLAYER

    run._enter_room("bamboo_path", "start")
    enemy = run.enemies[0]
    hp = enemy.health.hp
    uids = set()
    for _ in range(3):
        run.player.attack_power = 1.0
        run._spawn_player_arrow()
        arrow = run.projectiles.pop()
        uids.add(arrow.uid)
        hits = run.combat.resolve_melee(
            f"projectile:{arrow.uid}", enemy.rect, TEAM_PLAYER, arrow.damage
        )
        assert hits
        del arrow
    assert len(uids) == 3
    assert enemy.health.hp == hp - 3


def test_bow_shot_spawns_player_projectile(run):
    from game.systems.combat import TEAM_PLAYER

    run.weapon = run._make_weapon(run.weapon_data["bow"], "bow", 1)
    run.player.weapon = run.weapon
    run._enter_room("bamboo_path", "start")
    run.player.facing = 1
    run.player.attack_power = 9.0
    run.player.pending_shot = True

    run._spawn_player_arrow()

    assert run.projectiles
    arrow = run.projectiles[-1]
    assert arrow.team == TEAM_PLAYER
    assert arrow.damage == 9
    assert arrow.vel_x > 0
    assert arrow.rect.left >= run.player.rect.right
