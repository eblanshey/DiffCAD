"""File responsibility: Unit tests for SnapshotPresenter.

These tests verify that the presenter passes raw data to views without
formatting user-facing messages. Translation and formatting are handled
by the view layer.
"""

from freecad.diff_wb.application.actions.result_models import SnapshotResult
from freecad.diff_wb.ui.presenters.snapshot_presenter import SnapshotPresenter
from tests.fakes.fake_snapshot_view import FakeSnapshotView


class TestSnapshotPresenter:
    """Tests for SnapshotPresenter."""

    def test_present_result_success_calls_view(self):
        """Calls view.show_success() on successful snapshot with raw data."""
        # Arrange
        fake_view = FakeSnapshotView()
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=True,
            snapshot_id="snap-123",
            snapshot_name="my_snapshot",
            error_message=None,
        )

        # Act
        presenter.present_result(result)

        # Assert
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_success"
        assert last_call["snapshot_name"] == "my_snapshot"

    def test_present_result_error_calls_view(self):
        """Calls view.show_error() on failed snapshot."""
        # Arrange
        fake_view = FakeSnapshotView()
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=False,
            snapshot_id=None,
            snapshot_name=None,
            error_message="Disk space insufficient",
        )

        # Act
        presenter.present_result(result)

        # Assert
        assert fake_view.get_call_count() == 1
        last_call = fake_view._last_call
        assert last_call["method"] == "show_error"
        assert last_call["error_message"] == "Disk space insufficient"

    def test_passes_raw_snapshot_name_without_formatting(self):
        """Presenter passes raw snapshot_name - view handles formatting."""
        # Arrange
        fake_view = FakeSnapshotView()
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=True,
            snapshot_id="snap-456",
            snapshot_name="test_snapshot",
            error_message=None,
        )

        # Act
        presenter.present_result(result)

        # Assert
        last_call = fake_view._last_call
        # Presenter should pass raw snapshot_name only
        assert last_call["snapshot_name"] == "test_snapshot"
        # No pre-formatted message - that's the view's responsibility
        assert "message" not in last_call or "created successfully" not in str(last_call.get("message", ""))

    def test_passes_error_message_as_is(self):
        """Error message passed through without modification."""
        # Arrange
        fake_view = FakeSnapshotView()
        presenter = SnapshotPresenter(fake_view)
        result = SnapshotResult(
            success=False,
            snapshot_id=None,
            snapshot_name=None,
            error_message="Permission denied",
        )

        # Act
        presenter.present_result(result)

        # Assert
        last_call = fake_view._last_call
        assert last_call["error_message"] == "Permission denied"
