"""标题页：进入回环前的第一屏。

夜岭背景 + 余烬上升，菜单可键盘或鼠标操作；所有文案走本地化 key。
"""

import random

import pygame

from game import config
from game.core import hd
from game.core.assets import load_json
from game.core.scene_manager import Scene
from game.ui import theme
from game.ui.widgets import EmberField, Fade, Menu, MenuItem

WIDTH = config.INTERNAL_WIDTH
HEIGHT = config.INTERNAL_HEIGHT


class TitleScene(Scene):
    def __init__(self, game) -> None:
        self.game = game
        self.loc = load_json("game/data/localization/zh_CN.json")
        self.embers = EmberField(WIDTH, HEIGHT, count=46, seed=3, speed=(6.0, 22.0))
        self.fade = Fade(0.5)
        self.time = 0.0
        self.menu = Menu(
            [
                MenuItem(self._t("ui.title.start", "踏入灰烬"), self._start),
                MenuItem(self._t("ui.title.controls", "键位与设置"), self._open_settings),
                MenuItem(self._t("ui.title.quit", "离开余烬"), self.game.quit),
            ]
        )
        self.backdrop = self._build_backdrop()
        self.title_art: pygame.Surface | None = None

    def _t(self, key: str, fallback: str) -> str:
        return self.loc.get(key, fallback)

    # -- 生命周期 -------------------------------------------------------
    def enter(self) -> None:
        self.fade.start()
        self.title_art = self._render_title()

    def handle_event(self, event) -> None:
        self.menu.handle_event(event)

    def update(self, dt: float) -> None:
        self.time += dt
        self.embers.update(dt)
        self.menu.update(dt)
        self.fade.update(dt)

    # -- 跳转 -----------------------------------------------------------
    def _start(self) -> None:
        self.game.open_weapon_select()

    def _open_settings(self) -> None:
        from game.scenes.settings import SettingsScene

        self.game.scenes.push(SettingsScene(self.game))

    # -- 绘制 -----------------------------------------------------------
    def _render_title(self) -> pygame.Surface:
        fonts = theme.fonts()
        scale = getattr(self.game.screen, "scale", 1)
        font = theme.hd_font(fonts.title, scale) if scale > 1 else fonts.title
        text = self._t("ui.title.name", "余烬回环")
        spacing = 7 * scale
        widths = [font.size(ch)[0] for ch in text]
        total = sum(widths) + spacing * max(0, len(text) - 1)
        art = hd.mark_native(
            pygame.Surface(
                (total + 6 * scale, font.get_height() + 6 * scale),
                pygame.SRCALPHA,
            )
        )
        x = 3 * scale
        for ch, width in zip(text, widths):
            shadow = font.render(ch, True, (28, 16, 10))
            glyph = font.render(ch, True, theme.GOLD_BRIGHT)
            art.blit(shadow, (x + scale, 4 * scale))
            art.blit(glyph, (x, 3 * scale))
            x += width + spacing
        return art

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.backdrop, (0, 0))
        self.embers.draw(surface)

        if self.title_art is not None:
            scale = getattr(surface, "scale", 1)
            rect = self.title_art.get_rect(
                midtop=(WIDTH // 2 * scale, 44 * scale)
            )
            if scale > 1:
                surface.blit_native(self.title_art, rect)
            else:
                surface.blit(self.title_art, rect)

        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.title.english", "E M B E R L O O P"),
            (WIDTH // 2, 82),
            theme.GOLD_DIM,
            anchor="midtop",
        )
        theme.draw_text(
            surface,
            theme.fonts().body,
            self._t("ui.title.tagline", "一具无面之躯，攀向不熄的熔炉"),
            (WIDTH // 2, 100),
            theme.TEXT_DIM,
            anchor="midtop",
        )
        theme.draw_rule(surface, WIDTH // 2, 118, 168)

        self.menu.draw(surface, center_x=WIDTH // 2, top=132, gap=12)

        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.title.controls_hint", "↑↓ 选择 · Enter 确认 · 鼠标可点选"),
            (WIDTH // 2, HEIGHT - 28),
            theme.TEXT_FAINT,
            anchor="midtop",
        )
        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.title.build", "M1 原型 · 竹坞客栈"),
            (WIDTH - 10, HEIGHT - 28),
            theme.TEXT_FAINT,
            anchor="topright",
        )
        self._draw_frame(surface)
        self.fade.draw(surface)

    def _draw_frame(self, surface: pygame.Surface) -> None:
        corner = 10
        inset = 4
        color = theme.GOLD_FAINT
        for x, y, dx, dy in (
            (inset, inset, 1, 1),
            (WIDTH - inset - 1, inset, -1, 1),
            (inset, HEIGHT - inset - 1, 1, -1),
            (WIDTH - inset - 1, HEIGHT - inset - 1, -1, -1),
        ):
            pygame.draw.line(surface, color, (x, y), (x + corner * dx, y), 1)
            pygame.draw.line(surface, color, (x, y), (x, y + corner * dy), 1)

    def _build_backdrop(self) -> pygame.Surface:
        backdrop = hd.Surface((WIDTH, HEIGHT))
        scale = backdrop.scale
        gradient = theme.vertical_gradient(
            (WIDTH, HEIGHT), theme.NIGHT_TOP, theme.NIGHT_BOTTOM
        )
        backdrop.blit_native(
            pygame.transform.scale(gradient, (WIDTH * scale, HEIGHT * scale)),
            (0, 0),
        )

        rng = random.Random(5)
        for _ in range(46):
            x = rng.randrange(2, WIDTH - 2)
            y = rng.randrange(4, 150)
            shade = rng.choice((52, 68, 84, 96))
            backdrop.set_at((x, y), (shade, shade + 6, shade + 2))

        theme.blit_glow(backdrop, (374, 56), 54, theme.MOON, 0.35)
        pygame.draw.circle(backdrop, theme.MOON, (374, 56), 12)
        pygame.draw.circle(backdrop, (206, 202, 176), (370, 52), 3)
        pygame.draw.circle(backdrop, (214, 210, 184), (379, 61), 2)

        pygame.draw.polygon(
            backdrop,
            theme.MOUNTAIN_FAR,
            [
                (0, 214),
                (44, 176),
                (82, 198),
                (126, 162),
                (172, 202),
                (232, 172),
                (300, 206),
                (362, 178),
                (422, 200),
                (480, 174),
                (480, HEIGHT),
                (0, HEIGHT),
            ],
        )
        pygame.draw.polygon(
            backdrop,
            theme.MOUNTAIN_NEAR,
            [
                (0, 234),
                (58, 204),
                (108, 224),
                (158, 196),
                (220, 228),
                (280, 206),
                (342, 230),
                (402, 208),
                (480, 226),
                (480, HEIGHT),
                (0, HEIGHT),
            ],
        )

        for x, top, width in ((16, 62, 3), (38, 94, 2), (464, 70, 3), (442, 102, 2)):
            self._bamboo(backdrop, x, top, theme.BAMBOO_SHADE, width)

        pygame.draw.rect(backdrop, (13, 17, 17), (0, HEIGHT - 16, WIDTH, 16))
        pygame.draw.line(
            backdrop, (26, 34, 32), (0, HEIGHT - 16), (WIDTH, HEIGHT - 16), 1
        )
        return backdrop

    @staticmethod
    def _bamboo(surface: pygame.Surface, x: int, top: int, color, width: int) -> None:
        bottom = HEIGHT - 16
        pygame.draw.line(surface, color, (x, top), (x, bottom), width)
        for y in range(top + 18, bottom, 24):
            pygame.draw.line(surface, color, (x - 3, y), (x + 3, y), 1)
        for index, (dx, dy) in enumerate(((6, 8), (-7, 16), (8, 26), (-6, 34))):
            length = 9 if index % 2 == 0 else 7
            pygame.draw.polygon(
                surface,
                color,
                [
                    (x, top + dy),
                    (x + dx * length // 6, top + dy - 3),
                    (x + dx * length // 4, top + dy + 1),
                ],
            )
