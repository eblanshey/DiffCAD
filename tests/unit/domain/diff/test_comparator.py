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


def build_hierarchical_diffs(sorted_paths, added_paths, deleted_paths, old_index, new_index):
    """Wrapper for testing with default excluded_properties."""
    return _tree_comparator._build_hierarchical_diffs(
        sorted_paths, added_paths, deleted_paths, old_index, new_index, EXCLUDED_PROPERTIES
    )


def compare_nodes_by_path(path, old_index, new_index):
    """Wrapper with default excluded_properties."""
    return _tree_comparator._compare_nodes_by_path(path, old_index, new_index, EXCLUDED_PROPERTIES)


def create_added_node_diff(path, node):
    """Wrapper with default excluded_properties."""
    return _tree_comparator._create_added_node_diff(path, node, EXCLUDED_PROPERTIES)


def create_deleted_node_diff(path, node):
    """Wrapper with default excluded_properties."""
    return _tree_comparator._create_deleted_node_diff(path, node, EXCLUDED_PROPERTIES)


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
        root = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        snapshot = Snapshot(snapshot_id="", document_name="Test", timestamp=datetime.now(), nodes=[root])

        index = build_path_index(snapshot.nodes)

        assert len(index) == 1
        assert "Body" in index
        assert index["Body"] is root

    def test_nested_children(self):
        """Test building index with nested children."""
        grandchild = TreeNode(
            id=3,
            name="ShapeSource",
            type_id="Part::Feature",
            label="ShapeSource",
            path="Body/Pad/ShapeSource",
            after="Pad",
        )
        child = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        root = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )

        # Build index from flat list of nodes
        index = build_path_index([root, child, grandchild])

        assert len(index) == 3
        assert "Body" in index
        assert "Body/Pad" in index
        assert "Body/Pad/ShapeSource" in index

    def test_multiple_roots(self):
        """Test building index with multiple root nodes."""
        root1 = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None)
        root2 = TreeNode(id=2, name="Cube", type_id="Part::Box", label="Cube", path="Cube", after=None)

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
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )

        old_index = {"Body": old_node}
        new_index = {"Body": new_node}

        result = compare_nodes_by_path("Body", old_index, new_index)

        assert result is not None
        assert result.state == DiffState.UNCHANGED
        assert result.path == "Body"

    def test_modified_property(self):
        """Test detecting a modified property."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=old_props,
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
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
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=old_props,
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
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
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=old_props,
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
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
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=old_props,
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=new_props,
        )

        old_index = {"Body/Pad": old_node}
        new_index = {"Body/Pad": new_node}

        result = compare_nodes_by_path("Body/Pad", old_index, new_index)

        # Should return UNCHANGED because only excluded property (TimeStamp) differs
        assert result is not None
        assert result.state == DiffState.UNCHANGED


class TestCreateAddedNodeDiff:
    """Tests for create_added_node_diff function."""

    def test_creates_correct_state(self):
        """Test that added node diff has ADDED state."""
        node = TreeNode(
            id=1,
            name="NewObject",
            type_id="Part::Box",
            label="New Object",
            path="NewObject",
            after=None,
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
            id=1,
            name="OldObject",
            type_id="Part::Box",
            label="Old Object",
            path="OldObject",
            after=None,
        )

        result = create_deleted_node_diff("OldObject", node)

        assert result.path == "OldObject"
        assert result.type_id == "Part::Box"
        assert result.state == DiffState.DELETED


class TestBuildHierarchicalDiffs:
    """Tests for _build_hierarchical_diffs method (single-pass hierarchy construction)."""

    def test_simple_case_one_changed_child_missing_parent_becomes_placeholder(self):
        """Test simple case: one changed child, missing parent becomes placeholder.

        This is the core scenario for single-pass hierarchy construction.
        When a child has changes but its parent doesn't, the parent should be
        created as a placeholder during iteration.
        """

        # Setup: Body/Pocket has changes, Body does not
        sorted_paths = ["Body", "Body/Pocket"]
        added_paths = {"Body/Pocket"}
        deleted_paths = set()

        old_index: dict[str, TreeNode] = {
            "Body": TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None)
        }
        new_index = {
            "Body": TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            "Body/Pocket": TreeNode(
                id=2, name="Pocket", type_id="PartDesign::Pocket", label="Pocket", path="Body/Pocket", after="Body"
            ),
        }

        diff_by_path, has_parent = build_hierarchical_diffs(
            sorted_paths, added_paths, deleted_paths, old_index, new_index
        )

        # Verify both Body and Body/Pocket exist
        assert "Body" in diff_by_path
        assert "Body/Pocket" in diff_by_path

        # Body should be a placeholder (UNCHANGED)
        assert diff_by_path["Body"].state == DiffState.UNCHANGED
        assert diff_by_path["Body"].type_id == "PartDesign::Body"

        # Body/Pocket should be ADDED
        assert diff_by_path["Body/Pocket"].state == DiffState.ADDED

        # Body should have Body/Pocket as child
        assert len(diff_by_path["Body"].children) == 1
        assert diff_by_path["Body"].children[0].path == "Body/Pocket"

        # Body/Pocket should be marked as having a parent
        assert "Body/Pocket" in has_parent

    def test_deep_nesting_multiple_missing_ancestors_all_created(self):
        """Test deep nesting: multiple missing ancestors all created.

        When deeply nested nodes have changes, all intermediate ancestors
        should be created as placeholders.
        """

        # Only Body/Pad/Sketch has changes - Body and Pad are missing
        sorted_paths = ["Body", "Body/Pad", "Body/Pad/Sketch"]
        added_paths = {"Body/Pad/Sketch"}
        deleted_paths = set()

        sketch = TreeNode(
            id=3, name="Sketch", type_id="PartDesign::Sketch", label="Sketch", path="Body/Pad/Sketch", after="Pad"
        )
        pad = TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", after="Body")
        body = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None)

        old_index: dict[str, TreeNode] = {}
        new_index = {"Body": body, "Body/Pad": pad, "Body/Pad/Sketch": sketch}

        diff_by_path, has_parent = build_hierarchical_diffs(
            sorted_paths, added_paths, deleted_paths, old_index, new_index
        )

        # All three paths should exist
        assert "Body" in diff_by_path
        assert "Body/Pad" in diff_by_path
        assert "Body/Pad/Sketch" in diff_by_path

        # Body and Body/Pad should be placeholders (UNCHANGED)
        assert diff_by_path["Body"].state == DiffState.UNCHANGED
        assert diff_by_path["Body/Pad"].state == DiffState.UNCHANGED

        # Body/Pad/Sketch should be ADDED
        assert diff_by_path["Body/Pad/Sketch"].state == DiffState.ADDED

        # Verify hierarchy: Body -> Body/Pad -> Body/Pad/Sketch
        assert len(diff_by_path["Body"].children) == 1
        assert diff_by_path["Body"].children[0].path == "Body/Pad"

        assert len(diff_by_path["Body/Pad"].children) == 1
        assert diff_by_path["Body/Pad"].children[0].path == "Body/Pad/Sketch"

        # Both Body/Pad and Body/Pad/Sketch should have parents
        assert "Body/Pad" in has_parent
        assert "Body/Pad/Sketch" in has_parent

    def test_mixed_states_added_deleted_modified_properly_linked(self):
        """Test mixed states: added, deleted, modified nodes properly linked.

        Verifies that the single-pass approach correctly handles all three
        state types and maintains proper parent-child relationships.
        """

        # Mixed scenario:
        # - Body/Pocket: ADDED
        # - Body/Pad: MODIFIED (property changed)
        # - Body/DeletedNode: DELETED
        sorted_paths = ["Body", "Body/Pad", "Body/DeletedNode", "Body/Pocket"]
        added_paths = {"Body/Pocket"}
        deleted_paths = {"Body/DeletedNode"}

        old_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.create(PropertyType.FLOAT, 10.0)},
        )
        new_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
        )

        old_index = {
            "Body": TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            "Body/Pad": old_pad,
            "Body/DeletedNode": TreeNode(
                id=3,
                name="DeletedNode",
                type_id="Part::Feature",
                label="Deleted",
                path="Body/DeletedNode",
                after="Body",
            ),
        }
        new_index = {
            "Body": TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            "Body/Pad": new_pad,
            "Body/Pocket": TreeNode(
                id=4, name="Pocket", type_id="PartDesign::Pocket", label="Pocket", path="Body/Pocket", after="Pad"
            ),
        }

        diff_by_path, has_parent = build_hierarchical_diffs(
            sorted_paths, added_paths, deleted_paths, old_index, new_index
        )

        # Verify all paths exist
        assert len(diff_by_path) == 4

        # Body should be placeholder (UNCHANGED)
        assert diff_by_path["Body"].state == DiffState.UNCHANGED

        # Body/Pad should be MODIFIED
        assert diff_by_path["Body/Pad"].state == DiffState.MODIFIED

        # Body/DeletedNode should be DELETED
        assert diff_by_path["Body/DeletedNode"].state == DiffState.DELETED

        # Body/Pocket should be ADDED
        assert diff_by_path["Body/Pocket"].state == DiffState.ADDED

        # All children should be linked to Body
        assert len(diff_by_path["Body"].children) == 3

    def test_path_format_preservation_leading_slashes_maintained(self):
        """Test path format preservation: leading slashes maintained throughout.

        Verifies that paths with leading slashes maintain their format
        when creating placeholders and linking children.
        """

        # Use paths without leading slashes
        sorted_paths = ["Body", "Body/Pocket"]
        added_paths = {"Body/Pocket"}
        deleted_paths = set()

        old_index: dict[str, TreeNode] = {
            "Body": TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None)
        }
        new_index = {
            "Body": TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            "Body/Pocket": TreeNode(
                id=2, name="Pocket", type_id="PartDesign::Pocket", label="Pocket", path="Body/Pocket", after="Body"
            ),
        }

        diff_by_path, has_parent = build_hierarchical_diffs(
            sorted_paths, added_paths, deleted_paths, old_index, new_index
        )

        # Paths should be without leading slashes
        assert "Body" in diff_by_path
        assert "Body/Pocket" in diff_by_path

        # Parent path should also be without leading slash
        assert diff_by_path["Body"].path == "Body"
        assert diff_by_path["Body/Pocket"].path == "Body/Pocket"

    def test_empty_sorted_paths_returns_empty(self):
        """Test that empty sorted_paths returns empty dicts."""
        diff_by_path, has_parent = build_hierarchical_diffs([], set(), set(), {}, {})

        assert diff_by_path == {}
        assert has_parent == set()

    def test_single_root_node_no_parent_needed(self):
        """Test single root node - no parent needed since it's a root."""

        sorted_paths = ["Body"]
        added_paths = {"Body"}
        deleted_paths = set()

        old_index: dict[str, TreeNode] = {}
        new_index = {
            "Body": TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None)
        }

        diff_by_path, has_parent = build_hierarchical_diffs(
            sorted_paths, added_paths, deleted_paths, old_index, new_index
        )

        # Body should exist and be ADDED
        assert "Body" in diff_by_path
        assert diff_by_path["Body"].state == DiffState.ADDED

        # Body should not have a parent (it's a root)
        assert "Body" not in has_parent


class TestGetParentPath:
    """Tests for _get_parent_path method."""

    def test_parent_with_leading_slash(self):
        """Test extracting parent from path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad")
        assert result == "/Body"

    def test_parent_without_leading_slash(self):
        """Test extracting parent from path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad")
        assert result == "Body"

    def test_root_with_leading_slash_returns_empty(self):
        """Test that root node with leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("/Part")
        assert result == ""

    def test_root_without_leading_slash_returns_empty(self):
        """Test that root node without leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("Part")
        assert result == ""

    def test_deep_nesting_with_leading_slash(self):
        """Test extracting parent from deeply nested path with leading slash."""
        result = _tree_comparator._get_parent_path("/A/B/C/D")
        assert result == "/A/B/C"

    def test_deep_nesting_without_leading_slash(self):
        """Test extracting parent from deeply nested path without leading slash."""
        result = _tree_comparator._get_parent_path("A/B/C/D")
        assert result == "A/B/C"

    def test_two_level_path_with_leading_slash(self):
        """Test extracting parent from two-level path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad/Sketch")
        assert result == "/Body/Pad"

    def test_two_level_path_without_leading_slash(self):
        """Test extracting parent from two-level path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad/Sketch")
        assert result == "Body/Pad"


class TestEnsurePlaceholder:
    """Tests for _ensure_placeholder method."""

    def test_creates_placeholder_with_correct_type_id_from_new_index(self):
        """Test that placeholder is created with correct type_id from new_index."""
        diff_by_path: dict[str, NodeDiff] = {}
        has_parent: set[str] = set()

        old_index: dict[str, TreeNode] = {}
        new_index = {
            "Body/Pad": TreeNode(
                id=1,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Body/Pad",
                after="Body",
            )
        }

        _tree_comparator._ensure_placeholder("Body/Pad", old_index, new_index, diff_by_path, has_parent)

        assert "Body/Pad" in diff_by_path
        assert diff_by_path["Body/Pad"].type_id == "PartDesign::Pad"
        assert diff_by_path["Body/Pad"].state == DiffState.UNCHANGED

    def test_creates_placeholder_with_correct_type_id_from_old_index(self):
        """Test that placeholder is created with correct type_id from old_index."""
        diff_by_path: dict[str, NodeDiff] = {}
        has_parent: set[str] = set()

        old_index = {
            "Body/Pad": TreeNode(
                id=1,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Body/Pad",
                after="Body",
            )
        }
        new_index: dict[str, TreeNode] = {}

        _tree_comparator._ensure_placeholder("Body/Pad", old_index, new_index, diff_by_path, has_parent)

        assert "Body/Pad" in diff_by_path
        assert diff_by_path["Body/Pad"].type_id == "PartDesign::Pad"

    def test_links_placeholder_to_parent(self):
        """Test that placeholder is linked to its parent."""
        diff_by_path: dict[str, NodeDiff] = {}
        has_parent: set[str] = set()

        # First create the parent
        parent_node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None)
        old_index = {"Body": parent_node}
        new_index = {"Body": parent_node}

        _tree_comparator._ensure_placeholder("Body", old_index, new_index, diff_by_path, has_parent)

        # Now ensure child placeholder
        child_node = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        old_index["Body/Pad"] = child_node
        new_index["Body/Pad"] = child_node

        _tree_comparator._ensure_placeholder("Body/Pad", old_index, new_index, diff_by_path, has_parent)

        # Verify parent has child in its children list
        assert len(diff_by_path["Body"].children) == 1
        assert diff_by_path["Body"].children[0].path == "Body/Pad"
        assert "Body/Pad" in has_parent

    def test_recursively_creates_ancestor_chain(self):
        """Test that entire ancestor chain is created recursively."""
        diff_by_path: dict[str, NodeDiff] = {}
        has_parent: set[str] = set()

        # Create mock indices for full hierarchy (flat nodes)
        sketch = TreeNode(
            id=3,
            name="Sketch",
            type_id="PartDesign::Sketch",
            label="Sketch",
            path="Body/Pad/Sketch",
            after="Pad",
        )
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )

        old_index: dict[str, TreeNode] = {}
        new_index = {"Body": body, "Body/Pad": pad, "Body/Pad/Sketch": sketch}

        # Ensure the deepest node exists (should recursively create Body and Body/Pad)
        _tree_comparator._ensure_placeholder("Body/Pad/Sketch", old_index, new_index, diff_by_path, has_parent)

        # Verify all ancestors were created
        assert "Body" in diff_by_path
        assert "Body/Pad" in diff_by_path
        assert "Body/Pad/Sketch" in diff_by_path

        # Verify hierarchy is correct
        assert len(diff_by_path["Body"].children) == 1
        assert diff_by_path["Body"].children[0].path == "Body/Pad"
        assert len(diff_by_path["Body/Pad"].children) == 1
        assert diff_by_path["Body/Pad"].children[0].path == "Body/Pad/Sketch"

    def test_does_not_create_duplicate_if_already_exists(self):
        """Test that existing diff is not overwritten."""
        diff_by_path: dict[str, NodeDiff] = {}
        has_parent: set[str] = set()

        # First create a real diff (not placeholder)
        from freecad.diff_wb.domain.diff import PropertyDiff

        existing_diff = NodeDiff(
            path="Body/Pad",
            type_id="PartDesign::Pad",
            property_diffs=[
                PropertyDiff(
                    property_name="Length",
                    old_value=None,
                    new_value=Property.create(PropertyType.FLOAT, 10.0),
                )
            ],
            _force_state=DiffState.ADDED,
        )
        diff_by_path["Body/Pad"] = existing_diff

        old_index: dict[str, TreeNode] = {}
        new_index = {
            "Body/Pad": TreeNode(
                id=1,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Body/Pad",
                after="Body",
            )
        }

        # Try to ensure placeholder for same path
        _tree_comparator._ensure_placeholder("Body/Pad", old_index, new_index, diff_by_path, has_parent)

        # Verify original diff is unchanged
        assert diff_by_path["Body/Pad"] is existing_diff
        assert diff_by_path["Body/Pad"].state == DiffState.ADDED


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

    def test_state_unchanged_same_value_different_expression(self):
        """Test UNCHANGED state when values are same (expression tracked separately)."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
            new_value=Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        )
        assert prop_diff.state == DiffState.UNCHANGED


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

    def test_only_unchanged_included(self):
        """Test that unchanged properties are included in result."""
        old_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "same"),
        }
        new_props = {
            "Prop1": Property.create(PropertyType.FLOAT, 10.0),
            "Prop2": Property.create(PropertyType.STRING, "same"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 2
        for prop_diff in result:
            assert prop_diff.state == DiffState.UNCHANGED

    def test_mixed_changes(self):
        """Test combination of added, deleted, modified and unchanged properties."""
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
        assert len(result) == 4

        states = {prop_diff.property_name: prop_diff.state for prop_diff in result}
        assert states["DeletedProp"] == DiffState.DELETED
        assert states["AddedProp"] == DiffState.ADDED
        assert states["ModifiedProp"] == DiffState.MODIFIED
        assert states["UnchangedProp"] == DiffState.UNCHANGED

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
        # TimeStamp is excluded, Length is unchanged but included
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert result[0].state == DiffState.UNCHANGED

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

        assert len(result) == 6  # All properties including unchanged IntProp

        prop_names = {p.property_name for p in result}
        assert prop_names == {"BoolProp", "IntProp", "FloatProp", "StringProp", "VectorProp", "PlacementProp"}

        # Verify modified are MODIFIED
        modified_props = [p for p in result if p.property_name != "IntProp"]
        for prop_diff in modified_props:
            assert prop_diff.state == DiffState.MODIFIED
        # Verify IntProp is unchanged
        assert next(p for p in result if p.property_name == "IntProp").state == DiffState.UNCHANGED

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
        assert len(result) == 1  # Within tolerance, so unchanged but included
        assert result[0].state == DiffState.UNCHANGED

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

    def test_same_value_different_expression_is_unchanged(self):
        """Test that same value with different expression returns UNCHANGED."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0, expression="Body.Length"),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0, expression="Cube.Size"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].state == DiffState.UNCHANGED


class TestPropertyDiffChildrenAutoComputed:
    """Tests verifying PropertyDiff auto-computes children for expandable properties.

    These tests verify that when the comparator creates PropertyDiff objects,
    the children are automatically populated by PropertyDiff's __post_init__ method.
    This is Phase 3 of the refactor-diff-architecture task.
    """

    def test_placement_property_diff_has_position_and_rotation_children(self):
        """Test that PropertyDiff for Placement has Position and Rotation children."""
        # Create two Placement properties that differ in position
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)

        assert len(result) == 1
        prop_diff = result[0]
        assert prop_diff.property_name == "Placement"
        assert prop_diff.state == DiffState.MODIFIED

        # Verify children are auto-computed
        assert len(prop_diff.children) == 2
        child_names = {child.property_name for child in prop_diff.children}
        assert "Position" in child_names
        assert "Rotation" in child_names

    def test_placement_property_diff_position_child_has_correct_state(self):
        """Test that Position child of Placement diff has MODIFIED state when position changes."""
        # Create two Placement properties with different positions
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        # Find Position child
        position_child = next(child for child in prop_diff.children if child.property_name == "Position")
        assert position_child.state == DiffState.MODIFIED

    def test_placement_property_diff_rotation_child_has_correct_state(self):
        """Test that Rotation child of Placement diff has MODIFIED state when rotation changes."""
        # Create two Placement properties with different rotations
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 45.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        # Find Rotation child
        rotation_child = next(child for child in prop_diff.children if child.property_name == "Rotation")
        assert rotation_child.state == DiffState.MODIFIED

    def test_unchanged_placement_has_unchanged_children(self):
        """Test that unchanged Placement has UNCHANGED children."""
        # Create identical Placement properties
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.UNCHANGED

        # Both children should be UNCHANGED
        for child in prop_diff.children:
            assert child.state == DiffState.UNCHANGED

    def test_primitive_property_has_empty_children(self):
        """Test that primitive property (e.g., FLOAT) has empty children list."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.MODIFIED
        # Primitive types have no children
        assert len(prop_diff.children) == 0

    def test_vector_property_has_x_y_z_children(self):
        """Test that VECTOR property has x, y, z children."""
        old_props = {
            "Position": Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0)),
        }
        new_props = {
            "Position": Property.create(PropertyType.VECTOR, (4.0, 5.0, 6.0)),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.MODIFIED
        # Vector has x, y, z children
        assert len(prop_diff.children) == 3
        child_names = {child.property_name for child in prop_diff.children}
        assert child_names == {"x", "y", "z"}

    def test_added_placement_has_children(self):
        """Test that added Placement has Position and Rotation children with ADDED state."""
        old_props: dict[str, Property] = {}
        new_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.ADDED

        # Children should also have ADDED state
        for child in prop_diff.children:
            assert child.state == DiffState.ADDED

    def test_deleted_placement_has_children(self):
        """Test that deleted Placement has Position and Rotation children with DELETED state."""
        old_props = {
            "Placement": Property.create(
                PropertyType.PLACEMENT,
                {"position": (1.0, 2.0, 3.0), "rotation": (0.0, 0.0, 1.0, 90.0)},
            ),
        }
        new_props: dict[str, Property] = {}

        result = compare_properties(old_props, new_props)
        prop_diff = result[0]

        assert prop_diff.state == DiffState.DELETED

        # Children should also have DELETED state
        for child in prop_diff.children:
            assert child.state == DiffState.DELETED


class TestBuildIdIndex:
    """Tests for ID-based indexing (_build_id_index method)."""

    def test_empty_nodes_list(self):
        """Test building ID index from empty nodes list."""
        index = _tree_comparator._build_id_index([])
        assert index == {}

    def test_single_node(self):
        """Test building index with a single node."""
        node = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        index = _tree_comparator._build_id_index([node])
        assert len(index) == 1
        assert 1 in index
        assert index[1] is node

    def test_multiple_nodes(self):
        """Test building index with multiple nodes."""
        node1 = TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        node2 = TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        node3 = TreeNode(id=3, name="Sketch", type_id="PartDesign::Sketch", label="Sketch", path="Body/Sketch")
        index = _tree_comparator._build_id_index([node1, node2, node3])
        assert len(index) == 3
        assert 1 in index
        assert 2 in index
        assert 3 in index


class TestFindAddedIds:
    """Tests for ID-based added node detection."""

    def test_no_added_ids(self):
        """Test when new snapshot has no new IDs."""
        old_index = {1: None, 2: None}  # type: ignore
        new_index = {1: None, 2: None}  # type: ignore

        added = _tree_comparator._find_added_ids(old_index, new_index)

        assert added == set()

    def test_simple_addition(self):
        """Test detecting a simple addition."""
        old_index: dict[int, TreeNode] = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        }
        new_index = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body"),
            2: TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad"),
        }

        added = _tree_comparator._find_added_ids(old_index, new_index)

        assert added == {2}

    def test_multiple_additions(self):
        """Test detecting multiple additions."""
        old_index: dict[int, TreeNode] = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        }
        new_index = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body"),
            2: TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad"),
            3: TreeNode(id=3, name="Pocket", type_id="PartDesign::Pocket", label="Pocket", path="Body/Pocket"),
        }

        added = _tree_comparator._find_added_ids(old_index, new_index)

        assert added == {2, 3}


class TestFindDeletedIds:
    """Tests for ID-based deleted node detection."""

    def test_no_deleted_ids(self):
        """Test when old snapshot has no deleted IDs."""
        old_index = {1: None, 2: None}  # type: ignore
        new_index = {1: None, 2: None}  # type: ignore

        deleted = _tree_comparator._find_deleted_ids(old_index, new_index)

        assert deleted == set()

    def test_simple_deletion(self):
        """Test detecting a simple deletion."""
        old_index = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body"),
            2: TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad"),
        }
        new_index: dict[int, TreeNode] = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        }

        deleted = _tree_comparator._find_deleted_ids(old_index, new_index)

        assert deleted == {2}

    def test_multiple_deletions(self):
        """Test detecting multiple deletions."""
        old_index = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body"),
            2: TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad"),
            3: TreeNode(id=3, name="Pocket", type_id="PartDesign::Pocket", label="Pocket", path="Body/Pocket"),
        }
        new_index: dict[int, TreeNode] = {
            1: TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body")
        }

        deleted = _tree_comparator._find_deleted_ids(old_index, new_index)

        assert deleted == {2, 3}


class TestFindCommonIds:
    """Tests for ID-based common node detection."""

    def test_all_common(self):
        """Test when all IDs are common."""
        old_index = {1: None, 2: None}  # type: ignore
        new_index = {1: None, 2: None}  # type: ignore

        common = _tree_comparator._find_common_ids(old_index, new_index)

        assert common == {1, 2}

    def test_no_common(self):
        """Test when no IDs are common."""
        old_index = {1: None}  # type: ignore
        new_index = {2: None}  # type: ignore

        common = _tree_comparator._find_common_ids(old_index, new_index)

        assert common == set()

    def test_partial_common(self):
        """Test when some IDs are common."""
        old_index = {1: None, 2: None}  # type: ignore
        new_index = {1: None, 3: None}  # type: ignore

        common = _tree_comparator._find_common_ids(old_index, new_index)

        assert common == {1}


class TestCompareNodesById:
    """Tests for ID-based node comparison."""

    def test_identical_nodes_returns_unchanged(self):
        """Test comparing identical nodes returns UNCHANGED."""
        props = {
            "Label": Property.create(PropertyType.STRING, "Body"),
        }
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties=props,
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        assert result is not None
        assert result.state == DiffState.UNCHANGED

    def test_modified_property_returns_modified(self):
        """Test detecting a modified property returns MODIFIED."""
        old_props = {
            "Length": Property.create(PropertyType.FLOAT, 10.0),
        }
        new_props = {
            "Length": Property.create(PropertyType.FLOAT, 20.0),
        }
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=old_props,
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties=new_props,
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        assert result is not None
        assert result.state == DiffState.MODIFIED

    def test_includes_old_and_new_path_in_result(self):
        """Test that NodeDiff includes old_path and new_path."""
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        # NodeDiff should include old_path and new_path for move detection
        assert result.old_path == "Body/Pad"
        assert result.new_path == "Body/Pad"

    def test_includes_old_and_new_after_in_result(self):
        """Test that NodeDiff includes old_after and new_after."""
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )

        old_index = {1: old_node}
        new_index = {1: new_node}

        result = _tree_comparator._compare_nodes_by_id(1, old_index, new_index, EXCLUDED_PROPERTIES)

        # NodeDiff should include old_after and new_after for reorder detection
        assert result.old_after == "Body"
        assert result.new_after == "Body"


class TestIdBasedCompareSnapshots:
    """Tests for ID-based snapshot comparison (end-to-end)."""

    def test_compare_two_flat_node_lists_by_id(self):
        """Test comparing two flat node lists by ID."""
        # Old snapshot has ID 1 only
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot has both ID 1 and ID 2
        new_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node1, new_node2],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        # ID 2 should be added
        assert 2 in result.added_ids
        # ID 1 should be common
        assert 1 in result.common_ids
        # No deleted IDs
        assert result.deleted_ids == set()

    def test_detect_added_nodes(self):
        """Test detecting ADDED nodes (in new, not in old)."""
        # Old snapshot: only ID 1
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot: ID 1 and ID 2 (added)
        new_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node1, new_node2],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        assert result.added_ids == {2}
        assert result.common_ids == {1}
        assert result.deleted_ids == set()

    def test_detect_deleted_nodes(self):
        """Test detecting DELETED nodes (in old, not in new)."""
        # Old snapshot: ID 1 and ID 2
        old_node1 = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        old_node2 = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node1, old_node2],
        )

        # New snapshot: only ID 1
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        assert result.added_ids == set()
        assert result.common_ids == {1}
        assert result.deleted_ids == {2}

    def test_detect_modified_nodes(self):
        """Test detecting MODIFIED nodes (in both, properties differ)."""
        # Old snapshot: ID 1 with Length=10
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.create(PropertyType.FLOAT, 10.0)},
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot: ID 1 with Length=20 (modified)
        new_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        assert result.added_ids == set()
        assert result.common_ids == {1}
        assert result.deleted_ids == set()

        # Find the node diff for ID 1 - it may be nested under parent placeholder
        # Look through the hierarchy for Body/Pad
        def find_node_diff(node_diffs, path):
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        pad_diff = find_node_diff(result.node_diffs, "Body/Pad")
        assert pad_diff is not None
        assert pad_diff.state == DiffState.MODIFIED

    def test_id_based_comparison_produces_correct_sets(self):
        """Test ID-based comparison produces correct added/deleted/common sets."""
        # Old: IDs 1, 2, 3
        old_nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", after="Body"),
            TreeNode(
                id=3, name="Sketch", type_id="PartDesign::Sketch", label="Sketch", path="Body/Sketch", after="Pad"
            ),
        ]
        # New: IDs 1, 2, 4 (2 unchanged, 1 modified, 3 deleted, 4 added)
        new_nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            TreeNode(  # ID 2 modified (different properties)
                id=2,
                name="Pad",
                type_id="PartDesign::Pad",
                label="Pad",
                path="Body/Pad",
                after="Body",
                properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
            ),
            TreeNode(id=4, name="Box", type_id="Part::Box", label="Box", path="Box", after=None),  # Added
        ]

        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=old_nodes)
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=new_nodes)

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        # Correct sets: 3 deleted (old only), 1 added (new only), 1 common (both)
        assert result.added_ids == {4}
        assert result.deleted_ids == {3}
        assert result.common_ids == {1, 2}

    def test_node_diff_includes_path_and_after_for_move_detection(self):
        """Test NodeDiff includes old_path, new_path, old_after, new_after for future move/reorder detection."""
        # Old: ID 1 at path "Body/Original"
        old_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Body/Original",
            after="Body",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New: Same ID but moved to different path "Body/Moved"
        new_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Body/Moved",
            after="Body",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        # The NodeDiff should include old_path and new_path for move detection
        # Since the node is unchanged in properties but path changed
        # The node may be nested under a parent placeholder
        def find_node_diff(node_diffs, path):
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        feature_diff = find_node_diff(result.node_diffs, "Body/Moved")
        assert feature_diff is not None
        assert feature_diff.old_path == "Body/Original"
        assert feature_diff.new_path == "Body/Moved"

    def test_node_diff_for_added_node_has_null_old_path(self):
        """Test that added node has None for old_path."""
        # New only: ID 2
        new_node = TreeNode(
            id=2,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Old is empty
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        # Added node should have old_path = None
        box_diff = result.node_diffs[0]
        assert box_diff.old_path is None
        assert box_diff.new_path == "Box"

    def test_node_diff_for_deleted_node_has_null_new_path(self):
        """Test that deleted node has None for new_path."""
        # Old only: ID 1
        old_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Box",
            label="Box",
            path="Box",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New is empty
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        # Deleted node should have new_path = None
        box_diff = result.node_diffs[0]
        assert box_diff.old_path == "Box"
        assert box_diff.new_path is None

    def test_hierarchical_output_preserved(self):
        """Test that hierarchical NodeDiff.children is preserved for UI."""
        # Create a parent-child relationship in flat nodes
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[body, pad])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[body, pad])

        result = _tree_comparator.compare_snapshots(old_snapshot.nodes, new_snapshot.nodes, [])

        # Should have hierarchical structure: Body -> Pad
        assert len(result.node_diffs) == 1  # Root: Body
        body_diff = result.node_diffs[0]
        assert len(body_diff.children) == 1  # Child: Pad
        assert body_diff.children[0].path == "Body/Pad"
