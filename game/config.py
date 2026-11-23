import sys
from pathlib import Path

INTERNAL_WIDTH = 480
INTERNAL_HEIGHT = 270
# 窗口取 480x270 的整数倍：3 倍 = 1440x810，铺满窗口且像素不糊。
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 810
FPS = 60
DT = 1.0 / 60.0
MAX_FRAME_DT = 0.1

ROOT_DIR = Path(__file__).resolve().parent.parent


def resource_path(rel: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", ROOT_DIR))
    return base / rel


MOVE_SPEED = 135.0
GROUND_ACCEL = 2000.0
GROUND_DECEL = 2400.0
AIR_ACCEL = 1200.0
GRAVITY = 950.0
MAX_FALL = 420.0
JUMP_VELOCITY = -320.0
JUMP_CUT_VELOCITY = -110.0
COYOTE_TIME = 0.10
JUMP_BUFFER = 0.12
DROP_THROUGH_TIME = 0.20

DASH_SPEED = 380.0
DASH_TIME = 0.16
DASH_COOLDOWN = 0.45
DASH_INVULN = 0.18

ATTACK_WINDUP = 0.05
ATTACK_ACTIVE = 0.08
ATTACK_RECOVERY = 0.14
ATTACK_BUFFER = 0.12
ATTACK_HITBOX = (30, 26)
HITSTOP_ON_HIT = 0.05

STAMINA_MAX = 100.0
STAMINA_REGEN = 35.0
STAMINA_REGEN_DELAY = 0.6
DASH_STAMINA_COST = 20.0
PARRY_STAMINA_COST = 15.0

MANA_MAX = 100.0
MANA_REGEN = 10.0
MANA_REGEN_DELAY = 1.0

FALL_SAFE_SPEED = 380.0
FALL_DAMAGE_SCALE = 0.35

PLAYER_SIZE = (18, 38)
DEBUG_HITBOXES = False

COLORS = {
    "bg": (18, 14, 26),
    "terrain": (58, 51, 72),
    "terrain_top": (87, 80, 110),
    "one_way": (107, 91, 62),
    "player": (232, 213, 176),
    "player_eye": (30, 26, 40),
    "ember": (255, 154, 60),
    "slash": (255, 210, 122),
    "dummy": (120, 110, 140),
    "dummy_flash": (255, 245, 230),
    "hud": (200, 195, 215),
    "hud_dim": (120, 115, 140),
    "stamina": (122, 200, 132),
    "mana": (92, 150, 232),
    "spike": (178, 166, 196),
    "poison": (108, 188, 92),
}