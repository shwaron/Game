import random

import pygame

from game import config
from game.core.animation import build_clips
from game.core.assets import load_json
from game.core.camera import Camera
from game.core.scene_manager import Scene
from game.entities.enemy import ChaserEnemy, ShooterEnemy
from game.entities.pickup import (
    EMBER_VALUE,
    FIRE_SEED,
    POTION,
    POTION_HEAL,
    Pickup,
)
from game.entities.player import Player
from game.entities.projectile import Projectile
from game.scenes.bamboo_world import (
    FLOOR_Y,
    HEIGHT,
    HUD_GOLD,
    LANTERN_GOLD,
    START_ROOM,
    WIDTH,
    WOOD,
    WOOD_DARK,
    WOOD_EDGE,
    build_world,
)
from game.systems.combat import TEAM_ENEMY, TEAM_PLAYER, CombatSystem
from game.systems.loot import load_tables, roll_table
from game.systems.weapons import scaling_bonus, weapon_damage, weapon_level
from game.ui import preferences, theme
from game.ui.hud import HudRenderer

TRANSITION_TIME = 0.16
ROOM_TITLE_TIME = 2.8
HINT_TIME = 14.0


class RunScene(Scene):
    def __init__(self, game) -> None:
        self.game = game
        self.loc = load_json("game/data/localization/zh_CN.json")
        self.rooms = build_world()
        weapon_data = load_json("game/data/weapons.json")["weapons"]
        self.weapon_slots = [
            self._make_weapon(weapon_data["worn_flame_blade"], "worn_flame_blade", 2),
            self._make_weapon(weapon_data["desperate_edge"], "desperate_edge", 1),
            self._make_weapon(weapon_data["bell_hammer"], "bell_hammer", 1),
            self._make_weapon(weapon_data["rift_spear"], "rift_spear", 1),
            self._make_weapon(weapon_data["gale_daggers"], "gale_daggers", 1),
            self._make_weapon(weapon_data["ember_staff"], "ember_staff", 1),
        ]
        self.weapon_index = 0
        self.weapon = self.weapon_slots[0]
        self.skills = load_json("game/data/skills.json")["skills"]
        self.skill_cooldowns = {skill_id: 0.0 for skill_id in self.skills}
        self.cast_id = 0
        self.enemy_data = load_json("game/data/enemies.json")["enemies"]
        self.loot_tables = load_tables(load_json("game/data/loot_tables.json"))
        anim_data = load_json("game/data/animations.json")
        self.player_anims = build_clips(anim_data["player"])
        self.enemy_anims = {
            enemy_id: build_clips(section)
            for enemy_id, section in anim_data["enemies"].items()
        }
        self.rng = random.Random()
        self.camera = Camera(WIDTH, HEIGHT)
        self.room = self.rooms[START_ROOM]
        self.world_surface = pygame.Surface((self.room.width, HEIGHT))
        self.combat = CombatSystem(self.rng)
        self.player = None
        self.enemies: list = []
        self.room_enemies: dict[str, list] = {}
        self.focus_exit = None
        self.projectiles: list = []
        self.pickups: list = []
        self._loot_sources: dict[int, tuple[str, int]] = {}
        self.embers = 0
        self.kills = 0
        self.hitstop = 0.0
        self.death_timer = 0.0
        self.room_title_timer = 0.0
        self.clear_banner_timer = 0.0
        self.hint_timer = 0.0
        self.exit_cooldown = 0.0
        self.transition: dict | None = None
        self.show_map = False
        self.discovered: set[str] = set()
        self.cleared: set[str] = set()
        self.taken_loot: set[tuple[str, int]] = set()
        self.skill_fx: list[list] = []
        self.font_title = None
        self.font_info = None
        self.font_tiny = None
        self.hud = HudRenderer(self.loc)
        self.run_time = 0.0

    def enter(self) -> None:
        fonts = theme.fonts()
        self.font_title = fonts.heading
        self.font_info = fonts.body
        self.font_tiny = fonts.body
        self._start_run()

    @staticmethod
    def _make_weapon(data: dict, weapon_id: str, level: int) -> dict:
        weapon = dict(data)
        weapon["id"] = weapon_id
        weapon["level"] = level
        return weapon

    # -- run / room lifecycle -------------------------------------------
    def _start_run(self) -> None:
        self.weapon_index = 0
        self.weapon = self.weapon_slots[0]
        self.player = Player(0, 0, self.weapon, self.player_anims)
        self.enemies = []
        self.room_enemies = {}
        self.focus_exit = None
        self.projectiles = []
        self.pickups = []
        self._loot_sources = {}
        self.embers = 0
        self.kills = 0
        self.hitstop = 0.0
        self.death_timer = 0.0
        self.clear_banner_timer = 0.0
        self.hint_timer = HINT_TIME
        self.exit_cooldown = 0.0
        self.transition = None
        self.show_map = False
        self.discovered = set()
        self.cleared = set()
        self.taken_loot = set()
        self.skill_cooldowns = {skill_id: 0.0 for skill_id in self.skills}
        self.cast_id = 0
        self.skill_fx = []
        self.run_time = 0.0
        self._enter_room(START_ROOM, "start")

    def _enter_room(self, room_id: str, entry: str) -> None:
        room = self.rooms[room_id]
        spawn = room.entries[entry]
        self.room = room
        self.player.body.x = float(spawn[0])
        self.player.body.y = float(spawn[1])
        self.player.body.vel_x = 0.0
        self.player.body.vel_y = 0.0
        self.player.body.on_ground = False
        self.player.drop_timer = 0.0
        self.player.dash_time = 0.0
        self.player.cast_timer = 0.0
        self.player.parry_timer = 0.0
        self.player.attack_phase = None
        self.player.attack_timer = 0.0
        self.player.jump_buffer = 0.0
        self.player.attack_buffer = 0.0
        self.player.hurt_timer = 0.0
        self.player.invuln = max(self.player.invuln, 0.25)
        self.player.ghosts = []
        self.player.facing = 1 if spawn[0] < room.width / 2 else -1
        self.player.state = "fall"

        self.combat = CombatSystem(self.rng)
        self.combat.register(self.player)
        self.enemies = self._load_room_enemies(room)
        for enemy in self.enemies:
            self.combat.register(enemy)
        self.focus_exit = None
        self.projectiles = []
        self.pickups = []
        self._loot_sources = {}
        for index, (item_id, x, y) in enumerate(room.loot):
            source = (room.room_id, index)
            if source in self.taken_loot:
                continue
            pickup = Pickup(item_id, x, y)
            self.pickups.append(pickup)
            self._loot_sources[id(pickup)] = source
        self.world_surface = pygame.Surface((room.width, HEIGHT))
        self.camera.snap(self.player.rect, room.width, HEIGHT)
        self.room_title_timer = ROOM_TITLE_TIME
        self.clear_banner_timer = 0.0
        self.exit_cooldown = 0.55
        self.discovered.add(room.room_id)

    def _load_room_enemies(self, room) -> list:
        """一局内每个房间的敌人只生成一次。

        离开房间时保留残血、站位与存活状态，回来沿用同一批实例；
        已清房间缓存空列表，不会再次刷新。
        """
        if room.room_id in self.room_enemies:
            alive = [
                enemy for enemy in self.room_enemies[room.room_id] if enemy.health.alive
            ]
            self.room_enemies[room.room_id] = alive
            return alive
        if room.room_id in self.cleared or not room.spawns:
            self.room_enemies[room.room_id] = []
            return []
        enemies = [self._spawn_enemy(spawn) for spawn in room.spawns]
        self.room_enemies[room.room_id] = enemies
        return enemies

    def _spawn_enemy(self, spawn: dict):
        enemy_id = spawn["enemy_id"]
        data = self.enemy_data[enemy_id]
        enemy_type = ShooterEnemy if data.get("keep_distance") else ChaserEnemy
        return enemy_type(
            enemy_id,
            spawn["x"],
            spawn["y"],
            data,
            self.room,
            self.enemy_anims[enemy_id],
        )

    def handle_event(self, event) -> None:
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self._start_run()

    # -- update ---------------------------------------------------------
    def update(self, dt: float) -> None:
        inp = self.game.input
        if inp.is_action_just_pressed("pause"):
            from game.scenes.pause import PauseScene

            self.game.scenes.push(PauseScene(self.game))
            return

        self.run_time += dt
        self.room.art.update(dt)
        self.room_title_timer = max(0.0, self.room_title_timer - dt)
        self.clear_banner_timer = max(0.0, self.clear_banner_timer - dt)
        self.hint_timer = max(0.0, self.hint_timer - dt)
        self.exit_cooldown = max(0.0, self.exit_cooldown - dt)

        if self.transition is not None:
            self._update_transition(dt)
            return

        if inp.is_action_just_pressed("map") and self.player.health.alive:
            self.show_map = not self.show_map
            return
        if self.show_map:
            return

        if self.hitstop > 0:
            self.hitstop -= dt
            return

        self.player.update(dt, inp, self.room)
        if not self.player.health.alive:
            self.death_timer += dt
            if not self.player.death_reported:
                self.player.death_reported = True
                self.game.bus.publish(
                    "player.died",
                    {"run_id": 0, "depth": 1, "cause": "combat"},
                )
            if self.death_timer > 1.6:
                self._end_run("death")
            return

        self.camera.update(
            dt, self.player.rect, self.room.width, HEIGHT, self.player.facing
        )

        if inp.is_action_just_pressed("swap") and self.player.attack_phase is None:
            self.weapon_index = (self.weapon_index + 1) % len(self.weapon_slots)
            self.weapon = self.weapon_slots[self.weapon_index]
            self.player.weapon = self.weapon
        self._update_hazards()
        self._update_skills(inp, dt)
        for fx in self.skill_fx:
            fx[1] -= dt
        self.skill_fx = [fx for fx in self.skill_fx if fx[1] > 0]

        hitbox = self.player.attack_hitbox
        if hitbox:
            hits = self.combat.resolve_melee(
                f"player:{self.player.swing_id}",
                hitbox,
                TEAM_PLAYER,
                self.player.attack_power,
                self.player.weapon.get("knockback", 0.0),
                source_pos=(self.player.rect.centerx, self.player.rect.centery),
                crit_chance=0.05,
            )
            if hits:
                self.hitstop = config.HITSTOP_ON_HIT

        for enemy in list(self.enemies):
            enemy.update(dt, self.player)
            if enemy.health.alive:
                enemy_hitbox = enemy.attack_hitbox
                if enemy_hitbox:
                    if self.player.is_parrying and enemy_hitbox.colliderect(
                        self.player.rect
                    ):
                        self.player.parry_success()
                        enemy.stagger(0.4)
                        self.hitstop = 0.08
                    else:
                        hits = self.combat.resolve_melee(
                            f"enemy:{id(enemy)}:{enemy.swing_id}",
                            enemy_hitbox,
                            TEAM_ENEMY,
                            enemy.data["damage"],
                            enemy.attack.get("knockback", 0.0),
                            source_pos=(
                                enemy.rect.centerx,
                                enemy.rect.centery,
                            ),
                        )
                        if hits:
                            self.hitstop = config.HITSTOP_ON_HIT
                if enemy.pending_projectile:
                    self._spawn_projectile(enemy)
                    enemy.pending_projectile = None
            else:
                if not enemy.death_reported:
                    enemy.death_reported = True
                    self.kills += 1
                    self.game.bus.publish(
                        "enemy.killed",
                        {
                            "enemy_id": enemy.enemy_id,
                            "position": (
                                enemy.rect.centerx,
                                enemy.rect.centery,
                            ),
                            "loot_table": enemy.data.get("loot_table", ""),
                        },
                    )
                    self._drop_loot(enemy)
                if enemy.dead_timer <= 0:
                    self.combat.unregister(enemy)
                    self.enemies.remove(enemy)

        for projectile in list(self.projectiles):
            projectile.update(dt, self.room)
            if projectile.dead:
                self.projectiles.remove(projectile)
                continue
            if projectile.team == TEAM_ENEMY and projectile.rect.colliderect(
                self.player.rect
            ):
                if self.player.is_parrying:
                    projectile.reflect()
                    self.player.parry_success()
                    self.hitstop = 0.08
                    continue
            hits = self.combat.resolve_melee(
                f"projectile:{id(projectile)}",
                projectile.rect,
                projectile.team,
                projectile.damage,
                80.0,
                source_pos=(projectile.x, projectile.y),
            )
            if hits:
                self.hitstop = config.HITSTOP_ON_HIT
                self.projectiles.remove(projectile)

        for pickup in list(self.pickups):
            pickup.update(dt, self.room)
            if pickup.collect_rect.colliderect(self.player.rect):
                self.pickups.remove(pickup)
                self._collect(pickup)

        if (
            not self.enemies
            and self.room.spawns
            and self.room.room_id not in self.cleared
        ):
            self.cleared.add(self.room.room_id)
            self.clear_banner_timer = 2.4

        self.focus_exit = (
            self._exit_under_player() if self.player.health.alive else None
        )
        self._try_use_exit(inp)

    def _update_transition(self, dt: float) -> None:
        self.transition["timer"] -= dt
        if self.transition["timer"] > 0:
            return
        if self.transition["phase"] == "out":
            target = self.transition["target"]
            entry = self.transition["entry"]
            self._enter_room(target, entry)
            self.transition = {"phase": "in", "timer": TRANSITION_TIME}
        else:
            self.transition = None

    def _exit_under_player(self):
        """玩家当前站着的出口；没有则返回 None。"""
        for exit_ in self.room.exits:
            if self.player.rect.colliderect(exit_.rect):
                return exit_
        return None

    def _try_use_exit(self, inp) -> bool:
        """站在门口按交互键才传送，避免战斗中被门自动吸走。"""
        if self.focus_exit is None or self.exit_cooldown > 0:
            return False
        if not inp.is_action_just_pressed("interact"):
            return False
        self._begin_transition(self.focus_exit)
        return True

    def _begin_transition(self, exit_) -> None:
        self.transition = {
            "phase": "out",
            "timer": TRANSITION_TIME,
            "target": exit_.target,
            "entry": exit_.entry,
        }
        self.exit_cooldown = 0.9

    def _end_run(self, cause: str) -> None:
        """本局结束：登记 run.ended 后交给死亡结算页。"""
        depth = 1
        self.game.bus.publish(
            "run.ended",
            {"outcome": cause, "embers": self.embers, "depth": depth},
        )
        from game.scenes.death import DeathScene

        self.game.scenes.replace(
            DeathScene(
                self.game,
                {
                    "embers": self.embers,
                    "kills": self.kills,
                    "rooms": len(self.cleared),
                    "total_rooms": len(self.rooms),
                    "time": self.run_time,
                    "zone": self.loc.get(self.room.title_key, self.room.room_id),
                },
            )
        )

    def _spawn_projectile(self, enemy) -> None:
        spec = enemy.pending_projectile
        speed = spec.get("speed", 160)
        size = tuple(spec.get("size", [6, 2]))
        self.projectiles.append(
            Projectile(
                enemy.rect.centerx,
                enemy.rect.centery,
                enemy.facing * speed,
                0.0,
                enemy.data["damage"],
                TEAM_ENEMY,
                size,
                spec.get("life", 3.0),
            )
        )

    def _drop_loot(self, enemy) -> None:
        table = self.loot_tables.get(enemy.data.get("loot_table", ""))
        if not table:
            return
        item_id = roll_table(table, self.rng)
        self.pickups.append(Pickup(item_id, enemy.rect.centerx, enemy.rect.centery))

    def _collect(self, pickup) -> None:
        if pickup.item_id == FIRE_SEED:
            self.embers += EMBER_VALUE
        elif pickup.item_id == POTION:
            self.player.heal(POTION_HEAL)
        source = self._loot_sources.pop(id(pickup), None)
        if source is not None:
            self.taken_loot.add(source)
        self.game.bus.publish(
            "loot.picked",
            {"item_id": pickup.item_id, "rarity": "common", "slot": "none"},
        )

    def _update_hazards(self) -> None:
        player = self.player
        for hazard in self.room.hazards:
            if not hazard.rect.colliderect(player.rect):
                continue
            if hazard.kind == "spikes":
                player.take_hit(hazard.damage, hazard.rect.center, 120.0)
            elif hazard.kind == "poison":
                player.status.apply("poison", 2.0, hazard.damage, max_stacks=1)

    def _update_skills(self, inp, dt: float) -> None:
        for skill_id in self.skill_cooldowns:
            self.skill_cooldowns[skill_id] = max(
                0.0, self.skill_cooldowns[skill_id] - dt
            )
        skill = self.skills.get("ember_burst")
        if not skill or not inp.is_action_just_pressed("skill1"):
            return
        if self.skill_cooldowns["ember_burst"] > 0:
            return
        if not self.player.mana.spend(skill["mana_cost"]):
            return
        self.skill_cooldowns["ember_burst"] = skill["cooldown"]
        self.player.cast_timer = 0.25
        self.cast_id += 1
        radius = skill["radius"]
        cx, cy = self.player.rect.center
        area = pygame.Rect(cx - radius, cy - radius, radius * 2, radius * 2)
        hits = self.combat.resolve_melee(
            f"skill:ember_burst:{self.cast_id}",
            area,
            TEAM_PLAYER,
            skill["damage"],
            skill.get("knockback", 0.0),
            source_pos=(cx, cy),
        )
        for target, _, _ in hits:
            for effect in skill.get("effects", []):
                if effect.get("status"):
                    target.status.apply(
                        effect["status"],
                        effect.get("duration", 1.0),
                        effect.get("potency", 0.0),
                        effect.get("max_stacks", 1),
                    )
        self.skill_fx.append([area, 0.2])
        if hits:
            self.hitstop = config.HITSTOP_ON_HIT

    # -- draw -----------------------------------------------------------
    def draw(self, surface: pygame.Surface) -> None:
        world = self.world_surface
        self.room.art.draw_back(world)
        self._draw_exit_markers(world)
        self._draw_hazards(world)
        for pickup in self.pickups:
            pickup.draw(world)
        for projectile in self.projectiles:
            projectile.draw(world)
        for enemy in self.enemies:
            enemy.draw(world)
        for rect, ttl in self.skill_fx:
            radius = max(2, int(rect.w / 2 * (1.0 - ttl / 0.2)))
            pygame.draw.circle(world, (255, 176, 88), rect.center, radius, 2)
            pygame.draw.circle(
                world, (255, 220, 150), rect.center, max(1, radius - 5), 1
            )
        self.player.draw(world)

        surface.blit(world, (0, 0), self.camera.rect)
        self.room.art.draw_front(surface)
        self._draw_exit_hints(surface)
        self._draw_enemy_names(surface)
        self._draw_hud(surface)
        self._draw_room_title(surface)
        self._draw_clear_banner(surface)
        if self.show_map:
            self._draw_minimap(surface)
        if not self.player.health.alive:
            self._draw_death(surface)
        self._draw_fade(surface)

    def _draw_exit_markers(self, surface: pygame.Surface) -> None:
        cx = self.player.rect.centerx
        for exit_ in self.room.exits:
            rect = exit_.rect
            near = abs(cx - rect.centerx) < 90
            if exit_.kind == "hatch":
                pygame.draw.rect(
                    surface, WOOD_EDGE, (rect.x, FLOOR_Y - 2, rect.w, 8)
                )
                pygame.draw.rect(
                    surface, WOOD_DARK, (rect.x + 2, FLOOR_Y - 1, rect.w - 4, 5)
                )
                pygame.draw.rect(
                    surface, (8, 8, 7), (rect.x + 6, FLOOR_Y + 1, rect.w - 12, 10)
                )
                for hx in range(rect.x + 8, rect.right - 6, 8):
                    pygame.draw.line(
                        surface,
                        WOOD,
                        (hx, FLOOR_Y - 1),
                        (hx + 3, FLOOR_Y + 3),
                        1,
                    )
                pygame.draw.line(
                    surface,
                    LANTERN_GOLD,
                    (rect.centerx - 3, FLOOR_Y + 7),
                    (rect.centerx + 3, FLOOR_Y + 7),
                    1,
                )
            elif exit_.kind == "stairs":
                pygame.draw.rect(
                    surface, (14, 12, 10), (rect.x + 4, rect.y + 8, rect.w - 8, rect.h - 8)
                )
                pygame.draw.rect(
                    surface, WOOD_EDGE, (rect.x + 2, rect.y + 6, rect.w - 4, 52), 1
                )
                pygame.draw.line(
                    surface,
                    LANTERN_GOLD if near else (120, 96, 60),
                    (rect.centerx, rect.bottom - 4),
                    (rect.centerx, rect.y + 12),
                    1,
                )
            else:
                color = LANTERN_GOLD if near else (132, 104, 66)
                pygame.draw.rect(
                    surface,
                    color,
                    (rect.x if rect.centerx < WIDTH else rect.right - 2, rect.y + 14, 2, 58),
                )
                if exit_ is not self.focus_exit:
                    # 玩家站在门里时改用屏幕提示，箭头会压住角色头顶。
                    pygame.draw.polygon(
                        surface,
                        color,
                        [
                            (rect.centerx - 3, rect.y + 26),
                            (rect.centerx + 3, rect.y + 26),
                            (rect.centerx, rect.y + 32),
                        ],
                    )

    def _draw_exit_hints(self, surface: pygame.Surface) -> None:
        if self.transition is not None or not self.player.health.alive:
            return
        px = self.player.rect.centerx
        for exit_ in self.room.exits:
            sx = exit_.rect.centerx - round(self.camera.x)
            if sx < -60 or sx > WIDTH + 60:
                continue
            sy = exit_.rect.centery - round(self.camera.y)
            near = abs(px - exit_.rect.centerx) < 104
            focused = exit_ is self.focus_exit
            if focused:
                color = (246, 216, 158)
            elif near:
                color = (226, 196, 134)
            else:
                color = (148, 120, 84)
            pygame.draw.polygon(
                surface,
                color,
                [(sx - 3, sy - 3), (sx + 3, sy - 3), (sx, sy + 2)],
            )
            if not near:
                continue
            label = self.loc.get(exit_.label_key, exit_.target)
            if exit_.hidden:
                label = self.loc.get("ui.exit.secret", "暗门") + " · " + label
            usable = focused and self.exit_cooldown <= 0
            if usable:
                label = f"{self.loc.get('ui.exit.enter', 'E')} · {label}"
            text = self.font_tiny.render(
                label, True, (246, 216, 158) if usable else (232, 214, 174)
            )
            plate = pygame.Surface(
                (text.get_width() + 8, text.get_height() + 4), pygame.SRCALPHA
            )
            plate.fill((8, 7, 6, 170))
            lx = max(6, min(WIDTH - text.get_width() - 14, sx - text.get_width() // 2))
            ly = max(18, min(HEIGHT - 26, sy - text.get_height() - 12))
            surface.blit(plate, (lx - 4, ly - 2))
            if usable:
                pygame.draw.rect(
                    surface,
                    (196, 158, 88),
                    (lx - 4, ly - 2, plate.get_width(), plate.get_height()),
                    1,
                )
            surface.blit(text, (lx, ly))

    def _draw_hazards(self, surface: pygame.Surface) -> None:
        for hazard in self.room.hazards:
            r = hazard.rect
            if hazard.kind == "spikes":
                pygame.draw.rect(surface, (48, 34, 25), (r.x, r.bottom - 3, r.w, 3))
                for x in range(r.x + 2, r.right, 8):
                    pygame.draw.polygon(
                        surface,
                        (164, 160, 148),
                        [(x, r.bottom), (x + 2, r.top), (x + 4, r.bottom)],
                    )
                    pygame.draw.line(
                        surface,
                        (220, 214, 196),
                        (x + 2, r.top),
                        (x + 3, r.bottom - 1),
                        1,
                    )
            else:
                pygame.draw.ellipse(surface, (66, 78, 42), r.inflate(8, 2))
                pygame.draw.ellipse(surface, (98, 114, 54), r)
                for dx in (4, 15, 26):
                    if r.x + dx < r.right:
                        pygame.draw.circle(
                            surface, (142, 150, 78), (r.x + dx, r.y + 3), 1
                        )

    def _draw_enemy_names(self, surface: pygame.Surface) -> None:
        cam_x = self.camera.x
        cam_y = self.camera.y
        for enemy in self.enemies:
            if not enemy.health.alive:
                continue
            if enemy.health.hp >= enemy.health.max_hp:
                continue
            key = enemy.data.get("name_key", f"enemy.{enemy.enemy_id}.name")
            name = self.loc.get(key, enemy.enemy_id)
            label = self.font_tiny.render(name, True, (232, 214, 174))
            shadow = self.font_tiny.render(name, True, (14, 12, 10))
            r = enemy.rect
            x = r.centerx - label.get_width() // 2 - round(cam_x)
            y = r.y - 20 - round(cam_y)
            if x < -label.get_width() or x > WIDTH:
                continue
            surface.blit(shadow, (x + 1, y + 1))
            surface.blit(label, (x, y))

    def _bestiary_text(self) -> str:
        if self.room.room_id in self.cleared:
            return self.loc.get("ui.hud.cleared_room", "此间已清")
        if not self.room.spawns:
            return self.loc.get("ui.hud.peaceful", "此间暂无妖物")
        names = []
        for spawn in self.room.spawns:
            data = self.enemy_data.get(spawn["enemy_id"], {})
            key = data.get("name_key", f"enemy.{spawn['enemy_id']}.name")
            name = self.loc.get(key, spawn["enemy_id"])
            if name not in names:
                names.append(name)
        return self.loc.get("ui.hud.bestiary_prefix", "妖物：") + " · ".join(names)

    def hud_state(self) -> dict:
        """按 interfaces.md 第 5 节组装只读状态，交给 ui.hud 渲染。"""
        p = self.player
        skill_id = "ember_burst"
        cooldown = self.skill_cooldowns.get(skill_id, 0.0)
        weapon = self.weapon
        name_key = weapon.get("name_key", f"weapon.{weapon.get('id')}.name")
        show_hints = bool(preferences.get("show_hints", True))
        return {
            "hp": p.health.hp,
            "max_hp": p.health.max_hp,
            "stamina": p.stamina.value,
            "max_stamina": p.stamina.max_value,
            "mana": p.mana.value,
            "max_mana": p.mana.max_value,
            "embers": self.embers,
            "kills": self.kills,
            "skills": [
                {
                    "id": skill_id,
                    "name": self.loc.get(f"skill.{skill_id}.name", skill_id),
                    "cooldown": cooldown,
                    "ready": cooldown <= 0,
                }
            ],
            "weapon": {
                "name": self.loc.get(name_key, weapon.get("id", "?")),
                "slot": self.weapon_index + 1,
                "slots": len(self.weapon_slots),
                "level": weapon_level(weapon),
                "damage_text": f"{weapon_damage(weapon, p):.1f}",
                "bonus": scaling_bonus(weapon, p),
            },
            "bestiary": self._bestiary_text(),
            "hints": [
                self.loc.get(
                    "ui.hud.hint1",
                    "A/D 移动  空格 跳  Shift 冲刺  J 攻击  K 弹反",
                ),
                self.loc.get(
                    "ui.hud.hint2",
                    "Q 换武器  U 烬爆  M 舆图  R 重来  ESC 暂停",
                ),
            ],
            "hint_alpha": (
                min(1.0, self.hint_timer / 1.2)
                if show_hints and self.hint_timer > 0
                else 0.0
            ),
        }

    def _draw_hud(self, surface: pygame.Surface) -> None:
        self.hud.draw(surface, self.hud_state())

    def _draw_room_title(self, surface: pygame.Surface) -> None:
        if self.room_title_timer <= 0:
            return
        alpha = (
            255
            if self.room_title_timer > 0.7
            else int(255 * self.room_title_timer / 0.7)
        )
        title = self.loc.get(self.room.title_key, self.room.room_id)
        subtitle = self.loc.get(self.room.subtitle_key, "")
        text = f"{title} · {subtitle}" if subtitle else title
        label = self.font_info.render(text, True, (238, 214, 160))
        plate = pygame.Surface((label.get_width() + 16, 15), pygame.SRCALPHA)
        plate.fill((8, 7, 6, 160))
        pygame.draw.line(plate, (150, 116, 68), (4, 0), (plate.get_width() - 4, 0), 1)
        plate.blit(label, (8, 0))
        plate.set_alpha(alpha)
        surface.blit(plate, ((WIDTH - plate.get_width()) // 2, 100))

    def _draw_clear_banner(self, surface: pygame.Surface) -> None:
        if self.clear_banner_timer <= 0 or self.show_map:
            return
        alpha = min(255, int(255 * self.clear_banner_timer / 0.6))
        title = self.loc.get("ui.hud.room_cleared", "此处已清")
        label = self.font_title.render(title, True, (238, 214, 160))
        width = label.get_width() + 32
        card = pygame.Surface((width, 22), pygame.SRCALPHA)
        card.fill((8, 7, 6, 170))
        pygame.draw.rect(card, (150, 116, 68), card.get_rect(), 1)
        card.blit(label, ((width - label.get_width()) // 2, 2))
        card.set_alpha(alpha)
        surface.blit(card, ((WIDTH - width) // 2, 124))

    def _map_center(self, pos: tuple[int, int]) -> tuple[int, int]:
        gx, gy = pos
        return 86 + gx * 58, 132 + gy * 44

    def _draw_minimap(self, surface: pygame.Surface) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((5, 5, 4, 210))
        surface.blit(overlay, (0, 0))
        panel = pygame.Rect(24, 22, WIDTH - 48, HEIGHT - 44)
        pygame.draw.rect(surface, (10, 9, 8), panel)
        pygame.draw.rect(surface, (150, 116, 68), panel, 1)
        title = self.loc.get("ui.map.title", "青篁岭 · 竹坞舆图")
        title_surf = self.font_title.render(title, True, (238, 214, 160))
        surface.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 30))
        subtitle = self.loc.get("ui.map.subtitle", "已探索 {n}/{total}").format(
            n=len(self.discovered), total=len(self.rooms)
        )
        sub_surf = self.font_info.render(subtitle, True, (166, 158, 138))
        surface.blit(sub_surf, (WIDTH // 2 - sub_surf.get_width() // 2, 48))

        shown: set[str] = set()
        for room_id, room in self.rooms.items():
            if room_id not in self.discovered:
                continue
            for exit_ in room.exits:
                key = tuple(sorted((room_id, exit_.target)))
                if key in shown:
                    continue
                shown.add(key)
                x1, y1 = self._map_center(room.map_pos)
                target = self.rooms[exit_.target]
                x2, y2 = self._map_center(target.map_pos)
                if exit_.target in self.discovered:
                    pygame.draw.line(
                        surface, (110, 96, 68), (x1, y1), (x2, y2), 1
                    )
                else:
                    pygame.draw.line(
                        surface, (62, 56, 46), (x1, y1), (x2, y2), 1
                    )

        unknown: set[str] = set()
        for room_id in self.discovered:
            for exit_ in self.rooms[room_id].exits:
                if exit_.target not in self.discovered:
                    unknown.add(exit_.target)
        for room_id in unknown:
            pos = self._map_center(self.rooms[room_id].map_pos)
            pygame.draw.rect(
                surface, (60, 56, 48), (pos[0] - 8, pos[1] - 5, 16, 10), 1
            )

        for room_id in self.discovered:
            room = self.rooms[room_id]
            x, y = self._map_center(room.map_pos)
            if room_id == self.room.room_id:
                fill = (226, 196, 134)
                border = (255, 232, 174)
            elif room_id in self.cleared:
                fill = (116, 148, 112)
                border = (152, 180, 146)
            else:
                fill = (146, 126, 94)
                border = (188, 164, 120)
            pygame.draw.rect(surface, fill, (x - 7, y - 4, 14, 8))
            pygame.draw.rect(surface, border, (x - 7, y - 4, 14, 8), 1)

        current_name = self.loc.get(self.room.title_key, self.room.room_id)
        label = self.font_info.render(current_name, True, HUD_GOLD)
        surface.blit(label, (WIDTH // 2 - label.get_width() // 2, 206))
        hint = self.loc.get("ui.map.close", "M 关闭舆图")
        hint_surf = self.font_info.render(hint, True, (166, 158, 138))
        surface.blit(
            hint_surf,
            (WIDTH // 2 - hint_surf.get_width() // 2, HEIGHT - 44),
        )

    def _draw_death(self, surface: pygame.Surface) -> None:
        alpha = min(170, int(170 * self.death_timer / 0.6))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 5, 5, alpha))
        surface.blit(overlay, (0, 0))
        if self.death_timer < 0.25:
            return
        title = self.loc.get("ui.death.title", "魂归余烬祠")
        hint = self.loc.get("ui.death.hint", "余烬未熄 · 重头再来")
        title_surf = self.font_title.render(title, True, (238, 214, 160))
        hint_surf = self.font_info.render(hint, True, (188, 172, 138))
        surface.blit(
            title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 112)
        )
        surface.blit(hint_surf, (WIDTH // 2 - hint_surf.get_width() // 2, 134))

    def _draw_fade(self, surface: pygame.Surface) -> None:
        if self.transition is None:
            return
        timer = max(0.0, self.transition["timer"])
        if self.transition["phase"] == "out":
            alpha = int(255 * (1.0 - timer / TRANSITION_TIME))
        else:
            alpha = int(255 * (timer / TRANSITION_TIME))
        fade = pygame.Surface((WIDTH, HEIGHT))
        fade.fill((0, 0, 0))
        fade.set_alpha(max(0, min(255, alpha)))
        surface.blit(fade, (0, 0))
