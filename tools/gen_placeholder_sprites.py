"""Generate stick-figure skeleton animation strips.

Bones are drawn as 2px lines between joints so poses read clearly.
Replace generated files with real art using the same paths/frame counts.
"""

import math
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
CRAWLER = (150, 96, 84)
CRAWLER_DARK = (104, 62, 56)
ARCHER = (160, 150, 170)
ARCHER_DARK = (108, 99, 124)
BOW = (107, 91, 62)


def line(surface, color, a, b, width=2):
    pygame.draw.line(
        surface,
        color,
        (round(a[0]), round(a[1])),
        (round(b[0]), round(b[1])),
        width,
    )


def dot(surface, color, p, radius=1):
    pygame.draw.circle(surface, color, (round(p[0]), round(p[1])), radius)


def save_strip(rel: str, cell: tuple[int, int], frames: int, painter) -> None:
    surface = pygame.Surface((cell[0] * frames, cell[1]), pygame.SRCALPHA)
    for index in range(frames):
        painter(surface, index, index * cell[0])
    path = OUT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(surface, str(path))
    print(f"wrote {path.relative_to(ROOT)}")


# --- player skeleton -------------------------------------------------------


def player_pose(**overrides):
    pose = {
        "head": (16, 8),
        "neck": (16, 12),
        "chest": (16, 15),
        "pelvis": (16, 25),
        "near_elbow": (12, 20),
        "near_hand": (11, 26),
        "far_elbow": (20, 20),
        "far_hand": (21, 26),
        "near_knee": (15, 31),
        "near_foot": (14, 38),
        "far_knee": (18, 31),
        "far_foot": (19, 38),
    }
    pose.update(overrides)
    return pose


def draw_player_skeleton(surface, ox, pose, color=SKIN, dark=SKIN_DARK, eye=True):
    def pt(name):
        x, y = pose[name]
        return (ox + x, y)

    head = pt("head")
    neck = pt("neck")
    chest = pt("chest")
    pelvis = pt("pelvis")
    near_elbow = pt("near_elbow")
    near_hand = pt("near_hand")
    far_elbow = pt("far_elbow")
    far_hand = pt("far_hand")
    near_knee = pt("near_knee")
    near_foot = pt("near_foot")
    far_knee = pt("far_knee")
    far_foot = pt("far_foot")

    line(surface, dark, chest, far_elbow)
    line(surface, dark, far_elbow, far_hand)
    line(surface, dark, pelvis, far_knee)
    line(surface, dark, far_knee, far_foot)

    line(surface, color, neck, pelvis, 2)
    line(surface, color, (chest[0] - 4, chest[1]), (chest[0] + 4, chest[1]))
    line(surface, color, (pelvis[0] - 3, pelvis[1]), (pelvis[0] + 3, pelvis[1]))
    line(surface, color, chest, near_elbow)
    line(surface, color, near_elbow, near_hand)
    line(surface, color, pelvis, near_knee)
    line(surface, color, near_knee, near_foot)

    line(surface, EMBER, (chest[0] - 3, chest[1]), (chest[0] + 3, chest[1]), 1)
    dot(surface, color, near_hand, 1)
    dot(surface, color, far_hand, 1)
    pygame.draw.circle(surface, color, (round(head[0]), round(head[1])), 4, 2)
    if eye:
        dot(surface, EYE, (head[0] + 2, head[1] - 1), 1)


def draw_blade(surface, hand, tip):
    line(surface, FLASH, hand, tip, 2)
    line(surface, SLASH, hand, tip, 1)


def draw_spear(surface, tail, tip):
    line(surface, BOW, tail, tip, 2)
    dx, dy = tip[0] - tail[0], tip[1] - tail[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    base = (tip[0] - ux * 4, tip[1] - uy * 4)
    pygame.draw.polygon(
        surface,
        FLASH,
        [
            (round(tip[0]), round(tip[1])),
            (round(base[0] - uy * 2), round(base[1] + ux * 2)),
            (round(base[0] + uy * 2), round(base[1] - ux * 2)),
        ],
    )


def draw_hammer(surface, hand, head_topleft, size=(14, 7)):
    x, y = head_topleft
    line(surface, BOW, hand, (x + size[0] // 2, y + size[1] - 1), 2)
    pygame.draw.rect(surface, ARCHER, (x, y, size[0], size[1]))
    pygame.draw.rect(surface, ARCHER_DARK, (x, y + size[1] - 2, size[0], 2))
    pygame.draw.rect(surface, FLASH, (x + 2, y + 2, 3, 2))


def draw_staff(surface, top, bottom, orb_center=None, orb_radius=0):
    line(surface, BOW, top, bottom, 2)
    if orb_center and orb_radius > 0:
        pygame.draw.circle(
            surface,
            EMBER,
            (round(orb_center[0]), round(orb_center[1])),
            orb_radius,
            1,
        )
        dot(surface, FLASH, orb_center, 1)


def draw_idle(surface, i, ox):
    bob = (0, 0, -1, 0)[i]
    sway = (0, 1, 0, -1)[i]
    pose = player_pose(
        head=(16, 8 + bob),
        neck=(16, 12 + bob),
        chest=(16, 15 + bob),
        pelvis=(16, 25 + bob),
        near_elbow=(12 + sway, 20 + bob),
        near_hand=(11 + sway, 26 + bob),
        far_elbow=(20 - sway, 20 + bob),
        far_hand=(21 - sway, 26 + bob),
        near_knee=(15, 31 + bob),
        far_knee=(18, 31 + bob),
    )
    draw_player_skeleton(surface, ox, pose)


def draw_run(surface, i, ox):
    swing = math.sin(i / 6 * math.tau)
    bob = -1 if abs(swing) > 0.6 else 0
    lean = 1
    pose = player_pose(
        head=(16 + lean + swing * 0.5, 8 + bob),
        neck=(16 + lean, 12 + bob),
        chest=(16 + lean, 15 + bob),
        pelvis=(16, 25 + bob),
        near_elbow=(16 - 4 * swing, 20 + bob),
        near_hand=(16 - 7 * swing, 25 + bob),
        far_elbow=(16 + 4 * swing, 20 + bob),
        far_hand=(16 + 7 * swing, 25 + bob),
        near_knee=(16 + 4 * swing, 31 + bob),
        near_foot=(16 + 8 * swing, 38 - max(0.0, swing) * 2),
        far_knee=(16 - 4 * swing, 31 + bob),
        far_foot=(16 - 8 * swing, 38 - max(0.0, -swing) * 2),
    )
    draw_player_skeleton(surface, ox, pose)


def draw_jump(surface, i, ox):
    pose = player_pose(
        head=(16, 7),
        neck=(16, 11),
        chest=(16, 14),
        pelvis=(16, 23),
        near_elbow=(20, 12),
        near_hand=(23, 7),
        far_elbow=(12, 11),
        far_hand=(9, 6),
        near_knee=(20, 27),
        near_foot=(22, 32),
        far_knee=(12, 27),
        far_foot=(10, 32),
    )
    draw_player_skeleton(surface, ox, pose)


def draw_fall(surface, i, ox):
    sway = (-1, 1)[i]
    pose = player_pose(
        near_elbow=(21, 12 + sway),
        near_hand=(24, 8 + sway * 2),
        far_elbow=(11, 12 - sway),
        far_hand=(8, 8 - sway * 2),
        near_knee=(19, 29),
        near_foot=(21, 36),
        far_knee=(13, 29),
        far_foot=(10, 36),
    )
    draw_player_skeleton(surface, ox, pose)


def draw_dash(surface, i, ox):
    ghost_pose = player_pose(
        head=(19, 9),
        neck=(18, 13),
        chest=(18, 16),
        pelvis=(17, 25),
        near_elbow=(22, 18),
        near_hand=(26, 21),
        near_knee=(14, 30),
        near_foot=(10, 35),
        far_knee=(12, 28),
        far_foot=(7, 33),
    )
    for ghost in range(1, i + 1):
        draw_player_skeleton(
            surface,
            ox - ghost * 5,
            ghost_pose,
            color=(*SKIN, 60),
            dark=(*SKIN_DARK, 60),
            eye=False,
        )
    pose = player_pose(
        head=(20, 9),
        neck=(19, 13),
        chest=(19, 16),
        pelvis=(17, 25),
        near_elbow=(23, 18),
        near_hand=(27, 21),
        far_elbow=(20, 20),
        far_hand=(24, 24),
        near_knee=(14, 30),
        near_foot=(10, 35),
        far_knee=(12, 28),
        far_foot=(7, 33),
    )
    draw_player_skeleton(surface, ox, pose)
    line(surface, EMBER, (ox + 2, 14 + i * 3), (ox + 6, 14 + i * 3), 2)


def draw_attack_sword_windup(surface, i, ox):
    hand = (13 + i * 2, 10 + i * 3)
    tip = (hand[0] - 5, hand[1] - 6)
    pose = player_pose(
        head=(15, 8),
        neck=(15, 12),
        chest=(15, 15),
        near_elbow=(11 + i, 14),
        near_hand=hand,
        far_elbow=(20, 18),
        far_hand=(23, 20),
        near_knee=(19, 30),
        near_foot=(22, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_blade(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))


def draw_attack_sword_active(surface, i, ox):
    hands = [(18, 8), (23, 11), (27, 15), (26, 22)]
    hand = hands[i]
    tip = (hand[0] + 7, hand[1] + 2 + i)
    pose = player_pose(
        head=(18, 8),
        neck=(17, 12),
        chest=(17, 15),
        near_elbow=(15, 17),
        near_hand=hand,
        far_elbow=(12, 18),
        far_hand=(9, 21),
        near_knee=(21, 30),
        near_foot=(24, 37),
        far_knee=(13, 31),
        far_foot=(9, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_blade(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))
    for arc in range(2):
        y = 10 + i * 4 + arc * 5
        pygame.draw.polygon(
            surface,
            SLASH,
            [(ox + 29, y), (ox + 31, y + 3), (ox + 29, y + 6)],
        )


def draw_attack_sword_recovery(surface, i, ox):
    hand = (25, 20 + i * 2)
    tip = (hand[0] + 5, hand[1] + 4 + i)
    pose = player_pose(
        head=(17, 9),
        neck=(16, 13),
        chest=(16, 16),
        near_elbow=(18, 18),
        near_hand=hand,
        far_elbow=(12, 19),
        far_hand=(9, 23),
        near_knee=(19, 31),
        near_foot=(22, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_blade(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))
    line(surface, SLASH, (ox + 27, 12 + i * 2), (ox + 29, 15 + i * 2), 1)


def draw_attack_dagger_windup(surface, i, ox):
    pose = player_pose(
        head=(15, 10),
        neck=(15, 14),
        chest=(15, 17),
        pelvis=(15, 26),
        near_elbow=(14, 20),
        near_hand=(17, 18),
        far_elbow=(19, 19),
        far_hand=(21, 23),
        near_knee=(19, 30),
        near_foot=(21, 38),
        far_knee=(12, 30),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_blade(surface, (ox + 17, 18), (ox + 23, 15))


def draw_attack_dagger_active(surface, i, ox):
    hand = (20 + i * 2, 15 + i * 3)
    tip = (hand[0] + 6, hand[1] - 1)
    pose = player_pose(
        head=(17, 9),
        neck=(16, 13),
        chest=(16, 16),
        pelvis=(16, 25),
        near_elbow=(17, 18),
        near_hand=hand,
        far_elbow=(12, 18),
        far_hand=(9, 22),
        near_knee=(20, 30),
        near_foot=(24, 38),
        far_knee=(13, 31),
        far_foot=(9, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_blade(surface, (ox + hand[0] - 2, hand[1] + 1), (ox + tip[0], tip[1]))
    line(surface, FLASH, (ox + tip[0] - 5, tip[1] + 3), (ox + tip[0], tip[1] + 3), 1)


def draw_attack_dagger_recovery(surface, i, ox):
    hand = (22 - i * 2, 20 + i)
    pose = player_pose(
        head=(16, 9),
        neck=(16, 13),
        chest=(16, 16),
        near_elbow=(17, 19),
        near_hand=hand,
        near_knee=(19, 31),
        near_foot=(22, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_blade(surface, (ox + hand[0], hand[1]), (ox + hand[0] + 4, hand[1]))


def draw_attack_hammer_windup(surface, i, ox):
    pose = player_pose(
        head=(16, 9),
        neck=(16, 13),
        chest=(16, 16),
        pelvis=(16, 26),
        near_elbow=(20, 10),
        near_hand=(22, 5 + i),
        far_elbow=(12, 10),
        far_hand=(14, 6 + i),
        near_knee=(19, 31),
        near_foot=(22, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_hammer(surface, (ox + 22, 5 + i), (ox + 14 + i, i))


def draw_attack_hammer_active(surface, i, ox):
    pose = player_pose(
        head=(17, 10),
        neck=(16, 14),
        chest=(16, 17),
        pelvis=(16, 26),
        near_elbow=(19, 16 + i * 4),
        near_hand=(24, 10 + i * 12),
        far_elbow=(12, 18),
        far_hand=(9, 22),
        near_knee=(20, 30),
        near_foot=(23, 38),
        far_knee=(13, 31),
        far_foot=(9, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_hammer(surface, (ox + 24, 10 + i * 12), (ox + 13, 4 + i * 14), (15, 8))
    if i == 1:
        for arc in range(3):
            line(
                surface,
                SLASH,
                (ox + 26 + arc * 2, 34 - arc * 4),
                (ox + 29 + arc * 2, 38 - arc * 2),
                1,
            )


def draw_attack_hammer_recovery(surface, i, ox):
    pose = player_pose(
        head=(13, 13),
        neck=(14, 16),
        chest=(15, 19),
        pelvis=(16, 26),
        near_elbow=(20, 22),
        near_hand=(24, 24 + i),
        far_elbow=(11, 21),
        far_hand=(9, 26),
        near_knee=(19, 31),
        near_foot=(23, 38),
        far_knee=(13, 31),
        far_foot=(9, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_hammer(surface, (ox + 24, 24 + i), (ox + 12, 30), (15, 7))
    if i < 3:
        dot(surface, FLASH, (ox + 8 + i * 6, 37), 1)
        line(surface, SLASH, (ox + 27, 24 - i * 2), (ox + 30, 22 - i * 2), 1)


def draw_attack_spear_windup(surface, i, ox):
    pose = player_pose(
        head=(14, 8),
        neck=(14, 12),
        chest=(15, 15),
        pelvis=(16, 25),
        near_elbow=(12, 18),
        near_hand=(12 + i * 2, 19),
        far_elbow=(19, 18),
        far_hand=(20, 23),
        near_knee=(19, 30),
        near_foot=(22, 38),
        far_knee=(13, 31),
        far_foot=(9, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_spear(surface, (ox + 3, 20), (ox + 25 + i * 2, 17))


def draw_attack_spear_active(surface, i, ox):
    pose = player_pose(
        head=(20, 9),
        neck=(19, 13),
        chest=(19, 16),
        pelvis=(18, 25),
        near_elbow=(16, 18),
        near_hand=(21, 18 + i),
        far_elbow=(12, 19),
        far_hand=(9, 23),
        near_knee=(23, 29),
        near_foot=(26, 36),
        far_knee=(13, 30),
        far_foot=(9, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_spear(surface, (ox + 5, 19), (ox + 31, 17 + i))
    line(surface, SLASH, (ox + 2, 17 + i), (ox + 9, 17 + i), 1)


def draw_attack_spear_recovery(surface, i, ox):
    pose = player_pose(
        head=(17, 9),
        neck=(16, 13),
        chest=(16, 16),
        near_elbow=(15, 18),
        near_hand=(19, 19),
        near_knee=(20, 30),
        near_foot=(23, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_spear(surface, (ox + 7, 20), (ox + 29 - i * 3, 18))


def draw_attack_staff_windup(surface, i, ox):
    pose = player_pose(
        head=(16, 8),
        neck=(16, 12),
        chest=(16, 15),
        near_elbow=(18, 17),
        near_hand=(22, 20),
        far_elbow=(12, 18),
        far_hand=(10, 23),
        near_knee=(18, 30),
        near_foot=(20, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_staff(
        surface,
        (ox + 25, 8),
        (ox + 25, 36),
        orb_center=(ox + 26, 6),
        orb_radius=2 + i,
    )


def draw_attack_staff_active(surface, i, ox):
    pose = player_pose(
        head=(18, 8),
        neck=(17, 12),
        chest=(17, 15),
        near_elbow=(19, 16),
        near_hand=(23 + i, 17),
        far_elbow=(12, 18),
        far_hand=(9, 22),
        near_knee=(21, 30),
        near_foot=(24, 38),
        far_knee=(13, 31),
        far_foot=(9, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_staff(
        surface,
        (ox + 28 + i, 8),
        (ox + 20, 32),
        orb_center=(ox + 29 + i, 10),
        orb_radius=3 + i,
    )
    dot(surface, FLASH, (ox + 30, 12), 1)


def draw_attack_staff_recovery(surface, i, ox):
    pose = player_pose(
        head=(16, 9),
        neck=(16, 13),
        chest=(16, 16),
        near_elbow=(18, 17),
        near_hand=(22, 20),
        near_knee=(18, 31),
        near_foot=(20, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    draw_staff(
        surface,
        (ox + 25, 9 + i),
        (ox + 25, 36),
        orb_center=(ox + 26, 7 + i),
        orb_radius=max(1, 3 - i // 2),
    )


def draw_parry(surface, i, ox):
    pose = player_pose(
        head=(16, 8),
        neck=(16, 12),
        chest=(15, 15),
        near_elbow=(20, 16 - i),
        near_hand=(24, 12 - i),
        far_elbow=(11, 19),
        far_hand=(8, 23),
        near_knee=(18, 30),
        near_foot=(20, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    line(surface, FLASH, (ox + 24, 7 - i), (ox + 24, 18), 2)
    line(surface, SLASH, (ox + 22, 6 - i), (ox + 22, 19), 1)


def draw_skill(surface, i, ox):
    pose = player_pose(
        near_elbow=(21, 13),
        near_hand=(24, 9),
        far_elbow=(11, 13),
        far_hand=(8, 9),
        near_knee=(18, 30),
        near_foot=(21, 38),
        far_knee=(13, 30),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose)
    pygame.draw.circle(surface, EMBER, (ox + 26, 14), 3 + i * 3, 1)
    pygame.draw.circle(surface, SLASH, (ox + 26, 14), 1 + i, 1)


def draw_hurt(surface, i, ox):
    pose = player_pose(
        head=(13, 9 + i),
        neck=(14, 13),
        chest=(14, 16),
        near_elbow=(18, 12),
        near_hand=(21, 8 - i),
        far_elbow=(9, 13),
        far_hand=(6, 10),
        near_knee=(19, 30),
        near_foot=(21, 37),
        far_knee=(12, 31),
        far_foot=(10, 38),
    )
    draw_player_skeleton(surface, ox, pose, color=FLASH, eye=False)


def draw_death(surface, i, ox):
    poses = [
        player_pose(
            head=(14, 13),
            neck=(14, 17),
            chest=(14, 20),
            pelvis=(16, 27),
            near_elbow=(10, 22),
            near_hand=(8, 27),
            far_elbow=(20, 23),
            far_hand=(22, 28),
            near_knee=(20, 31),
            near_foot=(21, 38),
            far_knee=(12, 31),
            far_foot=(11, 38),
        ),
        player_pose(
            head=(23, 24),
            neck=(21, 27),
            chest=(18, 30),
            pelvis=(16, 33),
            near_elbow=(16, 26),
            near_hand=(13, 29),
            far_elbow=(22, 30),
            far_hand=(25, 32),
            near_knee=(12, 34),
            near_foot=(9, 36),
            far_knee=(14, 35),
            far_foot=(11, 37),
        ),
        player_pose(
            head=(25, 33),
            neck=(22, 33),
            chest=(19, 34),
            pelvis=(14, 34),
            near_elbow=(21, 31),
            near_hand=(24, 33),
            far_elbow=(18, 36),
            far_hand=(15, 37),
            near_knee=(11, 35),
            near_foot=(8, 36),
            far_knee=(13, 36),
            far_foot=(9, 37),
        ),
        player_pose(
            head=(25, 34),
            neck=(22, 34),
            chest=(19, 34),
            pelvis=(14, 34),
            near_elbow=(20, 32),
            near_hand=(23, 34),
            far_elbow=(17, 36),
            far_hand=(14, 37),
            near_knee=(11, 35),
            near_foot=(8, 36),
            far_knee=(13, 36),
            far_foot=(9, 37),
        ),
    ]
    color = SKIN if i < 2 else SKIN_DARK
    draw_player_skeleton(surface, ox, poses[i], color=color, eye=i == 0)
    if i == 3:
        dot(surface, EMBER, (ox + 16, 37), 1)


# --- enemies ---------------------------------------------------------------


def crawler_legs(body_y, swing=0.0):
    near = [
        ((6, body_y), (4 - 2 * swing, body_y + 7), (3 - 4 * swing, 35)),
        ((10, body_y - 1), (12 + 2 * swing, body_y + 7), (14 + 3 * swing, 35)),
        (
            (14, body_y - 2),
            (17 + 3 * swing, body_y + 6),
            (20 + 4 * swing, 35 - max(0.0, swing) * 2),
        ),
    ]
    far = [
        ((8, body_y), (8 + 2 * swing, body_y + 8), (7 + 4 * swing, 35)),
        ((11, body_y - 1), (11 - 2 * swing, body_y + 8), (12 - 3 * swing, 35)),
        (
            (13, body_y - 2),
            (15 - 3 * swing, body_y + 7),
            (18 - 4 * swing, 35 - max(0.0, -swing) * 2),
        ),
    ]
    return near, far


def draw_crawler_skeleton(
    surface,
    ox,
    body_y=20,
    head_x=19,
    swing=0.0,
    eye_color=EMBER,
    legs=None,
):
    near, far = legs or crawler_legs(body_y, swing)
    for hip, knee, foot in far:
        line(surface, CRAWLER_DARK, (ox + hip[0], hip[1]), (ox + knee[0], knee[1]))
        line(surface, CRAWLER_DARK, (ox + knee[0], knee[1]), (ox + foot[0], foot[1]))
    line(surface, CRAWLER, (ox + 5, body_y), (ox + 15, body_y - 2), 2)
    line(
        surface,
        CRAWLER_DARK,
        (ox + 6, body_y + 1),
        (ox + 14, body_y - 1),
        1,
    )
    for hip, knee, foot in near:
        line(surface, CRAWLER, (ox + hip[0], hip[1]), (ox + knee[0], knee[1]))
        line(surface, CRAWLER, (ox + knee[0], knee[1]), (ox + foot[0], foot[1]))
    head = (ox + head_x, body_y - 3)
    pygame.draw.circle(surface, CRAWLER, (round(head[0]), round(head[1])), 3, 2)
    dot(surface, eye_color, (head[0] + 2, head[1]), 1)
    dot(surface, EMBER, (ox + 9, body_y - 1), 1)


def draw_crawler_idle(surface, i, ox):
    body_y = 20 + (0, -1)[i]
    draw_crawler_skeleton(surface, ox, body_y=body_y, head_x=19)


def draw_crawler_walk(surface, i, ox):
    swing = math.sin(i / 4 * math.tau)
    body_y = 20 + (-1 if abs(swing) > 0.6 else 0)
    draw_crawler_skeleton(surface, ox, body_y=body_y, head_x=19, swing=swing)


def draw_crawler_windup(surface, i, ox):
    legs = (
        [
            ((6, 22), (4, 28), (3, 35)),
            ((10, 21), (12, 28), (14, 35)),
            ((14, 20), (19, 27), (22, 34)),
        ],
        [
            ((8, 22), (8, 29), (7, 35)),
            ((11, 21), (10, 29), (11, 35)),
            ((13, 20), (16, 28), (19, 34)),
        ],
    )
    draw_crawler_skeleton(
        surface,
        ox,
        body_y=23,
        head_x=20,
        eye_color=SLASH,
        legs=legs,
    )
    line(surface, EMBER, (ox + 16, 16), (ox + 18 + i, 14), 1)


def draw_crawler_active(surface, i, ox):
    legs = (
        [
            ((6, 20), (2, 27), (1, 35)),
            ((10, 19), (13, 26), (15, 35)),
            ((14, 18), (19, 25), (23, 33)),
        ],
        [
            ((8, 20), (7, 28), (6, 35)),
            ((11, 19), (12, 27), (13, 35)),
            ((13, 18), (16, 26), (20, 33)),
        ],
    )
    draw_crawler_skeleton(
        surface,
        ox,
        body_y=19,
        head_x=20 + i,
        eye_color=SLASH,
        legs=legs,
    )
    line(surface, SLASH, (ox + 21 + i, 17), (ox + 23 + i, 19), 1)


def draw_crawler_recovery(surface, i, ox):
    draw_crawler_skeleton(surface, ox, body_y=21, head_x=19)


def draw_crawler_stagger(surface, i, ox):
    legs = (
        [
            ((6, 24), (3, 29), (2, 35)),
            ((10, 23), (12, 29), (14, 35)),
            ((14, 22), (18, 28), (21, 34)),
        ],
        [
            ((8, 24), (7, 30), (6, 35)),
            ((11, 23), (11, 30), (12, 35)),
            ((13, 22), (15, 29), (18, 34)),
        ],
    )
    draw_crawler_skeleton(
        surface,
        ox,
        body_y=24 + i,
        head_x=18,
        eye_color=(200, 150, 60),
        legs=legs,
    )


def draw_crawler_death(surface, i, ox):
    body_y = 30 + i
    head_x = 18
    legs = (
        [
            ((6, body_y), (9, body_y + 3), (6, 34 + i)),
            ((10, body_y - 1), (13, body_y + 2), (11, 35)),
            ((14, body_y - 2), (16, body_y + 1), (15, 35)),
        ],
        [
            ((8, body_y), (10, body_y + 4), (8, 34 + i)),
            ((11, body_y - 1), (12, body_y + 3), (12, 35)),
            ((13, body_y - 2), (14, body_y + 2), (14, 35)),
        ],
    )
    draw_crawler_skeleton(
        surface,
        ox,
        body_y=body_y,
        head_x=head_x,
        eye_color=(200, 150, 60),
        legs=legs,
    )
    if i < 2:
        dot(surface, EMBER, (ox + 16, body_y - 4), 1)


def archer_pose(**overrides):
    pose = {
        "head": (16, 6),
        "neck": (16, 10),
        "chest": (16, 13),
        "pelvis": (16, 22),
        "near_elbow": (12, 16),
        "near_hand": (11, 21),
        "far_elbow": (19, 16),
        "far_hand": (20, 21),
        "near_knee": (15, 28),
        "near_foot": (14, 35),
        "far_knee": (17, 28),
        "far_foot": (18, 35),
    }
    pose.update(overrides)
    return pose


def draw_archer_skeleton(surface, ox, pose, eye=True):
    def pt(name):
        x, y = pose[name]
        return (ox + x, y)

    head = pt("head")
    neck = pt("neck")
    chest = pt("chest")
    pelvis = pt("pelvis")
    near_elbow = pt("near_elbow")
    near_hand = pt("near_hand")
    far_elbow = pt("far_elbow")
    far_hand = pt("far_hand")
    near_knee = pt("near_knee")
    near_foot = pt("near_foot")
    far_knee = pt("far_knee")
    far_foot = pt("far_foot")

    line(surface, ARCHER_DARK, chest, far_elbow)
    line(surface, ARCHER_DARK, far_elbow, far_hand)
    line(surface, ARCHER_DARK, pelvis, far_knee)
    line(surface, ARCHER_DARK, far_knee, far_foot)

    line(surface, ARCHER, neck, pelvis, 2)
    line(surface, ARCHER, (chest[0] - 3, chest[1]), (chest[0] + 3, chest[1]))
    line(surface, ARCHER, (pelvis[0] - 2, pelvis[1]), (pelvis[0] + 2, pelvis[1]))
    line(surface, ARCHER, chest, near_elbow)
    line(surface, ARCHER, near_elbow, near_hand)
    line(surface, ARCHER, pelvis, near_knee)
    line(surface, ARCHER, near_knee, near_foot)

    line(surface, ARCHER_DARK, (chest[0] - 2, chest[1]), (chest[0] + 2, chest[1]), 1)
    pygame.draw.circle(surface, ARCHER, (round(head[0]), round(head[1])), 3, 2)
    if eye:
        dot(surface, EMBER, (head[0] + 1, head[1] - 1), 1)


def draw_bow(surface, ox, tension=0, arrow=False):
    x = ox + 22
    line(surface, BOW, (x, 7), (x, 24), 2)
    line(surface, BOW, (x, 7), (x - 2, 10), 1)
    line(surface, BOW, (x, 24), (x - 2, 21), 1)
    string_x = x - tension
    line(surface, FLASH, (x, 7), (string_x, 15), 1)
    line(surface, FLASH, (string_x, 15), (x, 24), 1)
    if arrow:
        line(surface, SLASH, (string_x, 15), (x + 5, 15), 2)
        pygame.draw.polygon(
            surface,
            FLASH,
            [(x + 5, 15), (x + 2, 13), (x + 2, 17)],
        )


def draw_archer_idle(surface, i, ox):
    bob = (0, -1)[i]
    pose = archer_pose(
        head=(16, 6 + bob),
        neck=(16, 10 + bob),
        chest=(16, 13 + bob),
        pelvis=(16, 22 + bob),
        near_elbow=(14, 16 + bob),
        near_hand=(18, 16 + bob),
        far_elbow=(19, 16 + bob),
        far_hand=(21, 16 + bob),
    )
    draw_archer_skeleton(surface, ox, pose)
    draw_bow(surface, ox)


def draw_archer_walk(surface, i, ox):
    swing = math.sin(i / 4 * math.tau)
    bob = -1 if abs(swing) > 0.6 else 0
    pose = archer_pose(
        head=(16, 6 + bob),
        neck=(16, 10 + bob),
        chest=(16, 13 + bob),
        pelvis=(16, 22 + bob),
        near_elbow=(14, 16 + bob),
        near_hand=(18, 16 + bob),
        near_knee=(16 + 3 * swing, 28 + bob),
        near_foot=(16 + 6 * swing, 35 - max(0.0, swing) * 2),
        far_knee=(16 - 3 * swing, 28 + bob),
        far_foot=(16 - 6 * swing, 35 - max(0.0, -swing) * 2),
    )
    draw_archer_skeleton(surface, ox, pose)
    draw_bow(surface, ox)


def draw_archer_windup(surface, i, ox):
    pose = archer_pose(
        near_elbow=(15, 16),
        near_hand=(18 - i, 15),
        far_elbow=(19, 14),
        far_hand=(21, 14),
    )
    draw_archer_skeleton(surface, ox, pose)
    draw_bow(surface, ox, tension=2 + i)
    dot(surface, EMBER, (ox + 20, 15), 1)


def draw_archer_active(surface, i, ox):
    pose = archer_pose(
        near_elbow=(15, 16),
        near_hand=(21, 15),
        far_elbow=(19, 15),
        far_hand=(22, 15),
    )
    draw_archer_skeleton(surface, ox, pose)
    draw_bow(surface, ox, tension=1 - i, arrow=True)


def draw_archer_recovery(surface, i, ox):
    pose = archer_pose(
        near_elbow=(14, 16),
        near_hand=(18, 16),
    )
    draw_archer_skeleton(surface, ox, pose)
    draw_bow(surface, ox)


def draw_archer_stagger(surface, i, ox):
    pose = archer_pose(
        head=(14, 7 + i),
        neck=(15, 11 + i),
        chest=(15, 14 + i),
        near_elbow=(12, 18),
        near_hand=(10, 22),
        far_elbow=(18, 18 + i),
        far_hand=(20, 23),
        near_foot=(13, 35),
        far_foot=(17, 35),
    )
    draw_archer_skeleton(surface, ox, pose, eye=False)
    line(surface, BOW, (ox + 22, 16), (ox + 22, 33), 1)


def draw_archer_death(surface, i, ox):
    poses = [
        archer_pose(
            head=(14, 10),
            neck=(15, 13),
            chest=(15, 16),
            pelvis=(16, 24),
            near_knee=(19, 30),
            near_foot=(20, 35),
            far_knee=(13, 30),
            far_foot=(12, 35),
        ),
        archer_pose(
            head=(12, 22),
            neck=(14, 26),
            chest=(15, 29),
            pelvis=(17, 32),
            near_knee=(20, 33),
            near_foot=(22, 35),
            far_knee=(14, 34),
            far_foot=(13, 35),
        ),
        archer_pose(
            head=(9, 32),
            neck=(13, 33),
            chest=(16, 33),
            pelvis=(19, 33),
            near_elbow=(17, 31),
            near_hand=(20, 33),
            far_elbow=(13, 35),
            far_hand=(10, 35),
            near_knee=(21, 35),
            near_foot=(22, 35),
            far_knee=(18, 35),
            far_foot=(16, 35),
        ),
    ]
    draw_archer_skeleton(surface, ox, poses[i], eye=i < 2)
    if i < 2:
        dot(surface, EMBER, (ox + 16, poses[i]["chest"][1] - 4), 1)
    else:
        line(surface, BOW, (ox + 20, 30), (ox + 22, 35), 1)


def main() -> None:
    pygame.init()
    player = {
        "idle": (4, draw_idle),
        "run": (6, draw_run),
        "jump": (1, draw_jump),
        "fall": (2, draw_fall),
        "dash": (3, draw_dash),
        "attack_sword_windup": (2, draw_attack_sword_windup),
        "attack_sword_active": (4, draw_attack_sword_active),
        "attack_sword_recovery": (4, draw_attack_sword_recovery),
        "attack_dagger_windup": (1, draw_attack_dagger_windup),
        "attack_dagger_active": (3, draw_attack_dagger_active),
        "attack_dagger_recovery": (3, draw_attack_dagger_recovery),
        "attack_hammer_windup": (3, draw_attack_hammer_windup),
        "attack_hammer_active": (2, draw_attack_hammer_active),
        "attack_hammer_recovery": (6, draw_attack_hammer_recovery),
        "attack_spear_windup": (2, draw_attack_spear_windup),
        "attack_spear_active": (2, draw_attack_spear_active),
        "attack_spear_recovery": (4, draw_attack_spear_recovery),
        "attack_staff_windup": (3, draw_attack_staff_windup),
        "attack_staff_active": (3, draw_attack_staff_active),
        "attack_staff_recovery": (4, draw_attack_staff_recovery),
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