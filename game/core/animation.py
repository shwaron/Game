from __future__ import annotations

import pygame

from game.core.assets import load_image


class AnimationClip:
    def __init__(
        self,
        name: str,
        sheet: str,
        frames: int,
        fps: float,
        loop: bool = True,
        origin: tuple[int, int] = (0, 0),
        events: list[dict] | None = None,
        image_scale: int = 1,
    ) -> None:
        self.name = name
        self.sheet = sheet
        self.frames = max(1, int(frames))
        self.fps = max(1e-6, float(fps))
        self.loop = loop
        self.origin = (int(origin[0]), int(origin[1]))
        self.events = list(events or [])
        self.image_scale = max(1, int(image_scale))

    @property
    def frame_duration(self) -> float:
        return 1.0 / self.fps


def build_clips(section: dict) -> dict[str, AnimationClip]:
    origin = tuple(section.get("origin", (0, 0)))
    image_scale = int(section.get("image_scale", 1))
    clips: dict[str, AnimationClip] = {}
    for name, spec in section.get("clips", {}).items():
        clips[name] = AnimationClip(
            name,
            spec["sheet"],
            spec.get("frames", 1),
            spec.get("fps", 8),
            spec.get("loop", True),
            origin,
            spec.get("events"),
            image_scale,
        )
    return clips


_frame_cache: dict[tuple[str, int, int, int], tuple[list, list]] = {}


def _resize_frame(frame, source_scale: int, target_scale: int):
    if source_scale == target_scale:
        return frame
    width, height = frame.get_size()
    if target_scale == source_scale * 2:
        return pygame.transform.scale2x(frame)
    factor = target_scale / source_scale
    size = (max(1, round(width * factor)), max(1, round(height * factor)))
    if factor < 1:
        return pygame.transform.scale(frame, size)
    return pygame.transform.smoothscale(frame, size)


def _clip_frames(clip: AnimationClip, scale: int = 1) -> tuple[list, list]:
    key = (clip.sheet, clip.frames, clip.image_scale, scale)
    if key not in _frame_cache:
        rel = clip.sheet if clip.sheet.startswith("assets/") else f"assets/{clip.sheet}"
        sheet = load_image(rel)
        width = sheet.get_width() // clip.frames
        height = sheet.get_height()
        normal = [
            sheet.subsurface(pygame.Rect(i * width, 0, width, height)).copy()
            for i in range(clip.frames)
        ]
        normal = [
            _resize_frame(frame, clip.image_scale, scale) for frame in normal
        ]
        flipped = [pygame.transform.flip(frame, True, False) for frame in normal]
        _frame_cache[key] = (normal, flipped)
    return _frame_cache[key]


class Animator:
    def __init__(self, clips: dict[str, AnimationClip], on_event=None) -> None:
        self.clips = clips
        self.on_event = on_event
        self.current = ""
        self.frame_index = 0
        self.finished = False
        self._time = 0.0
        self._fired: set[int] = set()

    def play(self, name: str, restart: bool = False) -> None:
        if name not in self.clips:
            name = "idle" if "idle" in self.clips else next(iter(self.clips), "")
        if not name or (name == self.current and not restart):
            return
        self.current = name
        self.frame_index = 0
        self._time = 0.0
        self.finished = False
        self._fired.clear()
        self._fire_events(0)

    def update(self, dt: float) -> None:
        clip = self.clips.get(self.current)
        if not clip or self.finished:
            return
        self._time += dt
        while self._time >= clip.frame_duration:
            self._time -= clip.frame_duration
            if self.frame_index + 1 < clip.frames:
                self.frame_index += 1
            elif clip.loop:
                self.frame_index = 0
                self._fired.clear()
            else:
                self.frame_index = clip.frames - 1
                self.finished = True
                break
            self._fire_events(self.frame_index)

    def _fire_events(self, frame: int) -> None:
        clip = self.clips.get(self.current)
        if not clip or not self.on_event:
            return
        for index, event in enumerate(clip.events):
            if event.get("frame", 0) == frame and index not in self._fired:
                self._fired.add(index)
                self.on_event(event.get("name", ""), frame)

    def draw(
        self, surface: pygame.Surface, topleft: tuple[int, int], facing: int
    ) -> None:
        clip = self.clips.get(self.current)
        if not clip:
            return
        scale = getattr(surface, "scale", 1)
        normal, flipped = _clip_frames(clip, scale)
        frame = flipped[self.frame_index] if facing < 0 else normal[self.frame_index]
        dest = (
            topleft[0] * scale - clip.origin[0] * scale,
            topleft[1] * scale - clip.origin[1] * scale,
        )
        if scale > 1:
            surface.blit_native(frame, dest)
        else:
            surface.blit(frame, dest)