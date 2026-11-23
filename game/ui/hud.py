"""局内 HUD：左上三条资源、技能冷却、妖物名录、右下兵器与左下操作提示。

数据由 RunScene 组装成 ``hud_state``（见 docs/interfaces.md 第 5 节）后传入，
渲染器只读不写，方便后续换皮或加无障碍选项。
"""

import pygame

from game import config
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

    def draw(self, surface: pygame.Surface, state: dict) -> None:
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

        rendered = []
        max_right = 112
        for i, (label, value_text, ratio, color) in enumerate(rows):
            y = 8 + i * 12
            label_surf = self.fonts.body.render(label, True, (222, 208, 180))
            value_surf = self.fonts.body.render(value_text, True, (204, 192, 166))
            rendered.append((y, label_surf, value_surf, ratio, color))
            max_right = max(max_right, 108 + value_surf.get_width())

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
            skill_surf = self.fonts.body.render(
                f"{skill.get('name', '')} {skill_state}", True, skill_color
            )
            max_right = max(max_right, 12 + skill_surf.get_width())
        else:
            skill_surf = None

        bestiary_surf = self.fonts.body.render(
            state.get("bestiary", ""), True, theme.GOLD
        )
        max_right = max(max_right, 12 + bestiary_surf.get_width())

        panel = pygame.Surface((max_right - 2, 74), pygame.SRCALPHA)
        panel.fill((8, 7, 6, 178))
        surface.blit(panel, (HUD_MARGIN, 4))

        for y, label_surf, value_surf, ratio, color in rendered:
            surface.blit(label_surf, (12, y - 1))
            pygame.draw.rect(
                surface, (18, 16, 16), (38, y + 3, BAR_WIDTH, BAR_HEIGHT)
            )
            pygame.draw.rect(
                surface, color, (38, y + 3, int(BAR_WIDTH * ratio), BAR_HEIGHT)
            )
            pygame.draw.rect(
                surface, (50, 42, 36), (38, y + 3, BAR_WIDTH, BAR_HEIGHT), 1
            )
            surface.blit(value_surf, (108, y - 1))

        if skill_surf is not None:
            surface.blit(skill_surf, (12, 44))
        surface.blit(bestiary_surf, (12, 58))

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
        weapon_surf = self.fonts.body.render(line, True, (220, 210, 184))
        loot_surf = self.fonts.body.render(loot_line, True, (166, 158, 138))
        plate = pygame.Surface(
            (
                max(weapon_surf.get_width(), loot_surf.get_width()) + 10,
                weapon_surf.get_height() + loot_surf.get_height() + 8,
            ),
            pygame.SRCALPHA,
        )
        plate.fill((8, 7, 6, 178))
        right = config.INTERNAL_WIDTH - 8
        surface.blit(plate, (right - plate.get_width(), 6))
        surface.blit(weapon_surf, (right - weapon_surf.get_width() - 4, 7))
        surface.blit(
            loot_surf,
            (
                right - loot_surf.get_width() - 4,
                7 + weapon_surf.get_height() + 2,
            ),
        )

    def _draw_hints(self, surface: pygame.Surface, state: dict) -> None:
        hints = state.get("hints") or []
        alpha_ratio = float(state.get("hint_alpha", 0.0))
        if not hints or alpha_ratio <= 0:
            return
        rendered = [
            self.fonts.body.render(line, True, (206, 192, 162)) for line in hints
        ]
        plate_w = max(line.get_width() for line in rendered) + 8
        plate = pygame.Surface((plate_w, 26), pygame.SRCALPHA)
        plate.fill((8, 7, 6, 168))
        for index, line in enumerate(rendered[:2]):
            plate.blit(line, (4, index * 11))
        plate.set_alpha(int(255 * min(1.0, alpha_ratio)))
        surface.blit(plate, (10, config.INTERNAL_HEIGHT - 30))
