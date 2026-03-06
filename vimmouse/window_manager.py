"""Window tiling: move/resize the focused window to a screen quadrant."""

import logging

import ApplicationServices as AX
import Quartz
from AppKit import NSScreen

log = logging.getLogger(__name__)


def _get_focused_window():
    """Return the AX element for the focused window, or None."""
    system = AX.AXUIElementCreateSystemWide()
    err, focused_app = AX.AXUIElementCopyAttributeValue(
        system, "AXFocusedApplication", None
    )
    if err != 0 or not focused_app:
        log.warning("window_manager: no focused app")
        return None
    err, focused_win = AX.AXUIElementCopyAttributeValue(
        focused_app, "AXFocusedWindow", None
    )
    if err != 0 or not focused_win:
        log.warning("window_manager: no focused window")
        return None
    return focused_win


def _get_visible_rect():
    """Return (ax_x, ax_y, ax_w, ax_h) in AX (top-left origin) coordinates."""
    screen = NSScreen.mainScreen()
    full = screen.frame()
    visible = screen.visibleFrame()
    ax_x = visible.origin.x
    ax_y = full.size.height - visible.origin.y - visible.size.height
    return ax_x, ax_y, visible.size.width, visible.size.height


def _set_window_frame(win, x, y, w, h):
    """Move and resize a window via AX."""
    pos = AX.AXValueCreate(AX.kAXValueCGPointType, Quartz.CGPointMake(x, y))
    size = AX.AXValueCreate(AX.kAXValueCGSizeType, Quartz.CGSizeMake(w, h))
    AX.AXUIElementSetAttributeValue(win, "AXPosition", pos)
    AX.AXUIElementSetAttributeValue(win, "AXSize", size)


def tile_window(quadrant):
    """Move and resize the focused window to the given screen quadrant (1-4).

    1 = top-left, 2 = top-right, 3 = bottom-left, 4 = bottom-right.
    """
    win = _get_focused_window()
    if not win:
        return

    ax_x, ax_y, ax_w, ax_h = _get_visible_rect()
    half_w = ax_w / 2
    half_h = ax_h / 2

    if quadrant == 1:    # top-left
        x, y = ax_x, ax_y
    elif quadrant == 2:  # top-right
        x, y = ax_x + half_w, ax_y
    elif quadrant == 3:  # bottom-left
        x, y = ax_x, ax_y + half_h
    elif quadrant == 4:  # bottom-right
        x, y = ax_x + half_w, ax_y + half_h
    else:
        return

    _set_window_frame(win, x, y, half_w, half_h)
    log.info("tile_window: quadrant=%d pos=(%.0f,%.0f) size=(%.0f,%.0f)",
             quadrant, x, y, half_w, half_h)


def tile_window_sixth(col, row):
    """Move and resize the focused window to a sixth of the screen.

    col: 0=left, 1=center, 2=right
    row: 0=top, 1=bottom
    """
    win = _get_focused_window()
    if not win:
        return

    ax_x, ax_y, ax_w, ax_h = _get_visible_rect()
    third_w = ax_w / 3
    half_h = ax_h / 2

    x = ax_x + col * third_w
    y = ax_y + row * half_h

    _set_window_frame(win, x, y, third_w, half_h)
    log.info("tile_window_sixth: col=%d row=%d pos=(%.0f,%.0f) size=(%.0f,%.0f)",
             col, row, x, y, third_w, half_h)


def tile_window_half(side):
    """Move and resize the focused window to half the screen.

    side: 'left', 'right', 'top', 'bottom'
    """
    win = _get_focused_window()
    if not win:
        return

    ax_x, ax_y, ax_w, ax_h = _get_visible_rect()

    if side == "left":
        x, y, w, h = ax_x, ax_y, ax_w / 2, ax_h
    elif side == "right":
        x, y, w, h = ax_x + ax_w / 2, ax_y, ax_w / 2, ax_h
    elif side == "top":
        x, y, w, h = ax_x, ax_y, ax_w, ax_h / 2
    elif side == "bottom":
        x, y, w, h = ax_x, ax_y + ax_h / 2, ax_w, ax_h / 2
    else:
        return

    _set_window_frame(win, x, y, w, h)
    log.info("tile_window_half: side=%s pos=(%.0f,%.0f) size=(%.0f,%.0f)",
             side, x, y, w, h)


def center_window():
    """Center the focused window at half screen size."""
    win = _get_focused_window()
    if not win:
        return

    ax_x, ax_y, ax_w, ax_h = _get_visible_rect()
    w = ax_w / 2
    h = ax_h
    x = ax_x + (ax_w - w) / 2
    y = ax_y

    _set_window_frame(win, x, y, w, h)
    log.info("center_window: pos=(%.0f,%.0f) size=(%.0f,%.0f)", x, y, w, h)


def _get_window_frame(win):
    """Return (x, y, w, h) of a window, or None."""
    err, pos_val = AX.AXUIElementCopyAttributeValue(win, "AXPosition", None)
    err2, size_val = AX.AXUIElementCopyAttributeValue(win, "AXSize", None)
    if pos_val is None or size_val is None:
        return None
    _, p = AX.AXValueGetValue(pos_val, AX.kAXValueCGPointType, None)
    _, s = AX.AXValueGetValue(size_val, AX.kAXValueCGSizeType, None)
    return (p.x, p.y, s.width, s.height)


# Store original frames keyed by (pid, window title) for toggle restore
_saved_frames = {}


def toggle_maximize():
    """Toggle between maximized and original size."""
    win = _get_focused_window()
    if not win:
        return

    frame = _get_window_frame(win)
    if not frame:
        return

    key = hash(win)

    if key in _saved_frames:
        # Restore saved frame
        _set_window_frame(win, *_saved_frames.pop(key))
        log.info("toggle_maximize: restored %s", key)
    else:
        # Save current frame and maximize
        _saved_frames[key] = frame
        ax_x, ax_y, ax_w, ax_h = _get_visible_rect()
        _set_window_frame(win, ax_x, ax_y, ax_w, ax_h)
        log.info("toggle_maximize: maximized %s", key)
