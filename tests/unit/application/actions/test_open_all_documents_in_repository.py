# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for opening all FreeCAD documents in repository action.
"""Unit tests for OpenAllDocumentsInRepositoryAction."""

from __future__ import annotations

from pathlib import Path

from freecad.diff_wb.application.actions.open_all_documents_in_repository import (
    OpenAllDocumentsInRepositoryAction,
)
from freecad.diff_wb.domain.git.models import GitRepository
from tests.fakes.fake_freecad_port import FakeFreeCadPort


class TestOpenAllDocumentsInRepositoryAction:
    """Tests for OpenAllDocumentsInRepositoryAction."""

    def test_execute_opens_all_fcstd_files_recursively(self, tmp_path: Path) -> None:
        """Action opens all .FCStd files from repository tree."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        (repo_root / "root.FCStd").write_text("", encoding="utf-8")

        nested_dir = repo_root / "models" / "subdir"
        nested_dir.mkdir(parents=True)
        (nested_dir / "nested.FCStd").write_text("", encoding="utf-8")
        (nested_dir / "ignored.txt").write_text("", encoding="utf-8")

        fake_port = FakeFreeCadPort()
        repo = GitRepository(name="repo", absolute_path=str(repo_root))
        action = OpenAllDocumentsInRepositoryAction(fake_port)

        result = action.execute(repo)

        assert result.is_success is True
        assert sorted(result.data) == sorted(
            [
                str(repo_root / "root.FCStd"),
                str(nested_dir / "nested.FCStd"),
            ]
        )
        assert sorted(fake_port.opened_document_paths) == sorted(result.data)

    def test_execute_skips_dot_prefixed_directories(self, tmp_path: Path) -> None:
        """Action excludes dot-prefixed directories from traversal."""
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        visible_dir = repo_root / "visible"
        visible_dir.mkdir()
        hidden_dir = repo_root / ".hidden"
        hidden_dir.mkdir()

        (visible_dir / "ok.FCStd").write_text("", encoding="utf-8")
        (hidden_dir / "skip.FCStd").write_text("", encoding="utf-8")

        fake_port = FakeFreeCadPort()
        repo = GitRepository(name="repo", absolute_path=str(repo_root))
        action = OpenAllDocumentsInRepositoryAction(fake_port)

        result = action.execute(repo)

        assert result.is_success is True
        assert result.data == [str(visible_dir / "ok.FCStd")]
        assert fake_port.opened_document_paths == [str(visible_dir / "ok.FCStd")]
