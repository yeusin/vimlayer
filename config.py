"""Simple JSON config persistence."""

import json
import os

import Quartz

_CONFIG_PATH = os.path.expanduser("~/.config/vimmouse/config.json")

_DEFAULTS = {
    "keycode": 49,  # Space
    "flags": Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskShift,
}


def load():
    """Read config from disk, returning defaults if missing or invalid."""
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(_DEFAULTS)


def save(data):
    """Write config dict to disk."""
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w") as f:
        json.dump(data, f)
