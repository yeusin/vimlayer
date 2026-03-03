"""Spotlight-like search panel using AppKit NSPanel."""

import objc
from AppKit import (
    NSPanel,
    NSScreen,
    NSColor,
    NSCursor,
    NSFont,
    NSTextField,
    NSScrollView,
    NSTableView,
    NSTableColumn,
    NSView,
    NSMakeRect,
    NSBackingStoreBuffered,
    NSApplication,
    NSBezierPath,
    NSFloatingWindowLevel,
)
from AppKit import NSWorkspace
from Foundation import NSIndexSet, NSObject
import accessibility
import mouse

PANEL_WIDTH = 600
PANEL_HEIGHT = 400
INPUT_HEIGHT = 40
ROW_HEIGHT = 32
CORNER_RADIUS = 12


class SearchPanel:
    def __init__(self):
        self.panel = None
        self.input_field = None
        self.table_view = None
        self.scroll_view = None
        self.elements = []
        self.filtered = []
        self.selected_index = 0
        self._prev_app = None
        self._build()

    def _build(self):
        # Calculate center position
        screen = NSScreen.mainScreen().frame()
        x = (screen.size.width - PANEL_WIDTH) / 2
        y = (screen.size.height - PANEL_HEIGHT) / 2 + screen.size.height * 0.1

        style = (
            1 << 0  # NSWindowStyleMaskBorderless — constant not always exported
        )
        self.panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, PANEL_WIDTH, PANEL_HEIGHT),
            style,
            NSBackingStoreBuffered,
            False,
        )
        self.panel.setLevel_(NSFloatingWindowLevel)
        self.panel.setOpaque_(False)
        self.panel.setBackgroundColor_(NSColor.clearColor())
        self.panel.setHasShadow_(True)
        self.panel.setBecomesKeyOnlyIfNeeded_(False)

        # Background view with rounded corners
        content = RoundedView.alloc().initWithFrame_(
            NSMakeRect(0, 0, PANEL_WIDTH, PANEL_HEIGHT)
        )
        self.panel.setContentView_(content)

        # Search input field
        self.input_field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(16, PANEL_HEIGHT - INPUT_HEIGHT - 12, PANEL_WIDTH - 32, INPUT_HEIGHT)
        )
        self.input_field.setFont_(NSFont.systemFontOfSize_(20))
        self.input_field.setFocusRingType_(1)  # NSFocusRingTypeNone
        self.input_field.setBezeled_(False)
        self.input_field.setDrawsBackground_(False)
        self.input_field.setTextColor_(NSColor.whiteColor())
        self.input_field.setPlaceholderString_("Search UI elements...")
        content.addSubview_(self.input_field)

        # Separator line
        separator = NSView.alloc().initWithFrame_(
            NSMakeRect(16, PANEL_HEIGHT - INPUT_HEIGHT - 14, PANEL_WIDTH - 32, 1)
        )
        separator.setWantsLayer_(True)
        separator.layer().setBackgroundColor_(
            NSColor.colorWithWhite_alpha_(1.0, 0.2).CGColor()
        )
        content.addSubview_(separator)

        # Table view for results
        table_height = PANEL_HEIGHT - INPUT_HEIGHT - 30
        self.scroll_view = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(8, 8, PANEL_WIDTH - 16, table_height)
        )
        self.scroll_view.setHasVerticalScroller_(True)
        self.scroll_view.setDrawsBackground_(False)
        self.scroll_view.setBorderType_(0)  # NSNoBorder

        self.table_view = NSTableView.alloc().initWithFrame_(
            NSMakeRect(0, 0, PANEL_WIDTH - 16, table_height)
        )
        self.table_view.setRowHeight_(ROW_HEIGHT)
        self.table_view.setBackgroundColor_(NSColor.clearColor())
        self.table_view.setHeaderView_(None)
        self.table_view.setGridStyleMask_(0)  # No grid
        self.table_view.setSelectionHighlightStyle_(1)  # Regular

        col = NSTableColumn.alloc().initWithIdentifier_("main")
        col.setWidth_(PANEL_WIDTH - 40)
        self.table_view.addTableColumn_(col)

        self.delegate = TableDelegate.alloc().initWithPanel_(self)
        self.table_view.setDelegate_(self.delegate)
        self.table_view.setDataSource_(self.delegate)

        self.scroll_view.setDocumentView_(self.table_view)
        content.addSubview_(self.scroll_view)

        # Input field delegate for real-time filtering and key handling
        self.input_delegate = InputDelegate.alloc().initWithPanel_(self)
        self.input_field.setDelegate_(self.input_delegate)

    def show(self):
        """Show the panel and load elements from frontmost app."""
        self._prev_app = NSWorkspace.sharedWorkspace().frontmostApplication()
        pid = accessibility.get_frontmost_pid()
        self.elements = accessibility.get_elements(pid)
        self.filtered = list(self.elements)
        self.selected_index = 0

        self.input_field.setStringValue_("")
        self.table_view.reloadData()
        if self.filtered:
            idx_set = NSIndexSet.indexSetWithIndex_(0)
            self.table_view.selectRowIndexes_byExtendingSelection_(idx_set, False)

        self.panel.makeKeyAndOrderFront_(None)
        NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        self.panel.makeFirstResponder_(self.input_field)

    def hide(self):
        """Hide the panel."""
        self.panel.orderOut_(None)
        if self._prev_app:
            self._prev_app.activateWithOptions_(0)
            self._prev_app = None

    def update_filter(self, query):
        """Re-filter elements based on query text."""
        self.filtered = accessibility.search(query, self.elements)
        self.selected_index = 0
        self.table_view.reloadData()
        if self.filtered:
            idx_set = NSIndexSet.indexSetWithIndex_(0)
            self.table_view.selectRowIndexes_byExtendingSelection_(idx_set, False)
        self._move_cursor_to_selected()

    def move_selection(self, delta):
        """Move selection up or down."""
        if not self.filtered:
            return
        self.selected_index = max(0, min(len(self.filtered) - 1, self.selected_index + delta))
        idx_set = NSIndexSet.indexSetWithIndex_(self.selected_index)
        self.table_view.selectRowIndexes_byExtendingSelection_(idx_set, False)
        self.table_view.scrollRowToVisible_(self.selected_index)
        self._move_cursor_to_selected()

    def _move_cursor_to_selected(self):
        """Move cursor to the currently selected element."""
        if not self.filtered or self.selected_index >= len(self.filtered):
            return
        el = self.filtered[self.selected_index]
        cx, cy = mouse.element_center(el["position"], el["size"])
        mouse.move_cursor(cx, cy)

    def activate_selected(self, do_click):
        """Move cursor to selected element and optionally click it."""
        if not self.filtered or self.selected_index >= len(self.filtered):
            return
        el = self.filtered[self.selected_index]
        cx, cy = mouse.element_center(el["position"], el["size"])
        self.hide()
        if do_click:
            mouse.click(cx, cy)
        else:
            mouse.move_cursor(cx, cy)


class RoundedView(NSView):
    """Custom view with rounded corners and dark semi-transparent background."""

    def drawRect_(self, rect):
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            self.bounds(), CORNER_RADIUS, CORNER_RADIUS
        )
        NSColor.colorWithWhite_alpha_(0.15, 0.92).setFill()
        path.fill()


class TableDelegate(NSObject):
    """NSTableView data source and delegate."""

    def initWithPanel_(self, panel):
        self = objc.super(TableDelegate, self).init()
        if self is None:
            return None
        self.panel = panel
        return self

    def numberOfRowsInTableView_(self, table_view):
        return len(self.panel.filtered)

    def tableView_objectValueForTableColumn_row_(self, table_view, column, row):
        if row < len(self.panel.filtered):
            el = self.panel.filtered[row]
            role_short = el["role"].replace("AX", "")
            label = el["label"]
            return f"[{role_short}]  {label}"
        return ""


class InputDelegate(NSObject):
    """NSTextField delegate for filtering and key navigation."""

    def initWithPanel_(self, panel):
        self = objc.super(InputDelegate, self).init()
        if self is None:
            return None
        self.panel = panel
        return self

    def controlTextDidChange_(self, notification):
        query = self.panel.input_field.stringValue()
        self.panel.update_filter(query)
        NSCursor.setHiddenUntilMouseMoves_(False)

    def control_textView_doCommandBySelector_(self, control, text_view, selector):
        # selector may be bytes, str, or objc selector — normalize
        if isinstance(selector, bytes):
            sel_name = selector.decode()
        else:
            sel_name = str(selector)
        if sel_name == "moveUp:":
            self.panel.move_selection(-1)
            return True
        elif sel_name == "moveDown:":
            self.panel.move_selection(1)
            return True
        elif sel_name == "insertNewline:":
            # Enter → move + click
            self.panel.activate_selected(do_click=True)
            return True
        elif sel_name == "insertTab:":
            # Tab → move only
            self.panel.activate_selected(do_click=False)
            return True
        elif sel_name == "cancelOperation:":
            # Escape → dismiss
            self.panel.hide()
            return True
        return False
