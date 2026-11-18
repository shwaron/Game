"""Long-form bamboo-inn world: rooms, exits, and procedural art.

Everything here is drawn with primitives so the map stays free of external
assets.  Rooms are stitched into a small graph in ``build_world``; the run
scene streams one room at a time through a camera-clamped world surface.
"""

import math
import random
from dataclasses import dataclass

import pygame

WIDTH = 480
HEIGHT = 270
FLOOR_Y = 246

SKY_TOP = (12, 19, 21)
SKY_BOTTOM = (38, 50, 46)
MOON = (226, 222, 194)
MOON_DIM = (190, 190, 166)
MOUNTAIN_FAR = (30, 45, 44)
MOUNTAIN_NEAR = (24, 37, 38)

WOOD_DARK = (52, 36, 27)
WOOD = (82, 56, 38)
WOOD_LIGHT = (114, 78, 50)
WOOD_EDGE = (34, 24, 20)
ROOF = (37, 43, 44)
ROOF_DARK = (24, 28, 29)
ROOF_LIGHT = (66, 73, 72)
ROOF_EDGE = (16, 19, 20)
STONE = (73, 76, 67)
STONE_DARK = (50, 53, 48)
MOSS = (48, 70, 48)
PAPER = (214, 174, 110)
PAPER_LIGHT = (246, 206, 142)
LANTERN = (182, 54, 43)
LANTERN_LIGHT = (238, 118, 76)
LANTERN_GOLD = (196, 158, 88)
CLOTH = (150, 52, 46)
CLOTH_DARK = (94, 34, 34)
TALISMAN_RED = (176, 58, 48)
BAMBOO_FAR = (32, 54, 45)
BAMBOO_MID = (45, 77, 58)
BAMBOO_NEAR = (66, 103, 74)
BAMBOO_HI = (92, 132, 88)
BAMBOO_LEAF = (54, 90, 62)
BAMBOO_LEAF_LIGHT = (80, 118, 74)
FIREFLY = (190, 214, 128)
EMBER = (236, 158, 82)
HUD_GOLD = (226, 196, 134)

CELLAR_SKY = (13, 11, 11)
CELLAR_WALL = (40, 29, 24)
CELLAR_BRICK = (52, 38, 29)
CELLAR_DARK = (24, 18, 16)
VALLEY_SKY_TOP = (10, 22, 20)
VALLEY_SKY_BOTTOM = (34, 56, 42)
VALLEY_CLIFF = (26, 40, 32)
VALLEY_CLIFF_DARK = (18, 29, 24)
VALLEY_GLOW = (116, 176, 96)
TEMPLE_SKY_TOP = (9, 13, 24)
TEMPLE_SKY_BOTTOM = (30, 38, 50)
TEMPLE_STONE = (66, 70, 80)
TEMPLE_STONE_DARK = (43, 47, 56)
TEMPLE_RED = (118, 42, 38)
TEMPLE_RED_DARK = (73, 28, 26)

_GLOW_CACHE: dict[tuple, pygame.Surface] = {}
_VIGNETTE: pygame.Surface | None = None


def load_cjk_font(size: int) -> pygame.font.Font:
    if not pygame.font.get_init():
        pygame.font.init()
    for name in ("microsoftyahei", "simhei", "notosanssc", "simsun", "fangsong"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def _lerp(a, b, t: float):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _shared_glow(radius: int, color, strength: float = 1.0) -> pygame.Surface:
    key = (radius, tuple(color), strength)
    cached = _GLOW_CACHE.get(key)
    if cached is not None:
        return cached
    size = radius * 2
    surf = pygame.Surface((size, size))
    surf.fill((0, 0, 0))
    for y in range(size):
        for x in range(size):
            dist = math.hypot(x - radius + 0.5, y - radius + 0.5)
            if dist >= radius:
                continue
            falloff = (1.0 - dist / radius) ** 2 * strength
            surf.set_at(
                (x, y),
                (
                    min(255, int(color[0] * falloff)),
                    min(255, int(color[1] * falloff)),
                    min(255, int(color[2] * falloff)),
                ),
            )
    _GLOW_CACHE[key] = surf
    return surf


def _shared_vignette() -> pygame.Surface:
    global _VIGNETTE
    if _VIGNETTE is not None:
        return _VIGNETTE
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    cx, cy = WIDTH / 2, HEIGHT / 2
    max_dist = math.hypot(cx, cy)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            dist = math.hypot(x - cx, y - cy) / max_dist
            alpha = max(0, int((dist - 0.58) * 110))
            if alpha:
                surf.set_at((x, y), (5, 7, 8, min(70, alpha)))
    _VIGNETTE = surf
    return surf


class BaseArt:
    """Shared ambience, platform carpentry, and lighting helpers."""

    def __init__(self, width: int, seed: int, platforms=()) -> None:
        self.width = width
        self.seed = seed
        self.platforms = list(platforms)
        self.time = 0.0
        self.font_sign = load_cjk_font(14)
        self.font_small = load_cjk_font(11)
        self.lantern_glow = _shared_glow(34, (120, 50, 14), 1.0)
        self.window_glow = _shared_glow(58, (100, 64, 24), 0.7)
        self.ember_glow = _shared_glow(30, (150, 70, 20), 1.0)
        self.vignette = _shared_vignette()
        self.fireflies = self._make_fireflies()
        self.motes = self._make_motes()
        self.leaves = self._make_leaves()

    # -- particles ------------------------------------------------------
    def _make_fireflies(self):
        rng = random.Random(self.seed * 7 + 11)
        count = max(8, self.width // 34)
        return [
            {
                "x": rng.uniform(16, self.width - 16),
                "y": rng.uniform(84, 224),
                "phase": rng.uniform(0, math.tau),
                "amp": rng.uniform(3, 11),
                "speed": rng.uniform(0.3, 0.8),
            }
            for _ in range(count)
        ]

    def _make_motes(self):
        rng = random.Random(self.seed * 7 + 13)
        count = max(10, self.width // 26)
        return [
            {
                "x": rng.uniform(0, self.width),
                "y": rng.uniform(80, 230),
                "speed": rng.uniform(4, 10),
                "phase": rng.uniform(0, math.tau),
            }
            for _ in range(count)
        ]

    def _make_leaves(self):
        rng = random.Random(self.seed * 7 + 17)
        count = 14 + self.width // 55
        return [
            {
                "x": rng.uniform(0, self.width),
                "y": rng.uniform(0, HEIGHT),
                "speed": rng.uniform(5, 12),
                "sway": rng.uniform(6, 18),
                "phase": rng.uniform(0, math.tau),
            }
            for _ in range(count)
        ]

    def update(self, dt: float) -> None:
        self.time += dt

    # -- platforms ------------------------------------------------------
    def draw_platforms(self, surface: pygame.Surface, style: str = "wood") -> None:
        for rect in self.platforms:
            if style == "stone":
                self._stone_platform(surface, rect)
            else:
                self._wood_platform(surface, rect)

    def _wood_platform(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, rect.inflate(2, 2))
        pygame.draw.rect(surface, WOOD, rect)
        pygame.draw.line(
            surface, WOOD_LIGHT, (rect.x + 1, rect.y + 1), (rect.right - 2, rect.y + 1)
        )
        if rect.y >= 196:
            pygame.draw.rect(
                surface,
                CLOTH_DARK,
                (rect.x + 12, rect.y + 3, max(0, rect.w - 24), 3),
            )
            for x in (rect.x + 6, rect.right - 12):
                pygame.draw.rect(surface, WOOD_EDGE, (x, rect.bottom, 6, FLOOR_Y - rect.bottom))
                pygame.draw.rect(
                    surface, WOOD_DARK, (x + 1, rect.bottom, 3, FLOOR_Y - rect.bottom)
                )
        elif rect.y >= 148:
            pygame.draw.rect(surface, WOOD_EDGE, (rect.x, rect.y - 26, rect.w, 3))
            pygame.draw.line(
                surface, WOOD, (rect.x + 1, rect.y - 25), (rect.right - 2, rect.y - 25)
            )
            for x in range(rect.x + 6, rect.right - 4, 24):
                pygame.draw.rect(surface, WOOD_DARK, (x, rect.y - 23, 2, 23))
            for x in range(rect.x + 10, rect.right - 10, 52):
                pygame.draw.polygon(
                    surface,
                    WOOD_DARK,
                    [(x, rect.bottom), (x + 22, rect.bottom), (x + 11, rect.bottom + 18)],
                )
                pygame.draw.line(
                    surface,
                    WOOD,
                    (x + 11, rect.bottom),
                    (x + 11, rect.bottom + 14),
                    2,
                )
        else:
            for x in range(rect.x + 10, rect.right - 10, 46):
                pygame.draw.polygon(
                    surface,
                    WOOD_DARK,
                    [(x, rect.bottom), (x + 20, rect.bottom), (x + 10, rect.bottom + 16)],
                )
                pygame.draw.line(
                    surface,
                    WOOD,
                    (x + 10, rect.bottom),
                    (x + 10, rect.bottom + 12),
                    2,
                )

    def _stone_platform(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, STONE_DARK, rect.inflate(2, 2))
        pygame.draw.rect(surface, STONE, rect)
        pygame.draw.line(
            surface, (110, 112, 100), (rect.x + 1, rect.y + 1), (rect.right - 2, rect.y + 1)
        )
        for x in range(rect.x + 24, rect.right - 8, 48):
            pygame.draw.line(surface, STONE_DARK, (x, rect.y + 2), (x - 4, rect.bottom - 1), 1)
        if rect.y >= 196:
            for x in (rect.x + 10, rect.right - 18):
                pygame.draw.rect(
                    surface, STONE_DARK, (x, rect.bottom, 8, FLOOR_Y - rect.bottom)
                )
                pygame.draw.rect(
                    surface, STONE, (x + 1, rect.bottom, 4, FLOOR_Y - rect.bottom)
                )

    # -- light / ambience ----------------------------------------------
    def draw_lantern(
        self, surface: pygame.Surface, x: int, y: int, small: bool = False
    ) -> None:
        if small:
            pygame.draw.line(surface, (48, 34, 26), (x, y - 14), (x, y - 3), 1)
            body = pygame.Rect(x - 4, y, 8, 10)
        else:
            pygame.draw.line(surface, (48, 34, 26), (x, y - 18), (x, y - 5), 1)
            body = pygame.Rect(x - 5, y, 10, 14)
        pygame.draw.rect(surface, LANTERN_GOLD, (body.x + 1, body.y - 2, body.w - 2, 2))
        pygame.draw.rect(surface, LANTERN, body)
        pygame.draw.rect(
            surface, LANTERN_LIGHT, (body.x + 2, body.y + 2, 2, body.h - 4)
        )
        pygame.draw.line(
            surface, LANTERN_GOLD, (body.x, body.y + 3), (body.right - 1, body.y + 3), 1
        )
        pygame.draw.line(
            surface,
            LANTERN_GOLD,
            (body.x, body.bottom - 4),
            (body.right - 1, body.bottom - 4),
            1,
        )
        pygame.draw.rect(
            surface, LANTERN_GOLD, (body.x + 1, body.bottom, body.w - 2, 2)
        )
        pygame.draw.line(
            surface,
            LANTERN_LIGHT,
            (body.centerx, body.bottom + 2),
            (body.centerx, body.bottom + 6),
            1,
        )
        surface.blit(
            self.lantern_glow,
            (
                body.centerx - self.lantern_glow.get_width() // 2,
                body.centery - self.lantern_glow.get_height() // 2,
            ),
            special_flags=pygame.BLEND_RGB_ADD,
        )

    def _draw_ambient(self, surface: pygame.Surface) -> None:
        for fly in self.fireflies:
            x = fly["x"] + math.sin(self.time * fly["speed"] + fly["phase"]) * fly["amp"]
            y = fly["y"] + math.cos(self.time * fly["speed"] * 0.7 + fly["phase"]) * 5
            pygame.draw.circle(surface, FIREFLY, (round(x), round(y)), 1)
            if int(self.time * 2 + fly["phase"]) % 7 == 0:
                pygame.draw.circle(surface, (110, 130, 80), (round(x), round(y)), 2, 1)
        for mote in self.motes:
            x = mote["x"] + math.sin(self.time * 0.6 + mote["phase"]) * 3
            y = (mote["y"] - self.time * mote["speed"]) % 150 + 90
            pygame.draw.rect(surface, EMBER, (round(x), round(y), 1, 1))

    def _draw_leaves_front(self, surface: pygame.Surface) -> None:
        for leaf in self.leaves:
            x = (
                leaf["x"]
                + math.sin(self.time * 0.5 + leaf["phase"]) * leaf["sway"]
                + self.time * 4
            ) % (WIDTH + 24) - 12
            y = (leaf["y"] + self.time * leaf["speed"]) % (HEIGHT + 20) - 10
            if y > FLOOR_Y:
                continue
            pygame.draw.line(
                surface,
                (104, 126, 78),
                (round(x), round(y)),
                (round(x) + 2, round(y) + 1),
                1,
            )

    def draw_front(self, surface: pygame.Surface) -> None:
        self._draw_leaves_front(surface)
        surface.blit(self.vignette, (0, 0))


class ForestArt(BaseArt):
    """Bamboo forest with optional shrine / yard / ridge props."""

    def __init__(
        self,
        width: int,
        seed: int,
        platforms=(),
        density: float = 1.0,
        moon_x: int = 70,
        props=(),
        ground: str = "path",
    ) -> None:
        super().__init__(width, seed, platforms)
        rng = random.Random(seed)
        self.moon_x = moon_x
        self.props = list(props)
        self.ground = ground
        self.bamboo_far = self._make_layer(
            rng, max(8, int(width / 26 * density)), 2, 3, 28, 78
        )
        self.bamboo_mid = self._make_layer(
            rng, max(6, int(width / 52 * density) + 3), 3, 5, 20, 62
        )
        self.bamboo_near = self._make_near(rng)
        self.mountain_far = self._make_mountains(rng, 122, (70, 112), 66)
        self.mountain_near = self._make_mountains(rng, 154, (112, 148), 70)
        self.lantern_posts = []
        if ground == "path":
            step = 300
            for x in range(150, width - 60, step):
                self.lantern_posts.append(x)
        self.ground_marks = self._make_ground_marks(rng)

    def _make_layer(self, rng, count, w_min, w_max, top_min, top_max):
        stalkers = []
        span = self.width + 16
        for i in range(count):
            stalkers.append(
                {
                    "x": -8 + i * span / count + rng.uniform(-6, 6),
                    "top": rng.randint(top_min, top_max),
                    "width": rng.randint(w_min, w_max),
                    "phase": rng.uniform(0, math.tau),
                    "sway": rng.uniform(1.6, 3.2),
                }
            )
        return stalkers

    def _make_near(self, rng):
        stalkers = []
        for x, top, width in ((4, 0, 7), (48, 20, 5)):
            stalkers.append(
                {
                    "x": x,
                    "top": top,
                    "width": width,
                    "phase": rng.uniform(0, math.tau),
                    "sway": rng.uniform(2.4, 3.6),
                }
            )
        x = rng.randint(90, 150)
        while x < self.width - 20:
            stalkers.append(
                {
                    "x": x + rng.uniform(-8, 8),
                    "top": rng.randint(8, 36),
                    "width": rng.randint(5, 7),
                    "phase": rng.uniform(0, math.tau),
                    "sway": rng.uniform(2.4, 3.6),
                }
            )
            x += rng.randint(130, 190)
        return stalkers

    def _make_mountains(self, rng, base, top_range, step):
        points = [(0, base)]
        x = 0
        while x < self.width - 60:
            x += rng.randint(step, step + 40)
            points.append((min(x, self.width), rng.randint(*top_range)))
        points.extend([(self.width, base), (self.width, 200), (0, 200)])
        return points

    def _make_ground_marks(self, rng):
        marks = []
        for _ in range(max(10, self.width // 46)):
            marks.append(
                (
                    rng.randint(10, self.width - 20),
                    FLOOR_Y + rng.choice((5, 9, 13, 17)),
                    rng.randint(5, 13),
                    rng.randint(2, 4),
                )
            )
        return marks

    # -- drawing --------------------------------------------------------
    def draw_back(self, surface: pygame.Surface) -> None:
        self.draw_scenery(surface)
        for kind, x in self.props:
            if kind == "shrine":
                self._draw_shrine(surface, x)
            elif kind == "well":
                self._draw_well(surface, x)
            elif kind == "balcony":
                self._draw_balcony(surface, x)
            elif kind == "signpost":
                self._draw_signpost(surface, x)
        self._draw_bamboo_layer(surface, self.bamboo_near, BAMBOO_NEAR)
        self._draw_ground(surface)
        self.draw_platforms(surface, style="wood")
        for x in self.lantern_posts:
            self._draw_path_lantern(surface, x)
        self._draw_ambient(surface)

    def draw_scenery(self, surface: pygame.Surface) -> None:
        self._draw_sky(surface)
        pygame.draw.polygon(surface, MOUNTAIN_FAR, self.mountain_far)
        self._draw_bamboo_layer(surface, self.bamboo_far, BAMBOO_FAR)
        pygame.draw.polygon(surface, MOUNTAIN_NEAR, self.mountain_near)
        self._draw_mist(surface)
        self._draw_bamboo_layer(surface, self.bamboo_mid, BAMBOO_MID)
        self._draw_mist(surface, alpha_scale=0.6, offset=18)

    def _draw_sky(self, surface: pygame.Surface) -> None:
        for y in range(FLOOR_Y):
            t = y / FLOOR_Y
            pygame.draw.line(
                surface, _lerp(SKY_TOP, SKY_BOTTOM, t), (0, y), (self.width, y)
            )
        glow = _shared_glow(42, (26, 26, 16), 0.9)
        moon_x = self.moon_x
        surface.blit(
            glow,
            (moon_x - 39, 8),
            special_flags=pygame.BLEND_RGB_ADD,
        )
        pygame.draw.circle(surface, MOON_DIM, (moon_x + 3, 42), 16)
        pygame.draw.circle(surface, MOON, (moon_x, 39), 13)
        pygame.draw.circle(surface, (238, 234, 208), (moon_x - 4, 35), 6)

    def _draw_bamboo_layer(self, surface, layer, color) -> None:
        dark = _lerp(color, (10, 14, 12), 0.45)
        highlight = _lerp(color, BAMBOO_HI, 0.35)
        for stalk in layer:
            base_x = stalk["x"]
            top = stalk["top"]
            width = stalk["width"]
            if base_x < -8 or base_x > self.width + 8:
                continue
            sway = math.sin(self.time * 0.7 + stalk["phase"]) * stalk["sway"]

            def sx(y):
                f = max(0.0, (FLOOR_Y - y) / max(1, FLOOR_Y - top))
                return base_x + sway * f

            previous = (sx(top), top)
            y = top
            while y < FLOOR_Y:
                nxt = min(FLOOR_Y, y + 17)
                point = (sx(nxt), nxt)
                pygame.draw.line(surface, color, previous, point, width)
                if width >= 4:
                    pygame.draw.line(
                        surface,
                        highlight,
                        (previous[0] - 1, previous[1]),
                        (point[0] - 1, point[1]),
                        1,
                    )
                pygame.draw.line(
                    surface,
                    dark,
                    (point[0] - width // 2 - 1, nxt),
                    (point[0] + width // 2 + 1, nxt),
                    1,
                )
                previous = point
                y = nxt
            self._draw_leaf_cluster(surface, sx(top + 8) + 1, top + 8, BAMBOO_LEAF, 1)
            self._draw_leaf_cluster(surface, sx(top + 55) - 2, top + 55, BAMBOO_LEAF, -1)
            if width >= 5:
                self._draw_leaf_cluster(
                    surface, sx(top + 110) + 2, top + 110, BAMBOO_LEAF_LIGHT, 1
                )

    def _draw_leaf_cluster(self, surface, x, y, color, direction) -> None:
        for i, (dx, dy, length) in enumerate(
            ((4, -6, 9), (1, -9, 11), (-3, -7, 8), (7, -2, 7), (-6, -3, 6))
        ):
            wobble = math.sin(self.time * 0.9 + i) * 0.7
            end = (
                x + (dx + direction * 4) * (length / 8) + wobble,
                y + dy * (length / 8),
            )
            pygame.draw.line(surface, color, (x, y), end, 1)
            if i % 2 == 0:
                pygame.draw.line(
                    surface,
                    BAMBOO_LEAF_LIGHT,
                    ((x + end[0]) / 2, (y + end[1]) / 2),
                    end,
                    1,
                )

    def _draw_mist(self, surface, alpha_scale: float = 1.0, offset: int = 0) -> None:
        for i, (y, alpha) in enumerate(((92, 22), (132, 16), (184, 12))):
            band = pygame.Surface((self.width, 26), pygame.SRCALPHA)
            band.fill((132, 158, 146, int(alpha * alpha_scale)))
            drift = math.sin(self.time * 0.25 + y + offset) * 3
            surface.blit(band, (0, y + drift))

    def _draw_ground(self, surface: pygame.Surface) -> None:
        if self.ground == "none":
            return
        base = STONE_DARK if self.ground == "path" else (49, 39, 29)
        pygame.draw.rect(surface, base, (0, FLOOR_Y, self.width, HEIGHT - FLOOR_Y))
        for x, y, w, h in self.ground_marks:
            color = STONE if self.ground == "path" else (61, 48, 34)
            pygame.draw.rect(surface, color, (x, y, w, h))
            pygame.draw.line(
                surface,
                (35, 34, 28) if self.ground == "path" else (36, 28, 20),
                (x, y + h - 1),
                (x + w, y + h - 1),
                1,
            )
        for x in range(0, self.width, 22):
            pygame.draw.line(
                surface,
                (38, 41, 35) if self.ground == "path" else (39, 31, 23),
                (x, FLOOR_Y),
                (x + 6, FLOOR_Y + 5),
                1,
            )
        for x in range(0, self.width, 90):
            pygame.draw.rect(surface, MOSS, (x + 6, FLOOR_Y + 2, 22, 3))
        pygame.draw.line(surface, (100, 102, 88), (0, FLOOR_Y), (self.width, FLOOR_Y), 1)
        if self.ground == "yard":
            for x in range(20, self.width, 70):
                pygame.draw.line(surface, (70, 88, 56), (x, FLOOR_Y - 2), (x + 2, FLOOR_Y - 8), 1)
                pygame.draw.line(surface, (70, 88, 56), (x + 2, FLOOR_Y - 5), (x + 5, FLOOR_Y - 9), 1)

    def _draw_path_lantern(self, surface: pygame.Surface, x: int) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, (x - 2, 166, 4, FLOOR_Y - 166))
        pygame.draw.rect(surface, WOOD, (x - 1, 168, 2, FLOOR_Y - 168))
        pygame.draw.line(surface, WOOD_DARK, (x - 1, 172), (x - 12, 172), 2)
        self.draw_lantern(surface, x - 13, 174, small=True)

    def _draw_shrine(self, surface: pygame.Surface, x: int) -> None:
        pygame.draw.rect(surface, STONE_DARK, (x, 180, 82, 66))
        pygame.draw.rect(surface, STONE, (x + 4, 184, 74, 62))
        pygame.draw.rect(surface, (58, 60, 52), (x + 12, 214, 58, 32))
        pygame.draw.rect(surface, (12, 12, 11), (x + 30, 208, 22, 38))
        pygame.draw.polygon(
            surface,
            ROOF_EDGE,
            [(x - 12, 184), (x + 10, 164), (x + 72, 164), (x + 94, 184), (x + 86, 190), (x - 4, 190)],
        )
        pygame.draw.polygon(
            surface,
            ROOF,
            [(x - 6, 183), (x + 14, 168), (x + 68, 168), (x + 88, 183), (x + 82, 187), (x, 187)],
        )
        pygame.draw.line(surface, ROOF_LIGHT, (x + 14, 168), (x + 68, 168), 1)
        glow = self.ember_glow
        surface.blit(
            glow,
            (x + 41 - glow.get_width() // 2, 222 - glow.get_height() // 2),
            special_flags=pygame.BLEND_RGB_ADD,
        )
        pygame.draw.rect(surface, (222, 128, 66), (x + 39, 220, 4, 8))
        pygame.draw.rect(surface, (255, 208, 128), (x + 40, 221, 2, 4))
        self.draw_lantern(surface, x + 10, 192, small=True)
        plaque = self.font_small.render("烬", True, (226, 196, 134))
        surface.blit(plaque, (x + 41 - plaque.get_width() // 2, 198))

    def _draw_well(self, surface: pygame.Surface, x: int) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, (x - 6, 168, 4, 78))
        pygame.draw.rect(surface, WOOD_EDGE, (x + 62, 168, 4, 78))
        pygame.draw.rect(surface, WOOD_DARK, (x - 8, 166, 76, 5))
        pygame.draw.line(surface, WOOD_LIGHT, (x - 6, 167), (x + 66, 167), 1)
        pygame.draw.ellipse(surface, STONE_DARK, (x - 4, 224, 72, 24))
        pygame.draw.ellipse(surface, STONE, (x, 228, 64, 16))
        pygame.draw.ellipse(surface, (10, 12, 11), (x + 8, 232, 48, 9))
        for dx in (6, 24, 44):
            pygame.draw.arc(surface, (88, 91, 80), (x + dx, 227, 16, 14), 0.2, 3.0, 1)
        pygame.draw.rect(surface, WOOD_DARK, (x + 28, 176, 8, 52))
        pygame.draw.line(surface, (161, 148, 116), (x + 32, 178), (x + 32, 224), 1)
        pygame.draw.rect(surface, WOOD, (x + 26, 224, 12, 6))
        self.draw_lantern(surface, x + 68, 176, small=True)

    def _draw_balcony(self, surface: pygame.Surface, x: int) -> None:
        pygame.draw.rect(surface, (40, 29, 23), (0, 76, 238, 74))
        for px in range(4, 236, 10):
            pygame.draw.line(surface, WOOD_DARK, (px, 76), (px, 150), 1)
        pygame.draw.rect(surface, WOOD_EDGE, (0, 74, 240, 6))
        pygame.draw.rect(surface, WOOD, (0, 76, 238, 3))
        pygame.draw.rect(surface, WOOD_EDGE, (26, 92, 68, 52))
        pygame.draw.rect(surface, (24, 20, 17), (30, 96, 60, 44))
        pygame.draw.rect(surface, PAPER, (34, 100, 24, 28))
        for px in range(38, 58, 8):
            pygame.draw.line(surface, (78, 54, 34), (px, 100), (px, 128), 1)
        pygame.draw.rect(surface, WOOD_EDGE, (20, 150, 200, 8))
        pygame.draw.rect(surface, WOOD, (22, 152, 196, 5))
        for px in range(24, 218, 18):
            pygame.draw.rect(surface, WOOD_EDGE, (px, 128, 3, 23))
        pygame.draw.rect(surface, WOOD_DARK, (20, 126, 200, 3))
        pygame.draw.rect(surface, WOOD_EDGE, (206, 158, 8, 88))
        pygame.draw.rect(surface, WOOD_DARK, (208, 158, 4, 88))
        pygame.draw.rect(surface, WOOD_EDGE, (0, 158, 8, 88))
        pygame.draw.rect(surface, WOOD_DARK, (2, 158, 4, 88))

    def _draw_signpost(self, surface: pygame.Surface, x: int) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, (x - 3, 158, 8, 88))
        pygame.draw.rect(surface, WOOD, (x - 1, 160, 4, 84))
        signs = (("药王谷", 168, -1), ("寒山寺", 192, 1))
        for text, y, direction in signs:
            board = pygame.Rect(x + (8 if direction > 0 else -58), y, 52, 16)
            pygame.draw.rect(surface, WOOD_EDGE, board.inflate(2, 2))
            pygame.draw.rect(surface, (96, 64, 40), board)
            pygame.draw.polygon(
                surface,
                (96, 64, 40),
                [
                    (board.right if direction > 0 else board.left, board.y),
                    (board.right + direction * 8, board.centery),
                    (board.right if direction > 0 else board.left, board.bottom),
                ],
            )
            label = self.font_small.render(text, True, (226, 202, 150))
            surface.blit(label, (board.centerx - label.get_width() // 2, board.y + 2))


class InnArt(ForestArt):
    """Interior of the bamboo inn, stretched across a long hall."""

    def __init__(
        self,
        width: int,
        seed: int,
        platforms=(),
        upper: bool = False,
        stairs: bool = False,
    ) -> None:
        super().__init__(
            width,
            seed,
            platforms,
            density=0.7,
            moon_x=70,
            props=(),
            ground="none",
        )
        self.upper = upper
        self.stairs = stairs
        self.left = 24
        self.right = width - 24
        rng = random.Random(seed + 91)
        self.bays = list(range(112, width - 96, 232))
        if not self.bays:
            self.bays = [max(96, width // 2)]
        self.windows = []
        for i, bx in enumerate(self.bays):
            wx = bx + 40
            if wx + 54 < self.right - 16:
                self.windows.append(
                    (pygame.Rect(wx, 104 if upper else 108, 52, 56), i % 3 != 2)
                )
        self.banners = []
        for i, bx in enumerate(self.bays):
            text = "酒" if i % 2 == 0 else "茶"
            self.banners.append((bx + 104, 128, text))
        self.lanterns = []
        for i, bx in enumerate(self.bays):
            self.lanterns.append((bx + 8, 94, False))
            if i % 2:
                self.lanterns.append((bx + 150, 176, True))
        self.jar_clusters = []
        for i, bx in enumerate(self.bays):
            self.jar_clusters.append((bx + 116 + rng.randint(-8, 8), 226, rng.randint(2, 3)))

    # -- drawing --------------------------------------------------------
    def draw_back(self, surface: pygame.Surface) -> None:
        self.draw_scenery(surface)
        self._draw_floor(surface)
        self._draw_walls(surface)
        self._draw_roof(surface)
        self._draw_beams(surface)
        self._draw_doors(surface)
        if self.upper:
            self._draw_rafters(surface)
        if self.stairs:
            self._draw_ladder(surface)
        self.draw_platforms(surface, style="wood")
        self._draw_props(surface)
        if not self.upper:
            self._draw_sign(surface)
        self._draw_lights(surface)
        self._draw_inn_ambient(surface)

    def _draw_floor(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, STONE_DARK, (0, FLOOR_Y, self.left, HEIGHT - FLOOR_Y))
        for i in range(max(4, self.left // 8)):
            x = 2 + (i * 9) % max(1, self.left - 8)
            pygame.draw.rect(surface, STONE, (x, FLOOR_Y + 4 + (i * 5) % 16, 8, 4))
        pygame.draw.rect(
            surface,
            WOOD,
            (self.left, FLOOR_Y, self.width - self.left * 2, HEIGHT - FLOOR_Y),
        )
        pygame.draw.rect(
            surface,
            STONE_DARK,
            (self.width - self.left, FLOOR_Y, self.left, HEIGHT - FLOOR_Y),
        )
        for y in (FLOOR_Y + 5, FLOOR_Y + 11, FLOOR_Y + 17):
            pygame.draw.line(
                surface, WOOD_DARK, (self.left, y), (self.width - self.left, y), 1
            )
        for x in range(self.left + 12, self.width - self.left, 36):
            pygame.draw.line(surface, WOOD_EDGE, (x, FLOOR_Y), (x, HEIGHT), 1)
        runner_left = 60
        runner_right = self.width - 60
        pygame.draw.rect(surface, CLOTH_DARK, (runner_left, FLOOR_Y - 1, runner_right - runner_left, 7))
        pygame.draw.line(
            surface, CLOTH, (runner_left + 4, FLOOR_Y), (runner_right - 4, FLOOR_Y), 1
        )
        for x in (self.left - 3, self.width - self.left - 3):
            pygame.draw.rect(surface, WOOD_EDGE, (x, FLOOR_Y, 6, 24))
            pygame.draw.rect(surface, WOOD_LIGHT, (x + 2, FLOOR_Y, 2, 24))
        pygame.draw.rect(surface, MOSS, (0, FLOOR_Y + 2, 18, 3))

    def _draw_walls(self, surface: pygame.Surface) -> None:
        wall_top = 88 if not self.upper else 84
        pygame.draw.rect(
            surface,
            (44, 31, 24),
            (self.left, wall_top, self.width - self.left * 2, FLOOR_Y - wall_top),
        )
        for x in range(self.left + 4, self.width - self.left, 9):
            pygame.draw.line(surface, WOOD_DARK, (x, wall_top), (x, FLOOR_Y), 1)
        for bx in self.bays:
            pygame.draw.rect(
                surface,
                (40, 28, 22),
                (bx + 16, wall_top, 206, FLOOR_Y - wall_top),
            )
        pygame.draw.rect(
            surface, WOOD_DARK, (self.left, wall_top, self.width - self.left * 2, 3)
        )
        for rect, lit in self.windows:
            self._window(surface, rect, lit)
            if lit:
                surface.blit(
                    self.window_glow,
                    (
                        rect.centerx - self.window_glow.get_width() // 2,
                        rect.centery - self.window_glow.get_height() // 2,
                    ),
                    special_flags=pygame.BLEND_RGB_ADD,
                )
        for bx in self.bays:
            shelf_x = min(bx + 116, self.width - 150)
            pygame.draw.rect(surface, WOOD, (shelf_x, 182, 112, 6))
            pygame.draw.rect(surface, WOOD_LIGHT, (shelf_x, 182, 112, 1))
            for j in range(6):
                jar_x = shelf_x + 6 + j * 17
                jar_w = 7 + (j % 3)
                pygame.draw.rect(surface, (66, 48, 36), (jar_x, 170, jar_w, 12))
                pygame.draw.rect(surface, (168, 62, 44), (jar_x, 170, jar_w, 2))
                pygame.draw.rect(surface, (44, 32, 26), (jar_x + 1, 175, jar_w - 2, 5))
            pygame.draw.rect(surface, (36, 26, 21), (shelf_x + 6, 188, 100, 4))
        for x, y, text in self.banners:
            if x + 10 > self.width - self.left:
                continue
            pygame.draw.line(surface, WOOD_DARK, (x, y - 4), (x, y + 48), 2)
            self._vertical_banner(surface, x + 2, y, text)

    def _window(self, surface: pygame.Surface, rect: pygame.Rect, lit: bool) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, rect.inflate(6, 6))
        inner = PAPER if lit else (128, 104, 76)
        pygame.draw.rect(surface, inner, rect)
        pygame.draw.rect(surface, PAPER_LIGHT, rect.inflate(-4, -4))
        for x in range(rect.x + 8, rect.right, 16):
            pygame.draw.line(surface, (78, 54, 34), (x, rect.y), (x, rect.bottom), 1)
        for y in range(rect.y + 10, rect.bottom, 16):
            pygame.draw.line(surface, (78, 54, 34), (rect.x, y), (rect.right, y), 1)
        pygame.draw.line(surface, (60, 42, 28), rect.topleft, rect.bottomright)
        if not lit:
            pygame.draw.polygon(
                surface,
                (48, 38, 30),
                [
                    (rect.right - 18, rect.y + 2),
                    (rect.right - 2, rect.y + 2),
                    (rect.right - 2, rect.y + 16),
                ],
            )

    def _draw_roof(self, surface: pygame.Surface) -> None:
        left = 14
        right = self.width - 14
        pygame.draw.rect(surface, (20, 22, 22), (left, 68, right - left, 18))
        pygame.draw.polygon(
            surface,
            ROOF_EDGE,
            [
                (left - 2, 72),
                (left + 18, 54),
                (left + 48, 32),
                (right - 48, 32),
                (right - 18, 54),
                (right + 2, 72),
                (right - 6, 82),
                (left + 6, 82),
            ],
        )
        pygame.draw.polygon(
            surface,
            ROOF,
            [
                (left + 4, 70),
                (left + 22, 56),
                (left + 52, 35),
                (right - 52, 35),
                (right - 22, 56),
                (right - 4, 70),
                (right - 10, 76),
                (left + 10, 76),
            ],
        )
        pygame.draw.line(surface, ROOF_LIGHT, (left + 52, 35), (right - 52, 35), 2)
        pygame.draw.line(surface, ROOF_DARK, (left + 52, 37), (right - 52, 37), 1)
        for x in range(left + 60, right - 52, 14):
            pygame.draw.line(surface, ROOF_DARK, (x, 38), (x + 2, 74), 1)
            pygame.draw.line(surface, ROOF_LIGHT, (x + 1, 39), (x + 3, 72), 1)
        pygame.draw.line(surface, ROOF_LIGHT, (left + 10, 76), (right - 10, 76), 1)
        pygame.draw.polygon(
            surface, ROOF_DARK, [(left + 44, 34), (left + 52, 21), (left + 60, 34)]
        )
        pygame.draw.polygon(
            surface, ROOF_DARK, [(right - 60, 34), (right - 52, 21), (right - 44, 34)]
        )
        for x in (left + 2, right - 2):
            direction = 6 if x < self.width / 2 else -6
            pygame.draw.line(surface, ROOF_LIGHT, (x, 72), (x + direction, 63), 1)

    def _draw_beams(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, (self.left, 76, self.width - self.left * 2, 12))
        pygame.draw.rect(surface, WOOD, (self.left + 2, 78, self.width - self.left * 2 - 4, 7))
        pygame.draw.line(
            surface,
            WOOD_LIGHT,
            (self.left + 4, 79),
            (self.width - self.left - 4, 79),
            1,
        )
        pillars = [self.left] + self.bays + [self.width - self.left - 10]
        for x in pillars:
            pygame.draw.rect(surface, WOOD_EDGE, (x, 76, 10, 170))
            pygame.draw.rect(surface, WOOD, (x + 2, 76, 6, 170))
            pygame.draw.line(surface, WOOD_LIGHT, (x + 2, 80), (x + 2, 242), 1)
            pygame.draw.rect(surface, STONE_DARK, (x - 2, 238, 14, 8))
            pygame.draw.rect(surface, STONE, (x, 240, 10, 6))
        for x in (self.left + 16, self.width // 2 - 120, self.width - self.left - 120):
            pygame.draw.line(surface, WOOD_DARK, (x, 92), (x + 12, 106), 2)
            pygame.draw.line(surface, WOOD_DARK, (x + 12, 106), (x, 118), 2)

    def _draw_doors(self, surface: pygame.Surface) -> None:
        for x in (self.left + 4, self.width - self.left - 60):
            pygame.draw.rect(surface, (12, 13, 12), (x + 6, 96, 48, 150))
            pygame.draw.rect(surface, WOOD_EDGE, (x, 92, 10, 154))
            pygame.draw.rect(surface, WOOD, (x + 2, 94, 6, 150))
            pygame.draw.rect(surface, WOOD_EDGE, (x + 56, 92, 10, 154))
            pygame.draw.rect(surface, WOOD, (x + 58, 94, 6, 150))
            pygame.draw.rect(surface, WOOD_EDGE, (x, 88, 66, 12))
            pygame.draw.rect(surface, WOOD, (x + 2, 90, 62, 8))
            pygame.draw.line(surface, WOOD_LIGHT, (x + 4, 91), (x + 62, 91), 1)
            pygame.draw.rect(surface, (38, 56, 50), (x + 10, 102, 40, 18))
            for bx in range(x + 12, x + 50, 6):
                pygame.draw.line(surface, (28, 42, 38), (bx, 102), (bx, 120), 1)
            pygame.draw.line(surface, CLOTH_DARK, (x + 10, 120), (x + 50, 120), 2)
            pygame.draw.rect(surface, STONE, (x + 2, 240, 60, 5))
            pygame.draw.line(surface, STONE_DARK, (x + 2, 240), (x + 62, 240), 1)

    def _draw_rafters(self, surface: pygame.Surface) -> None:
        for x in range(self.left + 20, self.width - self.left - 20, 92):
            pygame.draw.line(surface, WOOD_DARK, (x, 88), (x + 26, 118), 2)
            pygame.draw.line(surface, WOOD_DARK, (x + 52, 88), (x + 26, 118), 2)
            pygame.draw.rect(surface, WOOD_EDGE, (x + 24, 116, 4, 18))
        pygame.draw.rect(surface, WOOD_EDGE, (self.left, 118, self.width - self.left * 2, 4))
        pygame.draw.rect(surface, WOOD, (self.left, 119, self.width - self.left * 2, 2))

    def _draw_ladder(self, surface: pygame.Surface) -> None:
        x = self.width - 108
        pygame.draw.line(surface, WOOD_DARK, (x, 112), (x, FLOOR_Y), 2)
        pygame.draw.line(surface, WOOD_DARK, (x + 10, 112), (x + 10, FLOOR_Y), 2)
        for y in range(124, FLOOR_Y, 14):
            pygame.draw.line(surface, WOOD, (x, y), (x + 10, y), 1)
        pygame.draw.rect(surface, WOOD_EDGE, (x - 3, 112, 16, 4))

    def _draw_props(self, surface: pygame.Surface) -> None:
        for x, y, count in self.jar_clusters:
            if x + count * 10 > self.width - self.left:
                continue
            for i in range(count):
                jx = x + i * 10
                jy = y - 18 + (i % 2) * 2
                pygame.draw.rect(surface, (62, 46, 38), (jx, jy, 8, 18))
                pygame.draw.rect(surface, (86, 60, 44), (jx + 1, jy - 2, 6, 5))
                pygame.draw.rect(surface, CLOTH, (jx + 1, jy - 3, 6, 2))
        rack_x = min(420, self.width - 160)
        self._draw_weapon_rack(surface, rack_x, 182)
        for bx in self.bays:
            stool_x = min(bx + 150, self.width - 120)
            pygame.draw.rect(surface, WOOD_EDGE, (stool_x, 230, 18, 5))
            pygame.draw.rect(surface, WOOD, (stool_x + 2, 230, 14, 3))
            pygame.draw.rect(surface, WOOD_DARK, (stool_x + 4, 235, 3, 11))
            pygame.draw.rect(surface, WOOD_DARK, (stool_x + 12, 235, 3, 11))
        for bx in self.bays:
            for dx, dy, w, h in ((60, 196, 8, 4), (78, 195, 10, 3)):
                px = min(bx + dx, self.width - 30)
                pygame.draw.ellipse(surface, (204, 188, 154), (px, dy, w, h))
                pygame.draw.line(surface, (130, 112, 86), (px + 1, dy + 1), (px + 3, dy + 1), 1)

    def _vertical_banner(self, surface: pygame.Surface, x, y, text: str) -> None:
        pygame.draw.rect(surface, (176, 152, 112), (x, y, 8, 38))
        pygame.draw.line(surface, (110, 84, 56), (x, y), (x, y + 38), 1)
        pygame.draw.line(surface, (110, 84, 56), (x + 7, y), (x + 7, y + 38), 1)
        label = self.font_small.render(text, True, (54, 44, 38))
        surface.blit(label, (x + (8 - label.get_width()) // 2, y + 10))

    def _draw_weapon_rack(self, surface, x, y) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, (x, y, 34, 4))
        pygame.draw.rect(surface, WOOD, (x, y + 1, 34, 2))
        pygame.draw.line(surface, WOOD_DARK, (x + 4, y), (x + 2, y + 24), 2)
        pygame.draw.line(surface, WOOD_DARK, (x + 30, y), (x + 32, y + 24), 2)
        for dx, lean in ((9, 3), (17, -2), (25, 2)):
            pygame.draw.line(
                surface, (196, 202, 208), (x + dx, y + 2), (x + dx + lean, y + 24), 1
            )
            pygame.draw.line(
                surface, (80, 58, 38), (x + dx + lean, y + 2), (x + dx + lean, y + 8), 1
            )

    def _draw_sign(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(88, 70, 84, 20)
        pygame.draw.rect(surface, WOOD_EDGE, rect.inflate(4, 4))
        pygame.draw.rect(surface, (94, 62, 38), rect)
        pygame.draw.rect(surface, HUD_GOLD, rect, 1)
        text = self.font_sign.render("竹坞客栈", True, (234, 204, 142))
        surface.blit(
            text,
            (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2,
            ),
        )
        pygame.draw.rect(surface, CLOTH, (rect.right - 10, rect.y + 5, 4, 7))

    def _draw_lights(self, surface) -> None:
        for x, y, small in self.lanterns:
            self.draw_lantern(surface, x, y, small=small)
        glow = self.ember_glow
        for x in range(120, self.width - 80, 360):
            surface.blit(
                glow,
                (x - glow.get_width() // 2, 246 - glow.get_height() // 2),
                special_flags=pygame.BLEND_RGB_ADD,
            )
        for x in range(160, self.width - 60, 300):
            pygame.draw.ellipse(surface, (86, 54, 34), (x, 247, 96, 5))
        for x in range(360, self.width - 80, 380):
            pygame.draw.ellipse(surface, (70, 46, 34), (x, 247, 108, 4))

    def _draw_inn_ambient(self, surface: pygame.Surface) -> None:
        for mote in self.motes:
            x = mote["x"] + math.sin(self.time * 0.6 + mote["phase"]) * 3
            y = (mote["y"] - self.time * mote["speed"]) % 150 + 90
            pygame.draw.rect(surface, EMBER, (round(x), round(y), 1, 1))
        for fly in self.fireflies[: max(4, len(self.fireflies) // 2)]:
            x = fly["x"] + math.sin(self.time * fly["speed"] + fly["phase"]) * fly["amp"]
            y = fly["y"] + math.cos(self.time * fly["speed"] * 0.7 + fly["phase"]) * 5
            pygame.draw.circle(surface, FIREFLY, (round(x), round(y)), 1)

    def draw_front(self, surface: pygame.Surface) -> None:
        surface.blit(self.vignette, (0, 0))


class CellarArt(BaseArt):
    """Underground wine cellar: timber supports, racks, and lantern light."""

    def __init__(self, width: int, seed: int, platforms=()) -> None:
        super().__init__(width, seed, platforms)
        rng = random.Random(seed + 3)
        self.supports = list(range(100, width - 40, 220))
        self.racks = list(range(150, width - 150, 240))
        self.lantern_spots = [
            (x, 148) for x in range(160, width - 60, 220)
        ]
        self.roots = [
            {
                "x": rng.uniform(20, width - 20),
                "length": rng.randint(18, 60),
                "phase": rng.uniform(0, math.tau),
            }
            for _ in range(max(6, width // 90))
        ]
        self.barrels = [
            (rng.randint(40, width - 70), rng.randint(216, 228))
            for _ in range(max(8, width // 90))
        ]
        self.puddle_glints = [
            (rng.randint(30, width - 50), FLOOR_Y + rng.randint(6, 16))
            for _ in range(max(6, width // 100))
        ]
        self.brick_rng = random.Random(seed + 33)
        self.glow_warm = self.lantern_glow

    def draw_back(self, surface: pygame.Surface) -> None:
        self._draw_wall(surface)
        self._draw_racks(surface)
        for x, y in self.barrels:
            self._draw_barrel(surface, x, y)
        self._draw_floor(surface)
        for x in self.supports:
            self._draw_support(surface, x)
        self._draw_roots(surface)
        self.draw_platforms(surface, style="wood")
        for x, y in self.lantern_spots:
            pygame.draw.line(surface, (40, 32, 27), (x, 54), (x, y - 5), 1)
            self.draw_lantern(surface, x, y, small=True)
        self._draw_dust(surface)

    def _draw_wall(self, surface: pygame.Surface) -> None:
        surface.fill(CELLAR_SKY)
        pygame.draw.rect(surface, CELLAR_WALL, (0, 52, self.width, HEIGHT - 52))
        pygame.draw.rect(surface, CELLAR_DARK, (0, 52, self.width, 10))
        for row, y in enumerate(range(66, FLOOR_Y, 16)):
            offset = 0 if row % 2 == 0 else 13
            pygame.draw.line(surface, CELLAR_DARK, (0, y), (self.width, y), 1)
            for x in range(offset, self.width, 27):
                pygame.draw.line(surface, CELLAR_DARK, (x, y), (x, y + 15), 1)
                if self.brick_rng.random() < 0.22:
                    pygame.draw.rect(
                        surface,
                        (56, 41, 31),
                        (x + 22, y + 2, 3, 5),
                    )
        for row, y in enumerate(range(0, 54, 13)):
            pygame.draw.arc(
                surface,
                (44, 32, 26),
                (row * 160 - 90, 4, 260, 110),
                0.0,
                math.pi,
                2,
            )
        pygame.draw.rect(surface, (10, 9, 8), (0, 0, self.width, 10))

    def _draw_racks(self, surface: pygame.Surface) -> None:
        for rx in self.racks:
            width = 130
            if rx + width > self.width - 26:
                continue
            for ry in (132, 160, 188):
                pygame.draw.rect(surface, WOOD_EDGE, (rx, ry, width, 5))
                pygame.draw.rect(surface, WOOD, (rx + 1, ry + 1, width - 2, 2))
                pygame.draw.line(
                    surface, WOOD_LIGHT, (rx + 2, ry + 1), (rx + width - 3, ry + 1), 1
                )
                for jx in range(rx + 8, rx + width - 10, 17):
                    pygame.draw.rect(surface, (54, 41, 32), (jx, ry - 14, 10, 14))
                    pygame.draw.ellipse(surface, (66, 50, 37), (jx - 1, ry - 16, 12, 5))
                    pygame.draw.rect(surface, (32, 24, 20), (jx + 2, ry - 9, 6, 5))
            pygame.draw.rect(surface, WOOD_EDGE, (rx - 3, 128, 6, 118))
            pygame.draw.rect(surface, WOOD_DARK, (rx + width - 3, 128, 6, 118))
            pygame.draw.rect(surface, WOOD_DARK, (rx + 4, 126, width - 8, 5))

    def _draw_barrel(self, surface, x: int, y: int) -> None:
        pygame.draw.ellipse(surface, (36, 27, 22), (x - 2, y + 12, 32, 12))
        pygame.draw.rect(surface, (72, 51, 36), (x + 2, y, 24, 24))
        pygame.draw.ellipse(surface, (84, 60, 42), (x + 2, y - 3, 24, 10))
        pygame.draw.ellipse(surface, (48, 34, 26), (x + 6, y + 1, 16, 5))
        for yy in (y + 4, y + 17):
            pygame.draw.line(surface, (42, 34, 29), (x + 1, yy), (x + 27, yy), 2)
            pygame.draw.line(surface, (104, 92, 72), (x + 1, yy + 1), (x + 27, yy + 1), 1)
        pygame.draw.line(surface, (56, 40, 30), (x + 8, y + 6), (x + 8, y + 21), 1)

    def _draw_floor(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (33, 27, 22), (0, FLOOR_Y, self.width, HEIGHT - FLOOR_Y))
        for x in range(0, self.width, 20):
            pygame.draw.line(
                surface, (44, 36, 28), (x, FLOOR_Y + 4), (x + 8, FLOOR_Y + 10), 1
            )
        for x, y in self.puddle_glints:
            pygame.draw.ellipse(surface, (54, 52, 38), (x, y, 16, 4))
            pygame.draw.line(surface, (98, 92, 64), (x + 3, y + 1), (x + 8, y + 1), 1)
        pygame.draw.line(surface, (70, 60, 44), (0, FLOOR_Y), (self.width, FLOOR_Y), 1)

    def _draw_support(self, surface, x: int) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, (x, 52, 14, FLOOR_Y - 52))
        pygame.draw.rect(surface, WOOD_DARK, (x + 2, 52, 10, FLOOR_Y - 52))
        pygame.draw.rect(surface, WOOD, (x + 3, 54, 4, FLOOR_Y - 54))
        pygame.draw.line(surface, WOOD_LIGHT, (x + 3, 58), (x + 3, 240), 1)
        pygame.draw.rect(surface, WOOD_EDGE, (x - 8, 52, 30, 8))
        pygame.draw.rect(surface, WOOD, (x - 6, 54, 26, 4))
        pygame.draw.rect(surface, STONE_DARK, (x - 5, 238, 24, 9))
        pygame.draw.rect(surface, STONE, (x - 3, 240, 20, 7))

    def _draw_roots(self, surface: pygame.Surface) -> None:
        for root in self.roots:
            x = root["x"]
            length = root["length"]
            sway = math.sin(self.time * 0.5 + root["phase"]) * 2
            pygame.draw.line(
                surface,
                (39, 32, 24),
                (x, 52),
                (x + sway, 52 + length),
                2,
            )
            if length > 32:
                pygame.draw.line(
                    surface,
                    (46, 38, 28),
                    (x + sway, 52 + length),
                    (x + sway + 5, 58 + length),
                    1,
                )

    def _draw_dust(self, surface: pygame.Surface) -> None:
        for mote in self.motes:
            x = mote["x"] + math.sin(self.time * 0.4 + mote["phase"]) * 4
            y = (mote["y"] + self.time * mote["speed"] * 0.5) % 220 + 30
            pygame.draw.rect(surface, (120, 108, 86), (round(x), round(y), 1, 1))
        for x, y in self.lantern_spots:
            if int(self.time * 1.5 + x) % 9 == 0:
                pygame.draw.rect(surface, (150, 96, 54), (x + 2, y + 6, 1, 2))

    def draw_front(self, surface: pygame.Surface) -> None:
        surface.blit(self.vignette, (0, 0))


class ValleyArt(BaseArt):
    """Poisoned valley gate teaser."""

    def __init__(self, width: int, seed: int, platforms=()) -> None:
        super().__init__(width, seed, platforms)
        rng = random.Random(seed + 5)
        self.left_cliff = self._cliff(rng, from_left=True)
        self.right_cliff = self._cliff(rng, from_left=False)
        self.vines = []
        for x in range(80, 240, 34):
            self.vines.append((x, rng.randint(60, 140), rng.randint(30, 80)))
        for x in range(width - 230, width - 70, 36):
            self.vines.append((x, rng.randint(50, 130), rng.randint(28, 72)))
        self.pools = [(228, 240, 74, 10), (356, 242, 52, 8), (520, 240, 46, 8)]
        self.glow_green = _shared_glow(46, (40, 92, 48), 1.0)
        self.fog = [
            {
                "y": rng.randint(120, 220),
                "speed": rng.uniform(2, 5),
                "phase": rng.uniform(0, math.tau),
            }
            for _ in range(6)
        ]

    def _cliff(self, rng, from_left: bool) -> list[tuple[int, int]]:
        edge = 0 if from_left else self.width
        inner = 96 if from_left else self.width - 96
        points = [(edge, 0), (inner, 0)]
        y = 0
        while y < FLOOR_Y:
            y += rng.randint(36, 60)
            depth = rng.randint(-18, 26)
            points.append((inner + depth if from_left else inner - depth, min(y, FLOOR_Y)))
        points.extend([(edge, FLOOR_Y), (edge, 0)])
        return points

    def draw_back(self, surface: pygame.Surface) -> None:
        for y in range(FLOOR_Y):
            t = y / FLOOR_Y
            pygame.draw.line(
                surface,
                _lerp(VALLEY_SKY_TOP, VALLEY_SKY_BOTTOM, t),
                (0, y),
                (self.width, y),
            )
        for x in range(40, self.width - 20, 48):
            pygame.draw.line(surface, (22, 38, 30), (x, 150), (x + 2, 70), 2)
        pygame.draw.circle(surface, (150, 176, 140), (400, 58), 22)
        pygame.draw.circle(surface, (120, 148, 112), (405, 62), 26, 1)
        pygame.draw.polygon(surface, VALLEY_CLIFF_DARK, self.left_cliff)
        pygame.draw.polygon(surface, VALLEY_CLIFF_DARK, self.right_cliff)
        self._draw_vines(surface)
        self._draw_gate(surface)
        self._draw_ground(surface)
        self.draw_platforms(surface, style="stone")
        for x, y, w, h in self.pools:
            pygame.draw.ellipse(surface, (44, 66, 40), (x - 6, y - 2, w + 12, h + 4))
            surface.blit(
                self.glow_green,
                (x + w // 2 - self.glow_green.get_width() // 2,
                 y + h // 2 - self.glow_green.get_height() // 2),
                special_flags=pygame.BLEND_RGB_ADD,
            )
            pygame.draw.ellipse(surface, (86, 128, 70), (x, y, w, h))
            for dx in range(8, w - 6, 14):
                pygame.draw.circle(surface, (132, 176, 92), (x + dx, y + 3), 1)
        for fog in self.fog:
            x = (self.time * fog["speed"] + fog["phase"] * 80) % (self.width + 120) - 60
            band = pygame.Surface((120, 10), pygame.SRCALPHA)
            band.fill((120, 160, 130, 18))
            surface.blit(band, (x, fog["y"]))
        for fly in self.fireflies:
            x = fly["x"] + math.sin(self.time * fly["speed"] + fly["phase"]) * fly["amp"]
            y = fly["y"] + math.cos(self.time * fly["speed"] * 0.7 + fly["phase"]) * 5
            pygame.draw.circle(surface, (150, 204, 112), (round(x), round(y)), 1)

    def _draw_vines(self, surface) -> None:
        for x, y, length in self.vines:
            sway = math.sin(self.time * 0.6 + x) * 2
            pygame.draw.line(
                surface, (34, 58, 38), (x, y), (x + sway, y + length), 1
            )
            for i in range(3):
                ly = y + 12 + i * (length // 4)
                pygame.draw.line(
                    surface, (50, 82, 48), (x + sway, ly), (x + sway + 4, ly + 3), 1
                )

    def _draw_gate(self, surface) -> None:
        x0, x1 = 258, 382
        pygame.draw.rect(surface, (48, 54, 46), (x0 + 8, 150, x1 - x0 - 16, 96))
        pygame.draw.rect(surface, (8, 12, 10), (x0 + 22, 164, x1 - x0 - 44, 82))
        for x in (x0, x1 - 18):
            pygame.draw.rect(surface, (58, 64, 52), (x, 120, 18, 126))
            pygame.draw.rect(surface, (74, 80, 64), (x + 2, 120, 5, 126))
        pygame.draw.rect(surface, (54, 60, 50), (x0 - 8, 108, x1 - x0 + 16, 18))
        pygame.draw.polygon(
            surface,
            (32, 37, 30),
            [(x0 - 24, 108), (x0 + 8, 84), (x1 - 8, 84), (x1 + 24, 108), (x1 + 14, 114), (x0 - 14, 114)],
        )
        pygame.draw.line(surface, (84, 92, 74), (x0 + 8, 86), (x1 - 8, 86), 1)
        plaque = pygame.Rect(296, 122, 48, 18)
        pygame.draw.rect(surface, (32, 38, 30), plaque)
        pygame.draw.rect(surface, (120, 136, 100), plaque, 1)
        text = self.font_sign.render("药王谷", True, (188, 206, 154))
        surface.blit(text, (plaque.centerx - text.get_width() // 2, plaque.y + 1))
        for x in (x0 + 10, x1 - 26):
            self.draw_lantern(surface, x, 142, small=True)

    def _draw_ground(self, surface) -> None:
        pygame.draw.rect(surface, (30, 39, 30), (0, FLOOR_Y, self.width, HEIGHT - FLOOR_Y))
        for x in range(0, self.width, 24):
            pygame.draw.line(
                surface, (44, 56, 42), (x, FLOOR_Y + 6), (x + 10, FLOOR_Y + 12), 1
            )
        for x in range(20, self.width, 80):
            pygame.draw.line(surface, (58, 78, 50), (x, FLOOR_Y), (x + 2, FLOOR_Y - 6), 1)
            pygame.draw.line(surface, (58, 78, 50), (x + 2, FLOOR_Y - 3), (x + 6, FLOOR_Y - 7), 1)
        pygame.draw.line(surface, (70, 88, 62), (0, FLOOR_Y), (self.width, FLOOR_Y), 1)

    def draw_front(self, surface: pygame.Surface) -> None:
        for i, leaf in enumerate(self.leaves[:16]):
            x = (
                leaf["x"]
                + math.sin(self.time * 0.5 + leaf["phase"]) * leaf["sway"]
            ) % (WIDTH + 24) - 12
            y = (leaf["y"] + self.time * leaf["speed"] * 0.5) % (HEIGHT + 20) - 10
            pygame.draw.line(surface, (74, 112, 76), (round(x), round(y)), (round(x) + 2, round(y) + 1), 1)
        surface.blit(self.vignette, (0, 0))


class TempleArt(BaseArt):
    """Cold mountain temple gate teaser with snow."""

    def __init__(self, width: int, seed: int, platforms=()) -> None:
        super().__init__(width, seed, platforms)
        rng = random.Random(seed + 7)
        self.snow = [
            {
                "x": rng.uniform(0, width),
                "y": rng.uniform(0, HEIGHT),
                "speed": rng.uniform(10, 26),
                "drift": rng.uniform(4, 12),
                "phase": rng.uniform(0, math.tau),
            }
            for _ in range(max(40, width // 8))
        ]
        self.vines = []
        self.glow_cold = _shared_glow(36, (48, 64, 92), 1.0)
        self.glow_bell = _shared_glow(52, (64, 54, 28), 0.8)

    def draw_back(self, surface: pygame.Surface) -> None:
        for y in range(FLOOR_Y):
            t = y / FLOOR_Y
            pygame.draw.line(
                surface,
                _lerp(TEMPLE_SKY_TOP, TEMPLE_SKY_BOTTOM, t),
                (0, y),
                (self.width, y),
            )
        pygame.draw.circle(surface, (196, 204, 214), (440, 52), 18)
        pygame.draw.circle(surface, (160, 172, 188), (444, 56), 23, 1)
        pygame.draw.polygon(
            surface,
            (25, 30, 40),
            [
                (0, 128),
                (82, 92),
                (156, 122),
                (238, 86),
                (330, 120),
                (420, 94),
                (510, 126),
                (610, 100),
                (680, 120),
                (680, 190),
                (0, 190),
            ],
        )
        pygame.draw.rect(surface, (50, 55, 66), (120, 150, 430, 96))
        for row, y in enumerate(range(154, 240, 14)):
            pygame.draw.line(surface, (40, 45, 54), (120, y), (550, y), 1)
            offset = 0 if row % 2 == 0 else 14
            for x in range(120 + offset, 550, 28):
                pygame.draw.line(surface, (40, 45, 54), (x, y), (x, y + 13), 1)
        self._draw_gate(surface)
        self._draw_bell(surface)
        self._draw_ground(surface)
        self.draw_platforms(surface, style="stone")
        for x in (150, 560):
            self._draw_stone_lantern(surface, x)
        for mote in self.motes:
            x = mote["x"] + math.sin(self.time * 0.3 + mote["phase"]) * 5
            y = (mote["y"] + self.time * mote["speed"] * 0.4) % 200 + 40
            pygame.draw.rect(surface, (120, 134, 160), (round(x), round(y), 1, 1))

    def _draw_gate(self, surface) -> None:
        x0, x1 = 262, 386
        pygame.draw.rect(surface, (14, 16, 20), (x0 + 22, 160, x1 - x0 - 44, 86))
        for x in (x0, x1 - 18):
            pygame.draw.rect(surface, TEMPLE_RED_DARK, (x, 118, 18, 128))
            pygame.draw.rect(surface, TEMPLE_RED, (x + 2, 120, 5, 126))
            pygame.draw.rect(surface, (52, 56, 66), (x - 4, 238, 26, 8))
        pygame.draw.rect(surface, TEMPLE_RED_DARK, (x0 - 10, 108, x1 - x0 + 20, 16))
        pygame.draw.rect(surface, TEMPLE_RED, (x0 - 8, 110, x1 - x0 + 16, 5))
        pygame.draw.polygon(
            surface,
            (20, 23, 29),
            [
                (x0 - 30, 108),
                (x0 + 6, 82),
                (x1 - 6, 82),
                (x1 + 30, 108),
                (x1 + 18, 116),
                (x0 - 18, 116),
            ],
        )
        pygame.draw.polygon(
            surface,
            (38, 43, 52),
            [(x0 - 20, 106), (x0 + 10, 86), (x1 - 10, 86), (x1 + 20, 106), (x1 + 12, 110), (x0 - 12, 110)],
        )
        pygame.draw.line(surface, (64, 70, 82), (x0 + 10, 86), (x1 - 10, 86), 1)
        for x in range(x0 - 6, x1, 12):
            pygame.draw.line(surface, (28, 32, 40), (x, 88), (x + 2, 108), 1)
        plaque = pygame.Rect(298, 120, 52, 19)
        pygame.draw.rect(surface, (30, 24, 22), plaque)
        pygame.draw.rect(surface, (120, 96, 58), plaque, 1)
        text = self.font_sign.render("寒山寺", True, (214, 198, 160))
        surface.blit(text, (plaque.centerx - text.get_width() // 2, plaque.y + 1))
        for x in (x0 + 12, x1 - 26):
            self.draw_lantern(surface, x, 140, small=True)

    def _draw_bell(self, surface) -> None:
        x = 470
        pygame.draw.rect(surface, WOOD_EDGE, (x - 4, 110, 8, 136))
        pygame.draw.rect(surface, WOOD, (x - 2, 112, 4, 134))
        pygame.draw.rect(surface, WOOD_EDGE, (x + 86, 110, 8, 136))
        pygame.draw.rect(surface, WOOD, (x + 88, 112, 4, 134))
        pygame.draw.rect(surface, WOOD_EDGE, (x - 12, 104, 116, 9))
        pygame.draw.rect(surface, WOOD_DARK, (x - 10, 106, 112, 4))
        surface.blit(
            self.glow_bell,
            (x + 45 - self.glow_bell.get_width() // 2, 170 - self.glow_bell.get_height() // 2),
            special_flags=pygame.BLEND_RGB_ADD,
        )
        pygame.draw.polygon(
            surface,
            (66, 58, 42),
            [(x + 18, 138), (x + 72, 138), (x + 80, 190), (x + 10, 190)],
        )
        pygame.draw.polygon(
            surface,
            (88, 76, 52),
            [(x + 22, 140), (x + 68, 140), (x + 74, 186), (x + 16, 186)],
        )
        pygame.draw.rect(surface, (48, 42, 32), (x + 8, 188, 74, 7))
        pygame.draw.line(surface, (112, 98, 66), (x + 12, 139), (x + 76, 139), 1)
        pygame.draw.circle(surface, (48, 42, 32), (x + 45, 128), 4)
        pygame.draw.rect(surface, (56, 48, 36), (x + 42, 112, 6, 18))
        pygame.draw.line(surface, (100, 86, 58), (x + 45, 196), (x + 45, 212), 2)
        pygame.draw.circle(surface, (120, 102, 62), (x + 45, 214), 4)

    def _draw_stone_lantern(self, surface, x: int) -> None:
        pygame.draw.rect(surface, TEMPLE_STONE_DARK, (x - 3, 208, 8, 38))
        pygame.draw.rect(surface, TEMPLE_STONE, (x - 2, 210, 4, 34))
        pygame.draw.rect(surface, TEMPLE_STONE_DARK, (x - 10, 198, 24, 8))
        pygame.draw.rect(surface, TEMPLE_STONE, (x - 8, 200, 20, 5))
        pygame.draw.rect(surface, (24, 28, 36), (x - 6, 186, 16, 13))
        surface.blit(
            self.glow_cold,
            (x + 2 - self.glow_cold.get_width() // 2, 190 - self.glow_cold.get_height() // 2),
            special_flags=pygame.BLEND_RGB_ADD,
        )
        pygame.draw.rect(surface, (146, 158, 190), (x - 2, 190, 3, 5))
        pygame.draw.polygon(
            surface,
            TEMPLE_STONE_DARK,
            [(x - 12, 186), (x + 2, 176), (x + 16, 186), (x + 10, 190), (x - 6, 190)],
        )

    def _draw_ground(self, surface) -> None:
        pygame.draw.rect(surface, (42, 45, 54), (0, FLOOR_Y, self.width, HEIGHT - FLOOR_Y))
        for x in range(0, self.width, 26):
            pygame.draw.rect(surface, (58, 62, 72), (x + 2, FLOOR_Y + 3, 20, 7))
            pygame.draw.line(surface, (34, 37, 44), (x + 2, FLOOR_Y + 9), (x + 22, FLOOR_Y + 9), 1)
        pygame.draw.line(surface, (104, 110, 124), (0, FLOOR_Y), (self.width, FLOOR_Y), 1)
        for x in (100, 604):
            pygame.draw.rect(surface, (34, 37, 44), (x, FLOOR_Y - 4, 34, 10))

    def draw_front(self, surface: pygame.Surface) -> None:
        for flake in self.snow:
            x = (flake["x"] + math.sin(self.time * 0.5 + flake["phase"]) * flake["drift"]) % (WIDTH + 12) - 6
            y = (flake["y"] + self.time * flake["speed"]) % (HEIGHT + 12) - 6
            pygame.draw.rect(surface, (196, 206, 220), (round(x), round(y), 1, 1))
        surface.blit(self.vignette, (0, 0))


@dataclass
class Hazard:
    kind: str
    rect: pygame.Rect
    damage: float


@dataclass
class Exit:
    rect: pygame.Rect
    target: str
    entry: str
    label_key: str
    kind: str = "door"
    hidden: bool = False


@dataclass
class Room:
    room_id: str
    title_key: str
    subtitle_key: str
    width: int
    art: object
    solids: list[pygame.Rect]
    one_ways: list[pygame.Rect]
    hazards: list[Hazard]
    exits: list[Exit]
    entries: dict[str, tuple[float, float]]
    spawns: list[dict]
    loot: list[tuple[str, float, float]]
    map_pos: tuple[int, int]


START_ROOM = "shrine"


def _exit(
    x: int,
    y: int,
    w: int,
    h: int,
    target: str,
    entry: str,
    kind: str = "door",
    hidden: bool = False,
) -> Exit:
    return Exit(
        pygame.Rect(x, y, w, h),
        target,
        entry,
        f"room.{target}.name",
        kind,
        hidden,
    )


def _spawn(enemy_id: str, x: float, y: float) -> dict:
    return {"enemy_id": enemy_id, "x": x, "y": y}


def _room(
    room_id: str,
    width: int,
    art_cls,
    seed: int,
    one_ways,
    exits,
    entries,
    spawns,
    hazards=(),
    loot=(),
    map_pos=(0, 0),
    art_kwargs=None,
) -> Room:
    ways = [pygame.Rect(*way) for way in one_ways]
    solids = [
        pygame.Rect(0, FLOOR_Y, width, HEIGHT - FLOOR_Y),
        pygame.Rect(0, 0, 8, HEIGHT),
        pygame.Rect(width - 8, 0, 8, HEIGHT),
        pygame.Rect(0, 0, width, 8),
    ]
    hazard_list = [
        Hazard(kind, pygame.Rect(*rect), damage) for kind, rect, damage in hazards
    ]
    art = art_cls(width, seed, ways, **(art_kwargs or {}))
    return Room(
        room_id=room_id,
        title_key=f"room.{room_id}.name",
        subtitle_key=f"room.{room_id}.subtitle",
        width=width,
        art=art,
        solids=solids,
        one_ways=ways,
        hazards=hazard_list,
        exits=list(exits),
        entries=dict(entries),
        spawns=list(spawns),
        loot=list(loot),
        map_pos=map_pos,
    )


def build_world() -> dict[str, Room]:
    """Create every room and the exit graph linking them."""

    rooms: dict[str, Room] = {}

    rooms["shrine"] = _room(
        "shrine",
        620,
        ForestArt,
        101,
        [(270, 206, 90, 8)],
        [_exit(588, 176, 32, 70, "bamboo_path", "start")],
        {"start": (60, 208), "from_path": (520, 208)},
        [],
        map_pos=(0, 0),
        art_kwargs={"ground": "path", "moon_x": 320, "props": [("shrine", 330)]},
    )

    rooms["bamboo_path"] = _room(
        "bamboo_path",
        1040,
        ForestArt,
        102,
        [
            (250, 204, 90, 8),
            (410, 176, 90, 8),
            (560, 150, 90, 8),
            (760, 204, 90, 8),
            (900, 176, 80, 8),
        ],
        [
            _exit(0, 176, 32, 70, "shrine", "from_path"),
            _exit(1008, 176, 32, 70, "inn_front", "west"),
        ],
        {"start": (60, 208), "from_inn": (950, 208)},
        [
            _spawn("wine_imp", 180, 212),
            _spawn("wine_imp", 600, 212),
            _spawn("paper_runner", 360, 212),
            _spawn("paper_runner", 820, 212),
            _spawn("paper_runner", 600, 116),
        ],
        hazards=[
            ("spikes", (500, 238, 28, 8), 15),
            ("poison", (680, 240, 40, 6), 4.0),
        ],
        map_pos=(1, 0),
        art_kwargs={"ground": "path", "moon_x": 300},
    )

    rooms["inn_front"] = _room(
        "inn_front",
        1440,
        InnArt,
        301,
        [
            (214, 204, 120, 8),
            (386, 158, 170, 8),
            (610, 112, 150, 8),
            (820, 158, 170, 8),
            (1030, 204, 120, 8),
            (1180, 204, 110, 8),
            (1280, 158, 100, 8),
            (1350, 112, 90, 8),
        ],
        [
            _exit(0, 176, 32, 70, "bamboo_path", "from_inn"),
            _exit(1408, 176, 32, 70, "backyard", "west"),
            _exit(1408, 64, 32, 50, "inn_upper", "west", kind="stairs"),
            _exit(664, 238, 40, 10, "cellar_upper", "hatch", kind="hatch", hidden=True),
        ],
        {
            "west": (44, 208),
            "east": (1370, 208),
            "from_upper": (1352, 74),
            "from_cellar": (744, 208),
        },
        [
            _spawn("wine_imp", 170, 212),
            _spawn("wine_imp", 520, 212),
            _spawn("wine_imp", 900, 212),
            _spawn("wine_imp", 1120, 212),
            _spawn("paper_runner", 320, 212),
            _spawn("paper_runner", 600, 212),
            _spawn("paper_runner", 780, 124),
            _spawn("paper_runner", 880, 124),
            _spawn("paper_runner", 1240, 170),
        ],
        hazards=[
            ("spikes", (560, 238, 32, 8), 15),
            ("poison", (900, 240, 40, 6), 4.0),
            ("poison", (1200, 240, 30, 6), 4.0),
        ],
        map_pos=(2, 0),
        art_kwargs={"stairs": True},
    )

    rooms["inn_upper"] = _room(
        "inn_upper",
        1000,
        InnArt,
        302,
        [
            (150, 204, 100, 8),
            (300, 158, 120, 8),
            (480, 112, 150, 8),
            (690, 158, 130, 8),
            (860, 204, 90, 8),
        ],
        [
            _exit(0, 176, 32, 70, "inn_front", "from_upper"),
            _exit(968, 176, 32, 70, "backyard", "from_upper"),
        ],
        {"west": (44, 208), "east": (900, 208)},
        [
            _spawn("wine_imp", 200, 212),
            _spawn("wine_imp", 760, 212),
            _spawn("paper_runner", 350, 212),
            _spawn("paper_runner", 560, 78),
            _spawn("paper_runner", 720, 124),
        ],
        hazards=[("spikes", (620, 238, 24, 8), 15)],
        map_pos=(2, -1),
        art_kwargs={"upper": True},
    )

    rooms["backyard"] = _room(
        "backyard",
        1000,
        ForestArt,
        303,
        [
            (20, 150, 190, 8),
            (300, 204, 110, 8),
            (520, 176, 110, 8),
            (720, 204, 100, 8),
        ],
        [
            _exit(0, 176, 32, 70, "inn_front", "east"),
            _exit(0, 100, 26, 50, "inn_upper", "east", kind="stairs"),
            _exit(968, 176, 32, 70, "ridge_fork", "west"),
            _exit(430, 238, 50, 10, "cellar_upper", "well", kind="hatch", hidden=True),
        ],
        {
            "west": (60, 208),
            "from_upper": (100, 112),
            "from_ridge": (900, 208),
        },
        [
            _spawn("wine_imp", 220, 212),
            _spawn("wine_imp", 700, 212),
            _spawn("paper_runner", 380, 212),
            _spawn("paper_runner", 560, 142),
        ],
        hazards=[
            ("spikes", (620, 238, 30, 8), 15),
            ("poison", (280, 240, 40, 6), 4.0),
        ],
        map_pos=(3, 0),
        art_kwargs={
            "ground": "yard",
            "moon_x": 300,
            "props": [("balcony", 0), ("well", 420)],
        },
    )

    rooms["cellar_upper"] = _room(
        "cellar_upper",
        1240,
        CellarArt,
        304,
        [
            (260, 204, 100, 8),
            (430, 158, 130, 8),
            (610, 204, 110, 8),
            (790, 158, 130, 8),
            (980, 204, 110, 8),
            (700, 112, 150, 8),
        ],
        [
            _exit(0, 176, 32, 70, "inn_front", "from_cellar"),
            _exit(1208, 176, 32, 70, "cellar_vault", "west"),
        ],
        {
            "hatch": (60, 208),
            "well": (200, 208),
            "from_vault": (1140, 208),
        },
        [
            _spawn("wine_imp", 300, 212),
            _spawn("wine_imp", 720, 212),
            _spawn("wine_imp", 1040, 212),
            _spawn("paper_runner", 460, 212),
            _spawn("paper_runner", 820, 212),
            _spawn("paper_runner", 760, 78),
        ],
        hazards=[
            ("poison", (330, 240, 46, 6), 4.0),
            ("spikes", (540, 238, 28, 8), 15),
            ("poison", (880, 240, 40, 6), 4.0),
        ],
        map_pos=(2, 1),
    )

    rooms["cellar_vault"] = _room(
        "cellar_vault",
        760,
        CellarArt,
        305,
        [(240, 204, 100, 8), (420, 204, 100, 8), (600, 158, 100, 8)],
        [_exit(0, 176, 32, 70, "cellar_upper", "from_vault")],
        {"west": (60, 208)},
        [
            _spawn("wine_imp", 420, 212),
            _spawn("paper_runner", 600, 212),
        ],
        loot=[
            ("fire_seed", 120, 220),
            ("fire_seed", 260, 220),
            ("potion", 400, 220),
            ("fire_seed", 540, 220),
            ("potion", 660, 220),
        ],
        map_pos=(3, 1),
    )

    rooms["ridge_fork"] = _room(
        "ridge_fork",
        1140,
        ForestArt,
        306,
        [
            (290, 204, 100, 8),
            (420, 174, 100, 8),
            (550, 144, 100, 8),
            (680, 114, 100, 8),
            (820, 96, 240, 8),
        ],
        [
            _exit(0, 176, 32, 70, "backyard", "from_ridge"),
            _exit(1108, 176, 32, 70, "valley_gate", "west"),
            _exit(1020, 50, 110, 46, "temple_gate", "west", kind="stairs"),
        ],
        {
            "west": (60, 208),
            "from_valley": (1040, 208),
            "from_temple": (860, 58),
        },
        [
            _spawn("wine_imp", 260, 212),
            _spawn("wine_imp", 880, 212),
            _spawn("paper_runner", 480, 212),
            _spawn("paper_runner", 700, 80),
        ],
        hazards=[
            ("spikes", (520, 238, 30, 8), 15),
            ("poison", (760, 240, 40, 6), 4.0),
        ],
        map_pos=(4, 0),
        art_kwargs={"ground": "path", "moon_x": 760, "props": [("signpost", 950)]},
    )

    rooms["valley_gate"] = _room(
        "valley_gate",
        640,
        ValleyArt,
        307,
        [(240, 204, 90, 8), (420, 176, 90, 8)],
        [_exit(608, 176, 32, 70, "ridge_fork", "from_valley")],
        {"west": (470, 208)},
        [
            _spawn("paper_runner", 300, 212),
            _spawn("wine_imp", 520, 212),
        ],
        hazards=[
            ("poison", (260, 240, 50, 6), 4.0),
            ("poison", (430, 240, 40, 6), 4.0),
        ],
        map_pos=(5, 1),
    )

    rooms["temple_gate"] = _room(
        "temple_gate",
        680,
        TempleArt,
        308,
        [(240, 204, 100, 8), (380, 176, 120, 8), (540, 148, 100, 8)],
        [_exit(648, 176, 32, 70, "ridge_fork", "from_temple")],
        {"west": (500, 208)},
        [
            _spawn("paper_runner", 300, 212),
            _spawn("wine_imp", 560, 212),
        ],
        hazards=[("spikes", (360, 238, 30, 8), 15)],
        map_pos=(5, -1),
    )

    return rooms



