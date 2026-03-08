import pytest
from unittest.mock import MagicMock, patch
import Quartz
from ApplicationServices import kAXValueCGPointType, kAXValueCGSizeType
from vimlayer.hint_overlay import HintOverlay

@pytest.fixture
def overlay(mocker):
    mocker.patch("vimlayer.hint_overlay.MouseController")
    mocker.patch("vimlayer.hint_overlay.WatermarkManager")
    mock_cs = mocker.patch("vimlayer.hint_overlay.CheatSheetOverlay").return_value
    mock_cs.is_visible.return_value = False
    mocker.patch("vimlayer.hint_overlay.WindowManager")
    mocker.patch("vimlayer.hint_overlay.Launcher")
    mocker.patch("vimlayer.config.load_keybindings", return_value={})
    return HintOverlay()

def test_raise_window_with_wid_match(overlay, mocker):
    # Mock AXUIElementCreateApplication
    mock_app_ref = MagicMock()
    mocker.patch("vimlayer.hint_overlay.AX.AXUIElementCreateApplication", return_value=mock_app_ref)
    
    # Mock AXUIElementCopyAttributeValue for AXWindows
    mock_win = MagicMock()
    mocker.patch("vimlayer.hint_overlay.AX.AXUIElementCopyAttributeValue", 
                 side_effect=lambda el, attr, val: (0, [mock_win]) if attr == "AXWindows" else (0, None))
    
    # Mock _AXUIElementGetWindow in hint_overlay
    mock_get_window = mocker.patch("vimlayer.hint_overlay._AXUIElementGetWindow", return_value=(0, 12345))
    
    # Mock AXUIElementPerformAction
    mock_perform = mocker.patch("vimlayer.hint_overlay.AX.AXUIElementPerformAction")
    
    pid = 100
    bounds = {"X": 10, "Y": 20, "Width": 100, "Height": 200}
    target_wid = 12345
    
    overlay._raise_window(pid, bounds, target_wid)
    
    # Should have called _AXUIElementGetWindow
    mock_get_window.assert_called_with(mock_win, None)
    # Should have called AXRaise
    mock_perform.assert_called_with(mock_win, "AXRaise")

def test_raise_window_fallback_to_bounds(overlay, mocker):
    # Mock AXUIElementCreateApplication
    mock_app_ref = MagicMock()
    mocker.patch("vimlayer.hint_overlay.AX.AXUIElementCreateApplication", return_value=mock_app_ref)
    
    # Mock AXUIElementCopyAttributeValue
    mock_win = MagicMock()
    def copy_attr(el, attr, val):
        if attr == "AXWindows":
            return (0, [mock_win])
        if attr in ("AXPosition", "AXSize"):
            return (0, MagicMock())
        return (0, None)
    
    mocker.patch("vimlayer.hint_overlay.AX.AXUIElementCopyAttributeValue", side_effect=copy_attr)
    
    # Mock AXValueGetValue
    def get_value(val, type, out):
        if type == kAXValueCGPointType:
            p = MagicMock()
            p.x, p.y = 10, 20
            return True, p
        if type == kAXValueCGSizeType:
            s = MagicMock()
            s.width, s.height = 100, 200
            return True, s
        return False, None
    mocker.patch("vimlayer.hint_overlay.AX.AXValueGetValue", side_effect=get_value)
    mocker.patch("vimlayer.hint_overlay.AX.kAXValueCGPointType", kAXValueCGPointType)
    mocker.patch("vimlayer.hint_overlay.AX.kAXValueCGSizeType", kAXValueCGSizeType)

    # Mock _AXUIElementGetWindow to return a DIFFERENT ID (no match)
    mocker.patch("vimlayer.hint_overlay._AXUIElementGetWindow", return_value=(0, 99999))
    
    # Mock AXUIElementPerformAction
    mock_perform = mocker.patch("vimlayer.hint_overlay.AX.AXUIElementPerformAction")
    
    pid = 100
    bounds = {"X": 10, "Y": 20, "Width": 100, "Height": 200}
    target_wid = 12345
    
    overlay._raise_window(pid, bounds, target_wid)
    
    # Should have fallen back to bounds match
    mock_perform.assert_called_with(mock_win, "AXRaise")

def test_raise_window_no_wid_helper(overlay, mocker):
    # Mock AXUIElementCreateApplication
    mock_app_ref = MagicMock()
    mocker.patch("vimlayer.hint_overlay.AX.AXUIElementCreateApplication", return_value=mock_app_ref)
    
    # Mock AXUIElementCopyAttributeValue
    mock_win = MagicMock()
    def copy_attr(el, attr, val):
        if attr == "AXWindows":
            return (0, [mock_win])
        if attr in ("AXPosition", "AXSize"):
            return (0, MagicMock())
        return (0, None)
    
    mocker.patch("vimlayer.hint_overlay.AX.AXUIElementCopyAttributeValue", side_effect=copy_attr)

    # Mock AXValueGetValue
    def get_value(val, type, out):
        if type == kAXValueCGPointType:
            p = MagicMock()
            p.x, p.y = 10, 20
            return True, p
        if type == kAXValueCGSizeType:
            s = MagicMock()
            s.width, s.height = 100, 200
            return True, s
        return False, None
    mocker.patch("vimlayer.hint_overlay.AX.AXValueGetValue", side_effect=get_value)
    mocker.patch("vimlayer.hint_overlay.AX.kAXValueCGPointType", kAXValueCGPointType)
    mocker.patch("vimlayer.hint_overlay.AX.kAXValueCGSizeType", kAXValueCGSizeType)
    
    # Mock _AXUIElementGetWindow to be None (unavailable)
    mocker.patch("vimlayer.hint_overlay._AXUIElementGetWindow", None)
    
    # Mock AXUIElementPerformAction
    mock_perform = mocker.patch("vimlayer.hint_overlay.AX.AXUIElementPerformAction")
    
    pid = 100
    bounds = {"X": 10, "Y": 20, "Width": 100, "Height": 200}
    target_wid = 12345
    
    overlay._raise_window(pid, bounds, target_wid)
    
    # Should have matched by bounds
    mock_perform.assert_called_with(mock_win, "AXRaise")
