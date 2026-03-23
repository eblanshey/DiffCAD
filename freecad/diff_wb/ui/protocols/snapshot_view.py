"""File responsibility: Snapshot view interface definition.

This protocol defines the interface for snapshot views. Views handle both
translation of templates (from translation_strings.py) AND parameter
substitution using Qt-style placeholders (%1, %2, etc.). Presenters pass
raw data only - they never format user-facing messages.

Translation Strategy:
    Views are responsible for:
    1. Looking up translation templates from translation_strings.py
    2. Applying Qt translation via QCoreApplication.translate()
    3. Substituting parameters using Python's % formatting

    Example view implementation:
        def show_success(self, snapshot_name: str) -> None:
            template = QCoreApplication.translate("SnapshotView", SNAPSHOT_SUCCESS_TEMPLATE)
            translated = template % snapshot_name
            self._label.setText(translated)
"""

from typing import Protocol


__all__ = ["SnapshotView"]


class SnapshotView(Protocol):
    """Interface that any snapshot display component must implement.

    Implemented by Qt implementations in the UI views layer.

    The view is responsible for translating messages and substituting
    parameters. Presenters pass raw data only.
    """

    def show_success(self, snapshot_name: str) -> None:
        """Display success message after snapshot creation.

        Args:
            snapshot_name: The name of the created snapshot. The view should
                use SNAPSHOT_SUCCESS_TEMPLATE from translation_strings.py and
                substitute %1 with this value.
        """

    def show_error(self, error_message: str) -> None:
        """Display error message.

        Args:
            error_message: The error message to display. If it contains
                "Unknown error", translate the template from ERROR_UNKNOWN.
                Otherwise, display as-is (may contain runtime-specific info).
        """

    def show_loading(self, message: str | None = None) -> None:
        """Display loading indicator.

        Args:
            message: Optional custom loading message. If None, use the
                default from SNAPSHOT_LOADING_DEFAULT in translation_strings.py.
        """
