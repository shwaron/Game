"""Generate placeholder pixel sprites for the wuxia swordsman and inn spirits.

Player art is built from the joint-pose rig but rendered as a robed wuxia
character. Enemies stay on the stick-figure rig; wine imps carry a gourd and
paper runners wear a talisman so their silhouettes read at a glance. Replace
generated files with real art using the same paths/frame counts.
"""

import math
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "sprites"

PLAYER_CELL = (64, 40)
PLAYER_ART_DX = 16
ENEMY_CELL = (24, 36)

SKIN = (232, 213, 176)
SKIN_DARK = (190, 168, 138)
EMBER = (255, 154, 60)
EYE = (30, 26, 40)
SLASH = (255, 210, 122)
FLASH = (255, 245, 230)
CRAWLER = (176, 112, 70)
CRAWLER_DARK = (112, 68, 44)
ARCHER = (226, 210, 176)
ARCHER_DARK = (156, 138, 112)
BOW = (78, 60, 44)
TALISMAN = (176, 58, 48)

ROBE = (60, 54, 76)
ROBE_DARK = (38, 33, 50)
ROBE_LIGHT = (100, 92, 122)
BOOT = (28, 24, 38)
SILVER = (206, 208, 220)
SILVER_DIM = (148, 150, 166)
BELT = (40, 34, 30)
BELT_METAL = (190, 174, 120)
STEEL = (214, 218, 228)
HAIR = (30, 26, 38)
HAIR_HI = (78, 68, 92)
IRON = (122, 118, 138)
IRON_DARK = (84, 80, 98)


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


def player_painter(painter):
    def wrapped(surface, index, ox):
        painter(surface, index, ox + PLAYER_ART_DX)

    return wrapped


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


def draw_player_character(
    surface, ox, pose, ghost=False, flash=False, dim=False, alpha=255
):
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
    hair_dx, hair_dy = pose.get("hair", (-1, 0))
    skirt_dx = pose.get("skirt", 0.0)

    if dim:
        layer = pygame.Surface(PLAYER_CELL, pygame.SRCALPHA)
        draw_player_character(layer, 0, pose)
        layer.set_alpha(alpha)
        surface.blit(layer, (ox, 0))
        return

    if ghost or flash:
        if ghost:
            silhouette = (*ROBE_LIGHT, 50)
            head_color = (*SKIN, 40)
        else:
            silhouette = FLASH
            head_color = FLASH
        line(surface, silhouette, chest, near_elbow, 3)
        line(surface, silhouette, near_elbow, near_hand, 4)
        line(surface, silhouette, pelvis, near_knee, 3)
        line(surface, silhouette, near_knee, near_foot, 3)
        pygame.draw.polygon(
            surface,
            silhouette,
            [
                (chest[0] - 5, chest[1] - 1),
                (chest[0] + 5, chest[1] - 1),
                (pelvis[0] + 4, pelvis[1] + 10),
                (pelvis[0] - 6, pelvis[1] + 10),
            ],
        )
        pygame.draw.circle(
            surface, head_color, (round(head[0]), round(head[1])), 3
        )
        return

    # ponytail flows behind the body
    root = (head[0] - 2, head[1] - 3)
    mid = (root[0] - 4 + hair_dx * 0.4, root[1] + 5 + hair_dy * 0.4)
    tip = (root[0] - 6 + hair_dx, root[1] + 11 + hair_dy)
    line(surface, HAIR, root, mid, 2)
    line(surface, HAIR, mid, tip, 2)
    line(surface, HAIR_HI, (root[0] - 1, root[1] + 1), mid, 1)
    dot(surface, SILVER, root, 1)

    # far limbs
    line(surface, ROBE_DARK, chest, far_elbow, 3)
    line(surface, ROBE_DARK, far_elbow, far_hand, 4)
    dot(surface, SKIN_DARK, far_hand, 1)
    line(surface, ROBE_DARK, pelvis, far_knee, 3)
    line(surface, BOOT, far_knee, far_foot, 3)
    pygame.draw.rect(
        surface, BOOT, (round(far_foot[0]) - 2, round(far_foot[1]) - 1, 4, 3)
    )

    # long robe skirt
    waist_y = pelvis[1] - 1
    hem_y = 38
    hem_center = pelvis[0] + skirt_dx
    pygame.draw.polygon(
        surface,
        ROBE,
        [
            (round(pelvis[0] - 5), round(waist_y)),
            (round(pelvis[0] + 5), round(waist_y)),
            (round(hem_center + 6), hem_y),
            (round(hem_center - 7), hem_y),
        ],
    )
    line(
        surface,
        ROBE_DARK,
        (pelvis[0] + 1, waist_y + 2),
        (hem_center + 2, hem_y - 1),
        1,
    )
    line(
        surface,
        SILVER_DIM,
        (hem_center - 6, hem_y - 1),
        (hem_center + 5, hem_y - 1),
        1,
    )
    line(
        surface,
        ROBE_LIGHT,
        (pelvis[0] + 4, waist_y + 1),
        (hem_center + 5, hem_y - 2),
        1,
    )

    # torso robe with silver shoulder embroidery
    pygame.draw.polygon(
        surface,
        ROBE,
        [
            (round(chest[0] - 5), round(chest[1] - 1)),
            (round(chest[0] + 5), round(chest[1] - 1)),
            (round(pelvis[0] + 4), round(pelvis[1] - 2)),
            (round(pelvis[0] - 4), round(pelvis[1] - 2)),
        ],
    )
    line(
        surface,
        ROBE_LIGHT,
        (chest[0] + 4, chest[1]),
        (pelvis[0] + 3, pelvis[1] - 3),
        1,
    )
    line(surface, SILVER_DIM, (neck[0] - 2, neck[1]), (chest[0], chest[1] + 4), 1)
    line(surface, SILVER_DIM, (neck[0] + 2, neck[1]), (chest[0] + 1, chest[1] + 5), 1)
    line(surface, SILVER, (chest[0] - 5, chest[1] - 1), (chest[0] - 2, chest[1] - 2), 1)
    line(surface, SILVER_DIM, (chest[0] - 5, chest[1] + 1), (chest[0] - 3, chest[1]), 1)
    line(surface, SILVER, (chest[0] + 5, chest[1] - 1), (chest[0] + 2, chest[1] - 2), 1)
    line(surface, SILVER_DIM, (chest[0] + 5, chest[1] + 1), (chest[0] + 3, chest[1]), 1)
    pygame.draw.rect(
        surface,
        SILVER_DIM,
        (round(chest[0]) - 7, round(chest[1]) - 1, 3, 2),
    )
    pygame.draw.rect(
        surface,
        SILVER,
        (round(chest[0]) + 4, round(chest[1]) - 1, 3, 2),
    )

    # belt with metal buckle
    by = pelvis[1] - 2
    pygame.draw.rect(surface, BELT, (round(pelvis[0] - 5), round(by), 10, 3))
    pygame.draw.rect(surface, BELT_METAL, (round(pelvis[0] - 2), round(by), 4, 2))
    dot(surface, EMBER, (pelvis[0], by + 1), 1)

    # sheathed sword hangs at the far hip
    sheath_hip = (pelvis[0] - 4, pelvis[1] - 1)
    sheath_tip = (pelvis[0] - 11 + skirt_dx * 0.4, pelvis[1] + 10)
    line(surface, (48, 44, 62), sheath_hip, sheath_tip, 2)
    dx = sheath_tip[0] - sheath_hip[0]
    dy = sheath_tip[1] - sheath_hip[1]
    length = math.hypot(dx, dy) or 1.0
    px, py = -dy / length, dx / length
    line(
        surface,
        SILVER_DIM,
        (sheath_tip[0] - px * 1.5, sheath_tip[1] - py * 1.5),
        (sheath_tip[0] + px * 1.5, sheath_tip[1] + py * 1.5),
        1,
    )
    line(
        surface,
        BELT_METAL,
        (sheath_hip[0] + 2, sheath_hip[1]),
        (sheath_hip[0] - 2, sheath_hip[1] - 5),
        2,
    )
    dot(surface, SILVER, (sheath_hip[0] - 2, sheath_hip[1] - 5), 1)

    # near leg and boot
    line(surface, ROBE_DARK, pelvis, near_knee, 3)
    line(surface, BOOT, near_knee, near_foot, 3)
    pygame.draw.rect(
        surface, BOOT, (round(near_foot[0]) - 2, round(near_foot[1]) - 1, 5, 3)
    )
    line(
        surface,
        SILVER_DIM,
        (near_foot[0] - 2, near_foot[1] + 1),
        (near_foot[0] + 2, near_foot[1] + 1),
        1,
    )

    # near wide sleeve
    line(surface, ROBE, chest, near_elbow, 4)
    line(surface, ROBE, near_elbow, near_hand, 5)
    line(
        surface,
        SILVER_DIM,
        (near_hand[0] - 1, near_hand[1] - 2),
        (near_hand[0] + 1, near_hand[1] + 1),
        1,
    )
    dot(surface, SKIN, near_hand, 1)

    # head, hair and topknot
    line(surface, SKIN_DARK, (neck[0], neck[1] - 2), (neck[0], neck[1] + 1), 3)
    pygame.draw.rect(
        surface, SKIN, (round(head[0]) - 2, round(head[1]) - 3, 6, 7)
    )
    pygame.draw.rect(
        surface, HAIR, (round(head[0]) - 3, round(head[1]) - 4, 7, 3)
    )
    pygame.draw.rect(
        surface, HAIR, (round(head[0]) - 4, round(head[1]) - 2, 2, 5)
    )
    pygame.draw.rect(
        surface, HAIR, (round(head[0]) - 3, round(head[1]) + 1, 2, 3)
    )
    line(surface, HAIR_HI, (head[0] - 2, head[1] - 3), (head[0] + 2, head[1] - 3), 1)
    pygame.draw.rect(
        surface, HAIR, (round(head[0]) - 1, round(head[1]) - 7, 3, 3)
    )
    line(surface, SILVER, (head[0] - 2, head[1] - 6), (head[0] + 3, head[1] - 6), 1)
    dot(surface, EYE, (head[0] + 2, head[1] - 1), 1)


def draw_blade(surface, hand, tip):
    dx, dy = tip[0] - hand[0], tip[1] - hand[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux

    line(
        surface,
        BOW,
        (hand[0] - ux * 3, hand[1] - uy * 3),
        (hand[0] + ux * 1, hand[1] + uy * 1),
        2,
    )
    dot(surface, BELT_METAL, (hand[0] - ux * 3, hand[1] - uy * 3), 1)
    gx, gy = hand[0] + ux * 2, hand[1] + uy * 2
    line(
        surface,
        SILVER,
        (gx - px * 2.5, gy - py * 2.5),
        (gx + px * 2.5, gy + py * 2.5),
        2,
    )
    base = (gx + ux * 1.5, gy + uy * 1.5)
    outline = [
        (base[0] - px * 2.2, base[1] - py * 2.2),
        (base[0] + px * 2.2, base[1] + py * 2.2),
        (tip[0] + ux * 1.2, tip[1] + uy * 1.2),
    ]
    pygame.draw.polygon(surface, (18, 16, 24), outline)
    blade = [
        (base[0] - px * 1.2, base[1] - py * 1.2),
        (base[0] + px * 1.2, base[1] + py * 1.2),
        (tip[0], tip[1]),
    ]
    pygame.draw.polygon(surface, STEEL, blade)
    line(surface, FLASH, base, (tip[0] - ux, tip[1] - uy), 1)
    dot(surface, EMBER, (hand[0], hand[1] + 2), 1)


def draw_curved_blade(surface, hand, tip, bend=3.0):
    dx, dy = tip[0] - hand[0], tip[1] - hand[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    line(
        surface,
        BOW,
        (hand[0] - ux * 4, hand[1] - uy * 4),
        (hand[0] + ux * 1, hand[1] + uy * 1),
        2,
    )
    dot(surface, BELT_METAL, (hand[0] - ux * 4, hand[1] - uy * 4), 1)
    gx, gy = hand[0] + ux * 2, hand[1] + uy * 2
    line(
        surface,
        BELT_METAL,
        (gx - px * 2, gy - py * 2),
        (gx + px * 2, gy + py * 2),
        2,
    )
    base = (gx + ux * 1.5, gy + uy * 1.5)
    ctrl = (
        (base[0] + tip[0]) / 2 + px * bend,
        (base[1] + tip[1]) / 2 + py * bend,
    )
    spine = []
    edge = []
    for step in range(7):
        t = step / 6
        mt = 1 - t
        x = mt * mt * base[0] + 2 * mt * t * ctrl[0] + t * t * tip[0]
        y = mt * mt * base[1] + 2 * mt * t * ctrl[1] + t * t * tip[1]
        width = 2.0 * (1 - t * 0.75)
        spine.append((x - px * width * 0.4, y - py * width * 0.4))
        edge.append((x + px * width, y + py * width))
    pygame.draw.polygon(surface, (18, 16, 24), spine + edge[::-1])
    pygame.draw.polygon(surface, STEEL, spine + edge[::-1])
    line(surface, FLASH, spine[0], spine[-2], 1)
    dot(surface, EMBER, (hand[0], hand[1] + 2), 1)


def draw_longsword(surface, hand, tip):
    dx, dy = tip[0] - hand[0], tip[1] - hand[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    line(
        surface,
        BOW,
        (hand[0] - ux * 4, hand[1] - uy * 4),
        (hand[0] + ux * 1, hand[1] + uy * 1),
        2,
    )
    dot(surface, BELT_METAL, (hand[0] - ux * 4, hand[1] - uy * 4), 1)
    gx, gy = hand[0] + ux * 2, hand[1] + uy * 2
    line(
        surface,
        SILVER,
        (gx - px * 3.5, gy - py * 3.5),
        (gx + px * 3.5, gy + py * 3.5),
        2,
    )
    base = (gx + ux * 1.5, gy + uy * 1.5)
    outline = [
        (base[0] - px * 2.4, base[1] - py * 2.4),
        (base[0] + px * 2.4, base[1] + py * 2.4),
        (tip[0] + ux * 1.2, tip[1] + uy * 1.2),
    ]
    pygame.draw.polygon(surface, (18, 16, 24), outline)
    blade = [
        (base[0] - px * 1.4, base[1] - py * 1.4),
        (base[0] + px * 1.4, base[1] + py * 1.4),
        (tip[0], tip[1]),
    ]
    pygame.draw.polygon(surface, STEEL, blade)
    line(surface, FLASH, base, (tip[0] - ux, tip[1] - uy), 1)
    dot(surface, EMBER, (hand[0], hand[1] + 2), 1)


def draw_zhanmadao(surface, hand, tip):
    dx, dy = tip[0] - hand[0], tip[1] - hand[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    line(
        surface,
        BOW,
        (hand[0] - ux * 9, hand[1] - uy * 9),
        (hand[0] + ux * 2, hand[1] + uy * 2),
        2,
    )
    dot(surface, IRON, (hand[0] - ux * 9, hand[1] - uy * 9), 1)
    line(surface, TALISMAN, (hand[0] - ux * 6, hand[1] - uy * 6), (hand[0] - ux * 4, hand[1] - uy * 4), 1)
    gx, gy = hand[0] + ux * 3, hand[1] + uy * 3
    line(
        surface,
        IRON,
        (gx - px * 2.5, gy - py * 2.5),
        (gx + px * 2.5, gy + py * 2.5),
        2,
    )
    base = (gx + ux * 1.5, gy + uy * 1.5)
    blade_len = length - 6
    wide = 3.2
    outline = [
        (base[0] - px * 1.2, base[1] - py * 1.2),
        (base[0] + px * wide, base[1] + py * wide),
        (base[0] + ux * blade_len * 0.7 + px * wide * 0.9, base[1] + uy * blade_len * 0.7 + py * wide * 0.9),
        (tip[0] + ux * 1.5, tip[1] + uy * 1.5),
        (base[0] + ux * blade_len * 0.5 - px * 1.0, base[1] + uy * blade_len * 0.5 - py * 1.0),
    ]
    pygame.draw.polygon(surface, (18, 16, 24), outline)
    inner = [
        (base[0] - px * 0.6, base[1] - py * 0.6),
        (base[0] + px * (wide - 1), base[1] + py * (wide - 1)),
        (base[0] + ux * blade_len * 0.7 + px * (wide - 1) * 0.9, base[1] + uy * blade_len * 0.7 + py * (wide - 1) * 0.9),
        (tip[0], tip[1]),
        (base[0] + ux * blade_len * 0.5 - px * 0.4, base[1] + uy * blade_len * 0.5 - py * 0.4),
    ]
    pygame.draw.polygon(surface, STEEL, inner)
    line(surface, FLASH, base, (tip[0] - ux * 2, tip[1] - uy * 2), 1)
    dot(surface, EMBER, (hand[0], hand[1] + 2), 1)


def draw_spear(surface, tail, tip):
    line(surface, BOW, tail, tip, 2)
    dx, dy = tip[0] - tail[0], tip[1] - tail[1]
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    base = (tip[0] - ux * 4, tip[1] - uy * 4)
    pygame.draw.polygon(
        surface,
        STEEL,
        [
            (round(tip[0]), round(tip[1])),
            (round(base[0] - uy * 2), round(base[1] + ux * 2)),
            (round(base[0] + uy * 2), round(base[1] - ux * 2)),
        ],
    )
    line(surface, FLASH, base, tip, 1)
    line(
        surface,
        SILVER,
        (round(base[0] - uy * 2), round(base[1] + ux * 2)),
        (round(base[0] + uy * 2), round(base[1] - ux * 2)),
        1,
    )


def draw_hammer(surface, hand, head_topleft, size=(14, 7)):
    x, y = head_topleft
    line(surface, BOW, hand, (x + size[0] // 2, y + size[1] - 1), 2)
    pygame.draw.rect(surface, IRON, (x, y, size[0], size[1]))
    pygame.draw.rect(surface, IRON_DARK, (x, y + size[1] - 2, size[0], 2))
    pygame.draw.rect(surface, SILVER, (x + 2, y + 2, 3, 2))


def draw_staff(surface, top, bottom, orb_center=None, orb_radius=0):
    line(surface, BOW, top, bottom, 2)
    if orb_center and orb_radius > 0:
        dot(surface, SILVER, (top[0], top[1] + 1), 1)
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
        hair=(sway * 0.5, 0),
        skirt=sway * 0.6,
    )
    draw_player_character(surface, ox, pose)


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
        hair=(-lean - swing * 0.6, 0),
        skirt=-swing * 2,
    )
    draw_player_character(surface, ox, pose)


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
        hair=(-1, 1),
        skirt=1,
    )
    draw_player_character(surface, ox, pose)


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
        hair=(-1, -1),
        skirt=sway,
    )
    draw_player_character(surface, ox, pose)


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
        hair=(-2, 0),
        skirt=-3,
    )
    for ghost in range(1, i + 1):
        draw_player_character(surface, ox - ghost * 5, ghost_pose, ghost=True)
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
        hair=(-3, 0),
        skirt=-4,
    )
    draw_player_character(surface, ox, pose)
    line(surface, EMBER, (ox + 2, 14 + i * 3), (ox + 6, 14 + i * 3), 2)


def draw_attack_tachi_windup(surface, i, ox):
    hand = (14 + i, 18 - i)
    tip = (hand[0] - 6, hand[1] - 8)
    pose = player_pose(
        head=(15, 9),
        neck=(15, 13),
        chest=(15, 16),
        pelvis=(15, 26),
        near_elbow=(12, 17),
        near_hand=hand,
        far_elbow=(19, 19),
        far_hand=(21, 23),
        near_knee=(19, 30),
        near_foot=(22, 38),
        far_knee=(12, 31),
        far_foot=(10, 38),
        hair=(-2, 0),
        skirt=-1,
    )
    draw_player_character(surface, ox, pose)
    draw_curved_blade(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]), bend=2.5)


def draw_attack_tachi_active(surface, i, ox):
    hands = [(18, 15), (22, 16), (24, 18)]
    hand = hands[i]
    tip = (hand[0] + 16, hand[1] + 1 + i)
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
        hair=(1, 0),
        skirt=2,
    )
    draw_player_character(surface, ox, pose)
    draw_curved_blade(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]), bend=2.5)
    for arc in range(2):
        y = 13 + i * 4 + arc * 5
        pygame.draw.polygon(
            surface,
            SLASH,
            [(ox + 40, y), (ox + 42, y + 3), (ox + 40, y + 6)],
        )


def draw_attack_tachi_recovery(surface, i, ox):
    hand = (23, 20 + i)
    tip = (hand[0] + 12, hand[1] + 4 + i)
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
        skirt=1,
    )
    draw_player_character(surface, ox, pose)
    draw_curved_blade(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]), bend=2.5)
    line(surface, SLASH, (ox + 32, 13 + i * 2), (ox + 34, 16 + i * 2), 1)


def draw_attack_longsword_windup(surface, i, ox):
    hand = (13 + i * 2, 10 + i * 2)
    tip = (hand[0] - 7, hand[1] - 9)
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
        hair=(-2, 0),
        skirt=-1,
    )
    draw_player_character(surface, ox, pose)
    draw_longsword(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))


def draw_attack_longsword_active(surface, i, ox):
    hands = [(19, 14), (23, 16), (25, 19), (25, 22)]
    hand = hands[i]
    tip = (hand[0] + 18, hand[1] + 3 + i)
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
        hair=(1, 0),
        skirt=2,
    )
    draw_player_character(surface, ox, pose)
    draw_longsword(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))
    for arc in range(2):
        y = 13 + i * 4 + arc * 5
        pygame.draw.polygon(
            surface,
            SLASH,
            [(ox + 46, y), (ox + 48, y + 3), (ox + 46, y + 6)],
        )


def draw_attack_longsword_recovery(surface, i, ox):
    hand = (25, 21 + i)
    tip = (hand[0] + 13, hand[1] + 4 + i)
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
        skirt=1,
    )
    draw_player_character(surface, ox, pose)
    draw_longsword(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))
    line(surface, SLASH, (ox + 33, 12 + i * 2), (ox + 35, 15 + i * 2), 1)


def draw_attack_zhanmadao_windup(surface, i, ox):
    hand = (16 + i, 16 - i)
    tip = (3 + i, 2)
    pose = player_pose(
        head=(15, 9),
        neck=(15, 13),
        chest=(15, 16),
        pelvis=(15, 26),
        near_elbow=(13, 15),
        near_hand=hand,
        far_elbow=(17, 18),
        far_hand=(hand[0] + 2, hand[1] + 3),
        near_knee=(19, 30),
        near_foot=(22, 38),
        far_knee=(12, 31),
        far_foot=(9, 38),
        hair=(-2, 0),
        skirt=-1,
    )
    draw_player_character(surface, ox, pose)
    draw_zhanmadao(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))


def draw_attack_zhanmadao_active(surface, i, ox):
    hands = [(18, 12), (22, 18)]
    hand = hands[i]
    tip = (hand[0] + 24, hand[1] + 8 + i * 6)
    pose = player_pose(
        head=(18, 9),
        neck=(17, 13),
        chest=(17, 16),
        pelvis=(16, 26),
        near_elbow=(15, 15 + i * 2),
        near_hand=hand,
        far_elbow=(13, 17 + i * 2),
        far_hand=(hand[0] - 3, hand[1] + 2),
        near_knee=(21, 30),
        near_foot=(24, 37),
        far_knee=(13, 31),
        far_foot=(9, 38),
        hair=(2, 0),
        skirt=3,
    )
    draw_player_character(surface, ox, pose)
    draw_zhanmadao(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))
    for arc in range(3):
        y = 12 + i * 8 + arc * 5
        pygame.draw.polygon(
            surface,
            SLASH,
            [(ox + 50, y), (ox + 53, y + 3), (ox + 50, y + 6)],
        )


def draw_attack_zhanmadao_recovery(surface, i, ox):
    settle = min(i, 2)
    hand = (22, 24 + settle)
    tip = (hand[0] + 20, hand[1] + 6)
    pose = player_pose(
        head=(16, 10 + settle),
        neck=(16, 14 + settle),
        chest=(16, 17 + settle),
        pelvis=(16, 26),
        near_elbow=(18, 20 + settle),
        near_hand=hand,
        far_elbow=(14, 21 + settle),
        far_hand=(hand[0] - 3, hand[1] + 2),
        near_knee=(19, 31),
        near_foot=(23, 38),
        far_knee=(13, 31),
        far_foot=(9, 38),
        skirt=1,
    )
    draw_player_character(surface, ox, pose)
    draw_zhanmadao(surface, (ox + hand[0], hand[1]), (ox + tip[0], tip[1]))
    if i < 3:
        dot(surface, FLASH, (ox + 10 + i * 6, 37), 1)
        line(surface, SLASH, (ox + 36, 22 - i * 2), (ox + 39, 20 - i * 2), 1)


def draw_shield(surface, center, w=10, h=16):
    x, y = center
    rect = pygame.Rect(round(x - w / 2), round(y - h / 2), w, h)
    pygame.draw.rect(surface, BOW, rect)
    pygame.draw.rect(surface, IRON, rect, 1)
    line(surface, IRON_DARK, (x, rect.y + 2), (x, rect.bottom - 2), 1)
    dot(surface, BELT_METAL, (x, y), 2)


def draw_attack_shield_windup(surface, i, ox):
    hand = (13 - i, 19)
    pose = player_pose(
        head=(14, 9),
        neck=(14, 13),
        chest=(14, 16),
        pelvis=(15, 26),
        near_elbow=(11, 18),
        near_hand=hand,
        far_elbow=(19, 19),
        far_hand=(21, 23),
        near_knee=(19, 30),
        near_foot=(22, 38),
        far_knee=(12, 31),
        far_foot=(9, 38),
        hair=(-2, 0),
        skirt=-1,
    )
    draw_player_character(surface, ox, pose)
    draw_shield(surface, (ox + hand[0] + 3, hand[1] - 1))


def draw_attack_shield_active(surface, i, ox):
    hands = [(19, 16), (23, 17)]
    hand = hands[i]
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
        hair=(1, 0),
        skirt=2,
    )
    draw_player_character(surface, ox, pose)
    draw_shield(surface, (ox + hand[0] + 5, hand[1] - 1))
    for spark in range(2):
        y = 12 + i * 5 + spark * 6
        line(surface, SLASH, (ox + 38, y), (ox + 41, y + 2), 1)


def draw_attack_shield_recovery(surface, i, ox):
    hand = (21 - i * 2, 18 + i)
    pose = player_pose(
        head=(16, 9),
        neck=(16, 13),
        chest=(16, 16),
        near_elbow=(17, 18),
        near_hand=hand,
        far_elbow=(12, 19),
        far_hand=(9, 23),
        near_knee=(19, 31),
        near_foot=(22, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
        skirt=1,
    )
    draw_player_character(surface, ox, pose)
    draw_shield(surface, (ox + hand[0] + 4, hand[1] - 1))


def draw_player_bow(surface, grip, tension=0, arrow=False):
    x, y = grip
    line(surface, BOW, (x, y - 9), (x, y + 9), 2)
    line(surface, BOW, (x, y - 9), (x - 2, y - 6), 1)
    line(surface, BOW, (x, y + 9), (x - 2, y + 6), 1)
    string_x = x - 2 - tension
    line(surface, FLASH, (x, y - 9), (string_x, y), 1)
    line(surface, FLASH, (string_x, y), (x, y + 9), 1)
    if arrow:
        line(surface, SLASH, (string_x, y), (x + 6, y), 2)
        pygame.draw.polygon(
            surface,
            FLASH,
            [(x + 6, y), (x + 3, y - 2), (x + 3, y + 2)],
        )


def draw_attack_bow_windup(surface, i, ox):
    grip = (20, 16)
    pull = (14 - i * 2, 16)
    pose = player_pose(
        head=(15, 8),
        neck=(15, 12),
        chest=(15, 15),
        near_elbow=(18, 16),
        near_hand=grip,
        far_elbow=(12 - i, 17),
        far_hand=pull,
        near_knee=(19, 30),
        near_foot=(22, 38),
        far_knee=(12, 31),
        far_foot=(9, 38),
        hair=(-1, 0),
        skirt=-1,
    )
    draw_player_character(surface, ox, pose)
    draw_player_bow(surface, (ox + grip[0], grip[1]), tension=2 + i * 3, arrow=True)


def draw_attack_bow_active(surface, i, ox):
    grip = (21, 16)
    pose = player_pose(
        head=(16, 8),
        neck=(16, 12),
        chest=(16, 15),
        near_elbow=(18, 16),
        near_hand=grip,
        far_elbow=(10, 17),
        far_hand=(7, 18),
        near_knee=(20, 30),
        near_foot=(23, 38),
        far_knee=(12, 31),
        far_foot=(9, 38),
        hair=(1, 0),
        skirt=1,
    )
    draw_player_character(surface, ox, pose)
    draw_player_bow(surface, (ox + grip[0], grip[1]))
    ax = ox + 34 + i * 8
    line(surface, SLASH, (ax, 15), (ax + 7, 15), 2)
    pygame.draw.polygon(surface, FLASH, [(ax + 7, 15), (ax + 4, 13), (ax + 4, 17)])


def draw_attack_bow_recovery(surface, i, ox):
    grip = (20, 17 + i)
    pose = player_pose(
        head=(16, 9),
        neck=(16, 13),
        chest=(16, 16),
        near_elbow=(18, 17 + i),
        near_hand=grip,
        far_elbow=(13, 19 + i),
        far_hand=(11, 23 + i),
        near_knee=(19, 31),
        near_foot=(22, 38),
        far_knee=(13, 31),
        far_foot=(10, 38),
        skirt=1,
    )
    draw_player_character(surface, ox, pose)
    draw_player_bow(surface, (ox + grip[0], grip[1]))


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
    draw_player_character(surface, ox, pose)
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
    draw_player_character(surface, ox, pose)
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
    draw_player_character(surface, ox, pose, flash=True)


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
    if i < 2:
        draw_player_character(surface, ox, poses[i])
    else:
        draw_player_character(
            surface, ox, poses[i], dim=True, alpha=170 - (i - 2) * 90
        )
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
    pygame.draw.circle(
        surface, CRAWLER_DARK, (round(ox + 7), body_y + 3), 3
    )
    pygame.draw.circle(surface, CRAWLER, (round(ox + 7), body_y + 3), 2)


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
    pygame.draw.rect(
        surface, TALISMAN, (chest[0] - 1, chest[1] + 2, 2, 7)
    )
    dot(surface, SLASH, (chest[0], chest[1] + 4), 1)
    pygame.draw.circle(surface, ARCHER, (round(head[0]), round(head[1])), 3, 2)
    pygame.draw.polygon(
        surface,
        BOW,
        [
            (head[0] - 5, head[1] - 2),
            (head[0] + 5, head[1] - 2),
            (head[0], head[1] - 7),
        ],
    )
    line(surface, (112, 88, 58), (head[0] - 5, head[1] - 2), (head[0] + 5, head[1] - 2), 1)
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
        "attack_tachi_windup": (2, draw_attack_tachi_windup),
        "attack_tachi_active": (3, draw_attack_tachi_active),
        "attack_tachi_recovery": (3, draw_attack_tachi_recovery),
        "attack_longsword_windup": (2, draw_attack_longsword_windup),
        "attack_longsword_active": (4, draw_attack_longsword_active),
        "attack_longsword_recovery": (4, draw_attack_longsword_recovery),
        "attack_zhanmadao_windup": (3, draw_attack_zhanmadao_windup),
        "attack_zhanmadao_active": (2, draw_attack_zhanmadao_active),
        "attack_zhanmadao_recovery": (6, draw_attack_zhanmadao_recovery),
        "attack_shield_windup": (2, draw_attack_shield_windup),
        "attack_shield_active": (2, draw_attack_shield_active),
        "attack_shield_recovery": (3, draw_attack_shield_recovery),
        "attack_bow_windup": (3, draw_attack_bow_windup),
        "attack_bow_active": (2, draw_attack_bow_active),
        "attack_bow_recovery": (4, draw_attack_bow_recovery),
        "parry": (2, draw_parry),
        "skill": (4, draw_skill),
        "hurt": (2, draw_hurt),
        "death": (4, draw_death),
    }
    for name, (frames, painter) in player.items():
        save_strip(f"player/{name}.png", PLAYER_CELL, frames, player_painter(painter))

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
    for enemy_id, clips in (("wine_imp", crawler), ("paper_runner", archer)):
        for name, (frames, painter) in clips.items():
            save_strip(f"enemies/{enemy_id}/{name}.png", ENEMY_CELL, frames, painter)
    pygame.quit()


if __name__ == "__main__":
    main()