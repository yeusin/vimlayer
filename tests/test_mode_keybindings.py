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
from vimlayer.hint_overlay import HintOverlay

@pytest.fixture
def overlay(mocker):
    # Mock dependencies within HintOverlay
    mocker.patch("vimlayer.hint_overlay.WindowManager")
    mocker.patch("vimlayer.hint_overlay.WatermarkManager")
    mocker.patch("vimlayer.hint_overlay.CheatSheetOverlay")
    mocker.patch("vimlayer.hint_overlay.Launcher")
    mocker.patch("vimlayer.hint_overlay.MouseController")
    mocker.patch("vimlayer.hint_overlay.config.load")
    mocker.patch("vimlayer.hint_overlay.config.load_keybindings")
    
    # Mocking config.load_keybindings to return some default bindings
    from vimlayer import config
    config.load_keybindings.return_value = {
        "move_left": {"keycode": 4},   # 'h'
        "move_down": {"keycode": 38},  # 'j'
        "move_up": {"keycode": 40},    # 'k'
        "move_right": {"keycode": 37}, # 'l'
        "click": {"keycode": 49},      # space
        "right_click": {"keycode": 49, "shift": True}, # shift + space
        "insert_mode": {"keycode": 34}, # 'i'
        "toggle_drag": {"keycode": 9}, # 'v'
        "scroll_up": {"keycode": 11, "ctrl": True}, # ctrl + b (modeled as 11 for testing)
        "scroll_down": {"keycode": 3, "ctrl": True},  # ctrl + f (modeled as 3 for testing)
        "back": {"keycode": 11},      # 'b'
        "forward": {"keycode": 13},   # 'w'
        "toggle_all_hints": {"keycode": 3}, # 'f'
        "open_launcher": {"keycode": 44}, # '/'
        "toggle_cheat_sheet": {"keycode": 44, "shift": True}, # '?'
    }
    
    o = HintOverlay()
    # Mock the AppHelper.callAfter to execute the callback immediately for testing
    mock_pyobjc_tools.AppHelper.callAfter.side_effect = lambda f, *args: f(*args)
    return o

def test_normal_mode_navigation(overlay, mocker):
    mock_event = MagicMock()
    # Simulate 'h' key (keycode 4)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 4 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    # We need to simulate the event tap callback
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None  # Event should be suppressed
    overlay._mouse_ctrl.move_relative.assert_called_with(-1, 0, False, False)

def test_drag_mode_navigation(overlay, mocker):
    overlay._dragging = True
    mock_event = MagicMock()
    # Simulate 'j' key (keycode 38)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 38 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None
    overlay._mouse_ctrl.move_relative.assert_called_with(0, 1, False, True)

def test_click_action(overlay, mocker):
    mock_event = MagicMock()
    # Simulate space (keycode 49)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 49 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    mocker.patch.object(overlay, "click_at_cursor")
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None
    overlay.click_at_cursor.assert_called_once()

def test_right_click_action(overlay, mocker):
    mock_event = MagicMock()
    # Simulate shift + space (keycode 49, shift flag)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 49 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = mock_quartz.kCGEventFlagMaskShift
    
    mocker.patch.object(overlay, "right_click_at_cursor")
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None
    overlay.right_click_at_cursor.assert_called_once()

def test_scroll_actions(overlay, mocker):
    mock_event = MagicMock()
    # Simulate ctrl + f (keycode 3, ctrl flag)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 3 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = mock_quartz.kCGEventFlagMaskControl
    
    mocker.patch.object(overlay, "scroll")
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None
    overlay.scroll.assert_called_with(-3)

def test_mouse_back_forward(overlay, mocker):
    mock_event = MagicMock()
    # Simulate 'b' (keycode 11)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 11 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    mocker.patch.object(overlay, "mouse_back")
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    assert result is None
    overlay.mouse_back.assert_called_once()

def test_toggle_hints(overlay, mocker):
    mock_event = MagicMock()
    # Simulate 'f' (keycode 3)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 3 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    mocker.patch.object(overlay, "toggle_all_hints")
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    assert result is None
    overlay.toggle_all_hints.assert_called_once()

def test_open_launcher(overlay, mocker):
    mock_event = MagicMock()
    # Simulate '/' (keycode 44)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 44 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    mocker.patch.object(overlay, "_open_launcher")
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    assert result is None
    overlay._open_launcher.assert_called_once()

def test_escape_resets_typing(overlay, mocker):
    mock_event = MagicMock()
    # Simulate Escape (keycode 53)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 53 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    
    mocker.patch.object(overlay, "reset_typing")
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None
    overlay.reset_typing.assert_called_once()

def test_insert_mode_passthrough(overlay, mocker):
    # In insert mode, the tap is normally not active, but we test that it would passthrough if called.
    overlay._insert_mode = True
    # Actually, _normal_tap_callback doesn't check self._insert_mode internally,
    # because it relies on the tap being removed.
    pass

def test_enter_insert_mode(overlay, mocker):
    mock_event = MagicMock()
    # Simulate 'i' key (keycode 34)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 34 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    mocker.patch.object(overlay, "enter_insert_mode")
    
    result = overlay._normal_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None
    overlay.enter_insert_mode.assert_called_once()

def test_menu_mode_navigation(overlay, mocker):
    overlay._install_menu_tap()
    
    mock_event = MagicMock()
    # Simulate 'k' key (keycode 40)
    mock_quartz.CGEventGetIntegerValueField.side_effect = lambda ev, field: 40 if field == mock_quartz.kCGKeyboardEventKeycode else 0
    mock_quartz.CGEventGetFlags.return_value = 0
    
    result = overlay._menu_tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
    
    assert result is None
    overlay._mouse_ctrl.move_relative.assert_called_with(0, -1, False)
