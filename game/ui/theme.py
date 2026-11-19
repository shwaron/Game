"""统一视觉语言：夜岭调色板、中文字体、文字/面板/渐变/辉光绘制。

只放与流程无关的绘制工具，scene 与 HUD 共用，避免各处重复写颜色和坐标。
配色对齐 ``game/scenes/bamboo_world.py`` 的竹坞客栈基调：冷夜青绿 + 灯纸暖橙。
"""

import math
from functools import lru_cache

import pygame

# -- 调色板 -----------------------------------------------------------
INK = (9, 8, 10)
INK_SOFT = (16, 14, 18)
NIGHT_TOP = (10, 16, 18)
NIGHT_BOTTOM = (30, 42, 39)
MOON = (226, 222, 194)
MOUNTAIN_FAR = (30, 45, 44)
MOUNTAIN_NEAR = (22, 34, 35)
BAMBOO_SHADE = (26, 44, 36)

PANEL = (10, 9, 8)
PANEL_ALPHA = 196
GOLD = (226, 196, 134)
GOLD_BRIGHT = (246, 216, 158)
GOLD_DIM = (150, 116, 68)
GOLD_FAINT = (94, 74, 48)

TEXT = (224, 210, 180)
TEXT_DIM = (166, 158, 138)
TEXT_FAINT = (112, 105, 92)

EMBER = (236, 158, 82)
BLOOD = (206, 92, 62)
JADE = (122, 200, 132)
AZURE = (92, 150, 232)

FONT_TITLE = 22
FONT_HEADING = 15
FONT_BODY = 10
FONT_TINY = 9


def lerp_color(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def load_cjk_font(size: int) -> pygame.font.Font:
    """系统中文字体优先，退回 pygame 默认字体。

    与 ``bamboo_world.load_cjk_font`` 同一套候选；待 A 落地 AssetManager 后
    统一收口到资源层，这里先保证 UI 层不反向依赖 scenes。
    """
    if not pygame.font.get_init():
        pygame.font.init()
    for name in ("microsoftyahei", "simhei", "notosanssc", "simsun", "fangsong"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


class Fonts:
    """一屏所需字号的集合，构造一次后全局复用。"""

    def __init__(self) -> None:
        self.title = load_cjk_font(FONT_TITLE)
        self.heading = load_cjk_font(FONT_HEADING)
        self.body = load_cjk_font(FONT_BODY)
        self.tiny = load_cjk_font(FONT_TINY)


_fonts: Fonts | None = None


def fonts() -> Fonts:
    global _fonts
    if _fonts is None:
        _fonts = Fonts()
    return _fonts


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    value: str,
    pos,
    color=TEXT,
    *,
    anchor: str = "topleft",
    shadow=None,
) -> pygame.Rect:
    """按锚点绘制文字，可选 1px 深色描影保证暗背景可读。"""
    text = font.render(str(value), True, color)
    rect = text.get_rect(**{anchor: pos})
    if shadow is not None:
        shade = font.render(str(value), True, shadow)
        surface.blit(shade, rect.move(1, 1))
    surface.blit(text, rect)
    return rect


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    *,
    fill=PANEL,
    alpha: int = PANEL_ALPHA,
    edge=GOLD_DIM,
    width: int = 1,
) -> pygame.Rect:
    """半透明底 + 细描边，全项目菜单与结算面板统一样式。"""
    plate = pygame.Surface(rect.size, pygame.SRCALPHA)
    plate.fill((*fill, alpha))
    surface.blit(plate, rect.topleft)
    if edge is not None:
        pygame.draw.rect(surface, edge, rect, width)
    return rect


@lru_cache(maxsize=32)
def vertical_gradient(size: tuple[int, int], top, bottom) -> pygame.Surface:
    """竖向渐变：先画 1px 宽的色带再横向放大，成本可忽略。"""
    width, height = size
    strip = pygame.Surface((1, height))
    for y in range(height):
        strip.set_at((0, y), lerp_color(top, bottom, y / max(1, height - 1)))
    return pygame.transform.scale(strip, (width, height))


@lru_cache(maxsize=48)
def glow(radius: int, color, strength: float = 0.9) -> pygame.Surface:
    """柔光贴图，用于月亮、余烬与选中项，缓存后重复 blit。

    逐像素写入 alpha，避免用 draw.circle 叠加导致中心被累加成实心色盘。
    """
    size = radius * 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    surf.fill((*color, 0))
    for y in range(size):
        for x in range(size):
            dist = math.hypot(x + 0.5 - radius, y + 0.5 - radius)
            if dist >= radius:
                continue
            falloff = (1.0 - dist / radius) ** 2
            alpha = int(255 * strength * falloff)
            if alpha > 0:
                surf.set_at((x, y), (*color, alpha))
    return surf


def blit_glow(
    surface: pygame.Surface,
    center,
    radius: int,
    color,
    strength: float = 0.9,
) -> None:
    sprite = glow(radius, tuple(color), strength)
    surface.blit(sprite, (int(center[0]) - radius, int(center[1]) - radius))


def draw_rule(
    surface: pygame.Surface,
    center_x: int,
    y: int,
    width: int,
    color=GOLD_FAINT,
) -> None:
    """带菱形的细分割线，标题页与结算页的头尾装饰。"""
    half = width // 2
    pygame.draw.line(
        surface, color, (center_x - half, y), (center_x - 6, y), 1
    )
    pygame.draw.line(
        surface, color, (center_x + 6, y), (center_x + half, y), 1
    )
    pygame.draw.polygon(
        surface,
        color,
        [
            (center_x, y - 2),
            (center_x + 2, y),
            (center_x, y + 2),
            (center_x - 2, y),
        ],
    )


def pulse(t: float, speed: float = 2.0, low: float = 0.45) -> float:
    """0..1 的呼吸值，用于选中项与提示闪烁。"""
    return low + (1.0 - low) * (0.5 + 0.5 * math.sin(t * speed))
