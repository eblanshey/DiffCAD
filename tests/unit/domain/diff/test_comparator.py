# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for the tree-comparison algorithm with path-based indexing.
"""Unit tests for tree_diff module.

These tests verify the core diff computation logic without any FreeCAD dependencies.
"""

from datetime import datetime

import pytest

from freecad.diff_wb.config import EXCLUDED_PROPERTIES
from freecad.diff_wb.domain.diff.comparator import PropertyComparator, TreeComparator
from freecad.diff_wb.domain.diff.models import DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.tree.node import TreeNode
from freecad.diff_wb.domain.tree.property import Property


# Test fixtures - create comparator instances
_tree_comparator = TreeComparator()
_property_comparator = PropertyComparator()


def compare_properties(
    old_props: dict[str, Property],
    new_props: dict[str, Property],
) -> list[PropertyDiff]:
    """Wrapper with default excluded_properties."""
    return _property_comparator.compare_properties(old_props, new_props, EXCLUDED_PROPERTIES)


class TestGetParentPath:
    """Tests for _get_parent_path method."""

    def test_parent_with_leading_slash(self) -> None:
        """Test extracting parent from path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad")
        assert result == "/Body"

    def test_parent_without_leading_slash(self) -> None:
        """Test extracting parent from path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad")
        assert result == "Body"

    def test_root_with_leading_slash_returns_empty(self) -> None:
        """Test that root node with leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("/Part")
        assert result == ""

    def test_root_without_leading_slash_returns_empty(self) -> None:
        """Test that root node without leading slash returns empty string."""
        result = _tree_comparator._get_parent_path("Part")
        assert result == ""

    def test_deep_nesting_with_leading_slash(self) -> None:
        """Test extracting parent from deeply nested path with leading slash."""
        result = _tree_comparator._get_parent_path("/A/B/C/D")
        assert result == "/A/B/C"

    def test_deep_nesting_without_leading_slash(self) -> None:
        """Test extracting parent from deeply nested path without leading slash."""
        result = _tree_comparator._get_parent_path("A/B/C/D")
        assert result == "A/B/C"

    def test_two_level_path_with_leading_slash(self) -> None:
        """Test extracting parent from two-level path with leading slash."""
        result = _tree_comparator._get_parent_path("/Body/Pad/Sketch")
        assert result == "/Body/Pad"

    def test_two_level_path_without_leading_slash(self) -> None:
        """Test extracting parent from two-level path without leading slash."""
        result = _tree_comparator._get_parent_path("Body/Pad/Sketch")
        assert result == "Body/Pad"


class TestPropertyDiffState:
    """Tests for PropertyDiff state calculation."""

    @pytest.mark.parametrize(
        ("old_val, new_val, expected_state"),
        [
            (None, "value", DiffState.ADDED),
            ("value", None, DiffState.DELETED),
            (10.0, 20.0, DiffState.MODIFIED),
            (10.0, 10.0, DiffState.UNCHANGED),
        ],
    )
    def test_state_variants(
        self,
        old_val,
        new_val,
        expected_state,  # type: ignore[no-untyped-def]
    ) -> None:
        """Parametrized test for ADDED/DELETED/MODIFIED/UNCHANGED state variants."""
        prop_diff = PropertyDiff(
            property_name="TestProp",
            old_value=Property.from_freecad(old_val, {}, "Base") if old_val is not None else None,
            new_value=Property.from_freecad(new_val, {}, "Base") if new_val is not None else None,
        )
        assert prop_diff.state == expected_state

    def test_state_modified_when_only_expression_changes(self) -> None:
        """Test MODIFIED state when value is same but expression differs."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {".": "Body.Length"}, "Base"),
            new_value=Property.from_freecad(10.0, {".": "Cube.Size"}, "Base"),
        )
        assert prop_diff.state == DiffState.MODIFIED
        # Expression change is tracked via path_diffs
        assert any(pd.expression_state != DiffState.UNCHANGED for pd in prop_diff.path_diffs)


class TestComparePropertiesPathDiffs:
    """Tests for compare_properties path_diffs behavior."""

    def test_unchanged_paths_emitted_in_path_diffs(self) -> None:
        """Verify path_diffs contains all paths including unchanged ones."""
        old_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")

        result = compare_properties({"Vector": old_vector}, {"Vector": new_vector})
        assert len(result) == 1

        path_names = {pd.path for pd in result[0].path_diffs}
        # All paths should be present (unchanged)
        assert "[0]" in path_names
        assert "[1]" in path_names
        assert "[2]" in path_names

        # All path diffs should be UNCHANGED
        for pd in result[0].path_diffs:
            assert pd.value_state == DiffState.UNCHANGED

    def test_property_exclusion_works(self) -> None:
        """Verify excluded properties are not in result."""
        old_props = {
            "Length": Property.from_freecad(10.0, {}, "Base"),
            "Width": Property.from_freecad(20.0, {}, "Base"),
        }
        new_props = {
            "Length": Property.from_freecad(10.0, {}, "Base"),
            "Width": Property.from_freecad(20.0, {}, "Base"),
        }
        # Exclude Width explicitly
        result = _property_comparator.compare_properties(old_props, new_props, ["Width"])
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert not any(p.property_name == "Width" for p in result)

    def test_deterministic_ordering(self) -> None:
        """Verify property names are sorted alphabetically."""
        old_props = {
            "Zebra": Property.from_freecad(1.0, {}, "Base"),
            "Alpha": Property.from_freecad(2.0, {}, "Base"),
            "Middle": Property.from_freecad(3.0, {}, "Base"),
        }
        new_props = {
            "Zebra": Property.from_freecad(1.0, {}, "Base"),
            "Alpha": Property.from_freecad(2.0, {}, "Base"),
            "Middle": Property.from_freecad(3.0, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        prop_names = [p.property_name for p in result]
        assert prop_names == sorted(prop_names)

    def test_path_sorting_with_indices(self) -> None:
        """Verify path keys with indices sort correctly ([2] before [10])."""
        # Create a property where the flattened paths include indexed entries
        # ListData with 12 items produces [0] through [11]
        values = list(range(12))
        old_list = Property.from_freecad(values, {}, "Base")
        new_list = Property.from_freecad(values, {}, "Base")

        result = compare_properties({"List": old_list}, {"List": new_list})
        assert len(result) == 1

        path_names = [pd.path for pd in result[0].path_diffs]
        # Find indices of [2] and [10]
        idx_2 = path_names.index("[2]")
        idx_10 = path_names.index("[10]")
        assert idx_2 < idx_10, f"[2] should come before [10], but got indices {idx_2} and {idx_10}"


class TestCompareProperties:
    """Tests for compare_properties function."""

    def test_empty_dictionaries(self) -> None:
        """Test comparing empty property dictionaries."""
        result = compare_properties({}, {})
        assert result == []

    @pytest.mark.parametrize(
        ("old_props, new_props, expected_state"),
        [
            # All additions
            ({}, {"NewProp1": Property.from_freecad("value1", {}, "Base")}, DiffState.ADDED),
            # All deletions
            ({"OldProp1": Property.from_freecad("value1", {}, "Base")}, {}, DiffState.DELETED),
            # All modifications
            (
                {"Prop1": Property.from_freecad(10.0, {}, "Base")},
                {"Prop1": Property.from_freecad(20.0, {}, "Base")},
                DiffState.MODIFIED,
            ),
            # All unchanged
            (
                {"Prop1": Property.from_freecad(10.0, {}, "Base")},
                {"Prop1": Property.from_freecad(10.0, {}, "Base")},
                DiffState.UNCHANGED,
            ),
        ],
    )
    def test_single_property_state_variants(
        self,
        old_props,
        new_props,
        expected_state,  # type: ignore[no-untyped-def]
    ) -> None:
        """Parametrized test for single-property comparison state variants."""
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].state == expected_state

    def test_mixed_changes(self) -> None:
        """Test combination of added, deleted, modified and unchanged properties."""
        old_props = {
            "DeletedProp": Property.from_freecad("gone", {}, "Base"),
            "ModifiedProp": Property.from_freecad(10.0, {}, "Base"),
            "UnchangedProp": Property.from_freecad(5, {}, "Base"),
        }
        new_props = {
            "AddedProp": Property.from_freecad("new", {}, "Base"),
            "ModifiedProp": Property.from_freecad(20.0, {}, "Base"),
            "UnchangedProp": Property.from_freecad(5, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 4

        states = {prop_diff.property_name: prop_diff.state for prop_diff in result}
        assert states["DeletedProp"] == DiffState.DELETED
        assert states["AddedProp"] == DiffState.ADDED
        assert states["ModifiedProp"] == DiffState.MODIFIED
        assert states["UnchangedProp"] == DiffState.UNCHANGED

    def test_excludes_time_stamp(self) -> None:
        """Test that TimeStamp property is filtered out."""
        old_props = {
            "TimeStamp": Property.from_freecad("2024-01-01T00:00:00", {}, "Base"),
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        new_props = {
            "TimeStamp": Property.from_freecad("2024-01-01T00:00:01", {}, "Base"),
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        # TimeStamp is excluded, Length is unchanged but included
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert result[0].state == DiffState.UNCHANGED

    def test_excludes_label2(self) -> None:
        """Test that Label2 property is filtered out."""
        old_props = {
            "Label2": Property.from_freecad("AutoLabel", {}, "Base"),
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        new_props = {
            "Label2": Property.from_freecad("NewLabel", {}, "Base"),
            "Length": Property.from_freecad(20.0, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].property_name == "Length"
        assert not any(p.property_name == "Label2" for p in result)

    def test_all_property_types(self) -> None:
        """Test comparison of all property types in a single call."""
        old_props = {
            "BoolProp": Property.from_freecad(True, {}, "Base"),
            "IntProp": Property.from_freecad(42, {}, "Base"),
            "FloatProp": Property.from_freecad(3.14, {}, "Base"),
            "StringProp": Property.from_freecad("hello", {}, "Base"),
            "VectorProp": Property.from_freecad((1.0, 2.0, 3.0), {}, "Base"),
            "PlacementProp": Property.from_freecad(
                {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
            ),
        }
        new_props = {
            "BoolProp": Property.from_freecad(False, {}, "Base"),  # Changed
            "IntProp": Property.from_freecad(42, {}, "Base"),  # Same
            "FloatProp": Property.from_freecad(2.71, {}, "Base"),  # Changed
            "StringProp": Property.from_freecad("world", {}, "Base"),  # Changed
            "VectorProp": Property.from_freecad((4.0, 5.0, 6.0), {}, "Base"),  # Changed
            "PlacementProp": Property.from_freecad(
                {"position": (1.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 90.0)}, {}, "Base"
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

    def test_float_precision_edge_cases(self) -> None:
        """Test float precision-based comparison with various edge cases."""
        # Very small difference — rounds to same value at precision 2
        old_props = {
            "FloatProp": Property.from_freecad(1.0, {}, "Base"),
        }
        new_props = {
            "FloatProp": Property.from_freecad(1.0 + 1e-10, {}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1  # Rounds to same value at precision 2, so unchanged
        assert result[0].state == DiffState.UNCHANGED

        # Difference exceeding precision — rounds to different value at precision 2
        new_props_exceed = {
            "FloatProp": Property.from_freecad(1.0 + 0.015, {}, "Base"),
        }
        result_exceed = compare_properties(old_props, new_props_exceed)
        assert len(result_exceed) == 1
        assert result_exceed[0].state == DiffState.MODIFIED

    def test_property_diff_string_representation(self) -> None:
        """Test string representation of PropertyDiff objects."""
        # ADDED
        added = PropertyDiff(
            property_name="NewProp",
            old_value=None,
            new_value=Property.from_freecad("value", {}, "Base"),
        )
        assert "NewProp: ADDED" in str(added)

        # DELETED
        deleted = PropertyDiff(
            property_name="OldProp",
            old_value=Property.from_freecad("value", {}, "Base"),
            new_value=None,
        )
        assert "OldProp: DELETED" in str(deleted)

        # MODIFIED
        modified = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {}, "Base"),
            new_value=Property.from_freecad(20.0, {}, "Base"),
        )
        assert "Length: MODIFIED" in str(modified)

    def test_same_value_different_expression_is_modified(self) -> None:
        """Test that same value with different expression returns MODIFIED."""
        old_props = {
            "Length": Property.from_freecad(10.0, {".": "Body.Length"}, "Base"),
        }
        new_props = {
            "Length": Property.from_freecad(10.0, {".": "Cube.Size"}, "Base"),
        }
        result = compare_properties(old_props, new_props)
        assert len(result) == 1
        assert result[0].state == DiffState.MODIFIED
        # Expression change is tracked via path_diffs
        assert any(pd.expression_state != DiffState.UNCHANGED for pd in result[0].path_diffs)


class TestCompareNodesById:
    """Tests for ID-based node comparison."""

    def test_identical_nodes_returns_unchanged(self) -> None:
        """Test comparing identical nodes returns UNCHANGED."""
        props = {
            "Label": Property.from_freecad("Body", {}, "Base"),
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

    def test_modified_property_returns_modified(self) -> None:
        """Test detecting a modified property returns MODIFIED."""
        old_props = {
            "Length": Property.from_freecad(10.0, {}, "Base"),
        }
        new_props = {
            "Length": Property.from_freecad(20.0, {}, "Base"),
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

    def test_includes_old_and_new_path_in_result(self) -> None:
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

    def test_includes_old_and_new_after_in_result(self) -> None:
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

    def test_compare_two_flat_node_lists_by_id(self) -> None:
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

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # ID 2 should be added, ID 1 unchanged
        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_detect_added_nodes(self) -> None:
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

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_detect_deleted_nodes(self) -> None:
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

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 1
        assert result.modified_count == 0

    def test_detect_modified_nodes(self) -> None:
        """Test detecting MODIFIED nodes (in both, properties differ)."""
        # Old snapshot: ID 1 with Length=10
        old_node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={"Length": Property.from_freecad(10.0, {}, "Base")},
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
            properties={"Length": Property.from_freecad(20.0, {}, "Base")},
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 1

        # Find the node diff for ID 1 - it may be nested under parent placeholder
        # Look through the hierarchy for Body/Pad
        def find_node_diff(node_diffs: list[NodeDiff], path: str) -> NodeDiff | None:
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        pad_diff = find_node_diff(result.hierarchy.roots, "Body/Pad")
        assert pad_diff is not None
        assert pad_diff.state == DiffState.MODIFIED

    def test_id_based_comparison_produces_correct_sets(self) -> None:
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
                properties={"Length": Property.from_freecad(20.0, {}, "Base")},
            ),
            TreeNode(id=4, name="Box", type_id="Part::Box", label="Box", path="Box", after=None),  # Added
        ]

        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=old_nodes)
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=new_nodes)

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Correct counts: 1 added (ID 4), 1 deleted (ID 3), 1 modified (ID 2)
        assert result.added_count == 1
        assert result.deleted_count == 1
        assert result.modified_count == 1

    def test_node_diff_includes_path_and_after_for_move_detection(self) -> None:
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

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # The NodeDiff should include old_path and new_path for move detection
        # Since the node is unchanged in properties but path changed
        # The node may be nested under a parent placeholder
        def find_node_diff(node_diffs: list[NodeDiff], path: str) -> NodeDiff | None:
            """Recursively find a NodeDiff by path."""
            for diff in node_diffs:
                if diff.path == path:
                    return diff
                found = find_node_diff(diff.children, path)
                if found:
                    return found
            return None

        feature_diff = find_node_diff(result.hierarchy.roots, "Body/Moved")
        assert feature_diff is not None
        assert feature_diff.old_path == "Body/Original"
        assert feature_diff.new_path == "Body/Moved"

    def test_node_diff_for_added_node_has_null_old_path(self) -> None:
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

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Added node should have old_path = None
        box_diff = result.hierarchy.roots[0]
        assert box_diff.old_path is None
        assert box_diff.new_path == "Box"

    def test_node_diff_for_deleted_node_has_null_new_path(self) -> None:
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

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Deleted node should have new_path = None
        box_diff = result.hierarchy.roots[0]
        assert box_diff.old_path == "Box"
        assert box_diff.new_path is None

    def test_hierarchical_output_preserved(self) -> None:
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

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        # Should have hierarchical structure: Body -> Pad
        assert len(result.hierarchy.roots) == 1  # Root: Body
        body_diff = result.hierarchy.roots[0]
        assert len(body_diff.children) == 1  # Child: Pad
        assert body_diff.children[0].path == "Body/Pad"


class TestHierarchyOrderingByAfter:
    """Tests for hierarchy sibling/root ordering based on after links."""

    def test_orders_added_siblings_using_new_after(self) -> None:
        """Added siblings follow new snapshot ordering from new_after links."""
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[])

        new_nodes = [
            TreeNode(id=1, name="Body", type_id="PartDesign::Body", label="Body", path="Body", after=None),
            # Intentionally not in desired after-chain order.
            TreeNode(
                id=4,
                name="Pocket",
                type_id="PartDesign::Pocket",
                label="Pocket",
                path="Body/Pocket",
                after="Sketch",
            ),
            TreeNode(id=2, name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", after=None),
            TreeNode(
                id=3,
                name="Sketch",
                type_id="PartDesign::Sketch",
                label="Sketch",
                path="Body/Sketch",
                after="Pad",
            ),
        ]
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=new_nodes)

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert len(result.hierarchy.roots) == 1
        body_diff = result.hierarchy.roots[0]
        assert [child.path for child in body_diff.children] == ["Body/Pad", "Body/Sketch", "Body/Pocket"]

    def test_orders_roots_using_new_after(self) -> None:
        """Root ordering follows new_after when nodes exist in new snapshot."""
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[])
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[
                TreeNode(id=1, name="ZRoot", type_id="Part::Feature", label="ZRoot", path="ZRoot", after=None),
                TreeNode(id=2, name="ARoot", type_id="Part::Feature", label="ARoot", path="ARoot", after="ZRoot"),
            ],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert [node.path for node in result.hierarchy.roots] == ["ZRoot", "ARoot"]

    def test_orders_deleted_nodes_using_old_after(self) -> None:
        """Deleted-only siblings fall back to old snapshot ordering via old_after."""
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[
                TreeNode(id=1, name="ZRoot", type_id="Part::Feature", label="ZRoot", path="ZRoot", after=None),
                TreeNode(id=2, name="ARoot", type_id="Part::Feature", label="ARoot", path="ARoot", after="ZRoot"),
            ],
        )
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[])

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert [node.path for node in result.hierarchy.roots] == ["ZRoot", "ARoot"]


class TestExcludedTypesFiltering:
    """Tests for excluded_types filtering in compare_snapshots."""

    def test_excludes_nodes_with_excluded_type(self) -> None:
        """Test that nodes with excluded type_id are filtered out."""
        # Old snapshot with App::Origin (excluded type)
        old_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot with same node
        new_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        # Pass App::Origin in excluded_types
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Origin node should be excluded
        assert len(result.hierarchy.roots) == 0
        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 0

    def test_excludes_children_of_excluded_type_parent(self) -> None:
        """Test that children of excluded type nodes are also filtered."""
        # Old snapshot with App::Origin and its child
        origin = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        xy_plane = TreeNode(
            id=2,
            name="XYPlane",
            type_id="App::Plane",
            label="XYPlane",
            path="Origin/XYPlane",
            after="Origin",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[origin, xy_plane],
        )

        # New snapshot with same nodes
        new_origin = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_xy_plane = TreeNode(
            id=2,
            name="XYPlane",
            type_id="App::Plane",
            label="XYPlane",
            path="Origin/XYPlane",
            after="Origin",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_origin, new_xy_plane],
        )

        # Pass App::Origin in excluded_types - should exclude both origin and its child
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Both nodes should be excluded
        assert len(result.hierarchy.roots) == 0

    def test_includes_nodes_not_in_excluded_types(self) -> None:
        """Test that nodes not in excluded_types are included."""
        # Old snapshot with Part::Feature
        old_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Feature",
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

        # New snapshot with same node
        new_node = TreeNode(
            id=1,
            name="Box",
            type_id="Part::Feature",
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

        # Pass App::Origin in excluded_types (but our node is Part::Feature)
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Box node should be included
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].path == "Box"

    def test_excludes_added_nodes_with_excluded_type(self) -> None:
        """Test that added nodes with excluded type are filtered."""
        # Old snapshot is empty
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        # New snapshot with App::Origin (newly added)
        new_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_node],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Should have no diffs (excluded)
        assert len(result.hierarchy.roots) == 0

    def test_excludes_deleted_nodes_with_excluded_type(self) -> None:
        """Test that deleted nodes with excluded type are filtered."""
        # Old snapshot with App::Origin (deleted)
        old_node = TreeNode(
            id=1,
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            path="Origin",
            after=None,
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[old_node],
        )

        # New snapshot is empty
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["App::Origin"])

        # Should have no diffs (excluded)
        assert len(result.hierarchy.roots) == 0


class TestExcludedParentPathFiltering:
    """Tests for excluded parent path filtering in compare_snapshots."""

    def test_excludes_child_when_parent_excluded_by_type(self) -> None:
        """Test that child nodes are excluded when parent type is excluded."""
        # Old: Body -> Pad -> Sketch (Sketch will be excluded because parent Pad type is excluded)
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
        sketch = TreeNode(
            id=3,
            name="Sketch",
            type_id="PartDesign::Sketch",
            label="Sketch",
            path="Body/Pad/Sketch",
            after="Pad",
        )
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[body, pad, sketch],
        )

        # New: same nodes
        new_body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_sketch = TreeNode(
            id=3,
            name="Sketch",
            type_id="PartDesign::Sketch",
            label="Sketch",
            path="Body/Pad/Sketch",
            after="Pad",
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[new_body, new_pad, new_sketch],
        )

        # Exclude PartDesign::Pad (parent of Sketch)
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["PartDesign::Pad"])

        # Body should be included (not excluded type), but Pad and Sketch should be excluded
        paths_in_result = {diff.path for diff in _flatten_diffs(result.hierarchy.roots)}
        assert "Body" in paths_in_result
        assert "Body/Pad" not in paths_in_result
        assert "Body/Pad/Sketch" not in paths_in_result

    def test_mixed_excluded_and_included_nodes(self) -> None:
        """Test that some nodes are excluded while others are included."""
        # Create nodes: Body with two children - one excluded, one included
        body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        # This Pad will be excluded
        pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        # This box will NOT be excluded (different parent)
        box = TreeNode(
            id=3,
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
            nodes=[body, pad, box],
        )

        # New: same nodes
        new_body = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        new_pad = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
        )
        new_box = TreeNode(
            id=3,
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
            nodes=[new_body, new_pad, new_box],
        )

        # Exclude PartDesign::Pad only
        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], ["PartDesign::Pad"])

        # Body and Box should be included, Pad should be excluded
        paths_in_result = {diff.path for diff in _flatten_diffs(result.hierarchy.roots)}
        assert "Body" in paths_in_result
        assert "Body/Pad" not in paths_in_result
        assert "Box" in paths_in_result


class TestEmptySnapshots:
    """Tests for handling empty snapshots in compare_snapshots."""

    def test_both_snapshots_empty_returns_empty(self) -> None:
        """Test that comparing two empty snapshots returns empty result."""
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 0
        assert result.modified_count == 0
        assert result.hierarchy.roots == []

    def test_old_empty_new_with_nodes_returns_added(self) -> None:
        """Test that when old is empty, new nodes are marked as added."""
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        new_box = TreeNode(
            id=1,
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
            nodes=[new_box],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 1
        assert result.deleted_count == 0
        assert result.modified_count == 0
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].state == DiffState.ADDED

    def test_new_empty_old_with_nodes_returns_deleted(self) -> None:
        """Test that when new is empty, old nodes are marked as deleted."""
        old_box = TreeNode(
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
            nodes=[old_box],
        )

        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.added_count == 0
        assert result.deleted_count == 1
        assert result.modified_count == 0
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].state == DiffState.DELETED

    def test_hierarchy_preserved_with_empty_parent(self) -> None:
        """Test that hierarchy is preserved when parent becomes empty."""
        # Old: Body with child Pad
        body = TreeNode(
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
            nodes=[body],
        )

        # New: empty (Body deleted)
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="Test",
            timestamp=datetime.now(),
            nodes=[],
        )

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [])

        assert result.deleted_count == 1
        assert len(result.hierarchy.roots) == 1
        assert result.hierarchy.roots[0].path == "Body"
        assert result.hierarchy.roots[0].state == DiffState.DELETED


def _flatten_diffs(node_diffs: list[NodeDiff]) -> list[NodeDiff]:
    """Flatten a hierarchical list of NodeDiffs into a flat list."""
    result: list[NodeDiff] = []
    for diff in node_diffs:
        result.append(diff)
        if diff.children:
            result.extend(_flatten_diffs(diff.children))
    return result


class TestTypeSpecificPropertyExclusions:
    """Tests for type-specific property exclusion in the comparator."""

    def test_excludes_property_for_matching_type(self) -> None:
        """Test that Template property is excluded for TechDraw::DrawSVGTemplate."""
        old_node = TreeNode(
            id=1,
            name="Template",
            type_id="TechDraw::DrawSVGTemplate",
            label="Template",
            path="Template",
            after=None,
            properties={
                "Template": Property.from_freecad("some_template_data", {}, "Base"),
                "Label": Property.from_freecad("MyTemplate", {}, "Base"),
            },
        )
        new_node = TreeNode(
            id=1,
            name="Template",
            type_id="TechDraw::DrawSVGTemplate",
            label="MyTemplate",
            path="Template",
            after=None,
            properties={
                "Template": Property.from_freecad("different_template_data", {}, "Base"),
                "Label": Property.from_freecad("MyTemplate", {}, "Base"),
            },
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[old_node])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[new_node])

        by_type: dict[str, list[str]] = {"TechDraw::DrawSVGTemplate": ["Template"]}

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [], by_type)

        # Template property should be excluded for this type, so no changes detected
        assert result.has_changes is False
        assert result.modified_count == 0

    def test_includes_property_for_non_matching_type(self) -> None:
        """Test that Template property is NOT excluded for unrelated types."""
        old_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Feature",
            after=None,
            properties={
                "Template": Property.from_freecad("some_data", {}, "Base"),
                "Label": Property.from_freecad("MyFeature", {}, "Base"),
            },
        )
        new_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="MyFeature",
            path="Feature",
            after=None,
            properties={
                "Template": Property.from_freecad("different_data", {}, "Base"),
                "Label": Property.from_freecad("MyFeature", {}, "Base"),
            },
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[old_node])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[new_node])

        by_type: dict[str, list[str]] = {"TechDraw::DrawSVGTemplate": ["Template"]}

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [], by_type)

        # Template property should NOT be excluded for Part::Feature
        assert result.has_changes is True
        assert result.modified_count == 1

    def test_type_change_uses_union_of_rules(self) -> None:
        """Test that type change uses union of per-type rules from both old and new types."""
        # Old node is TechDraw::DrawSVGTemplate with Template property changed
        old_node = TreeNode(
            id=1,
            name="Item",
            type_id="TechDraw::DrawSVGTemplate",
            label="Item",
            path="Item",
            after=None,
            properties={
                "Template": Property.from_freecad("old_template", {}, "Base"),
                "Label": Property.from_freecad("Item", {}, "Base"),
            },
        )
        # New node is Part::Feature with Template property changed
        new_node = TreeNode(
            id=1,
            name="Item",
            type_id="Part::Feature",
            label="Item",
            path="Item",
            after=None,
            properties={
                "Template": Property.from_freecad("new_template", {}, "Base"),
                "Label": Property.from_freecad("Item", {}, "Base"),
            },
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[old_node])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[new_node])

        # TechDraw::DrawSVGTemplate excludes "Template", Part::Feature excludes "Label"
        by_type: dict[str, list[str]] = {
            "TechDraw::DrawSVGTemplate": ["Template"],
            "Part::Feature": ["Label"],
        }

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [], by_type)

        # Template excluded by old type, Label excluded by new type
        # So both changes should be hidden
        assert result.has_changes is False
        assert result.modified_count == 0

    def test_global_exclusions_still_applied(self) -> None:
        """Test that global exclusions are applied alongside type-specific ones."""
        old_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Feature",
            after=None,
            properties={
                "TimeStamp": Property.from_freecad("2024-01-01", {}, "Base"),
                "Label": Property.from_freecad("Feature", {}, "Base"),
            },
        )
        new_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Feature",
            after=None,
            properties={
                "TimeStamp": Property.from_freecad("2024-01-02", {}, "Base"),
                "Label": Property.from_freecad("Feature", {}, "Base"),
            },
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[old_node])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[new_node])

        by_type: dict[str, list[str]] = {"Part::Feature": ["Label"]}

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, ["TimeStamp"], by_type)

        # TimeStamp excluded globally, Label excluded by type
        assert result.has_changes is False
        assert result.modified_count == 0

    def test_added_node_uses_new_type_exclusions(self) -> None:
        """Test that added nodes use their new type for property exclusion."""
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[])
        new_node = TreeNode(
            id=1,
            name="Template",
            type_id="TechDraw::DrawSVGTemplate",
            label="Template",
            path="Template",
            after=None,
            properties={
                "Template": Property.from_freecad("template_data", {}, "Base"),
                "Label": Property.from_freecad("MyTemplate", {}, "Base"),
            },
        )
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[new_node])

        by_type: dict[str, list[str]] = {"TechDraw::DrawSVGTemplate": ["Template"]}

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [], by_type)

        # Template property should be excluded, so only Label shows as added
        assert result.added_count == 1
        # Find the node diff and check that Template is not in property diffs
        node_diff = result.hierarchy.roots[0]
        template_props = [pd for pd in node_diff.property_diffs if pd.property_name == "Template"]
        assert len(template_props) == 0

    def test_deleted_node_uses_old_type_exclusions(self) -> None:
        """Test that deleted nodes use their old type for property exclusion."""
        old_node = TreeNode(
            id=1,
            name="Template",
            type_id="TechDraw::DrawSVGTemplate",
            label="Template",
            path="Template",
            after=None,
            properties={
                "Template": Property.from_freecad("template_data", {}, "Base"),
                "Label": Property.from_freecad("MyTemplate", {}, "Base"),
            },
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[old_node])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[])

        by_type: dict[str, list[str]] = {"TechDraw::DrawSVGTemplate": ["Template"]}

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], [], by_type)

        # Template property should be excluded, so only Label shows as deleted
        assert result.deleted_count == 1
        node_diff = result.hierarchy.roots[0]
        template_props = [pd for pd in node_diff.property_diffs if pd.property_name == "Template"]
        assert len(template_props) == 0

    def test_empty_by_type_ignores_type_specific_rules(self) -> None:
        """Test that empty by_type dict means no type-specific exclusions."""
        old_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Feature",
            after=None,
            properties={
                "Template": Property.from_freecad("data", {}, "Base"),
                "Label": Property.from_freecad("Feature", {}, "Base"),
            },
        )
        new_node = TreeNode(
            id=1,
            name="Feature",
            type_id="Part::Feature",
            label="Feature",
            path="Feature",
            after=None,
            properties={
                "Template": Property.from_freecad("different_data", {}, "Base"),
                "Label": Property.from_freecad("Feature", {}, "Base"),
            },
        )
        old_snapshot = Snapshot(snapshot_id="old", document_name="Test", timestamp=datetime.now(), nodes=[old_node])
        new_snapshot = Snapshot(snapshot_id="new", document_name="Test", timestamp=datetime.now(), nodes=[new_node])

        by_type: dict[str, list[str]] = {}

        result = _tree_comparator.compare_snapshots(old_snapshot, new_snapshot, [], by_type)

        # With empty by_type, Template should not be excluded
        assert result.has_changes is True
        assert result.modified_count == 1
