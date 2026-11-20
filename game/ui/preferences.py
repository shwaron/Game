"""UI 偏好的临时存放点（操作提示开关等）。

A 的 SaveManager 尚未落地，这里先用 ``%APPDATA%/Emberloop/preferences.json``
做原子写入，字段独立于 meta 存档；等 SaveManager 提供 settings 段后整体迁走。
"""

import json
import os
from pathlib import Path

DEFAULTS: dict = {
    "show_hints": True,
}

_cache: dict | None = None


def path() -> Path:
    base = os.environ.get("APPDATA")
    root = Path(base) if base else Path.home() / ".emberloop"
    return root / "Emberloop" / "preferences.json" if base else root / "preferences.json"


def load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    data = dict(DEFAULTS)
    target = path()
    try:
        with open(target, "r", encoding="utf-8") as handle:
            stored = json.load(handle)
        if isinstance(stored, dict):
            data.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    _cache = data
    return _cache


def get(key: str, default=None):
    return load().get(key, DEFAULTS.get(key, default))


def set_value(key: str, value) -> None:
    data = load()
    data[key] = value
    save(data)


def save(data: dict) -> None:
    global _cache
    _cache = dict(data)
    target = path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_suffix(".tmp")
        with open(temp, "w", encoding="utf-8") as handle:
            json.dump(_cache, handle, ensure_ascii=False, indent=2)
        os.replace(temp, target)
    except OSError:
        # 偏好写不进去不应打断游戏，内存里的值继续生效。
        pass


def reset_cache() -> None:
    """测试用：丢弃内存缓存，下一次访问重新读盘。"""
    global _cache
    _cache = None
