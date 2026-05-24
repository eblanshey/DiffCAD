# File responsibility: Unit tests for FreeCadFileManagerAdapter file management operations.
"""Unit tests for FreeCadFileManagerAdapter."""

from __future__ import annotations

import zipfile
from pathlib import Path

from freecad.history_wb.infrastructure.freecad.freecad_file_manager import (
    FreeCadFileManagerAdapter,
)

from tests.fakes.fake_git_port import FakeGitPort


def _create_fcstd_archive(path: Path, files: dict[str, str]) -> None:
    """Create a fake FCStd archive with the given files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in files.items():
            archive.writestr(name, content)


class TestFindExtractedFile:
    """Tests for FreeCadFileManagerAdapter.find_extracted_file()."""

    def test_returns_file_path_when_file_exists(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        extract_root = tmp_path / "extracted"
        target_file = extract_root / "PartData" / "Pad.Shape.brp"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("BREP_DATA", encoding="utf-8")

        result = adapter.find_extracted_file(extract_root, "Pad.Shape.brp")

        assert result == target_file

    def test_returns_none_when_file_not_found(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        extract_root = tmp_path / "extracted"
        other_file = extract_root / "PartData" / "Other.Shape.brp"
        other_file.parent.mkdir(parents=True, exist_ok=True)
        other_file.write_text("BREP_DATA", encoding="utf-8")

        result = adapter.find_extracted_file(extract_root, "Pad.Shape.brp")

        assert result is None

    def test_returns_none_when_extract_root_is_empty(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        extract_root = tmp_path / "empty_extract"
        extract_root.mkdir(parents=True, exist_ok=True)

        result = adapter.find_extracted_file(extract_root, "Pad.Shape.brp")

        assert result is None

    def test_finds_file_in_nested_directory(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        extract_root = tmp_path / "extracted"
        target_file = extract_root / "PartData" / "SubDir" / "Pad.Shape.brp"
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text("BREP_DATA", encoding="utf-8")

        result = adapter.find_extracted_file(extract_root, "Pad.Shape.brp")

        assert result == target_file


class TestExtractSafely:
    """Tests for FreeCadFileManagerAdapter._extract_safely()."""

    def test_extracts_valid_archive_successfully(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        archive_path = tmp_path / "test.FCStd"
        extract_dir = tmp_path / "extracted"
        _create_fcstd_archive(archive_path, {"PartData/test.Shape.brp": "BREP"})

        result = adapter._extract_safely(archive_path, extract_dir, "commits")

        assert result is True
        assert (extract_dir / "PartData" / "test.Shape.brp").exists()

    def test_returns_false_for_corrupt_archive(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        archive_path = tmp_path / "corrupt.FCStd"
        extract_dir = tmp_path / "extracted"
        archive_path.write_bytes(b"Not a valid zip file content")

        result = adapter._extract_safely(archive_path, extract_dir, "commits")

        assert result is False

    def test_returns_false_for_archive_with_unsafe_paths(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        archive_path = tmp_path / "unsafe.FCStd"
        extract_dir = tmp_path / "extracted"
        with zipfile.ZipFile(archive_path, "w") as zf:
            zf.writestr("../escape.txt", "escaped content")

        result = adapter._extract_safely(archive_path, extract_dir, "commits")

        assert result is False
        assert not (tmp_path / "escape.txt").exists()

    def test_clears_working_staging_extract_dirs_before_extraction(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        archive_path = tmp_path / "test.FCStd"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        old_file = extract_dir / "old_file.txt"
        old_file.write_text("old content")

        _create_fcstd_archive(archive_path, {"PartData/test.Shape.brp": "BREP"})

        result = adapter._extract_safely(archive_path, extract_dir, "working")

        assert result is True
        assert not old_file.exists()
        assert (extract_dir / "PartData" / "test.Shape.brp").exists()

    def test_skips_extraction_when_commit_extract_dir_exists(self, tmp_path: Path) -> None:
        fake_port = FakeGitPort()
        adapter = FreeCadFileManagerAdapter(git_service=fake_port)

        archive_path = tmp_path / "test.FCStd"
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        existing_file = extract_dir / "existing.txt"
        existing_file.write_text("existing content")

        _create_fcstd_archive(archive_path, {"PartData/test.Shape.brp": "BREP"})

        result = adapter._extract_safely(archive_path, extract_dir, "commits")

        assert result is True
        assert existing_file.exists()
        assert not (extract_dir / "PartData" / "test.Shape.brp").exists()
