"""Procedural art and room layout for the bamboo-inn first level.

The stage is drawn in two passes around the actors: the inn and forest go
behind the player/enemies, while leaves and a soft vignette sit in front.
Everything is hand-placed to keep the fixed layout readable and repeatable.
"""

import math
import random
from types import SimpleNamespace

import pygame

WIDTH = 480
HEIGHT = 270
FLOOR_Y = 246
INN_LEFT = 80

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


def build_room() -> SimpleNamespace:
    return SimpleNamespace(
        solids=[
            pygame.Rect(0, FLOOR_Y, WIDTH, HEIGHT - FLOOR_Y),
            pygame.Rect(0, 0, 8, HEIGHT),
            pygame.Rect(WIDTH - 8, 0, 8, HEIGHT),
            pygame.Rect(0, 0, WIDTH, 8),
        ],
        one_ways=[
            pygame.Rect(256, 204, 128, 8),
            pygame.Rect(100, 158, 184, 8),
            pygame.Rect(292, 114, 164, 8),
        ],
        hazards=[
            SimpleNamespace(
                kind="spikes", rect=pygame.Rect(218, 238, 32, 8), damage=15
            ),
            SimpleNamespace(
                kind="poison", rect=pygame.Rect(150, 240, 36, 6), damage=4.0
            ),
        ],
    )


ENEMY_SPAWNS = [
    {"enemy_id": "wine_imp", "x": 148, "y": 200},
    {"enemy_id": "wine_imp", "x": 356, "y": 200},
    {"enemy_id": "paper_runner", "x": 232, "y": 196},
    {"enemy_id": "paper_runner", "x": 432, "y": 196},
    {"enemy_id": "paper_runner", "x": 312, "y": 158},
    {"enemy_id": "wine_imp", "x": 196, "y": 110},
    {"enemy_id": "paper_runner", "x": 366, "y": 66},
]


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


def _radial_glow(radius: int, color, strength: float = 1.0) -> pygame.Surface:
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
    return surf


class InnStage:
    def __init__(self) -> None:
        self.time = 0.0
        self.font_sign = load_cjk_font(14)
        self.font_small = load_cjk_font(11)
        self.glow_lantern = _radial_glow(34, (120, 50, 14), 1.0)
        self.glow_window = _radial_glow(58, (100, 64, 24), 0.7)
        self.glow_moon = _radial_glow(42, (26, 26, 16), 0.9)
        self.vignette = self._make_vignette()
        self.bamboo_far, self.bamboo_mid, self.bamboo_near = self._make_bamboo()
        self.fireflies = self._make_fireflies()
        self.embers = self._make_embers()
        self.leaves = self._make_leaves()

    # -- generation -----------------------------------------------------
    def _make_bamboo(self):
        rng = random.Random(20261118)
        far = []
        for i in range(26):
            far.append(
                {
                    "x": -6 + i * (WIDTH + 12) / 26 + rng.uniform(-5, 5),
                    "top": rng.randint(28, 78),
                    "width": rng.randint(2, 3),
                    "phase": rng.uniform(0, math.tau),
                    "sway": rng.uniform(1.0, 2.4),
                }
            )
        mid = []
        for i in range(16):
            mid.append(
                {
                    "x": -4 + i * (WIDTH + 8) / 16 + rng.uniform(-7, 7),
                    "top": rng.randint(20, 62),
                    "width": rng.randint(3, 5),
                    "phase": rng.uniform(0, math.tau),
                    "sway": rng.uniform(1.8, 3.0),
                }
            )
        near = []
        for x, top, width in (
            (2, 0, 7),
            (18, 26, 5),
            (62, 10, 6),
            (154, 34, 6),
            (304, 8, 7),
            (476, 22, 6),
        ):
            near.append(
                {
                    "x": x,
                    "top": top,
                    "width": width,
                    "phase": rng.uniform(0, math.tau),
                    "sway": rng.uniform(2.4, 3.6),
                }
            )
        return far, mid, near

    def _make_fireflies(self):
        rng = random.Random(4411)
        return [
            {
                "x": rng.randint(20, 458),
                "y": rng.randint(84, 224),
                "phase": rng.uniform(0, math.tau),
                "amp": rng.uniform(3, 11),
                "speed": rng.uniform(0.3, 0.8),
            }
            for _ in range(16)
        ]

    def _make_embers(self):
        rng = random.Random(9082)
        return [
            {
                "x": rng.randint(66, 456),
                "y": rng.randint(100, 230),
                "speed": rng.uniform(4, 10),
                "phase": rng.uniform(0, math.tau),
            }
            for _ in range(14)
        ]

    def _make_leaves(self):
        rng = random.Random(7712)
        return [
            {
                "x": rng.randint(0, WIDTH),
                "y": rng.randint(0, HEIGHT),
                "speed": rng.uniform(5, 12),
                "sway": rng.uniform(6, 18),
                "phase": rng.uniform(0, math.tau),
            }
            for _ in range(18)
        ]

    def _make_vignette(self) -> pygame.Surface:
        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        cx, cy = WIDTH / 2, HEIGHT / 2
        max_dist = math.hypot(cx, cy)
        for y in range(HEIGHT):
            for x in range(WIDTH):
                dist = math.hypot(x - cx, y - cy) / max_dist
                alpha = max(0, int((dist - 0.58) * 110))
                if alpha:
                    surf.set_at((x, y), (5, 7, 8, min(70, alpha)))
        return surf

    # -- public ---------------------------------------------------------
    def update(self, dt: float) -> None:
        self.time += dt

    def draw_back(self, surface: pygame.Surface) -> None:
        self._draw_sky(surface)
        self._draw_bamboo_layer(surface, self.bamboo_far, BAMBOO_FAR)
        self._draw_mist(surface)
        self._draw_bamboo_layer(surface, self.bamboo_mid, BAMBOO_MID)
        self._draw_inn(surface)
        self._draw_light(surface)
        self._draw_ambient(surface)

    def draw_front(self, surface: pygame.Surface) -> None:
        self._draw_leaves_front(surface)
        surface.blit(self.vignette, (0, 0))

    # -- sky and forest -------------------------------------------------
    def _draw_sky(self, surface: pygame.Surface) -> None:
        for y in range(FLOOR_Y):
            t = y / FLOOR_Y
            pygame.draw.line(
                surface,
                _lerp(SKY_TOP, SKY_BOTTOM, t),
                (0, y),
                (WIDTH, y),
            )
        surface.blit(self.glow_moon, (10, 8))
        pygame.draw.circle(surface, MOON_DIM, (46, 42), 16)
        pygame.draw.circle(surface, MOON, (43, 39), 13)
        pygame.draw.circle(surface, (238, 234, 208), (39, 35), 6)
        pygame.draw.polygon(
            surface,
            MOUNTAIN_FAR,
            [
                (0, 122),
                (54, 82),
                (110, 110),
                (178, 70),
                (244, 108),
                (312, 76),
                (376, 112),
                (438, 84),
                (480, 104),
                (480, 160),
                (0, 160),
            ],
        )
        pygame.draw.polygon(
            surface,
            MOUNTAIN_NEAR,
            [
                (0, 154),
                (70, 118),
                (142, 142),
                (216, 112),
                (292, 146),
                (362, 120),
                (430, 148),
                (480, 132),
                (480, 190),
                (0, 190),
            ],
        )

    def _draw_bamboo_layer(self, surface, layer, color) -> None:
        dark = _lerp(color, (10, 14, 12), 0.45)
        highlight = _lerp(color, BAMBOO_HI, 0.35)
        for stalk in layer:
            base_x = stalk["x"]
            top = stalk["top"]
            width = stalk["width"]
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
            self._draw_leaf_cluster(
                surface, sx(top + 8) + 1, top + 8, BAMBOO_LEAF, 1
            )
            self._draw_leaf_cluster(
                surface, sx(top + 55) - 2, top + 55, BAMBOO_LEAF, -1
            )
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

    def _draw_mist(self, surface: pygame.Surface) -> None:
        for y, alpha in ((92, 22), (132, 16), (184, 12)):
            band = pygame.Surface((WIDTH, 26), pygame.SRCALPHA)
            band.fill((132, 158, 146, alpha))
            surface.blit(band, (0, y + math.sin(self.time * 0.25 + y) * 3))

    # -- inn ------------------------------------------------------------
    def _draw_inn(self, surface: pygame.Surface) -> None:
        self._draw_floor(surface)
        self._draw_back_walls(surface)
        self._draw_doorway(surface)
        self._draw_roof(surface)
        self._draw_beams(surface)
        self._draw_platforms(surface)
        self._draw_furniture(surface)
        self._draw_sign(surface)

    def _draw_floor(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, STONE_DARK, (0, FLOOR_Y, INN_LEFT, 24))
        for i in range(9):
            x = 4 + (i * 17) % INN_LEFT
            y = FLOOR_Y + 4 + (i * 7) % 16
            pygame.draw.rect(surface, STONE, (x, y, 10, 4))
        pygame.draw.rect(surface, MOSS, (0, FLOOR_Y + 2, 24, 4))
        pygame.draw.rect(surface, WOOD, (INN_LEFT, FLOOR_Y, WIDTH - INN_LEFT, 24))
        for y in (FLOOR_Y + 5, FLOOR_Y + 11, FLOOR_Y + 17):
            pygame.draw.line(surface, WOOD_DARK, (INN_LEFT, y), (WIDTH, y), 1)
        for x in range(INN_LEFT + 12, WIDTH, 36):
            pygame.draw.line(
                surface, WOOD_EDGE, (x, FLOOR_Y), (x, HEIGHT), 1
            )
        pygame.draw.rect(surface, CLOTH_DARK, (146, FLOOR_Y - 1, 224, 7))
        pygame.draw.line(
            surface, CLOTH, (150, FLOOR_Y), (366, FLOOR_Y), 1
        )
        pygame.draw.rect(surface, WOOD_EDGE, (INN_LEFT - 3, FLOOR_Y, 6, 24))
        pygame.draw.rect(surface, WOOD_LIGHT, (INN_LEFT, FLOOR_Y, 2, 24))

    def _window(self, surface, rect: pygame.Rect, lit: bool = True) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, rect.inflate(6, 6))
        inner = (PAPER if lit else (128, 104, 76))
        pygame.draw.rect(surface, inner, rect)
        pygame.draw.rect(surface, PAPER_LIGHT, rect.inflate(-4, -4))
        for x in range(rect.x + 8, rect.right, 16):
            pygame.draw.line(
                surface, (78, 54, 34), (x, rect.y), (x, rect.bottom), 1
            )
        for y in range(rect.y + 10, rect.bottom, 16):
            pygame.draw.line(
                surface, (78, 54, 34), (rect.x, y), (rect.right, y), 1
            )
        pygame.draw.line(
            surface, (60, 42, 28), rect.topleft, rect.bottomright
        )
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

    def _draw_back_walls(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (46, 32, 25), (84, 92, 74, 154))
        pygame.draw.rect(surface, (42, 29, 23), (310, 92, 162, 154))
        for x in range(88, 156, 9):
            pygame.draw.line(surface, WOOD_DARK, (x, 92), (x, 246), 1)
        for x in range(314, 472, 10):
            pygame.draw.line(surface, WOOD_DARK, (x, 92), (x, 246), 1)
        self._window(surface, pygame.Rect(94, 108, 54, 62), lit=True)
        self._window(surface, pygame.Rect(330, 108, 48, 56), lit=True)
        self._window(surface, pygame.Rect(404, 112, 46, 50), lit=False)
        pygame.draw.rect(surface, WOOD, (326, 182, 132, 6))
        for x, w in ((334, 8), (350, 6), (364, 9), (382, 6), (398, 8), (424, 6)):
            pygame.draw.rect(surface, (66, 48, 36), (x, 170, w, 12))
            pygame.draw.rect(surface, (170, 62, 44), (x, 170, w, 2))
            pygame.draw.rect(surface, (44, 32, 26), (x + 1, 175, w - 2, 5))
        pygame.draw.line(surface, WOOD_LIGHT, (326, 182), (458, 182), 1)
        pygame.draw.rect(surface, (36, 26, 21), (92, 224, 58, 22))
        pygame.draw.rect(surface, WOOD, (90, 218, 62, 8))
        pygame.draw.rect(surface, WOOD_LIGHT, (90, 218, 62, 1))
        for i in range(4):
            pygame.draw.rect(
                surface, (110, 78, 52), (94 + i * 14, 208 + (i % 2) * 3, 7, 10)
            )
            pygame.draw.rect(
                surface, (80, 54, 36), (95 + i * 14, 209 + (i % 2) * 3, 5, 2)
            )

    def _draw_doorway(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, STONE, (154, 238, 160, 8))
        pygame.draw.line(surface, STONE_DARK, (154, 238), (314, 238), 1)
        for x in (170, 214, 260, 300):
            pygame.draw.line(surface, STONE_DARK, (x, 239), (x + 8, 245), 1)
        pygame.draw.rect(surface, WOOD_EDGE, (152, 82, 10, 164))
        pygame.draw.rect(surface, WOOD, (154, 82, 6, 160))
        pygame.draw.rect(surface, WOOD_EDGE, (308, 82, 10, 164))
        pygame.draw.rect(surface, WOOD, (310, 82, 6, 160))
        pygame.draw.rect(surface, WOOD_EDGE, (152, 82, 166, 14))
        pygame.draw.rect(surface, WOOD, (154, 84, 162, 9))
        pygame.draw.line(surface, WOOD_LIGHT, (156, 85), (312, 85), 1)
        pygame.draw.rect(surface, (38, 56, 50), (160, 96, 148, 22))
        for x in range(162, 308, 6):
            pygame.draw.line(surface, (28, 42, 38), (x, 96), (x, 118), 1)
        pygame.draw.line(surface, CLOTH_DARK, (160, 117), (308, 117), 2)
        pygame.draw.line(surface, CLOTH, (160, 118), (308, 118), 1)
        for x in (168, 300):
            pygame.draw.line(surface, CLOTH_DARK, (x, 118), (x, 124), 2)

    def _draw_roof(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, (20, 22, 22), (54, 68, 424, 18))
        pygame.draw.polygon(
            surface,
            ROOF_EDGE,
            [
                (46, 72),
                (62, 54),
                (92, 32),
                (420, 32),
                (452, 52),
                (478, 72),
                (470, 80),
                (56, 80),
            ],
        )
        pygame.draw.polygon(
            surface,
            ROOF,
            [
                (52, 70),
                (66, 54),
                (96, 35),
                (416, 35),
                (446, 53),
                (470, 70),
                (464, 76),
                (60, 76),
            ],
        )
        pygame.draw.line(surface, ROOF_LIGHT, (96, 35), (416, 35), 2)
        pygame.draw.line(surface, ROOF_DARK, (96, 37), (416, 37), 1)
        for x in range(74, 462, 14):
            pygame.draw.line(surface, ROOF_DARK, (x, 38), (x + 2, 74), 1)
            pygame.draw.line(surface, ROOF_LIGHT, (x + 1, 39), (x + 3, 72), 1)
        pygame.draw.line(surface, ROOF_LIGHT, (60, 76), (464, 76), 1)
        pygame.draw.polygon(
            surface, ROOF_DARK, [(88, 34), (96, 22), (104, 34)]
        )
        pygame.draw.polygon(
            surface, ROOF_DARK, [(408, 34), (416, 22), (424, 34)]
        )
        for x in (56, 464):
            pygame.draw.line(
                surface, ROOF_LIGHT, (x, 72), (x + (6 if x < 240 else -6), 64), 1
            )

    def _draw_beams(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, WOOD_EDGE, (84, 76, 390, 10))
        pygame.draw.rect(surface, WOOD, (86, 78, 386, 6))
        pygame.draw.line(surface, WOOD_LIGHT, (88, 79), (470, 79), 1)
        for x in (84, 154, 310, 466):
            pygame.draw.rect(surface, WOOD_EDGE, (x, 76, 10, 172))
            pygame.draw.rect(surface, WOOD, (x + 2, 76, 6, 170))
            pygame.draw.line(
                surface, WOOD_LIGHT, (x + 2, 80), (x + 2, 242), 1
            )
            pygame.draw.rect(surface, STONE_DARK, (x - 2, 238, 14, 8))
            pygame.draw.rect(surface, STONE, (x, 240, 10, 6))
        for x in (100, 288):
            pygame.draw.line(
                surface, WOOD_DARK, (x, 92), (x + 10, 104), 2
            )
            pygame.draw.line(
                surface, WOOD_DARK, (x + 10, 104), (x, 112), 2
            )

    def _draw_platforms(self, surface: pygame.Surface) -> None:
        # mezzanine
        pygame.draw.rect(surface, WOOD_EDGE, (98, 156, 190, 12))
        pygame.draw.rect(surface, WOOD, (100, 158, 184, 8))
        pygame.draw.line(surface, WOOD_LIGHT, (102, 159), (282, 159), 1)
        for x in range(104, 284, 18):
            pygame.draw.rect(surface, WOOD_EDGE, (x, 160, 2, 9))
        for x in (112, 178, 246):
            pygame.draw.polygon(
                surface,
                WOOD_DARK,
                [(x, 166), (x + 18, 166), (x + 10, 184)],
            )
            pygame.draw.line(
                surface, WOOD, (x + 10, 166), (x + 10, 181), 2
            )
        # mezzanine railing (behind actors)
        pygame.draw.rect(surface, WOOD_EDGE, (100, 134, 184, 4))
        pygame.draw.rect(surface, WOOD, (102, 136, 180, 2))
        for x in range(106, 282, 22):
            pygame.draw.rect(surface, WOOD_EDGE, (x, 138, 3, 20))
            pygame.draw.rect(surface, WOOD, (x + 1, 138, 1, 18))
        pygame.draw.rect(surface, WOOD_DARK, (100, 150, 184, 3))
        # upper beam
        pygame.draw.rect(surface, WOOD_EDGE, (290, 112, 170, 12))
        pygame.draw.rect(surface, WOOD, (292, 114, 164, 8))
        pygame.draw.line(surface, WOOD_LIGHT, (294, 115), (454, 115), 1)
        for x in (300, 356, 414, 448):
            pygame.draw.polygon(
                surface,
                WOOD_DARK,
                [(x, 122), (x + 18, 122), (x + 10, 138)],
            )
            pygame.draw.line(surface, WOOD, (x + 10, 122), (x + 10, 135), 2)
        # banquet table
        pygame.draw.rect(surface, WOOD_EDGE, (254, 202, 132, 12))
        pygame.draw.rect(surface, WOOD, (256, 204, 128, 8))
        pygame.draw.line(surface, WOOD_LIGHT, (258, 205), (382, 205), 1)
        pygame.draw.rect(surface, CLOTH_DARK, (266, 207, 108, 3))
        for x in (264, 366):
            pygame.draw.rect(surface, WOOD_EDGE, (x, 212, 10, 34))
            pygame.draw.rect(surface, WOOD_DARK, (x + 2, 212, 6, 34))
        # small stool by the table
        pygame.draw.rect(surface, WOOD_EDGE, (398, 230, 18, 5))
        pygame.draw.rect(surface, WOOD, (400, 230, 14, 3))
        pygame.draw.rect(surface, WOOD_DARK, (402, 235, 3, 11))
        pygame.draw.rect(surface, WOOD_DARK, (410, 235, 3, 11))
        # ladder to the upper beam
        pygame.draw.line(surface, WOOD_DARK, (462, 122), (462, 246), 2)
        pygame.draw.line(surface, WOOD_DARK, (470, 122), (470, 246), 2)
        for y in range(132, 246, 14):
            pygame.draw.line(surface, WOOD, (462, y), (470, y), 1)

    def _draw_furniture(self, surface: pygame.Surface) -> None:
        for x, y, w, h in (
            (278, 196, 8, 4),
            (300, 196, 10, 3),
            (352, 196, 7, 4),
        ):
            pygame.draw.ellipse(surface, (204, 188, 154), (x, y, w, h))
            pygame.draw.line(surface, (130, 112, 86), (x + 1, y + 1), (x + 3, y + 1), 1)
        pygame.draw.rect(surface, (64, 48, 36), (320, 194, 10, 6))
        pygame.draw.rect(surface, (112, 88, 58), (322, 192, 6, 3))
        pygame.draw.rect(surface, (150, 94, 66), (372, 190, 8, 12))
        pygame.draw.rect(surface, (92, 58, 46), (373, 188, 6, 3))
        for x, y in ((410, 226), (424, 228), (440, 224)):
            pygame.draw.rect(surface, (62, 46, 38), (x, y, 10, 20))
            pygame.draw.rect(surface, (86, 60, 44), (x + 2, y - 2, 6, 6))
            pygame.draw.rect(surface, CLOTH, (x + 1, y - 3, 8, 2))
        pygame.draw.line(surface, WOOD_DARK, (326, 130), (326, 174), 2)
        pygame.draw.line(surface, (188, 166, 124), (328, 132), (328, 170), 7)
        self._vertical_banner(surface, 328, 132, "酒")
        pygame.draw.line(surface, WOOD_DARK, (390, 130), (390, 170), 2)
        pygame.draw.line(surface, (188, 166, 124), (392, 132), (392, 166), 7)
        self._vertical_banner(surface, 392, 132, "茶")
        self._draw_weapon_rack(surface, 416, 182)
        self._draw_lantern(surface, 66, 92, small=True)
        self._draw_lantern(surface, 222, 86)
        self._draw_lantern(surface, 362, 92)
        self._draw_lantern(surface, 132, 174, small=True)

    def _vertical_banner(self, surface, x, y, text: str) -> None:
        pygame.draw.rect(surface, (176, 152, 112), (x, y, 8, 38))
        pygame.draw.line(surface, (110, 84, 56), (x, y), (x, y + 38), 1)
        pygame.draw.line(surface, (110, 84, 56), (x + 7, y), (x + 7, y + 38), 1)
        label = self.font_small.render(text, False, (54, 44, 38))
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
        rect = pygame.Rect(88, 72, 84, 20)
        pygame.draw.rect(surface, WOOD_EDGE, rect.inflate(4, 4))
        pygame.draw.rect(surface, (94, 62, 38), rect)
        pygame.draw.rect(surface, HUD_GOLD, rect, 1)
        text = self.font_sign.render("竹坞客栈", False, (234, 204, 142))
        surface.blit(
            text,
            (
                rect.centerx - text.get_width() // 2,
                rect.centery - text.get_height() // 2,
            ),
        )
        pygame.draw.rect(surface, CLOTH, (rect.right - 10, rect.y + 5, 4, 7))

    def _draw_lantern(self, surface, x, y, small=False) -> None:
        if small:
            pygame.draw.line(surface, (48, 34, 26), (x, y - 14), (x, y - 3), 1)
            body = pygame.Rect(x - 4, y, 8, 10)
        else:
            pygame.draw.line(surface, (48, 34, 26), (x, y - 18), (x, y - 5), 1)
            body = pygame.Rect(x - 5, y, 10, 14)
        pygame.draw.rect(surface, LANTERN_GOLD, (body.x + 1, body.y - 2, body.w - 2, 2))
        pygame.draw.rect(surface, LANTERN, body)
        pygame.draw.rect(surface, LANTERN_LIGHT, (body.x + 2, body.y + 2, 2, body.h - 4))
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
        pygame.draw.rect(surface, LANTERN_GOLD, (body.x + 1, body.bottom, body.w - 2, 2))
        pygame.draw.line(
            surface, LANTERN_LIGHT, (body.centerx, body.bottom + 2), (body.centerx, body.bottom + 6), 1
        )
        surface.blit(
            self.glow_lantern,
            (body.centerx - self.glow_lantern.get_width() // 2,
             body.centery - self.glow_lantern.get_height() // 2),
            special_flags=pygame.BLEND_RGB_ADD,
        )

    def _draw_light(self, surface: pygame.Surface) -> None:
        for rect in (pygame.Rect(94, 108, 54, 62), pygame.Rect(330, 108, 48, 56)):
            surface.blit(
                self.glow_window,
                (
                    rect.centerx - self.glow_window.get_width() // 2,
                    rect.centery - self.glow_window.get_height() // 2,
                ),
                special_flags=pygame.BLEND_RGB_ADD,
            )
        pygame.draw.ellipse(surface, (86, 54, 34), (176, 247, 96, 5))
        pygame.draw.ellipse(surface, (70, 46, 34), (300, 247, 108, 4))

    def _draw_ambient(self, surface: pygame.Surface) -> None:
        for fly in self.fireflies:
            x = fly["x"] + math.sin(self.time * fly["speed"] + fly["phase"]) * fly["amp"]
            y = fly["y"] + math.cos(self.time * fly["speed"] * 0.7 + fly["phase"]) * 5
            pygame.draw.circle(surface, FIREFLY, (round(x), round(y)), 1)
            if int(self.time * 2 + fly["phase"]) % 7 == 0:
                pygame.draw.circle(surface, (110, 130, 80), (round(x), round(y)), 2, 1)
        for ember in self.embers:
            x = ember["x"] + math.sin(self.time * 0.6 + ember["phase"]) * 3
            y = (ember["y"] - self.time * ember["speed"]) % 150 + 90
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
