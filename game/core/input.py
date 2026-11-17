import pygame

KEY = "key"
MOUSE = "mouse"

DEFAULT_BINDINGS: dict[str, list[tuple[str, int]]] = {
    "move_left": [(KEY, pygame.K_a), (KEY, pygame.K_LEFT)],
    "move_right": [(KEY, pygame.K_d), (KEY, pygame.K_RIGHT)],
    "jump": [(KEY, pygame.K_SPACE)],
    "dash": [(KEY, pygame.K_LSHIFT), (KEY, pygame.K_RSHIFT), (MOUSE, 2)],
    "attack": [(KEY, pygame.K_j), (MOUSE, 1)],
    "offhand": [(KEY, pygame.K_k), (MOUSE, 3)],
    "skill1": [(KEY, pygame.K_u)],
    "skill2": [(KEY, pygame.K_i)],
    "interact": [(KEY, pygame.K_e)],
    "swap": [(KEY, pygame.K_q), (KEY, pygame.K_TAB)],
    "map": [(KEY, pygame.K_m)],
    "pause": [(KEY, pygame.K_ESCAPE)],
    "down": [(KEY, pygame.K_s), (KEY, pygame.K_DOWN)],
}


class InputManager:
    def __init__(self) -> None:
        self._bindings = {a: list(b) for a, b in DEFAULT_BINDINGS.items()}
        self._pressed: set[str] = set()
        self._just: set[str] = set()

    def update(self, events) -> None:
        keys = pygame.key.get_pressed()
        mouse = pygame.mouse.get_pressed(5)
        now: set[str] = set()
        for action, bindings in self._bindings.items():
            for kind, code in bindings:
                held = keys[code] if kind == KEY else mouse[code - 1]
                if held:
                    now.add(action)
                    break
        self._just = now - self._pressed
        self._pressed = now

    def end_step(self) -> None:
        self._just = set()

    def is_action_pressed(self, action: str) -> bool:
        return action in self._pressed

    def is_action_just_pressed(self, action: str) -> bool:
        return action in self._just

    def get_axis(self, axis: str) -> float:
        if axis == "move_x":
            return float(self.is_action_pressed("move_right")) - float(
                self.is_action_pressed("move_left")
            )
        if axis == "move_y":
            return float(self.is_action_pressed("down")) - float(
                self.is_action_pressed("jump")
            )
        raise ValueError(f"unknown axis: {axis}")

    def rebind(self, action: str, binding) -> None:
        self._bindings[action] = list(binding)