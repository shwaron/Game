"""死亡结算页：一次回环结束后的账目与去向。

由 RunScene 在死亡动画播完后切入，展示本局余烬、击杀、清场与存活时间。
"""

import pygame

from game import config
from game.core.assets import load_json
from game.core.scene_manager import Scene
from game.ui import theme
from game.ui.widgets import EmberField, Fade, Menu, MenuItem

WIDTH = config.INTERNAL_WIDTH
HEIGHT = config.INTERNAL_HEIGHT


class DeathScene(Scene):
    def __init__(self, game, stats: dict | None = None) -> None:
        self.game = game
        self.loc = load_json("game/data/localization/zh_CN.json")
        self.stats = {
            "embers": 0,
            "kills": 0,
            "rooms": 0,
            "total_rooms": 0,
            "time": 0.0,
        }
        if stats:
            self.stats.update(stats)
        self.embers = EmberField(WIDTH, HEIGHT, count=34, seed=9, speed=(14.0, 34.0))
        self.fade = Fade(0.55)
        self.time = 0.0
        self.menu = Menu(
            [
                MenuItem(self._t("ui.death.retry", "再入回环"), self.game.open_weapon_select),
                MenuItem(self._t("ui.death.to_title", "返回标题"), self.game.return_to_title),
            ]
        )

    def _t(self, key: str, fallback: str) -> str:
        return self.loc.get(key, fallback)

    def enter(self) -> None:
        self.fade.start()

    def handle_event(self, event) -> None:
        self.menu.handle_event(event)

    def update(self, dt: float) -> None:
        self.time += dt
        self.embers.update(dt)
        self.menu.update(dt)
        self.fade.update(dt)

    # -- 绘制 -----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(
            theme.vertical_gradient((WIDTH, HEIGHT), (8, 7, 9), (22, 17, 16)), (0, 0)
        )
        theme.blit_glow(surface, (WIDTH // 2, 60), 96, theme.EMBER, 0.18)
        self.embers.draw(surface, base=(190, 96, 62))

        theme.draw_text(
            surface,
            theme.fonts().title,
            self._t("ui.death.title", "魂归余烬祠"),
            (WIDTH // 2, 34),
            theme.GOLD_BRIGHT,
            anchor="midtop",
            shadow=(28, 16, 10),
        )
        theme.draw_text(
            surface,
            theme.fonts().body,
            self._t("ui.death.hint", "余烬未熄 · 重头再来"),
            (WIDTH // 2, 64),
            theme.TEXT_DIM,
            anchor="midtop",
        )
        if self.stats.get("zone"):
            theme.draw_text(
                surface,
                theme.fonts().tiny,
                str(self.stats["zone"]),
                (WIDTH // 2, 80),
                theme.TEXT_FAINT,
                anchor="midtop",
            )
        theme.draw_rule(surface, WIDTH // 2, 96, 156)

        self._draw_stats(surface)
        self.menu.draw(surface, center_x=WIDTH // 2, top=178, gap=12)

        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.death.menu_hint", "↑↓ 选择 · Enter 确认"),
            (WIDTH // 2, HEIGHT - 24),
            theme.TEXT_FAINT,
            anchor="midtop",
        )
        self.fade.draw(surface)

    def _draw_stats(self, surface: pygame.Surface) -> None:
        panel = pygame.Rect(150, 104, 180, 66)
        theme.draw_panel(surface, panel, alpha=140)

        def seconds(value: float) -> str:
            minutes, rest = divmod(int(value), 60)
            return f"{minutes}:{rest:02d}"

        rows = (
            (self._t("ui.death.stat.embers", "本局余烬"), str(self.stats["embers"])),
            (self._t("ui.death.stat.kills", "击杀"), str(self.stats["kills"])),
            (
                self._t("ui.death.stat.rooms", "已清房间"),
                f"{self.stats['rooms']}/{self.stats['total_rooms']}",
            ),
            (self._t("ui.death.stat.time", "存活"), seconds(self.stats["time"])),
        )
        for index, (label, value) in enumerate(rows):
            y = panel.top + 8 + index * 13
            theme.draw_text(
                surface, theme.fonts().body, label, (panel.left + 12, y), theme.TEXT_DIM
            )
            theme.draw_text(
                surface,
                theme.fonts().body,
                value,
                (panel.right - 12, y),
                theme.GOLD,
                anchor="topright",
            )
