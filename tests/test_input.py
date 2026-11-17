import pygame
import pytest

from game.core.input import InputManager


class FakeKeys:
    def __getitem__(self, code):
        return False


@pytest.fixture
def im(monkeypatch):
    monkeypatch.setattr(pygame.key, "get_pressed", lambda: FakeKeys())
    monkeypatch.setattr(pygame.mouse, "get_pressed", lambda n=3: (False,) * n)
    return InputManager()


def key_event(kind, code):
    return pygame.event.Event(kind, key=code)


def test_keydown_hold_and_just_pressed(im):
    im.update([key_event(pygame.KEYDOWN, pygame.K_d)])
    assert im.is_action_pressed("move_right")
    assert im.is_action_just_pressed("move_right")
    assert im.get_axis("move_x") == 1
    im.end_step()
    im.update([])
    assert im.is_action_pressed("move_right")
    assert not im.is_action_just_pressed("move_right")


def test_keyup_releases(im):
    im.update([key_event(pygame.KEYDOWN, pygame.K_d)])
    im.update([key_event(pygame.KEYUP, pygame.K_d)])
    assert not im.is_action_pressed("move_right")


def test_simultaneous_keys(im):
    im.update([key_event(pygame.KEYDOWN, pygame.K_d)])
    im.update([key_event(pygame.KEYDOWN, pygame.K_SPACE)])
    assert im.is_action_pressed("move_right")
    assert im.is_action_pressed("jump")
    assert im.is_action_just_pressed("jump")
    im.update([key_event(pygame.KEYUP, pygame.K_d)])
    assert im.is_action_pressed("jump")
    assert not im.is_action_pressed("move_right")


def test_focus_loss_clears_held(im):
    im.update([key_event(pygame.KEYDOWN, pygame.K_a)])
    im.update([pygame.event.Event(pygame.WINDOWFOCUSLOST)])
    assert not im.is_action_pressed("move_left")