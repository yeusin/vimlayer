import sys
from unittest.mock import MagicMock
import pytest
from vimlayer.window_manager import WindowManager

@pytest.fixture
def wm(mocker):
    manager = WindowManager()
    mocker.patch.object(manager, "_get_focused_window", return_value="mock_window")
    mocker.patch.object(manager, "_set_window_frame")
    
    # Mock _get_visible_rect to return a standard 1080p screen without menu bar
    # (ax_x, ax_y, ax_w, ax_h)
    mocker.patch.object(manager, "_get_visible_rect", return_value=(0.0, 25.0, 1920.0, 1055.0))
    return manager


def test_tile_window_half(wm):
    # Left half
    wm.tile_window_half("left")
    wm._set_window_frame.assert_called_with("mock_window", 0.0, 25.0, 960.0, 1055.0)

    # Right half
    wm.tile_window_half("right")
    wm._set_window_frame.assert_called_with("mock_window", 960.0, 25.0, 960.0, 1055.0)

    # Top half
    wm.tile_window_half("top")
    wm._set_window_frame.assert_called_with("mock_window", 0.0, 25.0, 1920.0, 527.5)

    # Bottom half
    wm.tile_window_half("bottom")
    wm._set_window_frame.assert_called_with("mock_window", 0.0, 552.5, 1920.0, 527.5)


def test_tile_window_quadrants(wm):
    # Top-left (Quadrant 1)
    wm.tile_window(1)
    wm._set_window_frame.assert_called_with("mock_window", 0.0, 25.0, 960.0, 527.5)
    
    # Top-right (Quadrant 2)
    wm.tile_window(2)
    wm._set_window_frame.assert_called_with("mock_window", 960.0, 25.0, 960.0, 527.5)
    
    # Bottom-left (Quadrant 3)
    wm.tile_window(3)
    wm._set_window_frame.assert_called_with("mock_window", 0.0, 552.5, 960.0, 527.5)
    
    # Bottom-right (Quadrant 4)
    wm.tile_window(4)
    wm._set_window_frame.assert_called_with("mock_window", 960.0, 552.5, 960.0, 527.5)


def test_tile_window_sixth(wm):
    # Top-left sixth (col 0, row 0)
    wm.tile_window_sixth(0, 0)
    wm._set_window_frame.assert_called_with("mock_window", 0.0, 25.0, 640.0, 527.5)

    # Bottom-right sixth (col 2, row 1)
    wm.tile_window_sixth(2, 1)
    wm._set_window_frame.assert_called_with("mock_window", 1280.0, 552.5, 640.0, 527.5)


def test_center_window(wm):
    wm.center_window()
    # Width is half of 1920 -> 960
    # X should be (1920 - 960) / 2 = 480
    wm._set_window_frame.assert_called_with("mock_window", 480.0, 25.0, 960.0, 1055.0)


def test_toggle_maximize(wm, mocker):
    mocker.patch.object(wm, "_get_window_frame", return_value=(100.0, 100.0, 500.0, 500.0))
    
    # First toggle: maximizes and saves old frame
    wm.toggle_maximize()
    wm._set_window_frame.assert_called_with("mock_window", 0.0, 25.0, 1920.0, 1055.0)
    
    assert hash("mock_window") in wm._saved_frames
    
    # Second toggle: restores old frame
    wm.toggle_maximize()
    wm._set_window_frame.assert_called_with("mock_window", 100.0, 100.0, 500.0, 500.0)
    
    assert hash("mock_window") not in wm._saved_frames
