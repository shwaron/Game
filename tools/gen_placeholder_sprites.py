"""Generate placeholder pixel-art animation strips.

Replace generated files with real art using the same paths/frame counts.
"""

import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "sprites"

PLAYER_CELL = (32, 40)
ENEMY_CELL = (24, 36)

SKIN = (232, 213, 176)
SKIN_DARK = (190, 168, 138)
EMBER = (255, 154, 60)
EYE = (30, 26, 40)
SLASH = (255, 210, 122)
FLASH = (255, 245, 230)
CRAWLER = (140, 90, 80)
CRAWLER_DARK = (104, 62, 56)
ARCHER = (150, 140, 160)
ARCHER_DARK = (108, 99, 124)
BOW = (107, 91, 62)


def save_strip(rel: str, cell: tuple[int, int], frames: int, painter) -> None:
    surface = pygame.Surface((cell[0] * frames, cell[1]), pygame.SRCALPHA)
    for index in range(frames):
        painter(surface, index, index * cell[0])
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(path))
    print(f"wrote {path.relative_to(ROOT)}")


def player_body(
    surface, ox: int, bottom: int, height: int = 38, color=SKIN,
    band: bool = True, eye: bool = True,
) -> pygame.Rect:
    rect = pygame.Rect(ox + 7, bottom - height, 18, height)
    pygame.draw.rect(surface, color, rect)
    if band and height >= 20:
        pygame.draw.rect(surface, EMBER, (rect.x, rect.y + 6, rect.w, 3))
    if eye and height >= 14:
        pygame.draw.rect(surface, EYE, (rect.right - 5, rect.y + 10, 3, 3))
    return rect


def draw_idle(surface, i, ox):
    bob = (0, 0, -1, 0)[i]
    player_body(surface, ox, 40 + bob, eye=i != 3)


def draw_run(surface, i, ox):
    bob = (0, -1, 0, -1, 0, -1)[i]
    player_body(surface, ox, 40 + bob)
    front = 8 if i % 2 == 0 else 5
    back = 5 if i % 2 == 0 else 8
    pygame.draw.rect(surface, SKIN_DARK, (ox + 9, 40 - front, 4, front))
    pygame.draw.rect(surface, SKIN_DARK, (ox + 17, 40 - back, 4, back))


def draw_jump(surface, i, ox):
    player_body(surface, ox, 38, height=36)
    pygame.draw.rect(surface, SKIN_DARK, (ox + 11, 32, 10, 4))
    pygame.draw.rect(surface, EMBER, (ox + 13, 36, 6, 2))


def draw_fall(surface, i, ox):
    player_body(surface, ox, 40)
    arm_y = 14 + i * 2
    pygame.draw.rect(surface, SKIN_DARK, (ox + 4, arm_y, 3, 8))
    pygame.draw.rect(surface, SKIN_DARK, (ox + 25, arm_y, 3, 8))
    pygame.draw.rect(surface, EMBER, (ox + 15, 2, 2, 6 + i * 4))


def draw_dash(surface, i, ox):
    for ghost in range(i):
        pygame.draw.rect(
            surface, (*SKIN, 70), (ox + 3 - ghost * 5, 4, 10, 32)
        )
    player_body(surface, ox, 40, height=38)
    pygame.draw.rect(surface, EMBER, (ox + 2, 12 + i * 3, 4, 8))


def draw_attack_windup(surface, i, ox):
    player_body(surface, ox, 40)
    pygame.draw.rect(surface, EMBER, (ox + 3, 16 + i * 2, 3 + i, 3 + i))


def draw_attack_active(surface, i, ox):
    player_body(surface, ox, 40)
    for arc in range(3):
        y = 8 + i * 5 + arc * 4
        pygame.draw.polygon(
            surface,
            SLASH,
            [(ox + 23, y), (ox + 30, y + 4), (ox + 23, y + 8)],
        )


def draw_attack_recovery(surface, i, ox):
    player_body(surface, ox, 40)
    pygame.draw.rect(surface, SLASH, (ox + 24, 10 + i * 6, 3, 10))


def draw_parry(surface, i, ox):
    player_body(surface, ox, 40)
    pygame.draw.rect(surface, SLASH, (ox + 24 + i, 11, 4, 18))
    pygame.draw.rect(surface, EMBER, (ox + 22, 10 + i, 8, 1))


def draw_skill(surface, i, ox):
    player_body(surface, ox, 40)
    pygame.draw.circle(surface, EMBER, (ox + 17, 20), 4 + i * 3, 1)


def draw_hurt(surface, i, ox):
    player_body(surface, ox - 1, 40, color=FLASH, band=False, eye=False)


def draw_death(surface, i, ox):
    heights = (38, 26, 14, 6)
    height = heights[i]
    color = SKIN if i < 2 else SKIN_DARK
    pygame.draw.rect(surface, color, (ox + 7, 40 - height, 18, height))
    if i == 0:
        pygame.draw.rect(surface, EMBER, (ox + 7, 46 - height, 18, 3))
        pygame.draw.rect(surface, EYE, (ox + 20, 50 - height, 3, 3))
    if i == 3:
        pygame.draw.rect(surface, EMBER, (ox + 14, 38, 4, 2))


def crawler_body(surface, ox, x_off=2, bob=0, height=34, color=CRAWLER):
    rect = pygame.Rect(ox + x_off, 36 - height + bob, 20, height)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, CRAWLER_DARK, (rect.x, rect.y, rect.w, 5))
    return rect


def crawler_eye(surface, ox, x_off, bob, color=EMBER):
    pygame.draw.rect(surface, color, (ox + x_off + 15, 8 + bob, 3, 3))


def draw_crawler_idle(surface, i, ox):
    bob = (0, -1)[i]
    crawler_body(surface, ox, bob=bob)
    crawler_eye(surface, ox, 2, bob)


def draw_crawler_walk(surface, i, ox):
    bob = (0, -1, 0, -1)[i]
    crawler_body(surface, ox, bob=bob)
    crawler_eye(surface, ox, 2, bob)
    front = 7 if i % 2 == 0 else 4
    pygame.draw.rect(surface, CRAWLER_DARK, (ox + 5, 36 - front, 4, front))
    pygame.draw.rect(surface, CRAWLER_DARK, (ox + 15, 36 - (11 - front), 4, 11 - front))


def draw_crawler_windup(surface, i, ox):
    crawler_body(surface, ox, x_off=1 - i, bob=0)
    crawler_eye(surface, ox, 1 - i, 0, SLASH)
    pygame.draw.rect(surface, EMBER, (ox + 7, 1, 2 + i, 2))


def draw_crawler_active(surface, i, ox):
    crawler_body(surface, ox, x_off=3 + i, height=32)
    pygame.draw.rect(surface, CRAWLER_DARK, (ox + 17 + i, 24, 5, 4))
    pygame.draw.rect(surface, SLASH, (ox + 18 + i, 24, 1, 2))
    crawler_eye(surface, ox, 3 + i, 2, SLASH)


def draw_crawler_recovery(surface, i, ox):
    crawler_body(surface, ox, x_off=2)
    crawler_eye(surface, ox, 2, 0)


def draw_crawler_stagger(surface, i, ox):
    crawler_body(surface, ox, x_off=1, bob=1 + i, height=32)
    crawler_eye(surface, ox, 1, 3, (200, 150, 60))


def draw_crawler_death(surface, i, ox):
    heights = (34, 18, 7)
    crawler_body(surface, ox, height=heights[i], color=CRAWLER_DARK)
    if i < 2:
        pygame.draw.rect(surface, EMBER, (ox + 16, 36 - heights[i] + 5, 2, 2))


def archer_body(surface, ox, x_off=2, bob=0, height=34):
    rect = pygame.Rect(ox + x_off, 36 - height + bob, 20, height)
    pygame.draw.rect(surface, ARCHER, rect)
    pygame.draw.rect(surface, ARCHER_DARK, (rect.x, rect.y, rect.w, 5))
    pygame.draw.rect(surface, EMBER, (rect.x + 15, rect.y + 8, 3, 3))
    return rect


def draw_bow(surface, ox, tension=0):
    x = ox + 22
    pygame.draw.line(surface, BOW, (x, 10), (x, 27), 2)
    if tension:
        pygame.draw.line(surface, SLASH, (x - 4, 18), (x, 18), 1)


def draw_archer_idle(surface, i, ox):
    bob = (0, -1)[i]
    archer_body(surface, ox, bob=bob)
    draw_bow(surface, ox)


def draw_archer_walk(surface, i, ox):
    bob = (0, -1, 0, -1)[i]
    archer_body(surface, ox, bob=bob)
    front = 6 if i % 2 == 0 else 3
    pygame.draw.rect(surface, ARCHER_DARK, (ox + 5, 36 - front, 4, front))
    pygame.draw.rect(surface, ARCHER_DARK, (ox + 15, 36 - (10 - front), 4, 10 - front))
    draw_bow(surface, ox)


def draw_archer_windup(surface, i, ox):
    archer_body(surface, ox)
    draw_bow(surface, ox, tension=1 + i)
    pygame.draw.rect(surface, EMBER, (ox + 19, 17, 1 + i, 2))


def draw_archer_active(surface, i, ox):
    archer_body(surface, ox, x_off=1)
    pygame.draw.line(surface, SLASH, (ox + 21, 17 + i), (ox + 28, 17 + i), 2)


def draw_archer_recovery(surface, i, ox):
    archer_body(surface, ox)
    draw_bow(surface, ox)


def draw_archer_stagger(surface, i, ox):
    archer_body(surface, ox, x_off=1, bob=1 + i, height=32)
    pygame.draw.rect(surface, EMBER, (ox + 16, 36 - 32 + 1 + i + 8, 2, 2))


def draw_archer_death(surface, i, ox):
    heights = (34, 18, 7)
    pygame.draw.rect(surface, ARCHER_DARK, (ox + 2, 36 - heights[i], 20, heights[i]))
    if i < 2:
        pygame.draw.rect(surface, EMBER, (ox + 16, 36 - heights[i] + 5, 2, 2))


def main() -> None:
    pygame.init()
    player = {
        "idle": (4, draw_idle),
        "run": (6, draw_run),
        "jump": (1, draw_jump),
        "fall": (2, draw_fall),
        "dash": (3, draw_dash),
        "attack_windup": (2, draw_attack_windup),
        "attack_active": (4, draw_attack_active),
        "attack_recovery": (4, draw_attack_recovery),
        "parry": (2, draw_parry),
        "skill": (4, draw_skill),
        "hurt": (2, draw_hurt),
        "death": (4, draw_death),
    }
    for name, (frames, painter) in player.items():
        save_strip(f"player/{name}.png", PLAYER_CELL, frames, painter)

    crawler = {
        "idle": (2, draw_crawler_idle),
        "walk": (4, draw_crawler_walk),
        "windup": (2, draw_crawler_windup),
        "active": (2, draw_crawler_active),
        "recovery": (2, draw_crawler_recovery),
        "stagger": (2, draw_crawler_stagger),
        "death": (3, draw_crawler_death),
    }
    archer = {
        "idle": (2, draw_archer_idle),
        "walk": (4, draw_archer_walk),
        "windup": (2, draw_archer_windup),
        "active": (2, draw_archer_active),
        "recovery": (2, draw_archer_recovery),
        "stagger": (2, draw_archer_stagger),
        "death": (3, draw_archer_death),
    }
    for enemy_id, clips in (("ash_crawler", crawler), ("bone_archer", archer)):
        for name, (frames, painter) in clips.items():
            save_strip(f"enemies/{enemy_id}/{name}.png", ENEMY_CELL, frames, painter)
    pygame.quit()


if __name__ == "__main__":
    main()