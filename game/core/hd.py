"""高分辨率绘制层：逻辑坐标仍是 480x270，实际按 RENDER_SCALE 倍绘制。

游戏逻辑、碰撞、镜头继续使用 480x270 的逻辑坐标；本模块包一层
``HDSurface``，把所有 pygamedraw 调用与 blit 目标按整数倍放大，
让程序化美术与 UI 真正获得更高像素密度，而不是把低分辨率画面拉大。

用法：``screen = hd.Surface((480, 270))``，之后场景照常绘制；
读取像素时用 ``screen.target``。
"""

from __future__ import annotations

import pygame

RENDER_SCALE = 2

_installed = False
_originals: dict[str, object] = {}
_NATIVE: dict[int, object] = {}


def mark_native(surface):
    """标记为“已经是目标分辨率”的贴图，blit 时不再放大。"""
    _NATIVE[id(surface)] = surface
    return surface


def is_native(surface) -> bool:
    return id(surface) in _NATIVE


def _scale_point(point, scale: int):
    return (point[0] * scale, point[1] * scale)


def _scale_points(points, scale: int):
    return [(_scale_point(p, scale)) for p in points]


def _scale_rect(rect, scale: int) -> pygame.Rect:
    rect = pygame.Rect(rect)
    return pygame.Rect(
        rect.x * scale,
        rect.y * scale,
        rect.w * scale,
        rect.h * scale,
    )


def _scaled(width: int, scale: int) -> int:
    return width if width <= 0 else width * scale


def _wrap_rect(original):
    def draw_rect(surface, color, rect, width=0, *args, **kwargs):
        if getattr(surface, "_is_hd", False):
            rect = _scale_rect(rect, surface.scale)
            width = _scaled(width, surface.scale)
            surface = surface.target
        return original(surface, color, rect, width, *args, **kwargs)

    return draw_rect


def _wrap_line(original):
    def draw_line(surface, color, start, end, width=1):
        if getattr(surface, "_is_hd", False):
            start = _scale_point(start, surface.scale)
            end = _scale_point(end, surface.scale)
            width = _scaled(width, surface.scale)
            surface = surface.target
        return original(surface, color, start, end, width)

    return draw_line


def _wrap_lines(original):
    def draw_lines(surface, color, closed, points, width=1):
        if getattr(surface, "_is_hd", False):
            points = _scale_points(points, surface.scale)
            width = _scaled(width, surface.scale)
            surface = surface.target
        return original(surface, color, closed, points, width)

    return draw_lines


def _wrap_polygon(original):
    def draw_polygon(surface, color, points, width=0):
        if getattr(surface, "_is_hd", False):
            points = _scale_points(points, surface.scale)
            width = _scaled(width, surface.scale)
            surface = surface.target
        return original(surface, color, points, width)

    return draw_polygon


def _wrap_circle(original):
    def draw_circle(surface, color, center, radius, width=0, *args, **kwargs):
        if getattr(surface, "_is_hd", False):
            center = _scale_point(center, surface.scale)
            radius = max(1, radius * surface.scale)
            width = _scaled(width, surface.scale)
            surface = surface.target
        return original(surface, color, center, radius, width, *args, **kwargs)

    return draw_circle


def _wrap_ellipse(original):
    def draw_ellipse(surface, color, rect, width=0):
        if getattr(surface, "_is_hd", False):
            rect = _scale_rect(rect, surface.scale)
            width = _scaled(width, surface.scale)
            surface = surface.target
        return original(surface, color, rect, width)

    return draw_ellipse


def _wrap_arc(original):
    def draw_arc(surface, color, rect, start_angle, stop_angle, width=1):
        if getattr(surface, "_is_hd", False):
            rect = _scale_rect(rect, surface.scale)
            width = _scaled(width, surface.scale)
            surface = surface.target
        return original(surface, color, rect, start_angle, stop_angle, width)

    return draw_arc


def _wrap_aaline(original):
    def draw_aaline(surface, color, start, end, blend=1):
        if getattr(surface, "_is_hd", False):
            start = _scale_point(start, surface.scale)
            end = _scale_point(end, surface.scale)
            surface = surface.target
        return original(surface, color, start, end, blend)

    return draw_aaline


def _wrap_aalines(original):
    def draw_aalines(surface, color, closed, points, blend=1):
        if getattr(surface, "_is_hd", False):
            points = _scale_points(points, surface.scale)
            surface = surface.target
        return original(surface, color, closed, points, blend)

    return draw_aalines


def install() -> None:
    """给 pygame.draw 装上缩放适配；只对 HDSurface 生效。"""
    global _installed
    if _installed:
        return
    wrappers = {
        "rect": _wrap_rect,
        "line": _wrap_line,
        "lines": _wrap_lines,
        "polygon": _wrap_polygon,
        "circle": _wrap_circle,
        "ellipse": _wrap_ellipse,
        "arc": _wrap_arc,
        "aaline": _wrap_aaline,
        "aalines": _wrap_aalines,
    }
    for name, factory in wrappers.items():
        original = getattr(pygame.draw, name)
        _originals[name] = original
        setattr(pygame.draw, name, factory(original))
    _installed = True


class HDSurface:
    """逻辑尺寸的绘制代理，所有绘制落到 ``scale`` 倍的目标 Surface。"""

    _is_hd = True

    def __init__(self, size, scale: int = RENDER_SCALE, flags: int = 0) -> None:
        self.scale = max(1, int(scale))
        self.target = pygame.Surface(
            (size[0] * self.scale, size[1] * self.scale), flags
        )
        self._logical_size = (int(size[0]), int(size[1]))

    # -- 基本属性 -------------------------------------------------------
    def get_size(self):
        return self._logical_size

    def get_width(self) -> int:
        return self._logical_size[0]

    def get_height(self) -> int:
        return self._logical_size[1]

    def get_rect(self, **kwargs) -> pygame.Rect:
        rect = pygame.Rect(0, 0, *self._logical_size)
        for key, value in kwargs.items():
            setattr(rect, key, value)
        return rect

    def get_flags(self) -> int:
        return self.target.get_flags()

    def get_at(self, pos):
        return self.target.get_at(_scale_point(pos, self.scale))

    def set_at(self, pos, color) -> None:
        self.target.set_at(_scale_point(pos, self.scale), color)

    # -- 绘制 -----------------------------------------------------------
    def fill(self, color, rect=None, special_flags=0) -> pygame.Rect:
        if rect is None:
            return self.target.fill(color, None, special_flags)
        return self.target.fill(color, _scale_rect(rect, self.scale), special_flags)

    def blit_native(self, source, dest, area=None, special_flags=0) -> pygame.Rect:
        """``source`` 与 ``dest`` 都已是目标分辨率（例如 2 倍字体、预放大精灵）。"""
        return self.target.blit(source, dest, area, special_flags)

    def blit(self, source, dest, area=None, special_flags=0) -> pygame.Rect:
        """``source`` 与 ``dest`` 使用逻辑分辨率；按需要放大后贴到目标。"""
        if isinstance(source, HDSurface):
            src_area = None
            if isinstance(area, pygame.Rect):
                src_area = _scale_rect(area, source.scale)
            elif area is not None:
                src_area = _scale_rect(pygame.Rect(area), source.scale)
            return self.target.blit(
                source.target,
                _scale_point(dest, self.scale),
                src_area,
                special_flags,
            )

        if is_native(source):
            return self.target.blit(
                source,
                _scale_point(dest, self.scale),
                area,
                special_flags,
            )

        if self.scale == 1:
            return self.target.blit(source, dest, area, special_flags)

        width, height = source.get_size()
        if source.get_flags() & pygame.SRCALPHA:
            scaled = pygame.transform.smoothscale(
                source, (width * self.scale, height * self.scale)
            )
        else:
            scaled = pygame.transform.scale(
                source, (width * self.scale, height * self.scale)
            )
        if isinstance(area, pygame.Rect):
            area = _scale_rect(area, self.scale)
        return self.target.blit(
            scaled, _scale_point(dest, self.scale), area, special_flags
        )

    def set_alpha(self, alpha, flags=0) -> None:
        self.target.set_alpha(alpha, flags)

    def get_alpha(self) -> int:
        return self.target.get_alpha()


def Surface(size, flags: int = 0, scale: int = RENDER_SCALE) -> HDSurface:
    """创建一个逻辑尺寸的 HD 绘制面。"""
    install()
    return HDSurface(size, scale, flags)
