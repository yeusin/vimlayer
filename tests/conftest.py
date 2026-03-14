import sys
from unittest.mock import MagicMock

# Create base mocks for macOS-specific modules
def create_mock_quartz():
    m = MagicMock()
    m.kCGEventFlagMaskCommand = 1 << 20
    m.kCGEventFlagMaskShift = 1 << 17
    m.kCGEventFlagMaskAlternate = 1 << 19
    m.kCGEventFlagMaskControl = 1 << 18
    m.kCGEventKeyDown = 10
    m.kCGEventKeyUp = 11
    m.kCGSessionEventTap = 0
    m.kCGHeadInsertEventTap = 0
    m.kCGEventTapOptionDefault = 0
    m.kCGKeyboardEventKeycode = 0
    m.kCGKeyboardEventAutorepeat = 1
    m.kCGEventTapDisabledByTimeout = 1000
    m.kCFRunLoopCommonModes = 0
    m.kCGWindowNumber = "kCGWindowNumber"
    m.kCGWindowOwnerPID = "kCGWindowOwnerPID"
    m.kCGWindowLayer = "kCGWindowLayer"
    m.kCGWindowBounds = "kCGWindowBounds"
    m.kCGWindowListOptionOnScreenOnly = 1
    m.kCGWindowListExcludeDesktopElements = 2
    m.kCGNullWindowID = 0
    
    # Default return values for common functions to avoid returning MagicMocks that evaluate to True
    m.CGEventGetFlags.return_value = 0
    m.CGEventGetIntegerValueField.return_value = 0
    
    return m

def create_mock_appkit():
    m = MagicMock()
    m.NSBackingStoreBuffered = 2
    m.NSWindowStyleMaskBorderless = 0
    m.NSFontWeightMedium = 0.23
    m.NSColor = MagicMock()
    m.NSColor.colorWithCalibratedRed_green_blue_alpha_.return_value = MagicMock()
    
    # Mock NSScreen.mainScreen().frame().size
    screen = MagicMock()
    screen.size.width = 1920.0
    screen.size.height = 1080.0
    m.NSScreen.mainScreen().frame.return_value = screen
    
    # Mock NSMakeRect
    m.NSMakeRect = lambda x, y, w, h: MagicMock(origin=MagicMock(x=x, y=y), size=MagicMock(width=w, height=h))
    
    # Mock NSTextField frame
    text_field = m.NSTextField.alloc().initWithFrame_().return_value
    text_field.frame.return_value.size.width = 100.0
    text_field.frame.return_value.size.height = 20.0
    
    return m

def create_mock_ax():
    m = MagicMock()
    m.kAXValueCGPointType = 1
    m.kAXValueCGSizeType = 2
    m.AXUIElementCopyAttributeValue.return_value = (0, MagicMock())
    m.AXUIElementCreateSystemWide.return_value = MagicMock()
    return m

# Initialize global mocks
mock_quartz = create_mock_quartz()
mock_appkit = create_mock_appkit()
mock_ax = create_mock_ax()
mock_objc = MagicMock()
mock_objc.lookUpClass.return_value = MagicMock
mock_objc.super = lambda cls, inst: inst

mock_pyobjc_tools = MagicMock()
mock_foundation = MagicMock()
mock_core_foundation = MagicMock()

# Populate sys.modules
sys.modules["objc"] = mock_objc
sys.modules["Quartz"] = mock_quartz
sys.modules["AppKit"] = mock_appkit
sys.modules["ApplicationServices"] = mock_ax
sys.modules["PyObjCTools"] = mock_pyobjc_tools
sys.modules["PyObjCTools.AppHelper"] = mock_pyobjc_tools.AppHelper
sys.modules["Foundation"] = mock_foundation
sys.modules["CoreFoundation"] = mock_core_foundation

import pytest

@pytest.fixture(autouse=True)
def reset_mocks():
    """Reset all global mocks before each test to ensure isolation."""
    # Reset call history but keep some configuration
    mock_quartz.reset_mock()
    mock_appkit.reset_mock()
    mock_ax.reset_mock()
    mock_objc.reset_mock()
    mock_pyobjc_tools.reset_mock()
    mock_foundation.reset_mock()
    mock_core_foundation.reset_mock()
    
    # Re-setup some defaults
    mock_quartz.kCGEventFlagMaskCommand = 1 << 20
    mock_quartz.kCGEventFlagMaskShift = 1 << 17
    mock_quartz.kCGEventFlagMaskAlternate = 1 << 19
    mock_quartz.kCGEventFlagMaskControl = 1 << 18
    mock_quartz.kCGEventKeyDown = 10
    mock_quartz.kCGEventKeyUp = 11
    mock_quartz.kCGEventTapDisabledByTimeout = 1000
    mock_quartz.kCGKeyboardEventKeycode = 0
    mock_quartz.kCGKeyboardEventAutorepeat = 1
    mock_quartz.kCGWindowNumber = "kCGWindowNumber"
    mock_quartz.kCGWindowOwnerPID = "kCGWindowOwnerPID"
    mock_quartz.kCGWindowLayer = "kCGWindowLayer"
    mock_quartz.kCGWindowBounds = "kCGWindowBounds"
    
    mock_ax.kAXValueCGPointType = 1
    mock_ax.kAXValueCGSizeType = 2
    mock_ax.AXUIElementCopyAttributeValue.return_value = (0, None)
    
    mock_objc.lookUpClass.return_value = MagicMock
    
    # Re-setup AppKit geometry
    screen = MagicMock()
    screen.size.width = 1920.0
    screen.size.height = 1080.0
    mock_appkit.NSScreen.mainScreen().frame.return_value = screen
    
    # Mock NSMakeRect
    mock_appkit.NSMakeRect = lambda x, y, w, h: MagicMock(origin=MagicMock(x=x, y=y), size=MagicMock(width=w, height=h))
    
    # Ensure NSTextField returns a mock with a frame that has float values
    def make_mock_text_field(*args, **kwargs):
        tf = MagicMock()
        tf.frame.return_value.size.width = 100.0
        tf.frame.return_value.size.height = 20.0
        return tf
    
    mock_appkit.NSTextField.alloc().initWithFrame_.side_effect = make_mock_text_field

    # Default behavior for AppHelper.callAfter (run immediately)
    mock_pyobjc_tools.AppHelper.callAfter.side_effect = lambda f, *args: f(*args)
    
    yield
