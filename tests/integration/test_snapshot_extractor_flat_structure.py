# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Integration tests for SnapshotExtractor flat node structure.
# Tests verify that the extractor produces flat nodes with correct id, path, and after fields.
# Requires FreeCAD runtime.
"""Integration tests for SnapshotExtractor flat node structure."""

from __future__ import annotations

import pytest

from freecad.diff_wb.domain.snapshots.gui_extractor import SnapshotExtractor
from freecad.diff_wb.infrastructure.freecad.ports import get_freecad_runtime_context, get_port


@pytest.fixture
def extractor() -> SnapshotExtractor:
    """Create a SnapshotExtractor instance."""
    return SnapshotExtractor()


@pytest.fixture
def freecad_port():
    """Get a FreeCadPort for testing."""
    ctx = get_freecad_runtime_context()
    return get_port(ctx)


class TestSnapshotExtractorFlatStructure:
    """Tests for flat node structure output from SnapshotExtractor.

    These tests verify the extractor produces the correct flat structure
    with id, path, and after fields as specified in the domain model.
    """

    def test_extracted_snapshot_has_flat_node_list(self, freecad_app, extractor, freecad_port, project_root):
        """Test that extracted snapshot has flat node list (no hierarchical tree).

        The Snapshot should have a 'nodes' list attribute, not 'root_nodes'.
        """
        from pathlib import Path

        # Open existing test file (has proper ViewProviders initialized)
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(freecad_port)

            # Verify it's a flat list
            assert hasattr(snapshot, "nodes"), "Snapshot should have 'nodes' attribute"
            assert isinstance(snapshot.nodes, list), "nodes should be a list"
            assert len(snapshot.nodes) > 0, "Should have at least one node"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_each_node_has_id_path_after(self, freecad_app, extractor, freecad_port, project_root):
        """Test that each node has id, path, and after fields populated correctly."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(freecad_port)

            # Check each node has required fields
            for node in snapshot.nodes:
                assert hasattr(node, "id"), "Node should have 'id' attribute"
                assert hasattr(node, "path"), "Node should have 'path' attribute"
                assert hasattr(node, "after"), "Node should have 'after' attribute"
                assert isinstance(node.id, int), "id should be an integer"
                assert isinstance(node.path, str), "path should be a string"
                assert node.after is None or isinstance(node.after, str), "after should be None or string"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_root_nodes_have_after_null(self, freecad_app, extractor, freecad_port, project_root):
        """Test that root nodes have after=None (they are first in document order).

        Root nodes are those that have no parent in the claimChildren hierarchy.
        """
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(freecad_port)

            # Find root nodes (those with no parent - path doesn't contain '/')
            root_nodes = [n for n in snapshot.nodes if "/" not in n.path]

            # First root should have after=None
            assert len(root_nodes) >= 1, "Should have at least one root node"
            assert root_nodes[0].after is None, f"First root node should have after=None, got {root_nodes[0].after}"

            # If there are multiple roots, they should have 'after' pointing to previous root
            if len(root_nodes) > 1:
                # Second root should have 'after' set to the first root's name
                assert root_nodes[1].after == root_nodes[0].name, (
                    f"Second root should have after={root_nodes[0].name}, got {root_nodes[1].after}"
                )
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_first_child_has_after_null(self, freecad_app, extractor, freecad_port, project_root):
        """Test that first child of any parent has after=None."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(freecad_port)

            # Find nodes that are children (have '/' in path)
            child_nodes = [n for n in snapshot.nodes if "/" in n.path]

            # Check that first child of each parent has after=None
            # Group by parent path
            parent_children: dict[str, list] = {}
            for node in child_nodes:
                parent = node.path.rsplit("/", 1)[0]
                if parent not in parent_children:
                    parent_children[parent] = []
                parent_children[parent].append(node)

            # For each parent's children, check first child has after=None
            for parent, children in parent_children.items():
                if children:
                    first_child = children[0]
                    assert first_child.after is None, (
                        f"First child of {parent} should have after=None, got {first_child.after}"
                    )
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_subsequent_children_have_after_set(self, freecad_app, extractor, freecad_port, project_root):
        """Test that subsequent children have after set to previous sibling name."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(freecad_port)

            # Find nodes that are children (have '/' in path)
            child_nodes = [n for n in snapshot.nodes if "/" in n.path]

            # Group by parent path
            parent_children: dict[str, list] = {}
            for node in child_nodes:
                parent = node.path.rsplit("/", 1)[0]
                if parent not in parent_children:
                    parent_children[parent] = []
                parent_children[parent].append(node)

            # For each parent with multiple children, verify 'after' ordering
            for parent, children in parent_children.items():
                if len(children) > 1:
                    # Verify that after is set correctly for subsequent children
                    for i in range(1, len(children)):
                        expected_after = children[i - 1].name
                        actual_after = children[i].after
                        assert actual_after == expected_after, (
                            f"Child {i} of {parent} should have after={expected_after}, got {actual_after}"
                        )
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_all_nodes_have_unique_ids(self, freecad_app, extractor, freecad_port, project_root):
        """Test that all nodes have unique ids."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(freecad_port)

            # Check all ids are unique
            ids = [node.id for node in snapshot.nodes]
            assert len(ids) == len(set(ids)), f"All node IDs should be unique. Got: {ids}"

            # All ids should be positive integers
            for node_id in ids:
                assert isinstance(node_id, int), f"ID should be an integer, got {type(node_id)}"
                assert node_id > 0, f"ID should be positive, got {node_id}"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_path_format_root_vs_child(self, freecad_app, extractor, freecad_port, project_root):
        """Test that root nodes have path=name, children have path=ParentName/ChildName."""
        from pathlib import Path

        # Open existing test file
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract the snapshot
            snapshot = extractor.extract_tree(freecad_port)

            # Find the Part node (should be root)
            part_node = next((n for n in snapshot.nodes if n.name == "Part"), None)

            # Find Body node (should be child of Part)
            body_node = next((n for n in snapshot.nodes if n.name == "Body_MyBody"), None)

            if part_node:
                # Root node: path = name
                assert part_node.path == "Part", f"Root node path should be name, got {part_node.path}"

            if body_node:
                # Child node: path = parent/child
                assert body_node.path == "Part/Body_MyBody", f"Child path should be Parent/Child, got {body_node.path}"
        finally:
            freecad_app.closeDocument(doc.Name)

    def test_node_id_is_object_id_property(self, freecad_app, extractor, freecad_port, project_root):
        """Test that node id uses FreeCAD's object.ID property.

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
                snapshot = extractor.extract_tree(freecad_port)

                # Find the nodes
                part_node = next((n for n in snapshot.nodes if n.name == "Part"), None)
                body_node = next((n for n in snapshot.nodes if n.name == "Body_MyBody"), None)

                if part_node:
                    assert part_node.id == part_id, f"Part node id should match .ID, got {part_node.id} vs {part_id}"

                if body_node:
                    assert body_node.id == body_id, f"Body node id should match .ID, got {body_node.id} vs {body_id}"
        finally:
            freecad_app.closeDocument(doc.Name)
