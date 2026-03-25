"""Window management: tiling, splitting, and cycling."""

import logging
from typing import Any, Dict, Optional, Tuple
import ApplicationServices as AX
import Quartz
from AppKit import NSScreen, NSWorkspace

log = logging.getLogger(__name__)


class WindowManager:
    """Manages window operations like tiling, centering, and maximizing."""

    def __init__(self) -> None:
        self._saved_frames: Dict[int, Tuple[float, float, float, float]] = {}

    def _get_focused_window(self) -> Optional[Any]:
        system = AX.AXUIElementCreateSystemWide()
        
        # Method 1: Get it from the focused element (most reliable for sub-windows/web-apps)
        err, focused_el = AX.AXUIElementCopyAttributeValue(system, "AXFocusedUIElement", None)
        if err == 0 and focused_el:
            err, win = AX.AXUIElementCopyAttributeValue(focused_el, "AXWindow", None)
            if err == 0 and win:
                log.debug("Found focused window via focused element")
                return win
        else:
            log.debug("No focused element found (err=%d)", err)

        # Method 2: Fallback to application's focused window (system-wide)
        err, focused_app = AX.AXUIElementCopyAttributeValue(system, "AXFocusedApplication", None)
        if err == 0 and focused_app:
            err, focused_win = AX.AXUIElementCopyAttributeValue(focused_app, "AXFocusedWindow", None)
            if err == 0 and focused_win:
                log.debug("Found focused window via system-wide application")
                return focused_win

        # Method 3: Fallback to NSWorkspace frontmost application (very robust)
        front_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if front_app:
            pid = front_app.processIdentifier()
            app_ref = AX.AXUIElementCreateApplication(pid)
            err, focused_win = AX.AXUIElementCopyAttributeValue(app_ref, "AXFocusedWindow", None)
            if err == 0 and focused_win:
                log.debug("Found focused window via NSWorkspace PID %d", pid)
                return focused_win
            else:
                log.debug("NSWorkspace app PID %d has no focused window (err=%d)", pid, err)
        
        log.warning("Could not find any focused window via all methods")
        return None

    def _get_visible_rect(self) -> Tuple[float, float, float, float]:
        screens = NSScreen.screens()
        if not screens:
            return 0.0, 0.0, 0.0, 0.0
        
        primary_screen = screens[0]
        primary_height = primary_screen.frame().size.height
        
        focused_screen = NSScreen.mainScreen() or primary_screen
        visible = focused_screen.visibleFrame()
        
        ax_x = visible.origin.x
        # Accessibility coordinates are top-down from the primary screen's top.
        # visible.origin.y is bottom-up from the primary screen's bottom.
        ax_y = primary_height - (visible.origin.y + visible.size.height)
        
        return ax_x, ax_y, visible.size.width, visible.size.height

    def _get_window_frame(self, win: Any) -> Optional[Tuple[float, float, float, float]]:
        err, pos_val = AX.AXUIElementCopyAttributeValue(win, "AXPosition", None)
        err2, size_val = AX.AXUIElementCopyAttributeValue(win, "AXSize", None)
        if pos_val and size_val:
            _, p = AX.AXValueGetValue(pos_val, AX.kAXValueCGPointType, None)
            _, s = AX.AXValueGetValue(size_val, AX.kAXValueCGSizeType, None)
            return p.x, p.y, s.width, s.height
        return None

    def _set_window_frame(self, win: Any, x: float, y: float, w: float, h: float) -> None:
        pos = AX.AXValueCreate(AX.kAXValueCGPointType, Quartz.CGPointMake(x, y))
        size = AX.AXValueCreate(AX.kAXValueCGSizeType, Quartz.CGSizeMake(w, h))
        if pos and size:
            # Set size first, then position, then size again. 
            # This handles cases where the window can't be at (x, y) with its current size,
            # or can't be size (w, h) at its current position.
            AX.AXUIElementSetAttributeValue(win, "AXSize", size)
            err1 = AX.AXUIElementSetAttributeValue(win, "AXPosition", pos)
            err2 = AX.AXUIElementSetAttributeValue(win, "AXSize", size)
            if err1 != 0 or err2 != 0:
                log.warning("Failed to set window frame: pos_err=%d, size_err=%d", err1, err2)
            else:
                log.debug("Set window frame to x=%.1f, y=%.1f, w=%.1f, h=%.1f", x, y, w, h)

    def tile_window(self, quadrant: int) -> None:
        win = self._get_focused_window()
        if not win:
            return
        ax_x, ax_y, ax_w, ax_h = self._get_visible_rect()
        hw, hh = ax_w / 2, ax_h / 2
        coords = {
            1: (ax_x, ax_y),
            2: (ax_x + hw, ax_y),
            3: (ax_x, ax_y + hh),
            4: (ax_x + hw, ax_y + hh),
        }
        if quadrant in coords:
            x, y = coords[quadrant]
            self._set_window_frame(win, x, y, hw, hh)

    def tile_window_sixth(self, col: int, row: int) -> None:
        win = self._get_focused_window()
        if not win:
            return
        ax_x, ax_y, ax_w, ax_h = self._get_visible_rect()
        tw, hh = ax_w / 3, ax_h / 2
        self._set_window_frame(win, ax_x + col * tw, ax_y + row * hh, tw, hh)

    def tile_window_half(self, side: str) -> None:
        win = self._get_focused_window()
        if not win:
            return
        ax_x, ax_y, ax_w, ax_h = self._get_visible_rect()
        frames = {
            "left": (ax_x, ax_y, ax_w / 2, ax_h),
            "right": (ax_x + ax_w / 2, ax_y, ax_w / 2, ax_h),
            "top": (ax_x, ax_y, ax_w, ax_h / 2),
            "bottom": (ax_x, ax_y + ax_h / 2, ax_w, ax_h / 2),
        }
        if side in frames:
            self._set_window_frame(win, *frames[side])

    def center_window(self) -> None:
        win = self._get_focused_window()
        if not win:
            return
        ax_x, ax_y, ax_w, ax_h = self._get_visible_rect()
        w = ax_w / 2
        self._set_window_frame(win, ax_x + (ax_w - w) / 2, ax_y, w, ax_h)

    def toggle_maximize(self) -> None:
        win = self._get_focused_window()
        if not win:
            return
        key = hash(win)
        if key in self._saved_frames:
            self._set_window_frame(win, *self._saved_frames.pop(key))
        else:
            frame = self._get_window_frame(win)
            if frame:
                self._saved_frames[key] = frame
                self._set_window_frame(win, *self._get_visible_rect())
