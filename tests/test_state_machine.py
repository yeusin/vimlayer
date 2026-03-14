import sys
from unittest.mock import MagicMock, patch
import pytest
from vimlayer.hint_overlay import HintOverlay

@pytest.fixture
def overlay(mocker):
    # Mock dependencies
    mocker.patch("vimlayer.hint_overlay.WindowManager")
    mocker.patch("vimlayer.hint_overlay.WatermarkManager")
    mocker.patch("vimlayer.hint_overlay.CheatSheetOverlay")
    mocker.patch("vimlayer.hint_overlay.Launcher")
    mocker.patch("vimlayer.hint_overlay.MouseController")
    mocker.patch("vimlayer.hint_overlay.config.load", return_value={"auto_insert_mode": True})
    
    # Mock threading.Timer to prevent polling
    mocker.patch("threading.Timer")
    
    # Immediate execution for callAfter
    import PyObjCTools
    PyObjCTools.AppHelper.callAfter.side_effect = lambda f, *args: f(*args)
    
    o = HintOverlay()
    o.window = MagicMock()
    o._launcher.is_visible.return_value = False
    return o


def test_enter_and_exit_insert_mode(overlay):
    # Should start in normal mode
    assert not overlay._insert_mode
    
    # Enter insert mode manually
    overlay.enter_insert_mode(auto=False)
    assert overlay._insert_mode
    assert not overlay._auto_insert
    
    # Exit insert mode
    overlay._exit_insert_mode()
    assert not overlay._insert_mode


def test_auto_insert_mode_logic(overlay, mocker):
    # Mock get_focused_element and is_input_element
    mock_get_focused = mocker.patch("vimlayer.hint_overlay.accessibility.get_focused_element")
    mock_is_input = mocker.patch("vimlayer.hint_overlay.accessibility.is_input_element")
    
    overlay._launcher.is_visible.return_value = False
    
    # 1. Element is focused and is an input element
    mock_get_focused.return_value = "mock_element"
    mock_is_input.return_value = True
    
    overlay._check_focus_and_auto_insert("mock_element")
    
    assert overlay._insert_mode
    assert overlay._auto_insert
    
    # 2. Element changes to non-input element
    mock_is_input.return_value = False
    
    overlay._check_focus_and_auto_insert("mock_element2")
    
    # Should exit insert mode automatically
    assert not overlay._insert_mode
    assert not overlay._auto_insert


def test_auto_insert_disabled(overlay, mocker):
    # Simulate user disabling auto_insert_mode in config
    overlay._auto_insert_enabled = False

    mock_get_focused = mocker.patch("vimlayer.hint_overlay.accessibility.get_focused_element")
    mock_is_input = mocker.patch("vimlayer.hint_overlay.accessibility.is_input_element")

    overlay._launcher.is_visible.return_value = False

    mock_get_focused.return_value = "mock_element"
    mock_is_input.return_value = True

    overlay._check_focus_and_auto_insert("mock_element")

    # Should NOT enter insert mode
    assert not overlay._insert_mode
