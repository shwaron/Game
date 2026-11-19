"""可复用控件：键盘/鼠标菜单、余烬粒子、淡入遮罩。

这些控件不依赖具体 scene，标题、暂停、死亡与设置页共用同一套交互。
"""

import math
import random

import pygame

from game.ui import theme

CONFIRM_KEYS = (pygame.K_RETURN, pygame.K_KP_ENTER)
UP_KEYS = (pygame.K_UP, pygame.K_w)
DOWN_KEYS = (pygame.K_DOWN, pygame.K_s)
BACK_KEYS = (pygame.K_ESCAPE, pygame.K_BACKSPACE)


class MenuItem:
    """一行菜单项。``label`` 可以是字符串或返回字符串的函数（用于开关项）。"""

    def __init__(self, label, action=None, *, enabled: bool = True) -> None:
        self.label = label
        self.action = action
        self.enabled = enabled

    def text(self) -> str:
        return self.label() if callable(self.label) else str(self.label)


class Menu:
    """竖向菜单：上下键/WS 切换，Enter 确认，鼠标悬停与点击同样可用。"""

    def __init__(self, items, *, index: int = 0) -> None:
        self.items = list(items)
        self.index = index
        self.rects: list[pygame.Rect] = []
        self.time = 0.0
        self._normalize()

    def _normalize(self) -> None:
        if not self.items:
            self.index = 0
            return
        self.index %= len(self.items)
        if self.items[self.index].enabled:
            return
        for offset in range(1, len(self.items) + 1):
            probe = (self.index + offset) % len(self.items)
            if self.items[probe].enabled:
                self.index = probe
                return

    def move(self, delta: int) -> None:
        if not self.items:
            return
        for _ in range(len(self.items)):
            self.index = (self.index + delta) % len(self.items)
            if self.items[self.index].enabled:
                return

    def activate(self) -> bool:
        if not self.items:
            return False
        item = self.items[self.index]
        if not item.enabled or item.action is None:
            return False
        item.action()
        return True

    def handle_event(self, event) -> str | None:
        """返回 ``"move"`` / ``"confirm"`` / ``"back"`` / ``None`` 供 scene 判断。"""
        if event.type == pygame.KEYDOWN:
            if event.key in UP_KEYS:
                self.move(-1)
                return "move"
            if event.key in DOWN_KEYS:
                self.move(1)
                return "move"
            if event.key in CONFIRM_KEYS:
                self.activate()
                return "confirm"
            if event.key in BACK_KEYS:
                return "back"
        elif event.type == pygame.MOUSEMOTION:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    if i != self.index:
                        self.index = i
                        return "move"
                    return None
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.rects):
                if rect.collidepoint(event.pos):
                    self.index = i
                    self.activate()
                    return "confirm"
        return None

    def update(self, dt: float) -> None:
        self.time += dt

    def height(self, fonts=None, *, gap: int = 12) -> int:
        fonts = fonts or theme.fonts()
        if not self.items:
            return 0
        return len(self.items) * fonts.heading.get_height() + (len(self.items) - 1) * gap

    def draw(
        self,
        surface: pygame.Surface,
        *,
        center_x: int,
        top: int,
        fonts=None,
        gap: int = 12,
    ) -> int:
        fonts = fonts or theme.fonts()
        self.rects = []
        y = top
        for i, item in enumerate(self.items):
            selected = i == self.index
            if selected:
                color = theme.GOLD_BRIGHT
            elif item.enabled:
                color = theme.TEXT_DIM
            else:
                color = theme.TEXT_FAINT
            label = fonts.heading.render(item.text(), True, color)
            rect = label.get_rect(midtop=(center_x, y))
            if selected:
                shadow = fonts.heading.render(item.text(), True, (12, 10, 8))
                surface.blit(shadow, rect.move(1, 1))
            surface.blit(label, rect)
            if selected:
                shimmer = theme.pulse(self.time, 2.4)
                marker_x = rect.left - 11
                marker_y = rect.centery
                pygame.draw.polygon(
                    surface,
                    theme.lerp_color(theme.GOLD_DIM, theme.GOLD_BRIGHT, shimmer),
                    [
                        (marker_x, marker_y - 3),
                        (marker_x + 3, marker_y),
                        (marker_x, marker_y + 3),
                        (marker_x - 3, marker_y),
                    ],
                )
                underline = theme.lerp_color(theme.GOLD_FAINT, theme.GOLD_DIM, shimmer)
                pygame.draw.line(
                    surface,
                    underline,
                    (rect.left + 2, rect.bottom + 2),
                    (rect.right - 2, rect.bottom + 2),
                    1,
                )
            self.rects.append(rect.inflate(28, 6))
            y = rect.bottom + gap
        return y - gap


class EmberField:
    """向上飘散的余烬粒子，标题与结算页背景用，固定种子保证每次一致。"""

    def __init__(
        self,
        width: int,
        height: int,
        *,
        count: int = 42,
        seed: int = 11,
        speed: tuple[float, float] = (7.0, 26.0),
    ) -> None:
        self.width = width
        self.height = height
        self.speed = speed
        self.rng = random.Random(seed)
        self.particles = [self._spawn(initial=True) for _ in range(count)]

    def _spawn(self, *, initial: bool = False) -> dict:
        low, high = self.speed
        return {
            "x": self.rng.uniform(-4, self.width + 4),
            "y": self.rng.uniform(0, self.height) if initial else self.height + self.rng.uniform(0, 30),
            "vy": self.rng.uniform(low, high),
            "vx": self.rng.uniform(-7.0, 7.0),
            "sway": self.rng.uniform(0.0, math.tau),
            "size": self.rng.choice((1, 1, 2)),
            "life": self.rng.uniform(0.0, 1.0),
            "fade": self.rng.uniform(0.10, 0.26),
        }

    def update(self, dt: float) -> None:
        for p in self.particles:
            p["y"] -= p["vy"] * dt
            p["sway"] += dt * 1.7
            p["x"] += (p["vx"] + math.sin(p["sway"]) * 6.0) * dt
            p["life"] += dt * p["fade"]
            if p["y"] < -8 or p["life"] >= 1.0:
                p.update(self._spawn())

    def draw(self, surface: pygame.Surface, *, base=theme.EMBER) -> None:
        for p in self.particles:
            fade = math.sin(min(1.0, p["life"]) * math.pi)
            color = theme.lerp_color(theme.INK, base, 0.15 + 0.85 * fade)
            surface.fill(
                color,
                (int(p["x"]), int(p["y"]), p["size"], p["size"]),
            )


class Fade:
    """进场淡入遮罩；``start`` 可重置，倒计时结束后不再绘制。"""

    def __init__(self, duration: float = 0.4, color=(0, 0, 0)) -> None:
        self.duration = max(0.001, duration)
        self.color = color
        self.timer = duration

    def start(self, duration: float | None = None) -> None:
        if duration is not None:
            self.duration = max(0.001, duration)
        self.timer = self.duration

    @property
    def alpha(self) -> int:
        if self.timer <= 0:
            return 0
        return max(0, min(255, int(255 * self.timer / self.duration)))

    def update(self, dt: float) -> None:
        self.timer = max(0.0, self.timer - dt)

    def draw(self, surface: pygame.Surface) -> None:
        alpha = self.alpha
        if alpha <= 0:
            return
        veil = pygame.Surface(surface.get_size())
        veil.fill(self.color)
        veil.set_alpha(alpha)
        surface.blit(veil, (0, 0))
