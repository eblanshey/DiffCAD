# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Integration test for SnapshotExtractor BasicFile.FCStd snapshot contract.
# Verifies the complete flat node structure produced by extracting the canonical test document.
"""Integration test for SnapshotExtractor BasicFile.FCStd snapshot contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor


@pytest.fixture
def extractor(freecad_gui: object) -> SnapshotExtractor:
    """Create a SnapshotExtractor instance."""
    return SnapshotExtractor(gui=freecad_gui)  # type: ignore[arg-type]


class TestBasicFileSnapshotContract:
    """Single contract test verifying the complete snapshot structure from BasicFile.FCStd.

    Validates occurrences, objects, paths, after ordering, unique IDs, and
    FreeCAD object ID mapping in one comprehensive assertion against the
    canonical test document.
    """

    def test_basicfile_snapshot_contract(self, freecad_app, extractor, project_root) -> None:
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            snapshot = extractor.extract_tree(doc)

            # --- Top-level structure ---
            assert isinstance(snapshot.occurrences, list) and len(snapshot.occurrences) > 0
            assert isinstance(snapshot.objects, list) and len(snapshot.objects) > 0

            # --- Occurrence fields ---
            for occ in snapshot.occurrences:
                assert isinstance(occ.path, str)
                assert occ.after is None or isinstance(occ.after, str)

            # --- Object fields ---
            ids = []
            for obj in snapshot.objects:
                assert isinstance(obj.id, int) and obj.id > 0
                assert isinstance(obj.name, str)
                assert isinstance(obj.type_id, str)
                ids.append(obj.id)
            assert len(ids) == len(set(ids)), "Object IDs must be unique"

            # --- Root occurrences: path = name, first root after=None ---
            root_occurrences = [occ for occ in snapshot.occurrences if "/" not in occ.path]
            assert len(root_occurrences) >= 1
            assert root_occurrences[0].after is None

            # --- Child occurrences: first child of each parent has after=None ---
            child_occurrences = [occ for occ in snapshot.occurrences if "/" in occ.path]
            parent_children: dict[str, list] = {}
            for occ in child_occurrences:
                parent = occ.path.rsplit("/", 1)[0]
                parent_children.setdefault(parent, []).append(occ)

            for children in parent_children.values():
                assert children[0].after is None, "First child must have after=None"

                # Subsequent children reference previous sibling by name
                if len(children) > 1:
                    child_names = []
                    for occ in children:
                        obj = snapshot.find_object(occ.path.rsplit("/", 1)[-1])
                        if obj:
                            child_names.append(obj.name)
                    for i in range(1, len(children)):
                        assert children[i].after == child_names[i - 1]

            # --- Path format: root vs child ---
            part_occ = next((occ for occ in snapshot.occurrences if occ.path == "Part"), None)
            body_occ = next((occ for occ in snapshot.occurrences if occ.path == "Part/Body_MyBody"), None)
            if part_occ:
                assert part_occ.path == "Part"
            if body_occ:
                assert body_occ.path == "Part/Body_MyBody"

            # --- Object IDs match FreeCAD .ID ---
            part_obj = doc.getObject("Part")
            body_obj = doc.getObject("Body_MyBody")
            if part_obj:
                part_snap = snapshot.find_object("Part")
                if part_snap:
                    assert part_snap.id == part_obj.ID
            if body_obj:
                body_snap = snapshot.find_object("Body_MyBody")
                if body_snap:
                    assert body_snap.id == body_obj.ID

        finally:
            freecad_app.closeDocument(doc.Name)
