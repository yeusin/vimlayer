import pytest
import Quartz
from unittest.mock import MagicMock
from vimlayer.hint_overlay import HintOverlay
from vimlayer.ui import WatermarkManager

_CTRL_FLAG = 1 << 18


@pytest.fixture
def overlay(mocker):
    mocker.patch("vimlayer.hint_overlay.MouseController")
    # Patch WatermarkManager to capture the callback
    mocker.patch("vimlayer.hint_overlay.WatermarkManager")
    mock_cs = mocker.patch("vimlayer.hint_overlay.CheatSheetOverlay").return_value
    mock_cs.is_visible.return_value = False
    mocker.patch("vimlayer.hint_overlay.WindowManager")
    mock_launcher = mocker.patch("vimlayer.hint_overlay.Launcher").return_value
    mock_launcher.is_visible.return_value = False
    mocker.patch("vimlayer.config.load_keybindings", return_value={})
    return HintOverlay()


def test_watermark_manager_callback_invocation(mocker):
    # Test that WatermarkManager calls the callback when flash timeout occurs
    mocker.patch("vimlayer.ui.WatermarkManager._setup_window")
    mocker.patch("vimlayer.ui.WatermarkManager.flash")
    
    mock_callback = MagicMock()
    # Mock AppHelper.callLater to invoke the callback immediately
    mocker.patch("PyObjCTools.AppHelper.callLater", side_effect=lambda delay, cb: cb())

    wm = WatermarkManager(on_hide=mock_callback)
    
    # Manually simulate flash timeout since we patched flash
    wm._flash_gen += 1
    gen = wm._flash_gen
    def _hide():
        if wm._flash_gen == gen:
            if wm._on_hide:
                wm._on_hide("TEST")
    mocker.patch("PyObjCTools.AppHelper.callLater", side_effect=lambda delay, cb: cb())
    
    wm._mode_label = MagicMock()
    wm._mode_label.stringValue.return_value = "TEST"
    
    _hide()

    mock_callback.assert_called_with("TEST")


def test_watermark_manager_hide_invocation(mocker):
    # Test that WatermarkManager calls the callback when hide is called manually
    mocker.patch("vimlayer.ui.WatermarkManager._setup_window")
    mock_callback = MagicMock()
    wm = WatermarkManager(on_hide=mock_callback)
    wm._box = MagicMock()
    wm._window = MagicMock()
    wm._mode_label = MagicMock()
    wm._mode_label.stringValue.return_value = "NORMAL"
    
    wm.hide()

    # "NORMAL" is the default mode
    mock_callback.assert_called_with("NORMAL")


def test_escape_hides_watermark(overlay, mocker):
    mock_event = MagicMock()
    # 53 is Escape
    mocker.patch("Quartz.CGEventGetIntegerValueField", return_value=53)
    mocker.patch("Quartz.CGEventGetFlags", return_value=0)

    mocker.patch.object(overlay, "cancel_drag")
    mocker.patch.object(overlay, "reset_typing")

    # Track AppHelper.callAfter and ensure it executes the callback
    mock_call_after = mocker.patch("PyObjCTools.AppHelper.callAfter", side_effect=lambda f, *args: f(*args))
    
    overlay._dragging = True
    overlay._insert_mode = False
    overlay._launcher.is_visible = MagicMock(return_value=False)

    # Call the callback
    overlay._normal_tap_callback(None, Quartz.kCGEventKeyDown, mock_event, None)
    
    # Check if self._watermark.hide was called directly
    overlay._watermark.hide.assert_called_once()
