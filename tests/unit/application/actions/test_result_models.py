# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for application action result models.

from freecad.history_wb.application.actions.result_models import (
    DocumentDiffResult,
    DocumentDiffStatus,
    Result,
)


def test_success_factory_returns_success_result() -> None:
    """Result.success() returns is_success=True, data, no message."""
    data = {"key": "value"}
    result = Result.success(data)

    assert result.is_success is True
    assert result.data == data
    assert result.message is None


def test_failure_factory_returns_failure_result() -> None:
    """Result.failure() returns is_success=False, no data, has message."""
    error_message = "Something went wrong"
    result = Result.failure(error_message)

    assert result.is_success is False
    assert result.data is None
    assert result.message == error_message


def test_document_diff_result_stores_application_fields() -> None:
    """DocumentDiffResult stores git_path, status, and snapshot_diff."""
    model = DocumentDiffResult(
        git_path="path/to/doc.FCStd",
        status=DocumentDiffStatus.MODIFIED,
        snapshot_diff=None,
    )

    assert model.git_path == "path/to/doc.FCStd"
    assert model.status == DocumentDiffStatus.MODIFIED
    assert model.snapshot_diff is None
