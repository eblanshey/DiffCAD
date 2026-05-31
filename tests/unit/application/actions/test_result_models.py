# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for application action result models.

from freecad.history_wb.application.actions.result_models import (
    DiffIssues,
    DocumentDiffResult,
    Result,
    SnapshotIssue,
)
from freecad.history_wb.domain.diff.models import DiffState


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
    """DocumentDiffResult stores git_path, document_state, issues, and snapshot_diff."""
    model = DocumentDiffResult(
        git_path="path/to/doc.FCStd",
        document_state=DiffState.MODIFIED,
        issues=DiffIssues(new_snapshot=SnapshotIssue.MISSING),
        snapshot_diff=None,
    )

    assert model.git_path == "path/to/doc.FCStd"
    assert model.document_state == DiffState.MODIFIED
    assert model.issues.new_snapshot == SnapshotIssue.MISSING
    assert model.snapshot_diff is None


def test_default_diff_issues_have_no_values() -> None:
    """Default DiffIssues is empty."""
    issues = DiffIssues()
    assert issues.old_snapshot is None
    assert issues.new_snapshot is None
    assert issues.general == []


def test_diff_issues_is_blocker_for_states() -> None:
    assert DiffIssues(new_snapshot=SnapshotIssue.MISSING).is_diff_blocker_for(DiffState.ADDED) is True
    assert DiffIssues(old_snapshot=SnapshotIssue.MISSING).is_diff_blocker_for(DiffState.ADDED) is False
    assert DiffIssues(old_snapshot=SnapshotIssue.MISSING).is_diff_blocker_for(DiffState.DELETED) is True
    assert DiffIssues(new_snapshot=SnapshotIssue.MISSING).is_diff_blocker_for(DiffState.DELETED) is False
    assert DiffIssues(old_snapshot=SnapshotIssue.INVALID).is_diff_blocker_for(DiffState.DELETED) is True
    assert DiffIssues(new_snapshot=SnapshotIssue.INVALID).is_diff_blocker_for(DiffState.MODIFIED) is True
    assert DiffIssues(old_snapshot=SnapshotIssue.INVALID).is_diff_blocker_for(DiffState.UNCHANGED) is False
    assert DiffIssues(old_snapshot=SnapshotIssue.MISSING).is_diff_blocker_for(DiffState.MODIFIED) is False
    assert DiffIssues().is_diff_blocker_for(DiffState.UNCHANGED) is False
