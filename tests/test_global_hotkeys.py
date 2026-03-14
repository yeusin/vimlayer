import sys
from unittest.mock import MagicMock, patch

# Mock Quartz and other macOS-specific modules
mock_quartz = MagicMock()
mock_quartz.kCGEventFlagMaskCommand = 1 << 20
mock_quartz.kCGEventFlagMaskShift = 1 << 17
mock_quartz.kCGEventFlagMaskAlternate = 1 << 19
mock_quartz.kCGEventFlagMaskControl = 1 << 18
mock_quartz.kCGEventKeyDown = 10
mock_quartz.kCGSessionEventTap = 0
mock_quartz.kCGHeadInsertEventTap = 0
mock_quartz.kCGEventTapOptionDefault = 0
mock_quartz.kCGKeyboardEventKeycode = 0
mock_quartz.kCGKeyboardEventAutorepeat = 1
mock_quartz.kCFRunLoopCommonModes = 0

mock_objc = MagicMock()
mock_appkit = MagicMock()
mock_app_services = MagicMock()
mock_pyobjc_tools = MagicMock()
mock_foundation = MagicMock()
mock_core_foundation = MagicMock()

sys.modules["objc"] = mock_objc
sys.modules["Quartz"] = mock_quartz
sys.modules["AppKit"] = mock_appkit
sys.modules["ApplicationServices"] = mock_app_services
sys.modules["PyObjCTools"] = mock_pyobjc_tools
sys.modules["PyObjCTools.AppHelper"] = mock_pyobjc_tools.AppHelper
sys.modules["Foundation"] = mock_foundation
sys.modules["CoreFoundation"] = mock_core_foundation

import pytest
from vimlayer.main import register_global_hotkeys

@pytest.fixture
def overlay(mocker):
    # Mock dependencies within HintOverlay
    mock_overlay = MagicMock()
    return mock_overlay

def test_register_global_hotkeys(overlay, mocker):
    mock_hotkey = mocker.patch("vimlayer.main.hotkey")
    
    cfg = {
        "global_tiling_bindings": {
            "win_tile_1": {"keycode": 18, "cmd": True, "ctrl": True},  # Cmd+Ctrl+1
            "win_center": {"keycode": 8, "cmd": True, "ctrl": True},   # Cmd+Ctrl+C
        }
    }
    
    register_global_hotkeys(overlay, cfg)
    
    # Check that hotkey.unregister_all was called
    mock_hotkey.unregister_all.assert_called_once()
    
    # Check that hotkey.register was called for both actions
    assert mock_hotkey.register.call_count == 2
    
    # Verify first registration (win_tile_1)
    # The callback is a nested function, so we can't easily check equality,
    # but we can check keycode and flags.
    calls = mock_hotkey.register.call_args_list
    
    # Map keycodes to actions for verification
    registered = {call[0][1]: call[0][2] for call in calls}
    
    expected_flags = mock_quartz.kCGEventFlagMaskCommand | mock_quartz.kCGEventFlagMaskControl
    assert registered[18] == expected_flags
    assert registered[8] == expected_flags
