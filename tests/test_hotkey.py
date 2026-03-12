import unittest
from unittest.mock import MagicMock, patch
import sys

# Define a mock Quartz object with necessary constants
mock_quartz = MagicMock()
mock_quartz.kCGEventFlagMaskCommand = 1 << 20
mock_quartz.kCGEventFlagMaskShift = 1 << 17
mock_quartz.kCGEventFlagMaskAlternate = 1 << 19
mock_quartz.kCGEventFlagMaskControl = 1 << 18
mock_quartz.kCGEventKeyDown = 10
mock_quartz.kCGSessionEventTap = 0
mock_quartz.kCGHeadInsertEventTap = 0
mock_quartz.kCGEventTapOptionDefault = 0
mock_quartz.kCGKeyboardEventKeycode = 0  # Standard value is 0, not 1
mock_quartz.kCFRunLoopCommonModes = 0

class TestHotkeyManager(unittest.TestCase):
    def setUp(self):
        # We use patch.dict to safely mock sys.modules["Quartz"] only for this test
        self.patcher = patch.dict("sys.modules", {"Quartz": mock_quartz})
        self.patcher.start()
        
        # Import hotkey here so it picks up the mock
        if "vimlayer.hotkey" in sys.modules:
            import importlib
            importlib.reload(sys.modules["vimlayer.hotkey"])
        from vimlayer import hotkey
        self.hotkey = hotkey
        
        # Reset the manager for each test
        self.hotkey._manager = self.hotkey.HotkeyManager()

    def tearDown(self):
        self.patcher.stop()

    def test_register_multiple_hotkeys(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        
        flags1 = mock_quartz.kCGEventFlagMaskCommand
        flags2 = mock_quartz.kCGEventFlagMaskAlternate

        self.hotkey.register(cb1, 10, flags1)
        self.hotkey.register(cb2, 20, flags2)
        
        self.assertEqual(len(self.hotkey._manager.hotkeys), 2)
        self.assertEqual(self.hotkey._manager.hotkeys[(10, flags1)], cb1)
        self.assertEqual(self.hotkey._manager.hotkeys[(20, flags2)], cb2)

    def test_primary_hotkey(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        
        flags1 = mock_quartz.kCGEventFlagMaskCommand
        flags2 = mock_quartz.kCGEventFlagMaskAlternate

        self.hotkey.register(cb1, 10, flags1, is_primary=True)
        self.hotkey.register(cb2, 20, flags2)
        
        self.assertEqual(self.hotkey.get_hotkey(), (10, flags1))

    def test_tap_callback_triggers_correct_hotkey(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        
        flags1 = mock_quartz.kCGEventFlagMaskCommand
        flags2 = mock_quartz.kCGEventFlagMaskAlternate
        
        self.hotkey.register(cb1, 10, flags1)
        self.hotkey.register(cb2, 20, flags2)
        
        # Simulate tap callback with hotkey 1
        mock_event = MagicMock()
        mock_quartz.CGEventGetIntegerValueField.return_value = 10
        mock_quartz.CGEventGetFlags.return_value = flags1
        
        result = self.hotkey._manager._tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
        
        cb1.assert_called_once()
        cb2.assert_not_called()
        self.assertIsNone(result) # Suppressed

    def test_tap_callback_ignores_unknown_hotkey(self):
        cb1 = MagicMock()
        flags = mock_quartz.kCGEventFlagMaskCommand
        self.hotkey.register(cb1, 10, flags)
        
        # Simulate tap callback with unknown key
        mock_event = MagicMock()
        mock_quartz.CGEventGetIntegerValueField.return_value = 99
        mock_quartz.CGEventGetFlags.return_value = flags
        
        result = self.hotkey._manager._tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
        
        cb1.assert_not_called()
        self.assertEqual(result, mock_event) # Not suppressed

    def test_suspend(self):
        cb1 = MagicMock()
        flags = mock_quartz.kCGEventFlagMaskCommand
        self.hotkey.register(cb1, 10, flags)
        self.hotkey.suspend(True)
        
        mock_event = MagicMock()
        mock_quartz.CGEventGetIntegerValueField.return_value = 10
        mock_quartz.CGEventGetFlags.return_value = flags
        
        result = self.hotkey._manager._tap_callback(None, mock_quartz.kCGEventKeyDown, mock_event, None)
        
        cb1.assert_not_called()
        self.assertEqual(result, mock_event)

if __name__ == "__main__":
    unittest.main()
