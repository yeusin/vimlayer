import sys
from unittest.mock import MagicMock
from vimlayer import config
import Quartz

def test_default_keybindings():
    bindings = config.default_keybindings()
    assert "move_left" in bindings
    assert bindings["move_left"]["keycode"] == 4
    # Media keys
    assert bindings["volume_mute"]["keycode"] == 109
    assert bindings["volume_down"]["keycode"] == 103
    assert bindings["volume_up"]["keycode"] == 111


def test_load_defaults(tmp_path, monkeypatch):
    # Redirect config path to a temp file
    temp_config = tmp_path / "config.json"
    monkeypatch.setattr(config, "_CONFIG_PATH", str(temp_config))

    # Should return defaults when file doesn't exist
    data = config.load()
    assert data["keycode"] == 49


def test_save_and_load(tmp_path, monkeypatch):
    temp_config = tmp_path / "config.json"
    monkeypatch.setattr(config, "_CONFIG_PATH", str(temp_config))

    test_data = {"keycode": 123, "keybindings": {"move_left": {"keycode": 99}}}
    config.save(test_data)

    loaded = config.load()
    assert loaded["keycode"] == 123
    assert loaded["keybindings"]["move_left"]["keycode"] == 99


def test_load_keybindings_merge(tmp_path, monkeypatch):
    temp_config = tmp_path / "config.json"
    monkeypatch.setattr(config, "_CONFIG_PATH", str(temp_config))

    # Save a user override
    user_data = {"keybindings": {"move_left": {"keycode": 99}}}
    config.save(user_data)

    merged = config.load_keybindings()
    # Overridden
    assert merged["move_left"]["keycode"] == 99
    # Still has other defaults
    assert merged["move_right"]["keycode"] == 37


def test_format_hotkey():
    # 49 is Space
    assert config.format_hotkey(49, 0, use_symbols=False) == "Space"
    
    # Command + Space
    cmd_flag = Quartz.kCGEventFlagMaskCommand
    assert config.format_hotkey(49, cmd_flag, use_symbols=False) == "Cmd+Space"
    assert config.format_hotkey(49, cmd_flag, use_symbols=True) == "\u2318Space"
    
    # Command + Shift + Space
    cmd_shift_flag = Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskShift
    assert config.format_hotkey(49, cmd_shift_flag, use_symbols=False) == "Shift+Cmd+Space"


def test_format_binding():
    # Simple binding
    assert config.format_binding({"keycode": 4}, use_symbols=False) == "H"
    
    # Binding with modifiers
    assert config.format_binding({"keycode": 11, "ctrl": True}, use_symbols=False) == "Ctrl+B"
    assert config.format_binding({"keycode": 11, "ctrl": True}, use_symbols=True) == "\u2303B"
    
    # List of bindings
    specs = [{"keycode": 4}, {"keycode": 38}]
    assert config.format_binding(specs, use_symbols=False) == "H / J"
