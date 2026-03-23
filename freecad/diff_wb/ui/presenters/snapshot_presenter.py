"""Module responsibility: Snapshot result presenter.

This presenter transforms SnapshotResult into view protocol calls.
It passes RAW DATA only - it NEVER formats user-facing messages.
Translation and parameter substitution are handled by the view.

Translation Strategy:
    The presenter passes raw values (e.g., snapshot_name) without formatting.
    The view is responsible for:
    1. Looking up the translation template from translation_strings.py
    2. Applying Qt translation via QCoreApplication.translate()
    3. Substituting parameters using Python's % formatting

    Example flow:
        Presenter: self._view.show_success(snapshot_name="my_snapshot")
        View: template = SNAPSHOT_SUCCESS_TEMPLATE  # "Snapshot '%1' created successfully"
        View: translated = QCoreApplication.translate("SnapshotView", template)
        View: final = translated % snapshot_name  # "Snapshot 'my_snapshot' created successfully"
"""

from ...application.actions.result_models import SnapshotResult
from ..protocols.snapshot_view import SnapshotView


class SnapshotPresenter:
    """Transform SnapshotResult into view calls.

    This presenter passes raw data to the view for display. It does NOT
    format any user-facing messages - that responsibility belongs to the view.

    Dependencies are injected for testability.
    """

    def __init__(self, view: SnapshotView) -> None:
        """Initialize with required dependencies.

        Args:
            view: SnapshotView implementation to display results
        """
        self._view = view

    def present_result(self, result: SnapshotResult) -> None:
        """Pass result data to view for display.

        The presenter passes raw data only. The view handles translation
        and parameter substitution.

        Args:
            result: SnapshotResult from TakeSnapshotAction.execute()
        """
        if result.success:
            # Pass raw snapshot_name - view handles translation and formatting
            self._view.show_success(snapshot_name=result.snapshot_name)
        else:
            # Pass error message as-is - view handles translation of templates
            self._view.show_error(result.error_message or "Unknown error occurred")
