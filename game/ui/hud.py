"""局内 HUD：左上三条资源、技能冷却、妖物名录、右下兵器与左下操作提示。

数据由 RunScene 组装成 ``hud_state``（见 docs/interfaces.md 第 5 节）后传入，
渲染器只读不写，方便后续换皮或加无障碍选项。
"""

import pygame

from game import config
from game.core import hd
from game.ui import theme

HUD_MARGIN = 6
BAR_WIDTH = 64
BAR_HEIGHT = 5


class HudRenderer:
    def __init__(self, loc: dict, fonts=None) -> None:
        self.loc = loc
        self.fonts = fonts or theme.fonts()

    def _t(self, key: str, fallback: str) -> str:
        return self.loc.get(key, fallback)

    @staticmethod
    def _ratio(value: float, maximum: float) -> float:
        if maximum <= 0:
            return 0.0
        return max(0.0, min(1.0, value / maximum))

    def _plate(self, surface, rect: pygame.Rect, alpha: int) -> None:
        theme.draw_plate(surface, rect, (8, 7, 6), alpha)

    def draw(self, surface: pygame.Surface, state: dict) -> None:
        body = self.fonts.body
        rows = (
            (
                self._t("ui.hud.hp", "气血"),
                f"{state['hp']}/{state['max_hp']}",
                self._ratio(state["hp"], state["max_hp"]),
                config.COLORS["ember"],
            ),
            (
                self._t("ui.hud.stamina", "体力"),
                f"{int(state['stamina'])}/{int(state['max_stamina'])}",
                self._ratio(state["stamina"], state["max_stamina"]),
                config.COLORS["stamina"],
            ),
            (
                self._t("ui.hud.mana", "内力"),
                f"{int(state['mana'])}/{int(state['max_mana'])}",
                self._ratio(state["mana"], state["max_mana"]),
                config.COLORS["mana"],
            ),
        )

        max_right = 112
        for _, value_text, _, _ in rows:
            max_right = max(max_right, 108 + theme.text_size(surface, body, value_text)[0])

        skills = state.get("skills") or []
        skill = skills[0] if skills else None
        if skill is not None:
            if skill.get("ready", True):
                skill_state = self._t("ui.hud.ready", "就绪")
                skill_color = theme.GOLD
            else:
                seconds = self._t("ui.hud.seconds", "秒")
                skill_state = f"{skill.get('cooldown', 0.0):.1f}{seconds}"
                skill_color = theme.TEXT_DIM
            skill_line = f"{skill.get('name', '')} {skill_state}"
            max_right = max(
                max_right, 12 + theme.text_size(surface, body, skill_line)[0]
            )
        else:
            skill_line = None
            skill_color = theme.TEXT_DIM

        bestiary = state.get("bestiary", "")
        max_right = max(max_right, 12 + theme.text_size(surface, body, bestiary)[0])

        panel_height = 74
        self._plate(
            surface,
            pygame.Rect(HUD_MARGIN, 4, max_right - 2, panel_height),
            178,
        )

        for index, (label, value_text, ratio, color) in enumerate(rows):
            y = 8 + index * 12
            theme.draw_text(
                surface, body, label, (12, y - 1), (222, 208, 180)
            )
            pygame.draw.rect(
                surface, (18, 16, 16), (38, y + 3, BAR_WIDTH, BAR_HEIGHT)
            )
            pygame.draw.rect(
                surface, color, (38, y + 3, int(BAR_WIDTH * ratio), BAR_HEIGHT)
            )
            pygame.draw.rect(
                surface, (50, 42, 36), (38, y + 3, BAR_WIDTH, BAR_HEIGHT), 1
            )
            theme.draw_text(
                surface, body, value_text, (108, y - 1), (204, 192, 166)
            )

        if skill_line is not None:
            theme.draw_text(surface, body, skill_line, (12, 44), skill_color)
        theme.draw_text(surface, body, bestiary, (12, 58), theme.GOLD)

        self._draw_weapon(surface, state)
        self._draw_hints(surface, state)

    def _draw_weapon(self, surface: pygame.Surface, state: dict) -> None:
        weapon = state.get("weapon") or {}
        if not weapon:
            return
        if weapon.get("slots", 1) > 1:
            prefix = f"{weapon.get('slot', 1)}/{weapon.get('slots', 1)} "
        else:
            prefix = ""
        line = (
            f"{prefix}"
            f"{weapon.get('name', '?')} "
            f"{self._t('ui.hud.level', '等级')}{weapon.get('level', 1)} "
            f"{self._t('ui.hud.damage', '伤害')} {weapon.get('damage_text', '0.0')}"
        )
        bonus = weapon.get("bonus", 0.0)
        if bonus > 0:
            line += f" +{int(bonus * 100)}%"
        loot_line = (
            f"{self._t('ui.hud.embers', '余烬')} {state.get('embers', 0)}   "
            f"{self._t('ui.hud.kills', '击杀')} {state.get('kills', 0)}"
        )
        body = self.fonts.body
        weapon_w, weapon_h = theme.text_size(surface, body, line)
        loot_w, loot_h = theme.text_size(surface, body, loot_line)
        plate_w = max(weapon_w, loot_w) + 10
        plate_h = weapon_h + loot_h + 8
        right = config.INTERNAL_WIDTH - 8
        self._plate(
            surface,
            pygame.Rect(right - plate_w, 6, plate_w, plate_h),
            178,
        )
        theme.draw_text(
            surface,
            body,
            line,
            (right - 4, 7),
            (220, 210, 184),
            anchor="topright",
        )
        theme.draw_text(
            surface,
            body,
            loot_line,
            (right - 4, 7 + weapon_h + 2),
            (166, 158, 138),
            anchor="topright",
        )

    def _draw_hints(self, surface: pygame.Surface, state: dict) -> None:
        hints = state.get("hints") or []
        alpha_ratio = float(state.get("hint_alpha", 0.0))
        if not hints or alpha_ratio <= 0:
            return
        scale = getattr(surface, "scale", 1)
        body = self.fonts.body
        rendered = hints[:2]
        widths = [theme.text_size(surface, body, line)[0] for line in rendered]
        plate_w = max(widths) + 8
        plate = hd.Surface((plate_w, 26), pygame.SRCALPHA, scale)
        plate.fill((8, 7, 6, 168))
        for index, line in enumerate(rendered):
            theme.draw_text(
                plate, body, line, (4, index * 11), (206, 192, 162)
            )
        plate.set_alpha(int(255 * min(1.0, alpha_ratio)))
        if scale > 1:
            surface.blit_native(
                plate.target,
                (10 * scale, (config.INTERNAL_HEIGHT - 30) * scale),
            )
        else:
            surface.blit(plate.target, (10, config.INTERNAL_HEIGHT - 30))
