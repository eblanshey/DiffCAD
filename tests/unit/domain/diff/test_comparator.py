# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for the tree-comparison algorithm with path-based indexing.
"""Unit tests for tree_diff module.

These tests verify the core diff computation logic without any FreeCAD dependencies.
"""

from datetime import datetime

from freecad.diff_wb.config import EXCLUDED_PROPERTIES
from freecad.diff_wb.domain.diff.comparator import PropertyComparator, TreeComparator
from freecad.diff_wb.domain.diff.models import DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.tree import Property, PropertyType
from freecad.diff_wb.domain.tree.node import TreeNode


# Test fixtures - create comparator instances
_tree_comparator = TreeComparator()
_property_comparator = PropertyComparator()


def build_path_index(root_nodes):
    """Wrapper for testing."""
    return _tree_comparator._build_path_index(root_nodes)


def find_added_paths(old_index, new_index):
    """Wrapper for testing."""
    return _tree_comparator._find_added_paths(old_index, new_index)


def find_deleted_paths(old_index, new_index):
    """Wrapper for testing."""
    return _tree_comparator._find_deleted_paths(old_index, new_index)


def find_common_paths(old_index, new_index):
    """Wrapper for testing."""
    return _tree_comparator._find_common_paths(old_index, new_index)


def reconstruct_hierarchy(node_diffs):
    """Wrapper for testing."""
    return _tree_comparator._reconstruct_hierarchy(node_diffs)


def compare_nodes_by_path(path, old_index, new_index):
    """Wrapper with default excluded_properties."""
    return _tree_comparator._compare_nodes_by_path(path, old_index, new_index, EXCLUDED_PROPERTIES)


def create_added_node_diff(path, node):
    """Wrapper with default excluded_properties."""
    return _tree_comparator._create_added_node_diff(path, node, EXCLUDED_PROPERTIES)


def create_deleted_node_diff(path, node):
    """Wrapper with default excluded_properties."""
    return _tree_comparator._create_deleted_node_diff(path, node, EXCLUDED_PROPERTIES)


def compare_snapshots(old_snapshot, new_snapshot):
    """Wrapper that extracts root_nodes from snapshots."""
    return _tree_comparator.compare_snapshots(old_snapshot.root_nodes, new_snapshot.root_nodes, [])


def compare_properties(old_props, new_props):
    """Wrapper with default excluded_properties."""
    return _property_comparator.compare_properties(old_props, new_props, EXCLUDED_PROPERTIES)


should_exclude_property = _property_comparator._should_exclude_property
values_are_equal = _property_comparator._values_are_equal


class TestBuildPathIndex:
    """Tests for build_path_index function."""

    def test_empty_root_nodes(self):
        """Test building index from empty root nodes list."""
        index = build_path_index([])
        assert index == {}

    def test_single_root_node(self):
        """Test building index with a single root node."""
        root = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        snapshot = Snapshot(snapshot_id="", document_name="Test", timestamp=datetime.now(), root_nodes=[root])

        index = build_path_index(snapshot.root_nodes)

        assert len(index) == 1
        assert "Body" in index
        assert index["Body"] is root

    def test_nested_children(self):
        """Test building index with nested children."""
        grandchild = TreeNode(
            name="ShapeSource",
            type_id="Part::Feature",
            label="ShapeSource",
            path="Body/Pad/ShapeSource",
        )
        child = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            children=[grandchild],
        )
        root = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[child],
        )

        index = build_path_index([root])

        assert len(index) == 3
        assert "Body" in index
        assert "Body/Pad" in index
        assert "Body/Pad/ShapeSource" in index

    def test_multiple_roots(self):
        """Test building index with multiple root nodes."""
        root1 = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        root2 = TreeNode(name="Cube", type_id="Part::Box", label="Cube", path="Cube")

        index = build_path_index([root1, root2])

        assert len(index) == 2
        assert "Body" in index
        assert "Cube" in index


class TestFindAddedPaths:
    """Tests for find_added_paths function."""

    def test_no_added_paths(self):
        """Test when new snapshot has no new paths."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        added = find_added_paths(old_index, new_index)

        assert added == set()

    def test_simple_addition(self):
        """Test detecting a simple addition."""
        old_index = {"Body": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        added = find_added_paths(old_index, new_index)

        assert added == {"Body/Pad"}

    def test_multiple_additions(self):
        """Test detecting multiple additions."""
        old_index = {"Body": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None, "Body/Pocket": None}  # type: ignore

        added = find_added_paths(old_index, new_index)

        assert added == {"Body/Pad", "Body/Pocket"}


class TestFindDeletedPaths:
    """Tests for find_deleted_paths function."""

    def test_no_deleted_paths(self):
        """Test when old snapshot has no deleted paths."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        deleted = find_deleted_paths(old_index, new_index)

        assert deleted == set()

    def test_simple_deletion(self):
        """Test detecting a simple deletion."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None}  # type: ignore

        deleted = find_deleted_paths(old_index, new_index)

        assert deleted == {"Body/Pad"}

    def test_multiple_deletions(self):
        """Test detecting multiple deletions."""
        old_index = {"Body": None, "Body/Pad": None, "Body/Pocket": None}  # type: ignore
        new_index = {"Body": None}  # type: ignore

        deleted = find_deleted_paths(old_index, new_index)

        assert deleted == {"Body/Pad", "Body/Pocket"}


class TestFindCommonPaths:
    """Tests for find_common_paths function."""

    def test_all_common(self):
        """Test when all paths are common."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pad": None}  # type: ignore

        common = find_common_paths(old_index, new_index)

        assert common == {"Body", "Body/Pad"}

    def test_no_common(self):
        """Test when no paths are common."""
        old_index = {"Body": None}  # type: ignore
        new_index = {"Cube": None}  # type: ignore

        common = find_common_paths(old_index, new_index)

        assert common == set()

    def test_partial_common(self):
        """Test when some paths are common."""
        old_index = {"Body": None, "Body/Pad": None}  # type: ignore
        new_index = {"Body": None, "Body/Pocket": None}  # type: ignore

        common = find_common_paths(old_index, new_index)

        assert common == {"Body"}


class TestCompareNodesByPath:
    """Tests for compare_nodes_by_path function."""

    def test_identical_nodes(self):
        """Test comparing identical nodes returns None."""
        props = {
            "Label": Property.create(PropertyType.STRING, "Body"),
        }
        old_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            properties=props,
        )
        new_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            properties=props,
        )

        old_index = {"Body": old_node}
        new_index = {"Body": new_node}

        result = compare_nodes_by_path("Body", old_index, new_index)

        assert result is None

    def test_modified_property(self):
        """Test detecting a modified property."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        assert result is not None
        assert result.path == "Body/Pad"
        assert result.state == DiffState.MODIFIED

    def test_added_property(self):
        """Test detecting an added property."""
        old_props = {}
        new_props = {
            "NewProperty": Property.create(PropertyType.STRING, "value"),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        assert result is not None
        assert result.state == DiffState.MODIFIED

    def test_deleted_property(self):
        """Test detecting a deleted property."""
        old_props = {
            "OldProperty": Property.create(PropertyType.STRING, "value"),
        }
        new_props = {}
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        assert result is not None
        assert result.state == DiffState.MODIFIED

    def test_excluded_properties_filtered(self):
        """Test that excluded properties are filtered out during comparison."""
        # TimeStamp is in EXCLUDED_PROPERTIES (AUTO_EXCLUDED_PROPERTIES)
        old_props = {
            "TimeStamp": Property.create(PropertyType.STRING, "2024-01-01T00:00:00"),
            "Label": Property.create(PropertyType.STRING, "Pad"),
        }
        new_props = {
            "TimeStamp": Property.create(PropertyType.STRING, "2024-01-01T00:00:01"),  # Different timestamp
            "Label": Property.create(PropertyType.STRING, "Pad"),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        # Should return None because only excluded property (TimeStamp) differs
        assert result is None


class TestCreateAddedNodeDiff:
    """Tests for create_added_node_diff function."""

    def test_creates_correct_state(self):
        """Test that added node diff has ADDED state."""
        node = TreeNode(
            name="NewObject",
            type_id="Part::Box",
            label="New Object",
            path="NewObject",
        )

        result = create_added_node_diff("NewObject", node)

        assert result.path == "NewObject"
        assert result.type_id == "Part::Box"
        assert result.state == DiffState.ADDED


class TestCreateDeletedNodeDiff:
    """Tests for create_deleted_node_diff function."""

    def test_creates_correct_state(self):
        """Test that deleted node diff has DELETED state."""
        node = TreeNode(
            name="OldObject",
            type_id="Part::Box",
            label="Old Object",
            path="OldObject",
        )

        result = create_deleted_node_diff("OldObject", node)

        assert result.path == "OldObject"
        assert result.type_id == "Part::Box"
        assert result.state == DiffState.DELETED


class TestReconstructHierarchy:
    """Tests for reconstruct_hierarchy function."""

    def test_hierarchy_order(self):
        """Test that hierarchy is reconstructed in correct tree order.

        Verifies that:
        - Parents appear before their children
        - Siblings are sorted alphabetically
        """
        from freecad.diff_wb.domain.diff import PropertyDiff

        # Create NodeDiff objects in random/unsorted order
        diffs = [
            NodeDiff(
                path="Body/Pad/ShapeSource",
                type_id="Part::Feature",
                property_diffs=[
                    PropertyDiff(
                        property_name="Placement",
                        old_value=Property.create(PropertyType.VECTOR, (0, 0, 0)),
                        new_value=Property.create(PropertyType.VECTOR, (1, 1, 1)),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pocket",
                type_id="PartDesign::Pocket",
                property_diffs=[
                    PropertyDiff(
                        property_name="Depth",
                        old_value=None,
                        new_value=Property.create(PropertyType.FLOAT, 5.0),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad",
                type_id="PartDesign::Pad",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=Property.create(PropertyType.FLOAT, 10.0),
                        new_value=None,
                    )
                ],
            ),
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=Property.create(PropertyType.STRING, "OldBody"),
                        new_value=Property.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Cube",
                type_id="Part::Box",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=Property.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        # Verify root nodes are in alphabetical order: Body, Cube
        assert len(result) == 2
        assert result[0].path == "Body"
        assert result[1].path == "Cube"

        # Verify Body's children are in order: Pad, Pocket (alphabetical)
        assert len(result[0].children) == 2
        assert result[0].children[0].path == "Body/Pad"
        assert result[0].children[1].path == "Body/Pocket"

        # Verify Pad has ShapeSource as child (parent before child)
        assert len(result[0].children[0].children) == 1
        assert result[0].children[0].children[0].path == "Body/Pad/ShapeSource"

    def test_empty_list(self):
        """Test reconstructing hierarchy from empty list."""
        result = reconstruct_hierarchy([])
        assert result == []

    def test_single_root(self):
        """Test reconstructing hierarchy with single root node."""
        from freecad.diff_wb.domain.diff import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=None,
                        new_value=Property.create(PropertyType.STRING, "Body"),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 1
        assert result[0].path == "Body"
        assert len(result[0].children) == 0

    def test_parent_child_relationship(self):
        """Test that parent-child relationships are correctly reconstructed."""
        from freecad.diff_wb.domain.diff import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=Property.create(PropertyType.STRING, "OldBody"),
                        new_value=Property.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad",
                type_id="PartDesign::Pad",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=Property.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 1
        assert result[0].path == "Body"
        assert len(result[0].children) == 1
        assert result[0].children[0].path == "Body/Pad"

    def test_deep_nesting(self):
        """Test reconstructing deeply nested hierarchy."""
        from freecad.diff_wb.domain.diff import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=Property.create(PropertyType.STRING, "OldBody"),
                        new_value=Property.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad",
                type_id="PartDesign::Pad",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=Property.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
            NodeDiff(
                path="Body/Pad/ShapeSource",
                type_id="Part::Feature",
                property_diffs=[
                    PropertyDiff(
                        property_name="Placement",
                        old_value=None,
                        new_value=Property.create(PropertyType.VECTOR, (0, 0, 0)),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 1
        assert result[0].path == "Body"
        assert len(result[0].children) == 1
        assert result[0].children[0].path == "Body/Pad"
        assert len(result[0].children[0].children) == 1
        assert result[0].children[0].children[0].path == "Body/Pad/ShapeSource"

    def test_multiple_roots(self):
        """Test reconstructing hierarchy with multiple root nodes."""
        from freecad.diff_wb.domain.diff import PropertyDiff

        diffs = [
            NodeDiff(
                path="Body",
                type_id="PartDesign::Body",
                property_diffs=[
                    PropertyDiff(
                        property_name="Label",
                        old_value=Property.create(PropertyType.STRING, "OldBody"),
                        new_value=Property.create(PropertyType.STRING, "NewBody"),
                    )
                ],
            ),
            NodeDiff(
                path="Cube",
                type_id="Part::Box",
                property_diffs=[
                    PropertyDiff(
                        property_name="Length",
                        old_value=None,
                        new_value=Property.create(PropertyType.FLOAT, 10.0),
                    )
                ],
            ),
        ]

        result = reconstruct_hierarchy(diffs)

        assert len(result) == 2
        paths = {d.path for d in result}
        assert paths == {"Body", "Cube"}

    def test_inserts_missing_parent_nodes(self):
        """Test that missing parent nodes are inserted to preserve hierarchy.

        When a child node has changes but its parent doesn't (and thus isn't in
        the diff list), placeholder parent nodes should be inserted so children
        appear nested under their parents.
        """
        from freecad.diff_wb.domain.diff import PropertyDiff

        # Only Body/Pocket has changes - Body itself is not in the diff list
        # This simulates when Pocket was added but only its properties were compared
        diffs = [
            NodeDiff(
                path="Body/Pocket",
                type_id="PartDesign::Pocket",
                property_diffs=[
                    PropertyDiff(
                        property_name="Depth",
                        old_value=None,
                        new_value=Property.create(PropertyType.FLOAT, 5.0),
                    )
                ],
            ),
        ]

        # Create mock indices with type information
        old_tree = TreeNode(name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        new_tree = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[
                TreeNode(
                    name="Pocket",
                    type_id="PartDesign::Pocket",
                    label="Pocket",
                    path="Body/Pocket",
                )
            ],
        )
        old_index = {"Body": old_tree}
        new_index = {"Body": new_tree, "Body/Pocket": new_tree.children[0]}

        result = _tree_comparator._reconstruct_hierarchy(diffs, old_index, new_index)

        # Should have Body as root (placeholder, UNCHANGED)
        assert len(result) == 1
        assert result[0].path == "Body"
        assert result[0].state == DiffState.UNCHANGED
        assert result[0].type_id == "PartDesign::Body"

        # Body should have Pocket as child (MODIFIED because it has added properties)
        assert len(result[0].children) == 1
        assert result[0].children[0].path == "Body/Pocket"
        # Note: State is MODIFIED because the node has property additions
        assert result[0].children[0].state == DiffState.MODIFIED

    def test_inserts_missing_ancestor_chain(self):
        """Test that entire ancestor chain is inserted when multiple levels are missing.

        When deeply nested nodes have changes but intermediate parents don't,
        all missing ancestors should be inserted.
        """
        from freecad.diff_wb.domain.diff import PropertyDiff

        # Only Body/Pad/Sketch has changes - Body and Pad are not in diff list
        diffs = [
            NodeDiff(
                path="Body/Pad/Sketch",
                type_id="PartDesign::Sketch",
                property_diffs=[
                    PropertyDiff(
                        property_name="Name",
                        old_value=None,
                        new_value=Property.create(PropertyType.STRING, "NewSketch"),
                    )
                ],
            ),
        ]

        # Create mock indices with type information for the full hierarchy
        sketch = TreeNode(name="Sketch", type_id="PartDesign::Sketch", label="Sketch", path="Body/Pad/Sketch")
        pad = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            children=[sketch],
        )
        body = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[pad],
        )

        old_index: dict[str, TreeNode] = {}
        new_index = {"Body": body, "Body/Pad": pad, "Body/Pad/Sketch": sketch}

        result = _tree_comparator._reconstruct_hierarchy(diffs, old_index, new_index)

        # Should have Body as root (placeholder, UNCHANGED)
        assert len(result) == 1
        assert result[0].path == "Body"
        assert result[0].state == DiffState.UNCHANGED

        # Body -> Pad (placeholder, UNCHANGED) -> Sketch (MODIFIED)
        assert len(result[0].children) == 1
        assert result[0].children[0].path == "Body/Pad"
        assert result[0].children[0].state == DiffState.UNCHANGED

        assert len(result[0].children[0].children) == 1
        assert result[0].children[0].children[0].path == "Body/Pad/Sketch"
        assert result[0].children[0].children[0].state == DiffState.MODIFIED


class TestCompareSnapshots:
    """Tests for compare_snapshots function (end-to-end tree comparison)."""

    def test_empty_snapshots(self):
        """Test comparing two empty snapshots."""
        old_snapshot = Snapshot(snapshot_id="", document_name="Test", timestamp=datetime.now(), root_nodes=[])
        new_snapshot = Snapshot(snapshot_id="", document_name="Test", timestamp=datetime.now(), root_nodes=[])

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == set()
        assert result.common_paths == set()
        assert result.node_diffs == []

    def test_identical_snapshots(self):
        """Test comparing identical snapshots returns no changes."""
        node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
        )
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[node],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == set()
        assert result.common_paths == {"Body"}
        assert result.node_diffs == []  # No changes means no NodeDiff objects

    def test_simple_addition(self):
        """Test detecting a simple addition."""
        old_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
        )
        new_node = TreeNode(
            name="Cube",
            type_id="Part::Box",
            label="Cube",
            path="Cube",
        )
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node, new_node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == {"Cube"}
        assert result.deleted_paths == set()
        assert len(result.node_diffs) == 1
        assert result.node_diffs[0].path == "Cube"
        assert result.node_diffs[0].state == DiffState.ADDED

    def test_simple_deletion(self):
        """Test detecting a simple deletion."""
        old_node = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
        )
        deleted_node = TreeNode(
            name="Cube",
            type_id="Part::Box",
            label="Cube",
            path="Cube",
        )
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node, deleted_node],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == {"Cube"}
        assert len(result.node_diffs) == 1
        assert result.node_diffs[0].path == "Cube"
        assert result.node_diffs[0].state == DiffState.DELETED

    def test_simple_modification(self):
        """Test detecting a simple modification."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }
        old_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=old_props,
        )
        new_node = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties=new_props,
        )
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[new_node],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == set()
        assert result.deleted_paths == set()
        assert result.common_paths == {"Body/Pad"}
        # Body is inserted as a placeholder parent since it wasn't in the diff
        assert len(result.node_diffs) == 1
        assert result.node_diffs[0].path == "Body"
        assert result.node_diffs[0].state == DiffState.UNCHANGED
        # Body/Pad is nested under Body
        assert len(result.node_diffs[0].children) == 1
        assert result.node_diffs[0].children[0].path == "Body/Pad"
        assert result.node_diffs[0].children[0].state == DiffState.MODIFIED

    def test_complex_hierarchy_changes(self):
        """Test complex hierarchy with additions and modifications."""
        # Old: Body -> Pad (Length=10)
        old_pad = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties={"Length": Property.create(PropertyType.FLOAT, 10.0)},
        )
        old_body = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[old_pad],
        )

        # New: Body -> Pad (Length=20), Pocket (added)
        new_pad = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
        )
        new_pocket = TreeNode(
            name="Pocket",
            type_id="PartDesign::Pocket",
            label="Pocket",
            path="Body/Pocket",
        )
        new_body = TreeNode(
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            children=[new_pad, new_pocket],
        )

        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_body],
        )
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[new_body],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.added_paths == {"Body/Pocket"}
        assert result.deleted_paths == set()
        assert "Body/Pad" in result.common_paths
        # Should have Body/Pad (modified) and Body/Pocket (added)
        assert len(result.node_diffs) >= 1

    def test_path_collision_different_paths(self):
        """Test that same name at different paths are handled correctly."""
        # Two objects with same name but different paths
        old_node1 = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body1/Pad",
        )
        old_node2 = TreeNode(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body2/Pad",
        )
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node1, old_node2],
        )

        # Delete Body1/Pad, keep Body2/Pad
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=[old_node2],
        )

        result = compare_snapshots(old_snapshot, new_snapshot)

        assert result.deleted_paths == {"Body1/Pad"}
        assert "Body2/Pad" in result.common_paths


class TestPerformance:
    """Performance tests for tree_diff module."""

    def test_large_snapshot_performance(self):
        """Test performance with 1000+ nodes."""
        # Build a snapshot with 1000 nodes
        root_nodes = []
        for i in range(100):
            # Create 10 children per root
            children = [
                TreeNode(
                    name=f"Child{j}",
                    type_id="Part::Feature",
                    label=f"Child {j}",
                    path=f"Root{i}/Child{j}",
                )
                for j in range(10)
            ]
            root = TreeNode(
                name=f"Root{i}",
                type_id="PartDesign::Body",
                label=f"Root {i}",
                path=f"Root{i}",
                children=children,
            )
            root_nodes.append(root)

        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=root_nodes,
        )

        # New snapshot with slight modifications
        new_root_nodes = list(root_nodes)  # Copy reference
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="Test",
            timestamp=datetime.now(),
            root_nodes=new_root_nodes,
        )

        # This should complete quickly (under 100ms for 1000 nodes)
        import time

        start = time.time()
        result = compare_snapshots(old_snapshot, new_snapshot)
        elapsed = time.time() - start

        # Verify we got results
        assert result is not None
        # Performance target: < 100ms for 1000 nodes
        assert elapsed < 0.1, f"Performance test failed: took {elapsed:.3f}s (> 100ms)"


class TestValuesAreEqual:
    """Tests for values_are_equal function."""

    def test_both_none(self):
        """Test that None vs None returns True."""
        assert values_are_equal(None, None) is True

    def test_old_none_new_value(self):
        """Test that None vs value returns False."""
        new_val = Property.create(PropertyType.STRING, "test")
        assert values_are_equal(None, new_val) is False

    def test_old_value_new_none(self):
        """Test that value vs None returns False."""
        old_val = Property.create(PropertyType.STRING, "test")
        assert values_are_equal(old_val, None) is False

    def test_identical_bool_values(self):
        """Test BOOL type with same values."""
        old_val = Property.create(PropertyType.BOOL, True)
        new_val = Property.create(PropertyType.BOOL, True)
        assert values_are_equal(old_val, new_val) is True

    def test_different_bool_values(self):
        """Test BOOL type with different values."""
        old_val = Property.create(PropertyType.BOOL, True)
        new_val = Property.create(PropertyType.BOOL, False)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_int_values(self):
        """Test INT type with same values."""
        old_val = Property.create(PropertyType.INT, 42)
        new_val = Property.create(PropertyType.INT, 42)
        assert values_are_equal(old_val, new_val) is True

    def test_different_int_values(self):
        """Test INT type with different values."""
        old_val = Property.create(PropertyType.INT, 42)
        new_val = Property.create(PropertyType.INT, 43)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_float_values(self):
        """Test FLOAT type with same values."""
        old_val = Property.create(PropertyType.FLOAT, 3.14)
        new_val = Property.create(PropertyType.FLOAT, 3.14)
        assert values_are_equal(old_val, new_val) is True

    def test_different_float_values(self):
        """Test FLOAT type with different values."""
        old_val = Property.create(PropertyType.FLOAT, 3.14)
        new_val = Property.create(PropertyType.FLOAT, 2.71)
        assert values_are_equal(old_val, new_val) is False

    def test_float_within_tolerance(self):
        """Test FLOAT type with values within tolerance (1e-9)."""
        old_val = Property.create(PropertyType.FLOAT, 1.0)
        new_val = Property.create(PropertyType.FLOAT, 1.0 + 1e-10)
        assert values_are_equal(old_val, new_val) is True

    def test_float_exceeds_tolerance(self):
        """Test FLOAT type with values exceeding tolerance (1e-9)."""
        old_val = Property.create(PropertyType.FLOAT, 1.0)
        new_val = Property.create(PropertyType.FLOAT, 1.0 + 1e-8)
        assert values_are_equal(old_val, new_val) is False

    def test_identical_string_values(self):
        """Test STRING type with same values."""
        old_val = Property.create(PropertyType.STRING, "hello")
        new_val = Property.create(PropertyType.STRING, "hello")
        assert values_are_equal(old_val, new_val) is True

    def test_different_string_values(self):
        """Test STRING type with different values."""
        old_val = Property.create(PropertyType.STRING, "hello")
        new_val = Property.create(PropertyType.STRING, "world")
        assert values_are_equal(old_val, new_val) is False

    def test_identical_vector_values(self):
        """Test VECTOR type with same values."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        assert values_are_equal(old_val, new_val) is True

    def test_different_vector_values(self):
        """Test VECTOR type with different values."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = Property.create(PropertyType.VECTOR, (4.0, 5.0, 6.0))
        assert values_are_equal(old_val, new_val) is False

    def test_vector_within_tolerance(self):
        """Test VECTOR type with components within tolerance."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0))
        new_val = Property.create(PropertyType.VECTOR, (1.0 + 1e-10, 2.0, 3.0))
        assert values_are_equal(old_val, new_val) is True

    def test_identical_placement_values(self):
        """Test PLACEMENT type with same values."""
        old_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        new_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        assert values_are_equal(old_val, new_val) is True

    def test_different_placement_values(self):
        """Test PLACEMENT type with different values."""
        old_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        new_val = Property.create(
            PropertyType.PLACEMENT,
            {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
        )
        assert values_are_equal(old_val, new_val) is False

    def test_identical_expression_values(self):
        """Test STRING type with same values and identical expressions."""
        old_val = Property.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        new_val = Property.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        assert values_are_equal(old_val, new_val) is True

    def test_different_expression_values(self):
        """Test STRING type with different values and different expressions."""
        old_val = Property.create(PropertyType.STRING, "Body.Length", expression="Body.Length")
        new_val = Property.create(PropertyType.STRING, "Cube.Size", expression="Cube.Size")
        assert values_are_equal(old_val, new_val) is False

    def test_same_value_different_expression(self):
        """Test that same value with different expression returns False."""
        old_val = Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length")
        new_val = Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size")
        assert values_are_equal(old_val, new_val) is False


class TestPropertyDiffState:
    """Tests for PropertyDiff state calculation."""

    def test_state_added(self):
        """Test ADDED state when old_value is None."""
        prop_diff = PropertyDiff(
            property_name="NewProperty",
            old_value=None,
            new_value=Property.create(PropertyType.STRING, "value"),
        )
        assert prop_diff.state == DiffState.ADDED

    def test_state_deleted(self):
        """Test DELETED state when new_value is None."""
        prop_diff = PropertyDiff(
            property_name="OldProperty",
            old_value=Property.create(PropertyType.STRING, "value"),
            new_value=None,
        )
        assert prop_diff.state == DiffState.DELETED

    def test_state_modified(self):
        """Test MODIFIED state when values differ."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 20.0),
        )
        assert prop_diff.state == DiffState.MODIFIED

    def test_state_unchanged(self):
        """Test UNCHANGED state when values are equal."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 10.0),
        )
        assert prop_diff.state == DiffState.UNCHANGED

    def test_state_modified_same_value_different_expression(self):
        """Test MODIFIED state when values are same but expressions differ."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
            new_value=Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        )
        assert prop_diff.state == DiffState.MODIFIED


class TestCompareProperties:
    """Tests for compare_properties function."""

    def test_empty_dictionaries(self):
        """Test comparing empty property dictionaries."""
        result = compare_properties({}, {})
        assert result == []

    def test_only_additions(self):
        """Test when all properties are new (added)."""
        old_props = {}
        new_props = {
            "NewProp1": Property.create(PropertyType.STRING, "value1"),
            "NewProp2": Property.create(PropertyType.INT, 42),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.ADDED

    def test_only_deletions(self):
        """Test when all properties are removed (deleted)."""
        old_props = {
            "OldProp1": Property.create(PropertyType.STRING, "value1"),
            "OldProp2": Property.create(PropertyType.INT, 42),
        }
        new_props = {}
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.DELETED

    def test_only_modifications(self):
        """Test when all properties are modified."""
        old_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "old"),
        }
        new_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 20.0),
            "Prop2": Property.create(PropertyType.STRING, "new"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.MODIFIED

    def test_only_unchanged_filtered_out(self):
        """Test that unchanged properties are filtered out."""
        old_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "same"),
        }
        new_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "same"),
        }
        result = compare_properties(old_props, new_props)
        assert result == []

    def test_mixed_changes(self):
        """Test combination of added, deleted, and modified properties."""
        old_props = {
            "DeletedProp": Property.create(PropertyType.STRING, "gone"),
            "ModifiedProp": Property.create(PropertyType.FLOAT, 10.0),
            "UnchangedProp": Property.create(PropertyType.INT, 5),
        }
        new_props = {
            "AddedProp": Property.create(PropertyType.STRING, "new"),
            "ModifiedProp": Property.create(PropertyType.FLOAT, 20.0),
            "UnchangedProp": Property.create(PropertyType.INT, 5),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 3

        states = {prop_diff.property_name: prop_diff.state for prop_diff in result}
        assert states["DeletedProp"] == DiffState.DELETED
        assert states["AddedProp"] == DiffState.ADDED
        assert states["ModifiedProp"] == DiffState.MODIFIED

    def test_excludes_time_stamp(self):
        """Test that TimeStamp property is filtered out."""
        old_props = {
            "TimeStamp": Property.create(PropertyType.STRING, "2024-01-01T00:00:00"),
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "TimeStamp": Property.create(PropertyType.STRING, "2024-01-01T00:00:01"),
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        result = compare_properties(old_props, new_props)
        # Only Length should appear (and it's unchanged, so filtered)
        assert len(result) == 0
        assert not any(p.property_name == "TimeStamp" for p in result)

    def test_excludes_label2(self):
        """Test that Label2 property is filtered out."""
        old_props = {
            "Label2": Property.create(PropertyType.STRING, "AutoLabel"),
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Label2": Property.create(PropertyType.STRING, "NewLabel"),
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert not any(p.property_name == "Label2" for p in result)

    def test_all_property_types(self):
        """Test comparison of all property types in a single call."""
        old_props = {
            "BoolProp": Property.create(PropertyType.BOOL, True),
            "IntProp": Property.create(PropertyType.INT, 42),
            "FloatProp": Property.create(PropertyType.FLOAT, 3.14),
            "StringProp": Property.create(PropertyType.STRING, "hello"),
            "VectorProp": Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0)),
            "PlacementProp": Property.create(
                PropertyType.PLACEMENT, {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}
            ),
        }
        new_props = {
            "BoolProp": Property.create(PropertyType.BOOL, False),  # Changed
            "IntProp": Property.create(PropertyType.INT, 42),  # Same
            "FloatProp": Property.create(PropertyType.FLOAT, 2.71),  # Changed
            "StringProp": Property.create(PropertyType.STRING, "world"),  # Changed
            "VectorProp": Property.create(PropertyType.VECTOR, (4.0, 5.0, 6.0)),  # Changed
            "PlacementProp": Property.create(
                PropertyType.PLACEMENT, {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}
            ),  # Changed
        }
        result = compare_properties(old_props, new_props)

        assert len(result) == 5  # All except IntProp which is unchanged

        prop_names = {p.property_name for p in result}
        assert prop_names == {"BoolProp", "FloatProp", "StringProp", "VectorProp", "PlacementProp"}

        # Verify all are MODIFIED
        for prop_diff in result:
            assert prop_diff.state == DiffState.MODIFIED

    def test_float_tolerance_edge_cases(self):
        """Test float tolerance with various edge cases."""
        # Very small difference within tolerance
        old_props = {
            "FloatProp": Property.create(PropertyType.FLOAT, 1.0),
        }
        new_props = {
            "FloatProp": Property.create(PropertyType.FLOAT, 1.0 + 1e-10),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 0  # Within tolerance, so unchanged

        # Difference exceeding tolerance
        new_props_exceed = {
            "FloatProp": Property.create(PropertyType.FLOAT, 1.0 + 1e-8),
        }
        result_exceed = compare_properties(old_props, new_props_exceed)
        assert len(result_exceed) == 1
        assert result_exceed[0].state == DiffState.MODIFIED

    def test_property_diff_string_representation(self):
        """Test string representation of PropertyDiff objects."""
        # ADDED
        added = PropertyDiff(
            property_name="NewProp",
            old_value=None,
            new_value=Property.create(PropertyType.STRING, "value"),
        )
        assert "+value" in str(added)

        # DELETED
        deleted = PropertyDiff(
            property_name="OldProp",
            old_value=Property.create(PropertyType.STRING, "value"),
            new_value=None,
        )
        assert "-value" in str(deleted)

        # MODIFIED
        modified = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 20.0),
        )
        assert "10.0" in str(modified)
        assert "20.0" in str(modified)
        assert "->" in str(modified)

    def test_same_value_different_expression_is_modified(self):
        """Test that same value with different expression returns MODIFIED."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].state == DiffState.MODIFIED
