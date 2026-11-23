import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from game.core.app import Game
from game.scenes.run import RunScene
from game.scenes.weapon_select import WEAPON_ORDER, WeaponSelectScene


@pytest.fixture(scope="module")
def game() -> Game:
    return Game()


def make_scene(game, **kwargs):
    confirmed = []
    cancelled = []
    scene = WeaponSelectScene(
        game,
        on_confirm=confirmed.append,
        on_cancel=lambda: cancelled.append(True),
        **kwargs,
    )
    return scene, confirmed, cancelled


def key(k):
    return pygame.event.Event(pygame.KEYDOWN, key=k)


def test_navigation_wraps(game):
    scene, confirmed, _ = make_scene(game)
    assert scene.index == 0

    scene.handle_event(key(pygame.K_a))
    assert scene.index == len(WEAPON_ORDER) - 1
    scene.handle_event(key(pygame.K_d))
    assert scene.index == 0
    scene.handle_event(key(pygame.K_RIGHT))
    assert scene.index == 1
    assert confirmed == []


def test_confirm_sends_selected_weapon(game):
    scene, confirmed, _ = make_scene(game)
    scene.handle_event(key(pygame.K_d))
    scene.handle_event(key(pygame.K_RETURN))
    assert confirmed == [WEAPON_ORDER[1]]


def test_escape_cancels(game):
    scene, confirmed, cancelled = make_scene(game)
    scene.handle_event(key(pygame.K_ESCAPE))
    assert cancelled == [True]
    assert confirmed == []


def test_current_weapon_preselected(game):
    scene, _, _ = make_scene(game, current_id="zhanmadao")
    assert scene.index == WEAPON_ORDER.index("zhanmadao")


def test_mouse_click_selects_then_confirms(game):
    scene, confirmed, _ = make_scene(game)
    scale = game._scale
    from game import config

    ox = (game.window.get_width() - config.INTERNAL_WIDTH * scale) // 2
    oy = (game.window.get_height() - config.INTERNAL_HEIGHT * scale) // 2
    rect = scene.card_rects[2]
    pos = (ox + rect.centerx * scale, oy + rect.centery * scale)
    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)

    scene.handle_event(click)
    assert scene.index == 2
    assert confirmed == []

    scene.handle_event(click)
    assert confirmed == ["zhanmadao"]


def test_open_weapon_select_flow(game):
    game.open_weapon_select()
    select = game.scenes.current
    assert isinstance(select, WeaponSelectScene)

    select.handle_event(key(pygame.K_d))
    select.handle_event(key(pygame.K_j))

    run = game.scenes.current
    assert isinstance(run, RunScene)
    assert run.weapon["id"] == WEAPON_ORDER[1]
    assert game.last_weapon_id == WEAPON_ORDER[1]


def test_start_run_remembers_last_weapon(game):
    game.start_run("zhanmadao")
    assert game.scenes.current.weapon["id"] == "zhanmadao"

    game.start_run()
    assert game.scenes.current.weapon["id"] == "zhanmadao"
    assert game.last_weapon_id == "zhanmadao"


def test_death_retry_opens_weapon_select(game):
    from game.scenes.death import DeathScene

    game.start_run("tachi")
    game.scenes.replace(DeathScene(game))
    game.scenes.current.handle_event(key(pygame.K_RETURN))

    select = game.scenes.current
    assert isinstance(select, WeaponSelectScene)
    assert select.index == WEAPON_ORDER.index("tachi")