import pygame

from game import config
from game.core import hd
from game.core.event_bus import EventBus
from game.core.input import InputManager
from game.core.scene_manager import SceneManager
from game.scenes.title import TitleScene


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.key.stop_text_input()
        pygame.display.set_caption("余烬回环 — 青篁岭 · 竹坞客栈")
        self.window = pygame.display.set_mode(
            (config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        )
        self.screen = hd.Surface(
            (config.INTERNAL_WIDTH, config.INTERNAL_HEIGHT)
        )
        self.clock = pygame.time.Clock()
        self.input = InputManager()
        self.bus = EventBus()
        self.scenes = SceneManager()
        self.running = True
        self.last_weapon_id = None
        self._accumulator = 0.0
        self._scale = 1
        self._recompute_scale()
        self.scenes.push(TitleScene(self))

    def _recompute_scale(self) -> None:
        """按实际窗口大小取最大整数倍，保证像素画不变形、不留黑边。"""
        width, height = self.window.get_size()
        self._scale = max(
            1,
            min(
                width // config.INTERNAL_WIDTH,
                height // config.INTERNAL_HEIGHT,
            ),
        )

    # -- 场景切换 -------------------------------------------------------
    def start_run(self, weapon_id: str | None = None) -> None:
        """开一局新回环；标题、暂停与结算页统一走这里。"""
        from game.scenes.run import RunScene

        weapon_id = weapon_id or self.last_weapon_id or "tachi"
        self.last_weapon_id = weapon_id
        self.scenes.replace(RunScene(self, weapon_id))
        # 用鼠标点「开始」时，左键同时是攻击键；清掉本次按下，避免开局自动挥一刀。
        self.input.end_step()

    def open_weapon_select(self) -> None:
        from game.scenes.weapon_select import WeaponSelectScene

        self.scenes.replace(
            WeaponSelectScene(
                self,
                on_confirm=self.start_run,
                on_cancel=self.return_to_title,
                current_id=self.last_weapon_id,
            )
        )
        self.input.end_step()

    def return_to_title(self) -> None:
        from game.scenes.title import TitleScene

        self.scenes.replace(TitleScene(self))
        self.input.end_step()

    def quit(self) -> None:
        self.running = False

    # -- 输入坐标 -------------------------------------------------------
    def internal_pos(self, pos) -> tuple[int, int]:
        """窗口坐标 → 480x270 内部坐标，供菜单与按钮命中判定。"""
        width, height = self.window.get_size()
        scaled_w = config.INTERNAL_WIDTH * self._scale
        scaled_h = config.INTERNAL_HEIGHT * self._scale
        ox = (width - scaled_w) // 2
        oy = (height - scaled_h) // 2
        return (
            int((pos[0] - ox) // self._scale),
            int((pos[1] - oy) // self._scale),
        )

    def internal_event(self, event):
        """把鼠标事件换算到内部坐标；其余事件原样返回。"""
        if event.type not in (
            pygame.MOUSEMOTION,
            pygame.MOUSEBUTTONDOWN,
            pygame.MOUSEBUTTONUP,
        ):
            return event
        data = dict(event.dict)
        data["pos"] = self.internal_pos(event.pos)
        if "rel" in data:
            data["rel"] = (
                data["rel"][0] // self._scale,
                data["rel"][1] // self._scale,
            )
        return pygame.event.Event(event.type, data)

    def run(self) -> None:
        while self.running:
            frame_dt = min(self.clock.tick(config.FPS) / 1000.0, config.MAX_FRAME_DT)
            events = pygame.event.get()
            self.input.update(events)
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scenes.current.handle_event(self.internal_event(event))
            self._accumulator += frame_dt
            while self._accumulator >= config.DT:
                self.scenes.current.update(config.DT)
                self.input.end_step()
                self._accumulator -= config.DT
            self._draw()
        pygame.quit()

    def _draw(self) -> None:
        self.scenes.current.draw(self.screen)
        source = self.screen.target
        size = (
            config.INTERNAL_WIDTH * self._scale,
            config.INTERNAL_HEIGHT * self._scale,
        )
        if size[0] % source.get_width() == 0 and size[1] % source.get_height() == 0:
            scaled = pygame.transform.scale(source, size)
        else:
            scaled = pygame.transform.smoothscale(source, size)
        self.window.fill((0, 0, 0))
        width, height = self.window.get_size()
        self.window.blit(
            scaled,
            (
                (width - scaled.get_width()) // 2,
                (height - scaled.get_height()) // 2,
            ),
        )
        pygame.display.flip()