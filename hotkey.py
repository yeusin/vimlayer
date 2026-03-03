"""Global hotkey registration via CGEventTap."""

import Quartz

# Mutable hotkey state (defaults: Cmd+Shift+Space)
_hotkey_keycode = 49  # Space
_hotkey_flags = Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskShift

MODIFIER_MASK = (
    Quartz.kCGEventFlagMaskCommand
    | Quartz.kCGEventFlagMaskShift
    | Quartz.kCGEventFlagMaskAlternate
    | Quartz.kCGEventFlagMaskControl
)

_callback = None
_suspended = False
_tap = None


def suspend(value=True):
    """Temporarily suspend/resume hotkey interception."""
    global _suspended
    _suspended = value


def _tap_callback(proxy, event_type, event, refcon):
    if event_type == Quartz.kCGEventTapDisabledByTimeout:
        Quartz.CGEventTapEnable(_tap, True)
        return event
    if _suspended:
        return event
    if event_type == Quartz.kCGEventKeyDown:
        keycode = Quartz.CGEventGetIntegerValueField(
            event, Quartz.kCGKeyboardEventKeycode
        )
        flags = Quartz.CGEventGetFlags(event) & MODIFIER_MASK
        if keycode == _hotkey_keycode and flags == _hotkey_flags:
            if _callback:
                _callback()
            return None  # Suppress the event
    return event


def get_hotkey():
    """Return current (keycode, flags) tuple."""
    return _hotkey_keycode, _hotkey_flags


def update_hotkey(keycode, flags):
    """Change the active hotkey at runtime."""
    global _hotkey_keycode, _hotkey_flags
    _hotkey_keycode = keycode
    _hotkey_flags = flags


def register(callback, keycode=None, flags=None):
    """Register a global hotkey that calls `callback`."""
    global _callback, _tap
    _callback = callback
    if keycode is not None:
        update_hotkey(keycode, flags)

    tap = Quartz.CGEventTapCreate(
        Quartz.kCGSessionEventTap,
        Quartz.kCGHeadInsertEventTap,
        Quartz.kCGEventTapOptionDefault,
        Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown),
        _tap_callback,
        None,
    )
    _tap = tap
    if tap is None:
        print("ERROR: Could not create event tap.")
        print("Grant Accessibility permission in System Settings → Privacy & Security.")
        return False

    source = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
    Quartz.CFRunLoopAddSource(
        Quartz.CFRunLoopGetCurrent(), source, Quartz.kCFRunLoopCommonModes
    )
    Quartz.CGEventTapEnable(tap, True)
    return True
