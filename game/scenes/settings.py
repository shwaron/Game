"""设置页：键位一览 + 操作提示开关。

从标题页或暂停页 push 进来，返回时 pop 回原场景；偏好暂存于 ui.preferences。
"""

import pygame

from game import config
from game.core.assets import load_json
from game.core.input import DEFAULT_BINDINGS, KEY, MOUSE
from game.core.scene_manager import Scene
from game.ui import preferences, theme
from game.ui.widgets import Fade, Menu, MenuItem

WIDTH = config.INTERNAL_WIDTH
HEIGHT = config.INTERNAL_HEIGHT

ACTIONS = (
    "move_left",
    "move_right",
    "jump",
    "dash",
    "attack",
    "offhand",
    "skill1",
    "skill2",
    "interact",
    "swap",
    "map",
    "pause",
)

_MOUSE_NAMES = {1: "左键", 2: "中键", 3: "右键"}
_KEY_NAMES = {
    pygame.K_SPACE: "空格",
    pygame.K_RETURN: "Enter",
    pygame.K_KP_ENTER: "Enter",
    pygame.K_ESCAPE: "Esc",
    pygame.K_TAB: "Tab",
    pygame.K_LSHIFT: "Shift",
    pygame.K_RSHIFT: "Shift",
    pygame.K_LEFT: "←",
    pygame.K_RIGHT: "→",
    pygame.K_UP: "↑",
    pygame.K_DOWN: "↓",
}


def key_name(code: int) -> str:
    if code in _KEY_NAMES:
        return _KEY_NAMES[code]
    return pygame.key.name(code).upper()


def binding_text(action: str) -> str:
    parts = []
    for kind, code in DEFAULT_BINDINGS.get(action, ()):
        parts.append(key_name(code) if kind == KEY else _MOUSE_NAMES.get(code, "鼠标"))
    return " / ".join(parts)


class SettingsScene(Scene):
    def __init__(self, game) -> None:
        self.game = game
        self.under = game.scenes.current
        self.loc = load_json("game/data/localization/zh_CN.json")
        self.fade = Fade(0.18)
        self.time = 0.0
        self.menu = Menu(
            [
                MenuItem(self._hint_label, self._toggle_hints),
                MenuItem(self._t("ui.settings.back", "返回"), self._back),
            ]
        )

    def _t(self, key: str, fallback: str) -> str:
        return self.loc.get(key, fallback)

    def _hint_label(self) -> str:
        value = preferences.get("show_hints", True)
        state = self._t("ui.settings.on", "开") if value else self._t("ui.settings.off", "关")
        return f"{self._t('ui.settings.hints', '操作提示')}：{state}"

    def enter(self) -> None:
        self.fade.start()

    def handle_event(self, event) -> None:
        if self.menu.handle_event(event) == "back":
            self._back()

    def update(self, dt: float) -> None:
        self.time += dt
        self.menu.update(dt)
        self.fade.update(dt)

    def _toggle_hints(self) -> None:
        preferences.set_value("show_hints", not preferences.get("show_hints", True))

    def _back(self) -> None:
        self.game.scenes.pop()
        self.game.input.end_step()

    # -- 绘制 -----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self.under.draw(surface)
        theme.draw_plate(
            surface, pygame.Rect(0, 0, WIDTH, HEIGHT), (5, 5, 4), 196
        )

        panel = pygame.Rect(60, 18, 360, 232)
        theme.draw_panel(surface, panel, alpha=214)

        theme.draw_text(
            surface,
            theme.fonts().heading,
            self._t("ui.settings.title", "设置"),
            (WIDTH // 2, panel.top + 6),
            theme.GOLD,
            anchor="midtop",
        )
        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.settings.subtitle", "回环不改其律，唯手可调"),
            (WIDTH // 2, panel.top + 24),
            theme.TEXT_FAINT,
            anchor="midtop",
        )
        theme.draw_rule(surface, WIDTH // 2, panel.top + 42, 150)

        fonts = theme.fonts()
        key_top = panel.top + 54
        for index, action in enumerate(ACTIONS):
            column = 0 if index < 6 else 1
            row = index % 6
            label_x = panel.left + 16 + column * 174
            value_x = label_x + 152
            y = key_top + row * 14
            label = self._t(f"ui.key.{action}", action)
            theme.draw_text(surface, fonts.body, label, (label_x, y), theme.TEXT_DIM)
            theme.draw_text(
                surface,
                fonts.body,
                binding_text(action),
                (value_x, y),
                theme.TEXT,
                anchor="topright",
            )

        pygame.draw.line(
            surface,
            theme.GOLD_FAINT,
            (panel.left + 14, key_top + 88),
            (panel.right - 14, key_top + 88),
            1,
        )
        self.menu.draw(
            surface, center_x=WIDTH // 2, top=key_top + 98, gap=11
        )
        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.settings.hint", "↑↓ 选择 · Enter 切换 · Esc 返回"),
            (WIDTH // 2, panel.bottom - 16),
            theme.TEXT_FAINT,
            anchor="midtop",
        )
        self.fade.draw(surface)
