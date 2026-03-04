"""Vimium-style hint overlay for clicking UI elements."""

import os
import objc
from AppKit import (
    NSScreen,
    NSColor,
    NSFont,
    NSTextField,
    NSWindow,
    NSMakeRect,
    NSBackingStoreBuffered,
    NSApplication,
    NSFloatingWindowLevel,
    NSWorkspace,
    NSRunningApplication,
)
from PyObjCTools import AppHelper
import ApplicationServices as AX
import accessibility
import mouse

# Hint label style
HINT_FONT_SIZE = 12
HINT_BG_COLOR = (0.15, 0.15, 0.15, 0.85)  # dark gray
HINT_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)  # white
HINT_PADDING = 4
HINT_CORNER_RADIUS = 4

# Window hint style
WIN_HINT_FONT_SIZE = 28
WIN_HINT_BG_COLOR = (0.15, 0.15, 0.15, 0.85)  # dark gray
WIN_HINT_TEXT_COLOR = (1.0, 1.0, 1.0, 1.0)  # white
WIN_HINT_PADDING = 12
WIN_HINT_CORNER_RADIUS = 10


_HINT_CHARS = "ABCDEFGIMNOPQRSTUVWXYZ"  # excludes H, J, K, L (used for movement)

# macOS hardware key codes → Latin letters (input-source-independent)
_KEYCODE_TO_CHAR = {
    0: "a", 1: "s", 2: "d", 3: "f", 4: "h", 5: "g", 6: "z", 7: "x",
    8: "c", 9: "v", 11: "b", 12: "q", 13: "w", 14: "e", 15: "r",
    16: "y", 17: "t", 18: "1", 19: "2", 20: "3", 21: "4", 22: "6",
    23: "5", 24: "=", 25: "9", 26: "7", 27: "-", 28: "8", 29: "0",
    30: "]", 31: "o", 32: "u", 33: "[", 34: "i", 35: "p", 37: "l",
    38: "j", 40: "k", 41: ";", 42: "'", 43: ",", 44: "/", 45: "n",
    46: "m", 47: ".",
}
_KEY_ESCAPE = 53
_KEY_BACKSPACE = 51
_KEY_H = 4
_KEY_J = 38
_KEY_K = 40
_KEY_L = 37
_KEY_B = 11
_KEY_F = 3
_KEY_SLASH = 44
_KEY_SPACE = 49
_KEY_I = 34
_MOUSE_STEP_MIN = 6
_MOUSE_STEP_MAX = 60
_MOUSE_ACCEL = 1.2  # multiplier per repeated move
_CTRL_FLAG = 1 << 18  # NSEventModifierFlagControl


def _generate_hints(count):
    """Generate hint strings. Uses single letters when they suffice, otherwise all two-letter."""
    chars = _HINT_CHARS
    if count <= len(chars):
        return list(chars[:count])
    # All two-letter to avoid prefix conflicts (e.g. "A" matching "AA", "AB", …)
    hints = []
    for first in chars:
        for second in chars:
            hints.append(first + second)
            if len(hints) >= count:
                return hints
    return hints


def _element_position(el):
    """Extract (x, y) from an element's AXPosition."""
    err, pos = AX.AXValueGetValue(el["position"], AX.kAXValueCGPointType, None)
    return (pos.x, pos.y)


class HintWindow(NSWindow):
    """Transparent full-screen window that captures keystrokes."""

    def initWithOverlay_(self, overlay):
        screen = NSScreen.mainScreen().frame()
        self = objc.super(HintWindow, self).initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, screen.size.width, screen.size.height),
            0,  # borderless
            NSBackingStoreBuffered,
            False,
        )
        if self is None:
            return None
        self.overlay = overlay
        self.setLevel_(NSFloatingWindowLevel)
        self.setOpaque_(False)
        self.setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.0, 0.01))
        self.setIgnoresMouseEvents_(True)
        self.setHasShadow_(False)

        # Centered "VM" watermark
        self._vm_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 0, 0))
        self._vm_label.setStringValue_("VM")
        self._vm_label.setEditable_(False)
        self._vm_label.setSelectable_(False)
        self._vm_label.setBezeled_(False)
        self._vm_label.setDrawsBackground_(False)
        self._vm_label.setTextColor_(NSColor.colorWithWhite_alpha_(0.5, 0.30))
        self._vm_label.setFont_(NSFont.boldSystemFontOfSize_(48))
        self._vm_label.sizeToFit()
        vm_f = self._vm_label.frame()

        # Mode label below VM
        self._mode_label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 0, 0))
        self._mode_label.setEditable_(False)
        self._mode_label.setSelectable_(False)
        self._mode_label.setBezeled_(False)
        self._mode_label.setDrawsBackground_(False)
        self._mode_label.setTextColor_(NSColor.colorWithWhite_alpha_(0.5, 0.25))
        self._mode_label.setFont_(NSFont.systemFontOfSize_(16))
        self._mode_label.setAlignment_(1)  # center

        self._screen_size = screen.size
        cx = screen.size.width / 2
        cy = screen.size.height / 2
        self._vm_label.setFrameOrigin_((cx - vm_f.size.width / 2, cy))
        self._set_mode("NORMAL")

        self.contentView().addSubview_(self._vm_label)
        self.contentView().addSubview_(self._mode_label)

        return self

    def _set_mode(self, text):
        self._mode_label.setStringValue_(text)
        self._mode_label.sizeToFit()
        f = self._mode_label.frame()
        vm_f = self._vm_label.frame()
        cx = self._screen_size.width / 2
        self._mode_label.setFrameOrigin_((cx - f.size.width / 2,
                                           vm_f.origin.y - f.size.height - 4))

    def canBecomeKeyWindow(self):
        return not self.overlay._insert_mode

    def resignKeyWindow(self):
        objc.super(HintWindow, self).resignKeyWindow()

    def keyDown_(self, event):
        code = event.keyCode()
        flags = event.modifierFlags()
        ctrl = flags & _CTRL_FLAG
        if code == _KEY_BACKSPACE:
            self.overlay.backspace()
        elif ctrl and code == _KEY_B:
            self.overlay.scroll(3)
        elif ctrl and code == _KEY_F:
            self.overlay.scroll(-3)
        elif code == _KEY_H:
            self.overlay.move_mouse(-1, 0, event.isARepeat())
        elif code == _KEY_J:
            self.overlay.move_mouse(0, 1, event.isARepeat())
        elif code == _KEY_K:
            self.overlay.move_mouse(0, -1, event.isARepeat())
        elif code == _KEY_L:
            self.overlay.move_mouse(1, 0, event.isARepeat())
        elif code == _KEY_SPACE:
            self.overlay.click_at_cursor()
        elif code == _KEY_I:
            self.overlay.enter_insert_mode()
        elif code == _KEY_SLASH:
            self.overlay.toggle_hints()
        elif code in _KEYCODE_TO_CHAR and _KEYCODE_TO_CHAR[code].isalpha():
            self.overlay.type_char(_KEYCODE_TO_CHAR[code].upper())


class HintOverlay:
    def __init__(self):
        self.window = None
        self.labels = []  # (hint_string, NSTextField, element)
        self.typed = ""
        self._prev_app = None
        self._pid = None
        self._scroll_gen = 0
        self._scroll_pending = False
        self._ws_observer = None
        self._clicking = False
        self._hints_visible = True
        self._win_hint_cache = {}  # kCGWindowNumber -> hint char
        self._mouse_dir = None  # (dx_sign, dy_sign) of last move
        self._mouse_speed = _MOUSE_STEP_MIN
        self._insert_mode = False
        self._insert_tap = None
        self._insert_source = None

    def _activate_overlay_window(self):
        """Activate the overlay window so it captures keystrokes."""
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(1)  # Accessory — enables key window
        self.window.makeKeyAndOrderFront_(None)
        app.activateIgnoringOtherApps_(True)

    def toggle(self):
        """Toggle the overlay on/off."""
        if self.window:
            self.dismiss()
        else:
            self.show()

    def show(self):
        """Show hint overlay on clickable elements of the frontmost app."""
        my_pid = os.getpid()
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if front.processIdentifier() == my_pid:
            # Already showing hints on ourselves — skip
            return
        self._prev_app = front
        self._pid = self._prev_app.processIdentifier()
        elements = accessibility.get_clickable_elements(self._pid)

        if not elements:
            print("No clickable elements found.")
            return

        # Move cursor to center of the frontmost app's focused window
        self._center_cursor_on_app()

        self.window = HintWindow.alloc().initWithOverlay_(self)
        self._populate(elements)
        self._activate_overlay_window()

        # Watch for target app gaining focus (alt-tab, mouse click, etc.)
        self._start_watching_focus()

    def _center_cursor_on_app(self):
        """Move the cursor to the center of the focused window of the target app."""
        app_ref = AX.AXUIElementCreateApplication(self._pid)
        err, focused = AX.AXUIElementCopyAttributeValue(app_ref, "AXFocusedWindow", None)
        if err != 0 or focused is None:
            return
        err, pos = AX.AXUIElementCopyAttributeValue(focused, "AXPosition", None)
        _, size = AX.AXUIElementCopyAttributeValue(focused, "AXSize", None)
        if pos is None or size is None:
            return
        _, p = AX.AXValueGetValue(pos, AX.kAXValueCGPointType, None)
        _, s = AX.AXValueGetValue(size, AX.kAXValueCGSizeType, None)
        mouse.move_cursor(p.x + s.width / 2, p.y + s.height / 2)

    def _start_watching_focus(self):
        """Register for workspace app-activation notifications."""
        ws = NSWorkspace.sharedWorkspace()
        self._ws_observer = ws.notificationCenter().addObserverForName_object_queue_usingBlock_(
            "NSWorkspaceDidActivateApplicationNotification",
            None,
            None,
            lambda note: AppHelper.callAfter(self._on_app_activated, note),
        )

    def _stop_watching_focus(self):
        """Remove the workspace observer."""
        if self._ws_observer:
            NSWorkspace.sharedWorkspace().notificationCenter().removeObserver_(self._ws_observer)
            self._ws_observer = None

    def _on_app_activated(self, note):
        """Called when any app gains focus. Refresh hints for the newly focused app."""
        if not self.window or self._clicking or self._insert_mode:
            return
        activated = note.userInfo()["NSWorkspaceApplicationKey"]
        activated_pid = activated.processIdentifier()
        # Ignore our own activation (we're about to reclaim key window)
        if activated_pid == os.getpid():
            return
        # Clear old hints immediately
        for _, label, *_ in self.labels:
            label.setHidden_(True)
        # Switch target to the newly focused app
        self._prev_app = activated
        self._pid = activated_pid
        if self._hints_visible:
            elements = accessibility.get_clickable_elements(self._pid)
            if elements:
                self._populate(elements)
        self._activate_overlay_window()

    def _get_visible_windows(self):
        """Get visible windows from other apps."""
        import Quartz
        my_pid = os.getpid()
        win_list = Quartz.CGWindowListCopyWindowInfo(
            Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements,
            Quartz.kCGNullWindowID,
        )
        windows = []
        for w in win_list:
            pid = w.get(Quartz.kCGWindowOwnerPID, 0)
            if pid == my_pid:
                continue
            if w.get(Quartz.kCGWindowLayer, -1) != 0:
                continue
            bounds = w.get(Quartz.kCGWindowBounds, {})
            if bounds.get("Width", 0) == 0 or bounds.get("Height", 0) == 0:
                continue
            windows.append(w)
        return windows

    def _populate(self, elements):
        """Place hint labels on the overlay for elements and visible windows."""
        # Clear existing labels
        for item in self.labels:
            item[1].removeFromSuperview()
        self.labels = []
        self.typed = ""

        windows = self._get_visible_windows()
        import Quartz

        # Reuse cached hints for known windows, assign new ones for new windows
        chars = _HINT_CHARS
        used_hints = set()
        win_assignments = []
        for w in windows:
            wid = w.get(Quartz.kCGWindowNumber, 0)
            cached = self._win_hint_cache.get(wid)
            if cached and cached not in used_hints:
                used_hints.add(cached)
                win_assignments.append((cached, w))
            else:
                win_assignments.append((None, w))
        available = [c for c in chars if c not in used_hints]
        avail_idx = 0
        new_cache = {}
        for i, (hint, w) in enumerate(win_assignments):
            if hint is None and avail_idx < len(available):
                hint = available[avail_idx]
                avail_idx += 1
                win_assignments[i] = (hint, w)
            if hint:
                new_cache[w.get(Quartz.kCGWindowNumber, 0)] = hint
        self._win_hint_cache = new_cache

        # Element hints use two-letter combos from chars not used by windows
        all_used = set(h for h, _ in win_assignments if h)
        remaining = [c for c in chars if c not in all_used]
        el_hints = []
        for first in remaining:
            for second in chars:
                el_hints.append(first + second)
                if len(el_hints) >= len(elements):
                    break
            if len(el_hints) >= len(elements):
                break

        screen = NSScreen.mainScreen().frame()
        content = self.window.contentView()

        for hint, w in win_assignments:
            if not hint:
                continue
            bounds = w[Quartz.kCGWindowBounds]
            cx = bounds["X"] + bounds["Width"] / 2
            cy = bounds["Y"] + bounds["Height"] / 2
            flipped_y = screen.size.height - cy
            label = self._create_window_hint_label(hint, cx, flipped_y)
            content.addSubview_(label)
            self.labels.append((hint, label, w, "window"))

        elements.sort(key=lambda el: _element_position(el))
        for hint, el in zip(el_hints, elements):
            x, y = _element_position(el)
            flipped_y = screen.size.height - y
            label = self._create_hint_label(hint, x, flipped_y)
            content.addSubview_(label)
            self.labels.append((hint, label, el, "element"))

    def _create_hint_label(self, hint_text, x, flipped_y):
        """Create a styled hint label at the given screen position."""
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 0, 0))
        label.setStringValue_(hint_text)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setBezeled_(False)
        label.setDrawsBackground_(True)
        label.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(*HINT_BG_COLOR)
        )
        label.setTextColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(*HINT_TEXT_COLOR)
        )
        label.setFont_(NSFont.boldSystemFontOfSize_(HINT_FONT_SIZE))
        label.sizeToFit()

        frame = label.frame()
        label.setFrame_(
            NSMakeRect(
                x - HINT_PADDING,
                flipped_y - frame.size.height,
                frame.size.width + HINT_PADDING * 2,
                frame.size.height,
            )
        )
        label.setWantsLayer_(True)
        label.layer().setCornerRadius_(HINT_CORNER_RADIUS)
        return label

    def _create_window_hint_label(self, hint_text, cx, flipped_cy):
        """Create a large centered hint label for window switching."""
        label = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 0, 0))
        label.setStringValue_(hint_text)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setBezeled_(False)
        label.setDrawsBackground_(True)
        label.setBackgroundColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(*WIN_HINT_BG_COLOR)
        )
        label.setTextColor_(
            NSColor.colorWithCalibratedRed_green_blue_alpha_(*WIN_HINT_TEXT_COLOR)
        )
        label.setFont_(NSFont.boldSystemFontOfSize_(WIN_HINT_FONT_SIZE))
        label.setAlignment_(1)  # NSTextAlignmentCenter
        label.sizeToFit()

        frame = label.frame()
        w = frame.size.width + WIN_HINT_PADDING * 2
        h = frame.size.height
        label.setFrame_(NSMakeRect(cx - w / 2, flipped_cy - h / 2, w, h))
        label.setWantsLayer_(True)
        label.layer().setCornerRadius_(WIN_HINT_CORNER_RADIUS)
        return label

    def move_mouse(self, dx, dy, repeat=False):
        """Move the mouse cursor with acceleration on repeated presses."""
        direction = (dx, dy)
        if repeat and self._mouse_dir == direction:
            self._mouse_speed = min(self._mouse_speed * _MOUSE_ACCEL, _MOUSE_STEP_MAX)
        else:
            self._mouse_speed = _MOUSE_STEP_MIN
        self._mouse_dir = direction
        step = int(self._mouse_speed)
        x, y = mouse.get_cursor_position()
        mouse.move_cursor(x + dx * step, y + dy * step)

    def scroll(self, lines):
        """Scroll the target app. Hints hide during scrolling, refresh when idle."""
        mouse.scroll(lines)
        # Hide hints on first scroll
        if not self._scroll_pending:
            for _, label, *_ in self.labels:
                label.setHidden_(True)
        # Bump the generation so earlier scheduled refreshes become no-ops
        self._scroll_gen += 1
        self._scroll_pending = True
        gen = self._scroll_gen
        AppHelper.callLater(1.0, lambda: self._refresh_if_idle(gen))

    def _refresh_if_idle(self, gen):
        """Refresh hints only if no further scrolling happened since gen."""
        if gen != self._scroll_gen or not self.window:
            return
        self._scroll_pending = False
        if self._hints_visible:
            elements = accessibility.get_clickable_elements(self._pid)
            self._populate(elements)

    def click_at_cursor(self):
        """Click at the current cursor position, then refresh hints."""
        x, y = mouse.get_cursor_position()
        print(f"[space click] ({x:.0f}, {y:.0f})")
        self._click_and_refresh(x, y)

    def _click_and_refresh(self, x, y):
        """Hide hints, click at (x, y) in the target app, then refresh hints."""
        self._clicking = True
        for _, label, *_ in self.labels:
            label.setHidden_(True)
        # Give focus to target app so click lands correctly
        if self._prev_app:
            self._prev_app.activateWithOptions_(0)
        AppHelper.callLater(0.15, lambda: self._perform_click_and_refresh(x, y))

    def _perform_click_and_refresh(self, x, y):
        """Execute the click and refresh hints afterward."""
        if not self.window:
            return
        # Hide overlay so the click lands on the target app
        self.window.orderOut_(None)
        mouse.click(x, y)
        self._reclaim_and_refresh()
        # AppHelper.callLater(0.3, self._reclaim_and_refresh)

    def _reclaim_and_refresh(self):
        """Reclaim key window and refresh hints after a click."""
        self._clicking = False
        if not self.window:
            return
        # Update target to whichever app is now frontmost
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if front.processIdentifier() != os.getpid():
            self._prev_app = front
            self._pid = front.processIdentifier()
        self._activate_overlay_window()
        if self._hints_visible:
            self.refresh()

    def refresh(self):
        """Re-collect elements and refresh hints."""
        elements = accessibility.get_clickable_elements(self._pid)
        if elements:
            self._populate(elements)
        self._hints_visible = True

    def toggle_hints(self):
        """Toggle hint labels on/off. Recalculates when showing."""
        if self._hints_visible:
            for _, label, *_ in self.labels:
                label.setHidden_(True)
            self._hints_visible = False
        else:
            self.refresh()

    def enter_insert_mode(self):
        """Enter insert mode: pass all keys to the target app until Escape."""
        import Quartz

        if self._insert_mode:
            return
        self._insert_mode = True

        # Hide main window, show a passive INSERT watermark
        if self.window:
            self.window.orderOut_(None)
        self._show_insert_watermark()

        # Give focus to target app
        NSApplication.sharedApplication().setActivationPolicy_(2)  # Prohibited
        if self._prev_app:
            self._prev_app.activateWithOptions_(0)

        # Install a global tap to catch Escape
        tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
            self._insert_tap_callback,
            None,
        )
        if tap:
            self._insert_tap = tap
            self._insert_source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
            Quartz.CFRunLoopAddSource(
                Quartz.CFRunLoopGetCurrent(), self._insert_source, Quartz.kCFRunLoopCommonModes
            )
            Quartz.CGEventTapEnable(tap, True)

    def _insert_tap_callback(self, proxy, event_type, event, refcon):
        """Global tap callback that catches Escape to exit insert mode."""
        import Quartz

        if event_type == Quartz.kCGEventTapDisabledByTimeout:
            if self._insert_tap:
                Quartz.CGEventTapEnable(self._insert_tap, True)
            return event
        if event_type == Quartz.kCGEventKeyDown:
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            if keycode == _KEY_ESCAPE:
                AppHelper.callAfter(self._exit_insert_mode)
                return None  # Suppress the Escape
        return event

    def _exit_insert_mode(self):
        """Exit insert mode and restore the overlay."""
        import Quartz

        self._insert_mode = False

        # Remove the tap
        if self._insert_tap:
            Quartz.CGEventTapEnable(self._insert_tap, False)
            if self._insert_source:
                Quartz.CFRunLoopRemoveSource(
                    Quartz.CFRunLoopGetCurrent(), self._insert_source, Quartz.kCFRunLoopCommonModes
                )
                self._insert_source = None
            self._insert_tap = None

        if not self.window:
            return

        # Update target to current frontmost app
        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if front.processIdentifier() != os.getpid():
            self._prev_app = front
            self._pid = front.processIdentifier()

        self._hide_insert_watermark()
        self.window._set_mode("NORMAL")
        self._activate_overlay_window()
        self.refresh()

    def _show_insert_watermark(self):
        """Show a passive floating watermark for INSERT mode."""
        screen = NSScreen.mainScreen().frame()
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, screen.size.width, screen.size.height),
            0, NSBackingStoreBuffered, False,
        )
        win.setLevel_(NSFloatingWindowLevel)
        win.setOpaque_(False)
        win.setBackgroundColor_(NSColor.colorWithWhite_alpha_(0.0, 0.0))
        win.setIgnoresMouseEvents_(True)
        win.setHasShadow_(False)

        cx, cy = screen.size.width / 2, screen.size.height / 2

        vm = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 0, 0))
        vm.setStringValue_("VM")
        vm.setEditable_(False)
        vm.setSelectable_(False)
        vm.setBezeled_(False)
        vm.setDrawsBackground_(False)
        vm.setTextColor_(NSColor.colorWithWhite_alpha_(0.5, 0.30))
        vm.setFont_(NSFont.boldSystemFontOfSize_(48))
        vm.sizeToFit()
        vm_f = vm.frame()
        vm.setFrameOrigin_((cx - vm_f.size.width / 2, cy))

        mode = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 0, 0))
        mode.setStringValue_("INSERT")
        mode.setEditable_(False)
        mode.setSelectable_(False)
        mode.setBezeled_(False)
        mode.setDrawsBackground_(False)
        mode.setTextColor_(NSColor.colorWithWhite_alpha_(0.5, 0.25))
        mode.setFont_(NSFont.systemFontOfSize_(16))
        mode.setAlignment_(1)
        mode.sizeToFit()
        mode_f = mode.frame()
        mode.setFrameOrigin_((cx - mode_f.size.width / 2, cy - mode_f.size.height - 4))

        win.contentView().addSubview_(vm)
        win.contentView().addSubview_(mode)
        win.orderFrontRegardless()
        self._insert_window = win

    def _hide_insert_watermark(self):
        """Remove the INSERT watermark window."""
        if hasattr(self, '_insert_window') and self._insert_window:
            self._insert_window.orderOut_(None)
            self._insert_window = None

    def _switch_to_window(self, win_info):
        """Activate the app owning the given window and raise it."""
        import Quartz
        bounds = win_info[Quartz.kCGWindowBounds]
        cx = bounds["X"] + bounds["Width"] / 2
        cy = bounds["Y"] + bounds["Height"] / 2
        mouse.move_cursor(cx, cy)
        pid = win_info[Quartz.kCGWindowOwnerPID]
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app:
            app.activateWithOptions_(0)
            self._prev_app = app
            self._pid = pid
        # Raise the specific window via AX
        self._raise_window(pid, bounds)
        AppHelper.callLater(0.15, self._activate_and_refresh)

    def _raise_window(self, pid, bounds):
        """Raise a specific window by matching its position/size via Accessibility."""
        app_ref = AX.AXUIElementCreateApplication(pid)
        err, windows = AX.AXUIElementCopyAttributeValue(app_ref, "AXWindows", None)
        if err != 0 or not windows:
            return
        tx, ty = bounds["X"], bounds["Y"]
        tw, th = bounds["Width"], bounds["Height"]
        for win in windows:
            err, pos = AX.AXUIElementCopyAttributeValue(win, "AXPosition", None)
            err2, size = AX.AXUIElementCopyAttributeValue(win, "AXSize", None)
            if pos is None or size is None:
                continue
            _, p = AX.AXValueGetValue(pos, AX.kAXValueCGPointType, None)
            _, s = AX.AXValueGetValue(size, AX.kAXValueCGSizeType, None)
            if abs(p.x - tx) < 2 and abs(p.y - ty) < 2 and abs(s.width - tw) < 2 and abs(s.height - th) < 2:
                AX.AXUIElementPerformAction(win, "AXRaise")
                return

    def _activate_and_refresh(self):
        """Re-activate overlay and refresh element hints after window switch."""
        if not self.window:
            return
        self._activate_overlay_window()
        self.refresh()

    def dismiss(self):
        """Dismiss the overlay without action."""
        if self._insert_mode:
            self._exit_insert_mode()
        self._hide_insert_watermark()
        self._stop_watching_focus()
        if self.window:
            self.window.orderOut_(None)
            self.window = None
        self.labels = []
        self.typed = ""
        NSApplication.sharedApplication().setActivationPolicy_(2)  # Prohibited
        if self._prev_app:
            self._prev_app.activateWithOptions_(0)
            self._prev_app = None

    def type_char(self, char):
        """Handle a typed letter: filter hints, click if unique match."""
        self.typed += char
        matching = []
        for hint, label, data, kind in self.labels:
            if hint.startswith(self.typed):
                label.setHidden_(False)
                matching.append((hint, label, data, kind))
            else:
                label.setHidden_(True)

        if len(matching) == 1:
            hint, label, data, kind = matching[0]
            if kind == "window":
                self._switch_to_window(data)
            else:
                cx, cy = mouse.element_center(data["position"], data["size"])
                print(f"[hint {hint}] role={data['role']} title={data.get('title', '')!r} desc={data.get('description', '')!r} ({cx:.0f}, {cy:.0f})")
                self._click_and_refresh(cx, cy)
        elif len(matching) == 0:
            # No match — reset typed filter and re-show all hints
            self.typed = ""
            for h, lbl, *_ in self.labels:
                lbl.setHidden_(False)

    def backspace(self):
        """Remove last typed char and re-show matching hints."""
        if not self.typed:
            return
        self.typed = self.typed[:-1]
        for hint, label, *_ in self.labels:
            if hint.startswith(self.typed):
                label.setHidden_(False)
            else:
                label.setHidden_(True)
