# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for snapshot path computation functions.
"""Unit tests for snapshot YAML path computation."""

from pathlib import Path

from freecad.history_wb.domain.snapshots import get_snapshot_yaml_path_for_document


class TestGetSnapshotYamlPathForDocument:
    """Tests for get_snapshot_yaml_path_for_document function."""

    def test_returns_yaml_path_not_directory(self) -> None:
        """Test: Returns YAML path, not directory path."""
        document_path = "/home/user/project/path/to/mydoc.FCStd"
        result = get_snapshot_yaml_path_for_document(document_path)

        # Should return the full YAML path, not just the directory
        expected = Path("/home/user/project/path/to/.snapshots/mydoc.yaml")
        assert result == expected

    def test_yaml_path_in_root_directory(self) -> None:
        """Test: Works when document is in root directory."""
        document_path = "mydoc.FCStd"
        result = get_snapshot_yaml_path_for_document(document_path)

        expected = Path(".snapshots/mydoc.yaml")
        assert result == expected

    def test_removes_extension_and_adds_yaml(self) -> None:
        """Test: Removes original extension and adds .yaml."""
        document_path = "/path/to/document.FCStd"
        result = get_snapshot_yaml_path_for_document(document_path)

        assert result.name == "document.yaml"
        assert result.suffix == ".yaml"

    def test_handles_nested_directories(self) -> None:
        """Test: Handles deeply nested directory structures."""
        document_path = "/a/b/c/d/e/f/document.FCStd"
        result = get_snapshot_yaml_path_for_document(document_path)

        expected = Path("/a/b/c/d/e/f/.snapshots/document.yaml")
        assert result == expected

    def test_preserves_document_name_with_spaces(self) -> None:
        """Test: Preserves document name with spaces."""
        document_path = "/path/to/my document.FCStd"
        result = get_snapshot_yaml_path_for_document(document_path)

        assert result.name == "my document.yaml"

    def test_handles_windows_separators_in_git_path(self) -> None:
        """Test: Windows-style git paths place snapshots beside document path."""
        document_path = "assemblies\\sub\\Widget.FCStd"
        result = get_snapshot_yaml_path_for_document(document_path)

        expected = Path("assemblies/sub/.snapshots/Widget.yaml")
        assert result == expected
