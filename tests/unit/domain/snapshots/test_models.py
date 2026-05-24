# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for normalized Snapshot models.
"""Unit tests for snapshot models."""

from datetime import datetime

from freecad.history_wb.domain import Snapshot, SnapshotObject, SnapshotOccurrence


class TestSnapshot:
    def test_creation(self) -> None:
        ts = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(snapshot_id="s", document_name="Doc", timestamp=ts, git_path="")
        assert snapshot.document_name == "Doc"
        assert snapshot.timestamp == ts

    def test_finders(self) -> None:
        ts = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(
            snapshot_id="s",
            document_name="Doc",
            timestamp=ts,
            objects=[SnapshotObject(name="Body", id=1, type_id="PartDesign::Body", properties={})],
            occurrences=[SnapshotOccurrence(path="Body", after=None)],
        )
        assert snapshot.find_object("Body") is not None
        assert snapshot.find_occurrence("Body") is not None
        assert snapshot.find_object("Missing") is None
        assert snapshot.find_occurrence("Missing") is None

    def test_node_count_uses_occurrences(self) -> None:
        ts = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(
            snapshot_id="s",
            document_name="Doc",
            timestamp=ts,
            objects=[SnapshotObject(name="A", id=1, type_id="Type", properties={})],
            occurrences=[
                SnapshotOccurrence(path="A", after=None),
                SnapshotOccurrence(path="Root/A", after=None),
            ],
        )
        assert snapshot.node_count == 2

    def test_with_identity_normalizes_windows_git_path(self) -> None:
        ts = datetime(2024, 1, 1, 0, 0, 0)
        snapshot = Snapshot(snapshot_id="s", document_name="Doc", timestamp=ts)

        result = snapshot.with_identity("assemblies\\sub\\Widget.FCStd")

        assert result.git_path == "assemblies/sub/Widget.FCStd"
        assert result.document_name == "Widget.FCStd"
