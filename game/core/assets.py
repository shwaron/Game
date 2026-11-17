import json
from pathlib import Path

import pygame

from game.config import resource_path

_images: dict[str, pygame.Surface] = {}
_sounds: dict[str, pygame.mixer.Sound] = {}
_fonts: dict[tuple[str, int], pygame.font.Font] = {}
_json: dict[str, dict] = {}


def load_image(rel: str) -> pygame.Surface:
    if rel not in _images:
        _images[rel] = pygame.image.load(str(resource_path(rel))).convert_alpha()
    return _images[rel]


def load_sound(rel: str) -> pygame.mixer.Sound:
    if rel not in _sounds:
        _sounds[rel] = pygame.mixer.Sound(str(resource_path(rel)))
    return _sounds[rel]


def load_font(rel: str, size: int) -> pygame.font.Font:
    key = (rel, size)
    if key not in _fonts:
        path = resource_path(rel)
        _fonts[key] = pygame.font.Font(str(path) if path.exists() else None, size)
    return _fonts[key]


def load_json(rel: str) -> dict:
    if rel not in _json:
        with open(resource_path(rel), "r", encoding="utf-8") as f:
            _json[rel] = json.load(f)
    return _json[rel]