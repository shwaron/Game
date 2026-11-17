class Scene:
    def enter(self) -> None:
        pass

    def exit(self) -> None:
        pass

    def handle_event(self, event) -> None:
        pass

    def update(self, dt: float) -> None:
        pass

    def draw(self, surface) -> None:
        pass


class SceneManager:
    def __init__(self) -> None:
        self._stack: list[Scene] = []

    def push(self, scene: Scene) -> None:
        self._stack.append(scene)
        scene.enter()

    def pop(self) -> None:
        if self._stack:
            self._stack.pop().exit()

    def replace(self, scene: Scene) -> None:
        if self._stack:
            self._stack.pop().exit()
        self.push(scene)

    @property
    def current(self) -> Scene:
        if not self._stack:
            raise RuntimeError("scene stack is empty")
        return self._stack[-1]