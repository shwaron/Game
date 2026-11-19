"""暂停页：压在关卡之上的覆盖场景。

SceneManager 只绘制栈顶，所以这里先让下面的关卡画完，再叠一层暗色与菜单。
"""

import pygame

from game import config
from game.core.assets import load_json
from game.core.scene_manager import Scene
from game.ui import theme
from game.ui.widgets import Fade, Menu, MenuItem

WIDTH = config.INTERNAL_WIDTH
HEIGHT = config.INTERNAL_HEIGHT


class PauseScene(Scene):
    def __init__(self, game) -> None:
        self.game = game
        self.under = game.scenes.current
        self.loc = load_json("game/data/localization/zh_CN.json")
        self.fade = Fade(0.18)
        self.time = 0.0
        self.menu = Menu(
            [
                MenuItem(self._t("ui.pause.resume", "继续前行"), self._resume),
                MenuItem(self._t("ui.pause.restart", "重新入局"), self._restart),
                MenuItem(self._t("ui.pause.controls", "键位与设置"), self._open_settings),
                MenuItem(self._t("ui.pause.quit", "离开游戏"), self.game.quit),
            ]
        )

    def _t(self, key: str, fallback: str) -> str:
        return self.loc.get(key, fallback)

    def enter(self) -> None:
        self.fade.start()

    def handle_event(self, event) -> None:
        if self.menu.handle_event(event) == "back":
            self._resume()

    def update(self, dt: float) -> None:
        self.time += dt
        self.menu.update(dt)
        self.fade.update(dt)

    # -- 选项 -----------------------------------------------------------
    def _resume(self) -> None:
        self.game.scenes.pop()
        # 同一次逻辑步里 ESC 的 just_pressed 仍为真，清掉避免立刻又弹暂停。
        self.game.input.end_step()

    def _restart(self) -> None:
        self.game.scenes.pop()
        self.game.start_run()

    def _open_settings(self) -> None:
        from game.scenes.settings import SettingsScene

        self.game.scenes.push(SettingsScene(self.game))

    # -- 绘制 -----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        self.under.draw(surface)

        veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        veil.fill((5, 5, 4, 172))
        surface.blit(veil, (0, 0))

        panel = pygame.Rect(140, 52, 200, 176)
        theme.draw_panel(surface, panel, alpha=210)
        pygame.draw.line(
            surface,
            theme.GOLD_FAINT,
            (panel.left + 12, panel.top + 27),
            (panel.right - 12, panel.top + 27),
            1,
        )
        theme.draw_text(
            surface,
            theme.fonts().heading,
            self._t("ui.pause.title", "暂停"),
            (WIDTH // 2, panel.top + 8),
            theme.GOLD,
            anchor="midtop",
        )
        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.pause.subtitle", "回环暂歇"),
            (panel.right - 12, panel.top + 12),
            theme.TEXT_FAINT,
            anchor="topright",
        )

        self.menu.draw(surface, center_x=WIDTH // 2, top=panel.top + 42, gap=12)

        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t("ui.pause.hint", "Esc 继续"),
            (WIDTH // 2, panel.bottom - 15),
            theme.TEXT_FAINT,
            anchor="midtop",
        )
        self.fade.draw(surface)
