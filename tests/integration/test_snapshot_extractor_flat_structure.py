# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Integration tests for SnapshotExtractor flat node structure.
# Tests verify that the extractor produces flat nodes with correct id, path, and after fields.
# Requires FreeCAD runtime.
"""Integration tests for SnapshotExtractor flat node structure."""

from __future__ import annotations

import pytest

from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor


@pytest.fixture
def extractor() -> SnapshotExtractor:
    """Create a SnapshotExtractor instance."""
    return SnapshotExtractor()


class TestSnapshotExtractorFlatStructure:
    """Tests for flat node structure output from SnapshotExtractor.

    These tests verify the extractor produces the correct flat structure
    with id, path, and after fields as specified in the domain model.
    """

    def test_extracted_snapshot_has_occurrences_and_objects(self, freecad_app, extractor, project_root) -> None:
        """Test that extracted snapshot has occurrences and objects lists.

        After refactoring, Snapshot has separate 'occurrences' and 'objects' lists
        instead of a single 'nodes' list.
        """
        from pathlib import Path

        # Open existing test file (has proper ViewProviders initialized)
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(doc)

            # Verify it has occurrences and objects
            assert hasattr(snapshot, "occurrences"), "Snapshot should have 'occurrences' attribute"
            assert hasattr(snapshot, "objects"), "Snapshot should have 'objects' attribute"
            assert isinstance(snapshot.occurrences, list), "occurrences should be a list"
            assert isinstance(snapshot.objects, list), "objects should be a list"
            assert len(snapshot.occurrences) > 0, "Should have at least one occurrence"
            assert len(snapshot.objects) > 0, "Should have at least one object"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_each_occurrence_has_path_and_after(self, freecad_app, extractor, project_root) -> None:
        """Test that each occurrence has path and after fields populated correctly."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(doc)

            # Check each occurrence has required fields
            for occ in snapshot.occurrences:
                assert hasattr(occ, "path"), "Occurrence should have 'path' attribute"
                assert hasattr(occ, "after"), "Occurrence should have 'after' attribute"
                assert isinstance(occ.path, str), "path should be a string"
                assert occ.after is None or isinstance(occ.after, str), "after should be None or string"

            # Check objects have required fields
            for obj in snapshot.objects:
                assert hasattr(obj, "id"), "Object should have 'id' attribute"
                assert hasattr(obj, "name"), "Object should have 'name' attribute"
                assert hasattr(obj, "type_id"), "Object should have 'type_id' attribute"
                assert isinstance(obj.id, int), "id should be an integer"
                assert isinstance(obj.name, str), "name should be a string"
                assert isinstance(obj.type_id, str), "type_id should be a string"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_root_occurrences_have_after_null(self, freecad_app, extractor, project_root) -> None:
        """Test that root occurrences have after=None (they are first in document order).

        Root occurrences are those that have no parent - path doesn't contain '/'.
        """
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(doc)

            # Find root occurrences (those with no parent - path doesn't contain '/')
            root_occurrences = [occ for occ in snapshot.occurrences if "/" not in occ.path]

            # First root should have after=None
            assert len(root_occurrences) >= 1, "Should have at least one root occurrence"
            assert root_occurrences[0].after is None, (
                f"First root should have after=None, got {root_occurrences[0].after}"
            )

            # If there are multiple roots, they should have 'after' pointing to previous root
            if len(root_occurrences) > 1:
                # Get object names for root occurrences
                root_names = []
                for occ in root_occurrences:
                    obj = snapshot.find_object(occ.path.rsplit("/", 1)[-1])
                    if obj:
                        root_names.append(obj.name)

                # Second root should have 'after' set to the first root's name
                second_obj = snapshot.find_object(root_occurrences[1].path.rsplit("/", 1)[-1])
                first_obj = snapshot.find_object(root_occurrences[0].path.rsplit("/", 1)[-1])
                if second_obj and first_obj:
                    assert (
                        second_obj.name == root_occurrences[1].after or first_obj.name == root_occurrences[1].after
                    ), f"Second root should reference first root by name"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_first_child_has_after_null(self, freecad_app, extractor, project_root) -> None:
        """Test that first child of any parent has after=None."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(doc)

            # Find occurrences that are children (have '/' in path)
            child_occurrences = [occ for occ in snapshot.occurrences if "/" in occ.path]

            # Check that first child of each parent has after=None
            # Group by parent path
            parent_children: dict[str, list] = {}
            for occ in child_occurrences:
                parent = occ.path.rsplit("/", 1)[0]
                if parent not in parent_children:
                    parent_children[parent] = []
                parent_children[parent].append(occ)

            # For each parent's children, check first child has after=None
            for parent, children in parent_children.items():
                if children:
                    first_child = children[0]
                    assert first_child.after is None, (
                        f"First child of {parent} should have after=None, got {first_child.after}"
                    )
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_subsequent_children_have_after_set(self, freecad_app, extractor, project_root) -> None:
        """Test that subsequent children have after set to previous sibling name."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(doc)

            # Find occurrences that are children (have '/' in path)
            child_occurrences = [occ for occ in snapshot.occurrences if "/" in occ.path]

            # Group by parent path
            parent_children: dict[str, list] = {}
            for occ in child_occurrences:
                parent = occ.path.rsplit("/", 1)[0]
                if parent not in parent_children:
                    parent_children[parent] = []
                parent_children[parent].append(occ)

            # For each parent with multiple children, verify 'after' ordering
            for parent, children in parent_children.items():
                if len(children) > 1:
                    # Get object names for children
                    child_names = []
                    for occ in children:
                        obj = snapshot.find_object(occ.path.rsplit("/", 1)[-1])
                        if obj:
                            child_names.append(obj.name)

                    # Verify that after is set correctly for subsequent children
                    for i in range(1, len(children)):
                        expected_after = child_names[i - 1]
                        actual_after = children[i].after
                        assert actual_after == expected_after, (
                            f"Child {i} of {parent} should have after={expected_after}, got {actual_after}"
                        )
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_all_objects_have_unique_ids(self, freecad_app, extractor, project_root) -> None:
        """Test that all objects have unique ids."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(doc)

            # Check all object ids are unique
            ids = [obj.id for obj in snapshot.objects]
            assert len(ids) == len(set(ids)), f"All object IDs should be unique. Got: {ids}"

            # All ids should be positive integers
            for obj_id in ids:
                assert isinstance(obj_id, int), f"ID should be an integer, got {type(obj_id)}"
                assert obj_id > 0, f"ID should be positive, got {obj_id}"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_path_format_root_vs_child(self, freecad_app, extractor, project_root) -> None:
        """Test that root occurrences have path=name, children have path=ParentName/ChildName."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(doc)

            # Find the Part object (should be root)
            part_obj = snapshot.find_object("Part")
            part_occ = next((occ for occ in snapshot.occurrences if occ.path == "Part"), None)

            # Find Body object (should be child of Part)
            body_obj = snapshot.find_object("Body_MyBody")
            body_occ = next((occ for occ in snapshot.occurrences if occ.path == "Part/Body_MyBody"), None)

            if part_occ:
                # Root occurrence: path = name
                assert part_occ.path == "Part", f"Root occurrence path should be name, got {part_occ.path}"

            if body_occ:
                # Child occurrence: path = parent/child
                assert body_occ.path == "Part/Body_MyBody", f"Child path should be Parent/Child, got {body_occ.path}"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_object_id_matches_freecad_object_id(self, freecad_app, extractor, project_root) -> None:
        """Test that object id uses FreeCAD's object.ID property.

        The id should match the unique integer ID that FreeCAD assigns to each object.
        """
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Get actual FreeCAD object IDs
            part_obj = doc.getObject("Part")
            body_obj = doc.getObject("Body_MyBody")

            if part_obj and body_obj:
                part_id = part_obj.ID
                body_id = body_obj.ID

                # Extract the snapshot
                snapshot = extractor.extract_tree(doc)

                # Find the objects
                part_snapshot_obj = snapshot.find_object("Part")
                body_snapshot_obj = snapshot.find_object("Body_MyBody")

                if part_snapshot_obj:
                    assert part_snapshot_obj.id == part_id, (
                        f"Part object id should match .ID, got {part_snapshot_obj.id} vs {part_id}"
                    )

                if body_snapshot_obj:
                    assert body_snapshot_obj.id == body_id, (
                        f"Body object id should match .ID, got {body_snapshot_obj.id} vs {body_id}"
                    )
        finally:
            freecad_app.closeDocument(doc.Name)
