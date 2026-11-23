"""兵器五选一：新开局与死亡重开时选择唯一武器。"""

import pygame

from game import config
from game.core.assets import load_json
from game.core.scene_manager import Scene
from game.ui import theme
from game.ui.widgets import EmberField, Fade

WIDTH = config.INTERNAL_WIDTH
HEIGHT = config.INTERNAL_HEIGHT

WEAPON_ORDER = ("tachi", "longsword", "zhanmadao", "shield", "bow")
CARD_W = 88
CARD_H = 152
CARD_TOP = 62
CARD_GAP = 8
MAX_DAMAGE = 24.0
MAX_REACH = 56.0
MAX_SPEED = 1000.0 / 190.0


class WeaponSelectScene(Scene):
    def __init__(
        self,
        game,
        on_confirm,
        on_cancel,
        current_id: str | None = None,
    ) -> None:
        self.game = game
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.loc = load_json("game/data/localization/zh_CN.json")
        self.weapons = load_json("game/data/weapons.json")["weapons"]
        self.index = (
            WEAPON_ORDER.index(current_id) if current_id in WEAPON_ORDER else 0
        )
        self.embers = EmberField(WIDTH, HEIGHT, count=30, seed=7, speed=(5.0, 16.0))
        self.fade = Fade(0.35)
        self.backdrop = theme.vertical_gradient(
            (WIDTH, HEIGHT), theme.NIGHT_TOP, theme.NIGHT_BOTTOM
        )
        self.card_rects = [
            pygame.Rect(
                4 + i * (CARD_W + CARD_GAP), CARD_TOP, CARD_W, CARD_H
            )
            for i in range(len(WEAPON_ORDER))
        ]

    def _t(self, key: str, fallback: str) -> str:
        return self.loc.get(key, fallback)

    def enter(self) -> None:
        self.fade.start()

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.index = (self.index - 1) % len(WEAPON_ORDER)
            elif event.key in (pygame.K_d, pygame.K_RIGHT):
                self.index = (self.index + 1) % len(WEAPON_ORDER)
            elif event.key in (pygame.K_j, pygame.K_e, pygame.K_RETURN):
                self.on_confirm(WEAPON_ORDER[self.index])
            elif event.key == pygame.K_ESCAPE:
                self.on_cancel()
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    self.index = i
                    break
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.card_rects):
                if rect.collidepoint(event.pos):
                    self.index = i
                    self.on_confirm(WEAPON_ORDER[i])
                    break

    def update(self, dt: float) -> None:
        self.embers.update(dt)
        self.fade.update(dt)

    def draw(self, surface: pygame.Surface) -> None:
        surface.blit(self.backdrop, (0, 0))
        self.embers.draw(surface)
        theme.draw_text(
            surface,
            theme.fonts().heading,
            self._t("ui.select.title", "选择兵器"),
            (WIDTH // 2, 26),
            theme.GOLD_BRIGHT,
            anchor="midtop",
        )
        theme.draw_rule(surface, WIDTH // 2, 48, 120)
        for i, weapon_id in enumerate(WEAPON_ORDER):
            self._draw_card(surface, i, weapon_id)
        theme.draw_text(
            surface,
            theme.fonts().tiny,
            self._t(
                "ui.select.hint", "A/D 选择 · J/Enter 确认 · 鼠标点选 · ESC 返回"
            ),
            (WIDTH // 2, HEIGHT - 24),
            theme.TEXT_FAINT,
            anchor="midtop",
        )
        self.fade.draw(surface)

    def _draw_card(self, surface: pygame.Surface, i: int, weapon_id: str) -> None:
        rect = self.card_rects[i]
        weapon = self.weapons[weapon_id]
        selected = i == self.index
        panel = pygame.Surface(rect.size, pygame.SRCALPHA)
        panel.fill((14, 12, 16, 210 if selected else 150))
        surface.blit(panel, rect.topleft)
        border = theme.GOLD_BRIGHT if selected else theme.GOLD_FAINT
        pygame.draw.rect(surface, border, rect, 1 if not selected else 2)
        if selected:
            theme.blit_glow(surface, rect.center, 46, theme.GOLD, 0.18)

        name = self._t(f"weapon.{weapon_id}.name", weapon_id)
        theme.draw_text(
            surface,
            theme.fonts().body,
            name,
            (rect.centerx, rect.y + 10),
            theme.GOLD_BRIGHT if selected else theme.TEXT_DIM,
            anchor="midtop",
        )
        self._draw_icon(surface, weapon_id, rect.centerx, rect.y + 40)

        cycle = weapon["windup_ms"] + weapon["active_ms"] + weapon["recovery_ms"]
        reach = MAX_REACH if weapon.get("projectile") else weapon["hitbox"][0]
        stats = (
            (self._t("ui.select.damage", "伤害"), weapon["base_damage"] / MAX_DAMAGE),
            (self._t("ui.select.reach", "距离"), reach / MAX_REACH),
            (self._t("ui.select.speed", "攻速"), (1000.0 / cycle) / MAX_SPEED),
        )
        for row, (label, ratio) in enumerate(stats):
            y = rect.y + 62 + row * 14
            theme.draw_text(
                surface,
                theme.fonts().tiny,
                label,
                (rect.x + 6, y),
                theme.TEXT_DIM,
                anchor="topleft",
            )
            bar_x = rect.x + 34
            bar_w = CARD_W - 40
            pygame.draw.rect(surface, (24, 20, 26), (bar_x, y + 2, bar_w, 5))
            pygame.draw.rect(
                surface,
                theme.GOLD if selected else theme.GOLD_DIM,
                (bar_x, y + 2, int(bar_w * min(1.0, ratio)), 5),
            )
            pygame.draw.rect(surface, (50, 42, 36), (bar_x, y + 2, bar_w, 5), 1)

        desc = self._t(f"weapon.{weapon_id}.desc", "")
        theme.draw_text(
            surface,
            theme.fonts().tiny,
            desc,
            (rect.centerx, rect.bottom - 32),
            theme.TEXT_FAINT,
            anchor="midtop",
        )
        if selected:
            theme.draw_text(
                surface,
                theme.fonts().tiny,
                self._t("ui.select.current", "点选确认"),
                (rect.centerx, rect.bottom - 16),
                theme.GOLD,
                anchor="midtop",
            )

    @staticmethod
    def _draw_icon(surface: pygame.Surface, weapon_id: str, cx: int, cy: int) -> None:
        steel = (214, 218, 228)
        hilt = (78, 60, 44)
        if weapon_id == "tachi":
            pts = [(cx - 16, cy + 6), (cx - 6, cy + 2), (cx + 6, cy - 2), (cx + 16, cy - 8)]
            pygame.draw.lines(surface, steel, False, pts, 2)
            pygame.draw.line(surface, hilt, (cx - 16, cy + 6), (cx - 22, cy + 9), 2)
        elif weapon_id == "longsword":
            pygame.draw.line(surface, steel, (cx - 14, cy + 6), (cx + 16, cy - 6), 2)
            pygame.draw.line(surface, (206, 208, 220), (cx - 12, cy + 1), (cx - 8, cy + 9), 2)
            pygame.draw.line(surface, hilt, (cx - 14, cy + 6), (cx - 20, cy + 9), 2)
        elif weapon_id == "zhanmadao":
            pygame.draw.line(surface, hilt, (cx - 22, cy + 10), (cx - 4, cy + 2), 2)
            pygame.draw.polygon(
                surface,
                steel,
                [(cx - 4, cy + 2), (cx + 18, cy - 8), (cx + 20, cy - 4), (cx - 2, cy + 6)],
            )
            pygame.draw.line(surface, (176, 58, 48), (cx - 8, cy + 4), (cx - 10, cy + 9), 1)
        elif weapon_id == "shield":
            rect = pygame.Rect(cx - 8, cy - 10, 16, 20)
            pygame.draw.rect(surface, hilt, rect)
            pygame.draw.rect(surface, (122, 118, 138), rect, 1)
            pygame.draw.line(surface, (84, 80, 98), (cx, cy - 8), (cx, cy + 8), 1)
            pygame.draw.circle(surface, (190, 174, 120), (cx, cy), 3)
        else:
            pygame.draw.line(surface, hilt, (cx + 4, cy - 10), (cx + 4, cy + 10), 2)
            pygame.draw.line(surface, hilt, (cx + 4, cy - 10), (cx + 1, cy - 7), 1)
            pygame.draw.line(surface, hilt, (cx + 4, cy + 10), (cx + 1, cy + 7), 1)
            pygame.draw.line(surface, (255, 245, 230), (cx + 4, cy - 10), (cx - 6, cy), 1)
            pygame.draw.line(surface, (255, 245, 230), (cx - 6, cy), (cx + 4, cy + 10), 1)
            pygame.draw.line(surface, steel, (cx - 6, cy), (cx + 10, cy), 2)
            pygame.draw.polygon(
                surface,
                (255, 245, 230),
                [(cx + 10, cy), (cx + 7, cy - 2), (cx + 7, cy + 2)],
            )