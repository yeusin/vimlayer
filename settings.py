"""Settings window with hotkey recorder."""

import objc
import Quartz
from AppKit import (
    NSApp,
    NSBackingStoreBuffered,
    NSBezelStyleRounded,
    NSButton,
    NSEvent,
    NSFont,
    NSKeyDownMask,
    NSMakeRect,
    NSTextField,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject

import config
import hotkey
from hotkey import MODIFIER_MASK

# Map modifier flag bits to display symbols
_MODIFIER_SYMBOLS = [
    (Quartz.kCGEventFlagMaskControl, "\u2303"),   # ⌃
    (Quartz.kCGEventFlagMaskAlternate, "\u2325"),  # ⌥
    (Quartz.kCGEventFlagMaskShift, "\u21e7"),      # ⇧
    (Quartz.kCGEventFlagMaskCommand, "\u2318"),    # ⌘
]

# Map keycodes to display names (common keys)
_KEYCODE_NAMES = {
    49: "Space", 36: "Return", 48: "Tab", 51: "Delete", 53: "Escape",
    123: "\u2190", 124: "\u2192", 125: "\u2193", 126: "\u2191",  # arrows
    # F-keys
    122: "F1", 120: "F2", 99: "F3", 118: "F4", 96: "F5", 97: "F6",
    98: "F7", 100: "F8", 101: "F9", 109: "F10", 103: "F11", 111: "F12",
}
# Letters (keycodes 0-50ish map to QWERTY layout)
_KEYCODE_LETTERS = {
    0: "A", 1: "S", 2: "D", 3: "F", 4: "H", 5: "G", 6: "Z", 7: "X",
    8: "C", 9: "V", 11: "B", 12: "Q", 13: "W", 14: "E", 15: "R",
    16: "Y", 17: "T", 18: "1", 19: "2", 20: "3", 21: "4", 22: "6",
    23: "5", 24: "=", 25: "9", 26: "7", 27: "-", 28: "8", 29: "0",
    30: "]", 31: "O", 32: "U", 33: "[", 34: "I", 35: "P", 37: "L",
    38: "J", 39: "'", 40: "K", 41: ";", 42: "\\", 43: ",", 44: "/",
    45: "N", 46: "M", 47: ".",
}
_KEYCODE_NAMES.update(_KEYCODE_LETTERS)


def _format_hotkey(keycode, flags):
    """Return a human-readable string like '⌘⇧Space'."""
    parts = [sym for mask, sym in _MODIFIER_SYMBOLS if flags & mask]
    parts.append(_KEYCODE_NAMES.get(keycode, f"Key{keycode}"))
    return "".join(parts)


class HotkeyRecorderField(NSTextField):
    """Text field that starts recording on click. Uses NSEvent local monitor
    to capture key events, bypassing the responder chain so Cmd+key combos
    aren't swallowed by the menu system."""

    def initWithFrame_(self, frame):
        self = objc.super(HotkeyRecorderField, self).initWithFrame_(frame)
        if self is None:
            return None
        self._recording = False
        self._monitor = None
        self._keycode = None
        self._flags = 0
        self.setEditable_(False)
        self.setAlignment_(1)  # center
        return self

    def mouseDown_(self, event):
        if self._recording:
            return
        self._recording = True
        hotkey.suspend(True)
        self.setStringValue_("Press shortcut...")
        # Capture self in a closure — avoids PyObjC trying to treat the
        # handler as an Objective-C method.
        field = self

        def handle(event):
            keycode = event.keyCode()
            flags = event.modifierFlags() & MODIFIER_MASK
            if not flags:
                return event
            field._keycode = keycode
            field._flags = flags
            field._stopRecording()
            field.setStringValue_(_format_hotkey(keycode, flags))
            return None

        self._monitor = NSEvent.addLocalMonitorForEventsMatchingMask_handler_(
            NSKeyDownMask, handle
        )

    def _stopRecording(self):
        if self._monitor is not None:
            NSEvent.removeMonitor_(self._monitor)
            self._monitor = None
        self._recording = False
        hotkey.suspend(False)


class SettingsController(NSObject):
    """Controller for the settings window."""

    def init(self):
        self = objc.super(SettingsController, self).init()
        if self is None:
            return None
        self._window = None
        self._recorder = None
        return self

    def showWindow(self):
        if self._window is not None:
            keycode, flags = hotkey.get_hotkey()
            self._recorder.setStringValue_(_format_hotkey(keycode, flags))
            self._recorder._keycode = None
            self._recorder._flags = 0
            NSApp.setActivationPolicy_(1)  # Accessory — needed for event monitors
            self._window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)
            return

        w = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 300, 100),
            NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
            NSBackingStoreBuffered,
            False,
        )
        w.setTitle_("VimMouse Settings")
        w.center()
        content = w.contentView()

        # Label
        label = NSTextField.labelWithString_("Shortcut:")
        label.setFrame_(NSMakeRect(15, 60, 70, 24))
        content.addSubview_(label)

        # Recorder field
        recorder = HotkeyRecorderField.alloc().initWithFrame_(
            NSMakeRect(90, 60, 195, 24)
        )
        keycode, flags = hotkey.get_hotkey()
        recorder.setStringValue_(_format_hotkey(keycode, flags))
        recorder.setFont_(NSFont.systemFontOfSize_(13))
        content.addSubview_(recorder)
        self._recorder = recorder

        # Save button
        save_btn = NSButton.alloc().initWithFrame_(NSMakeRect(120, 15, 80, 30))
        save_btn.setTitle_("Save")
        save_btn.setBezelStyle_(NSBezelStyleRounded)
        save_btn.setTarget_(self)
        save_btn.setAction_(b"save:")
        content.addSubview_(save_btn)

        # Cancel button
        cancel_btn = NSButton.alloc().initWithFrame_(NSMakeRect(205, 15, 80, 30))
        cancel_btn.setTitle_("Cancel")
        cancel_btn.setBezelStyle_(NSBezelStyleRounded)
        cancel_btn.setTarget_(self)
        cancel_btn.setAction_(b"cancel:")
        content.addSubview_(cancel_btn)

        self._window = w
        NSApp.setActivationPolicy_(1)  # Accessory — needed for event monitors
        w.makeKeyAndOrderFront_(None)
        NSApp.activateIgnoringOtherApps_(True)

    @objc.typedSelector(b"v@:@")
    def save_(self, sender):
        self._recorder._stopRecording()
        rec = self._recorder
        if rec._keycode is not None:
            hotkey.update_hotkey(rec._keycode, rec._flags)
            config.save({"keycode": rec._keycode, "flags": rec._flags})
        self._window.orderOut_(None)
        NSApp.setActivationPolicy_(2)  # Restore to Prohibited

    @objc.typedSelector(b"v@:@")
    def cancel_(self, sender):
        self._recorder._stopRecording()
        self._window.orderOut_(None)
        NSApp.setActivationPolicy_(2)  # Restore to Prohibited
