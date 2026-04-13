import logging
from typing import List, Optional, Tuple, Callable, Any
from ..base import UIProvider
from .hint_overlay import X11HintOverlay
from .ui_components import Watermark, SettingsWindow
from .launcher import X11Launcher

log = logging.getLogger(__name__)

class X11UI(UIProvider):
    def __init__(self):
        self._watermark = None
        self._settings_window = None
        self._launcher = None

    def show_watermark(self, mode: str, timeout: Optional[float] = None) -> None:
        log.info("X11UI.show_watermark mode=%s, timeout=%s", mode, timeout)
        if not self._watermark:
            self._watermark = Watermark(mode)
        self._watermark.show_mode(mode, timeout)

    def hide_watermark(self) -> None:
        log.info("X11UI.hide_watermark")
        if self._watermark:
            self._watermark.hide()
    def show_cheat_sheet(self, sections: List[Tuple[str, List[Tuple[str, str]]]]) -> None: pass
    def hide_cheat_sheet(self) -> None: pass
    def is_cheat_sheet_visible(self) -> bool: return False
    
    def show_launcher(self, on_dismiss: Optional[Callable] = None) -> None:
        log.info("X11UI.show_launcher")
        if not self._launcher:
            self._launcher = X11Launcher(on_dismiss=on_dismiss)
        else:
            self._launcher._on_dismiss = on_dismiss
        self._launcher.show_launcher()

    def hide_launcher(self) -> None:
        log.info("X11UI.hide_launcher")
        if self._launcher:
            self._launcher.hide()

    def is_launcher_visible(self) -> bool:
        return self._launcher is not None and self._launcher.isVisible()
    
    def show_settings(self) -> None:
        log.info("X11UI.show_settings")
        if not self._settings_window:
            self._settings_window = SettingsWindow()
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()
    
    def create_hint_overlay(self, on_mode_change: Optional[Callable] = None) -> Any:
        log.info("X11UI.create_hint_overlay")
        return X11HintOverlay(on_mode_change=on_mode_change)
