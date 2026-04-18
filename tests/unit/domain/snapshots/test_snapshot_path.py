# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for the get_snapshot_directory_for_document function
# which calculates the .snapshots directory path for a given document file.
"""Tests for snapshot path calculation."""

from pathlib import Path

from freecad.diff_wb.domain.snapshots import get_snapshot_directory_for_document


def test_get_snapshot_directory_returns_correct_path():
    """Test that get_snapshot_directory_for_document returns the correct path.

    Given a path "/home/user/project/path/to/doc.FCStd"
    When get_snapshot_directory_for_document is called
    Then it returns Path("/home/user/project/path/to/.snapshots")
    """
    # Given
    document_path = "/home/user/project/path/to/doc.FCStd"

    # When
    result = get_snapshot_directory_for_document(document_path)

    # Then
    assert result == Path("/home/user/project/path/to/.snapshots")


def test_get_snapshot_directory_strips_filename():
    """Test that the filename is stripped from the path.

    Given "path/to/mydoc.FCStd"
    When get_snapshot_directory_for_document is called
    Then the result is "path/to/.snapshots" not "path/to/mydoc.FCStd/.snapshots"
    """
    # Given
    document_path = "path/to/mydoc.FCStd"

    # When
    result = get_snapshot_directory_for_document(document_path)

    # Then
    assert result == Path("path/to/.snapshots")
    # Ensure it's not treating the filename as a directory
    assert "mydoc.FCStd" not in str(result)


def test_get_snapshot_directory_file_in_root():
    """Test handling of files in root directory.

    Given "mydoc.FCStd" (no directory component)
    When get_snapshot_directory_for_document is called
    Then it returns ".snapshots" (in current directory)
    """
    # Given
    document_path = "mydoc.FCStd"

    # When
    result = get_snapshot_directory_for_document(document_path)

    # Then
    assert result == Path(".snapshots")
