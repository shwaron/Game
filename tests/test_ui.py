import pygame

from game.scenes.settings import binding_text, key_name
from game.ui import theme
from game.ui.hud import HudRenderer
from game.ui.widgets import EmberField, Fade, Menu, MenuItem


def _state(**overrides) -> dict:
    state = {
        "hp": 80,
        "max_hp": 100,
        "stamina": 40.0,
        "max_stamina": 100.0,
        "mana": 12.0,
        "max_mana": 100.0,
        "embers": 7,
        "kills": 3,
        "skills": [{"id": "ember_burst", "name": "烬爆", "cooldown": 1.5, "ready": False}],
        "weapon": {
            "name": "残焰剑",
            "slot": 2,
            "slots": 6,
            "level": 3,
            "damage_text": "13.2",
            "bonus": 0.1,
        },
        "bestiary": "妖物：酒坛魈",
        "hints": ["A/D 移动", "Q 换武器"],
        "hint_alpha": 1.0,
    }
    state.update(overrides)
    return state


def test_menu_wraps_and_skips_disabled_items():
    menu = Menu(
        [
            MenuItem("一", lambda: None),
            MenuItem("二", None, enabled=False),
            MenuItem("三", lambda: None),
        ]
    )
    assert menu.index == 0
    menu.move(1)
    assert menu.index == 2
    menu.move(1)
    assert menu.index == 0
    menu.move(-1)
    assert menu.index == 2


def test_menu_confirm_runs_action_once():
    calls: list[str] = []
    menu = Menu([MenuItem("开始", lambda: calls.append("start"))])
    assert menu.activate() is True
    assert calls == ["start"]


def test_menu_confirm_on_disabled_item_does_nothing():
    calls: list[str] = []
    menu = Menu([MenuItem("灰", lambda: calls.append("no"), enabled=False)])
    assert menu.activate() is False
    assert calls == []


def test_menu_keyboard_events():
    menu = Menu([MenuItem("一", None), MenuItem("二", None)])
    assert menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN)) == "move"
    assert menu.index == 1
    assert menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_w)) == "move"
    assert menu.index == 0
    assert menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)) == "confirm"
    assert menu.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)) == "back"


def test_menu_mouse_hover_and_click():
    calls: list[str] = []
    menu = Menu(
        [
            MenuItem("一", lambda: calls.append("first")),
            MenuItem("二", lambda: calls.append("second")),
        ]
    )
    surface = pygame.Surface((480, 270))
    menu.draw(surface, center_x=120, top=20)
    assert len(menu.rects) == 2

    hover = pygame.event.Event(pygame.MOUSEMOTION, pos=menu.rects[1].center)
    assert menu.handle_event(hover) == "move"
    assert menu.index == 1

    click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=menu.rects[1].center)
    assert menu.handle_event(click) == "confirm"
    assert calls == ["second"]


def test_draw_text_respects_anchor():
    surface = pygame.Surface((160, 60))
    rect = theme.draw_text(surface, theme.fonts().body, "余烬", (80, 30), anchor="center")
    assert rect.center == (80, 30)

    right = theme.draw_text(surface, theme.fonts().body, "回环", (80, 10), anchor="topright")
    assert right.right == 80
    assert right.top == 10


def test_glow_is_soft_not_a_flat_disc():
    sprite = theme.glow(16, theme.EMBER, 0.8)
    center = sprite.get_at((16, 16)).a
    edge = sprite.get_at((0, 0)).a
    assert center > 0
    assert center < 255
    assert edge == 0


def test_hud_renders_on_blank_surface():
    surface = pygame.Surface((480, 270))
    surface.fill((0, 0, 0))
    HudRenderer({}).draw(surface, _state())
    assert surface.get_at((12, 36)) != (0, 0, 0, 255)


def test_hud_tolerates_zero_caps():
    surface = pygame.Surface((480, 270))
    HudRenderer({}).draw(
        surface,
        _state(
            hp=0,
            max_hp=0,
            stamina=0.0,
            max_stamina=0.0,
            mana=0.0,
            max_mana=0.0,
            skills=[],
            weapon={},
            hint_alpha=0.0,
        ),
    )


def test_ember_field_recycles_particles():
    field = EmberField(480, 270, count=8, seed=1)
    for _ in range(900):
        field.update(1 / 60)
    assert len(field.particles) == 8
    for particle in field.particles:
        assert 0.0 <= particle["life"] < 1.0
        assert particle["size"] in (1, 2)


def test_fade_alpha_decays():
    fade = Fade(0.4)
    assert fade.alpha == 255
    fade.update(0.2)
    assert 0 < fade.alpha < 255
    fade.update(0.5)
    assert fade.alpha == 0


def test_settings_binding_labels():
    assert binding_text("jump") == "空格"
    assert binding_text("attack") == "J / 左键"
    assert key_name(pygame.K_LSHIFT) == "Shift"
    assert binding_text("not_an_action") == ""
