"""File responsibility: Fake GUI port for testing.

TODO: Use this in presenter tests once presenters are implemented.
Currently unused but kept for future use.
"""

from freecad.diff_wb.infrastructure.freecad.ports import GuiPort


class FakeGuiPort(GuiPort):
    """Fake implementation of GuiPort for unit testing.

    Captures messages for verification in tests.
    """

    def __init__(self) -> None:
        self._message_log: list[str] = []
        self._last_message: object | None = None
        self._last_icon: object | None = None
        self._last_buttons: object | None = None

    def load_ui(self, ui_path: str) -> object:
        """Return a mock widget (not actually loading UI)."""
        self._message_log.append(f"load_ui:{ui_path}")
        return type("MockWidget", (), {})()

    def get_main_window(self) -> object:
        """Return a mock main window."""
        self._message_log.append("get_main_window")
        return type("MockMainWindow", (), {})()

    def get_mdi_area(self) -> object | None:
        """Return None (not implemented in fake)."""
        self._message_log.append("get_mdi_area")
        return None

    def add_subwindow(self, *, mdi_area: object, widget: object) -> object:
        """Return a mock subwindow (not actually adding)."""
        self._message_log.append("add_subwindow")
        return type("MockSubWindow", (), {})()

    def find_subwindow(self, *, mdi_area: object, title: str) -> object | None:
        """Return None (not implemented in fake)."""
        self._message_log.append(f"find_subwindow:{title}")
        return None
