"""Global hotkey registration via CGEventTap."""

import logging
import Quartz

log = logging.getLogger(__name__)

MODIFIER_MASK = (
    Quartz.kCGEventFlagMaskCommand
    | Quartz.kCGEventFlagMaskShift
    | Quartz.kCGEventFlagMaskAlternate
    | Quartz.kCGEventFlagMaskControl
)


class HotkeyManager:
    def __init__(self):
        self.hotkeys = {}  # (keycode, flags) -> callback
        self.primary_hotkey = (49, Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskShift)
        self.suspended = False
        self.tap = None

    def suspend(self, value=True):
        """Temporarily suspend/resume hotkey interception."""
        self.suspended = value

    def get_hotkey(self):
        """Return the primary (activation) hotkey as a (keycode, flags) tuple."""
        return self.primary_hotkey

    def register(self, callback, keycode, flags, is_primary=False):
        """Register a global hotkey that calls `callback`."""
        self.hotkeys[(keycode, flags)] = callback
        if is_primary:
            self.primary_hotkey = (keycode, flags)

        if self.tap is None:
            self.tap = Quartz.CGEventTapCreate(
                Quartz.kCGSessionEventTap,
                Quartz.kCGHeadInsertEventTap,
                Quartz.kCGEventTapOptionDefault,
                Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
                self._tap_callback,
                None,
            )
            if self.tap is None:
                log.error(
                    "Could not create event tap. Grant Accessibility permission in System Settings → Privacy & Security."
                )
                return False

            source = Quartz.CFMachPortCreateRunLoopSource(None, self.tap, 0)
            Quartz.CFRunLoopAddSource(
                Quartz.CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes
            )
            Quartz.CGEventTapEnable(self.tap, True)
        return True

    def _tap_callback(self, proxy, event_type, event, refcon):
        if event_type == Quartz.kCGEventTapDisabledByTimeout:
            Quartz.CGEventTapEnable(self.tap, True)
            return event
        if self.suspended:
            return event
        if event_type == Quartz.kCGEventKeyDown:
            keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
            flags = Quartz.CGEventGetFlags(event) & MODIFIER_MASK
            callback = self.hotkeys.get((keycode, flags))
            if callback:
                callback()
                return None  # Suppress the event
        return event


    def unregister_all(self):
        """Clear all registered hotkeys except the primary one."""
        primary_cb = self.hotkeys.get(self.primary_hotkey)
        self.hotkeys = {}
        if primary_cb:
            self.hotkeys[self.primary_hotkey] = primary_cb

    def update_hotkey(self, keycode, flags):
        """Update the primary (activation) hotkey registration."""
        old_primary = self.primary_hotkey
        callback = self.hotkeys.pop(old_primary, None)
        self.primary_hotkey = (keycode, flags)
        if callback:
            self.hotkeys[self.primary_hotkey] = callback


_manager = HotkeyManager()


def suspend(value=True):
    _manager.suspend(value)


def get_hotkey():
    return _manager.get_hotkey()


def register(callback, keycode, flags, is_primary=False):
    return _manager.register(callback, keycode, flags, is_primary)


def unregister_all():
    _manager.unregister_all()


def update_hotkey(keycode, flags):
    _manager.update_hotkey(keycode, flags)
