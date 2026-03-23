"""Module responsibility: Fake snapshot view for testing.

This fake implementation captures method calls for verification in tests.
It follows the updated SnapshotView protocol where presenters pass raw data
and views handle translation.
"""

from freecad.diff_wb.ui.protocols.snapshot_view import SnapshotView


class FakeSnapshotView(SnapshotView):
    """Fake implementation of SnapshotView for unit testing.

    Captures method calls for verification in tests.
    """

    def __init__(self):
        self._call_log = []
        self._last_call = None

    def show_success(self, snapshot_name: str) -> None:
        """Capture success call instead of showing UI.

        Args:
            snapshot_name: Raw snapshot name - view handles translation and formatting.
        """
        call = {"method": "show_success", "snapshot_name": snapshot_name}
        self._call_log.append(call)
        self._last_call = call

    def show_error(self, error_message: str) -> None:
        """Capture error call instead of showing UI.

        Args:
            error_message: Error message to display.
        """
        call = {"method": "show_error", "error_message": error_message}
        self._call_log.append(call)
        self._last_call = call

    def show_loading(self, message: str | None = None) -> None:
        """Capture loading call instead of showing UI.

        Args:
            message: Optional custom message. If None, uses default.
        """
        call = {"method": "show_loading", "message": message}
        self._call_log.append(call)
        self._last_call = call

    def clear_calls(self):
        """Clear the call log."""
        self._call_log.clear()
        self._last_call = None

    def get_call_count(self):
        """Return number of calls logged."""
        return len(self._call_log)
