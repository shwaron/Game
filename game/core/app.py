import pygame

from game import config
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
        self.screen = pygame.Surface(
            (config.INTERNAL_WIDTH, config.INTERNAL_HEIGHT)
        )
        self.clock = pygame.time.Clock()
        self.input = InputManager()
        self.bus = EventBus()
        self.scenes = SceneManager()
        self.running = True
        self._accumulator = 0.0
        self._scale = min(
            config.WINDOW_WIDTH // config.INTERNAL_WIDTH,
            config.WINDOW_HEIGHT // config.INTERNAL_HEIGHT,
        )
        self.scenes.push(TitleScene(self))

    # -- 场景切换 -------------------------------------------------------
    def start_run(self) -> None:
        """开一局新回环；标题、暂停与结算页统一走这里。"""
        from game.scenes.run import RunScene

        self.scenes.replace(RunScene(self))

    def return_to_title(self) -> None:
        from game.scenes.title import TitleScene

        self.scenes.replace(TitleScene(self))

    def quit(self) -> None:
        self.running = False

    def run(self) -> None:
        while self.running:
            frame_dt = min(self.clock.tick(config.FPS) / 1000.0, config.MAX_FRAME_DT)
            events = pygame.event.get()
            self.input.update(events)
            for event in events:
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.scenes.current.handle_event(event)
            self._accumulator += frame_dt
            while self._accumulator >= config.DT:
                self.scenes.current.update(config.DT)
                self.input.end_step()
                self._accumulator -= config.DT
            self._draw()
        pygame.quit()

    def _draw(self) -> None:
        self.scenes.current.draw(self.screen)
        scaled = pygame.transform.scale(
            self.screen,
            (
                config.INTERNAL_WIDTH * self._scale,
                config.INTERNAL_HEIGHT * self._scale,
            ),
        )
        self.window.fill((0, 0, 0))
        self.window.blit(
            scaled,
            (
                (config.WINDOW_WIDTH - scaled.get_width()) // 2,
                (config.WINDOW_HEIGHT - scaled.get_height()) // 2,
            ),
        )
        pygame.display.flip()