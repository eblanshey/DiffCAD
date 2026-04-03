# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for DiffEngine and related domain models including
# DiffState, PropertyDiff, NodeDiff, DiffSummary, and DiffResult.
"""Unit tests for DiffEngine and diff domain models."""

import datetime
import uuid

from freecad.diff_wb.domain import Property, PropertyType
from freecad.diff_wb.domain.diff import DiffResult, DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.diff.engine import DiffEngine
from freecad.diff_wb.domain.diff.models import DiffSummary
from freecad.diff_wb.domain.snapshots import Snapshot
from freecad.diff_wb.domain.tree.node import TreeNode


class TestDiffState:
    """Tests for the DiffState enum."""

    def test_states_exist(self):
        """Test that all states exist."""
        assert DiffState.ADDED is not None
        assert DiffState.DELETED is not None
        assert DiffState.MODIFIED is not None
        assert DiffState.UNCHANGED is not None


class TestPropertyDiff:
    """Tests for the PropertyDiff class."""

    def test_added_property(self):
        """Test added property diff - state auto-calculated."""
        new_val = Property.create(PropertyType.FLOAT, 10.0)
        diff = PropertyDiff(property_name="Length", old_value=None, new_value=new_val)
        assert diff.state == DiffState.ADDED
        assert "+10.0" in str(diff)

    def test_deleted_property(self):
        """Test deleted property diff - state auto-calculated."""
        old_val = Property.create(PropertyType.FLOAT, 5.0)
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=None)
        assert diff.state == DiffState.DELETED
        assert "-5.0" in str(diff)

    def test_modified_property(self):
        """Test modified property diff - state auto-calculated."""
        old_val = Property.create(PropertyType.FLOAT, 5.0)
        new_val = Property.create(PropertyType.FLOAT, 10.0)
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        assert "5.0 -> 10.0" in str(diff)

    def test_unchanged_property(self):
        """Test unchanged property diff - state auto-calculated."""
        val = Property.create(PropertyType.FLOAT, 10.0)
        diff = PropertyDiff(property_name="Length", old_value=val, new_value=val)
        assert diff.state == DiffState.UNCHANGED

    # =====================================================================
    # Expression Change Tests in PropertyDiff
    # =====================================================================

    def test_expression_only_change_detected(self):
        """Test that expression-only change shows as UNCHANGED (expression tracked separately)."""
        old_val = Property.create(PropertyType.FLOAT, 10.0)
        new_val = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch001.X")
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.UNCHANGED  # Value unchanged, expression tracked separately

    def test_value_only_change_detected(self):
        """Test that value-only change is detected as modified."""
        old_val = Property.create(PropertyType.INT, 10, expression="Sketch001.Count")
        new_val = Property.create(PropertyType.INT, 20, expression="Sketch001.Count")
        diff = PropertyDiff(property_name="Count", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        # String format: "Count: 10 (via Sketch001.Count) -> 20 (via Sketch001.Count)"
        assert "Count:" in str(diff)
        assert "10" in str(diff)
        assert "20" in str(diff)

    def test_both_expression_and_value_change(self):
        """Test that both expression and value change is detected."""
        old_val = Property.create(PropertyType.FLOAT, 5.0, expression="Sketch001.X")
        new_val = Property.create(PropertyType.FLOAT, 15.0, expression="Sketch002.Y")
        diff = PropertyDiff(property_name="Dimension", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        assert "Dimension:" in str(diff)
        assert "5.0" in str(diff)
        assert "15.0" in str(diff)

    def test_expression_changed_to_none(self):
        """Test that removing expression with same value shows UNCHANGED."""
        old_val = Property.create(PropertyType.STRING, "test", expression="Doc.Name")
        new_val = Property.create(PropertyType.STRING, "test")
        diff = PropertyDiff(property_name="Name", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.UNCHANGED  # Value unchanged, expression tracked separately

    def test_expression_added_from_none(self):
        """Test that adding expression with same value shows UNCHANGED."""
        old_val = Property.create(PropertyType.INT, 42)
        new_val = Property.create(PropertyType.INT, 42, expression="Some.Expr")
        diff = PropertyDiff(property_name="Value", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.UNCHANGED  # Value unchanged, expression tracked separately

    def test_different_expressions_same_value(self):
        """Test different expressions with same value shows UNCHANGED."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch001.X")
        new_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch002.X")
        diff = PropertyDiff(property_name="Position", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.UNCHANGED  # Value unchanged, expression tracked separately


class TestNodeDiff:
    """Tests for the NodeDiff class."""

    def test_creation(self):
        """Test node diff creation - state auto-calculated from empty property_diffs and children."""
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad")
        assert diff.path == "Body/Pad"
        # With no property diffs or children, state should be UNCHANGED
        assert diff.state == DiffState.UNCHANGED

    def test_state_auto_calculated_from_property_diffs(self):
        """Test that state is auto-calculated based on property diffs."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 5.0),
            new_value=Property.create(PropertyType.FLOAT, 10.0),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        # State should be MODIFIED because there's a changed property
        assert diff.state == DiffState.MODIFIED
        assert diff.has_changes is True

    def test_state_auto_calculated_unchanged(self):
        """Test that state is UNCHANGED when no property diffs."""
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[])
        assert diff.state == DiffState.UNCHANGED
        assert diff.has_changes is False

    def test_has_changes_with_property_diffs(self):
        """Test has_changes when there are property diffs."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 5.0),
            new_value=Property.create(PropertyType.FLOAT, 10.0),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        assert diff.has_changes is True

    def test_changed_properties(self):
        """Test getting only changed properties."""
        changed = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 5.0),
            new_value=Property.create(PropertyType.FLOAT, 10.0),
        )
        unchanged = PropertyDiff(
            property_name="Type",
            old_value=Property.create(PropertyType.STRING, "Dimension"),
            new_value=Property.create(PropertyType.STRING, "Dimension"),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[changed, unchanged])
        changed_props = diff.changed_properties
        assert len(changed_props) == 1
        assert changed_props[0].property_name == "Length"


class TestDiffSummary:
    """Tests for the DiffSummary class."""

    def test_empty_summary(self):
        """Test empty summary."""
        summary = DiffSummary()
        assert summary.total_nodes == 0
        assert summary.added_nodes == 0

    def test_string_representation(self):
        """Test string representation."""
        summary = DiffSummary(added_nodes=2, deleted_nodes=1, modified_nodes=3, unchanged_nodes=10)
        str_repr = str(summary)
        assert "2 added" in str_repr
        assert "1 deleted" in str_repr


class TestDiffResult:
    """Tests for the DiffResult class."""

    def test_creation(self):
        """Test diff result creation."""
        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2")
        assert diff.old_snapshot_name == "v1"
        assert diff.new_snapshot_name == "v2"

    def test_has_changes_false(self):
        """Test has_changes when no changes."""
        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2")
        assert diff.has_changes is False

    def test_has_changes_true(self):
        """Test has_changes when there are changes."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 20.0),
        )
        node_diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2", node_diffs=[node_diff])
        assert diff.has_changes is True

    def test_get_all_changed_paths(self):
        """Test getting all changed paths."""
        child_prop = PropertyDiff(
            property_name="Width",
            old_value=Property.create(PropertyType.FLOAT, 5.0),
            new_value=Property.create(PropertyType.FLOAT, 15.0),
        )
        child = NodeDiff(path="Body/Pad/Sub", type_id="Part::Feature", property_diffs=[child_prop])
        parent_prop = PropertyDiff(
            property_name="Length",
            old_value=Property.create(PropertyType.FLOAT, 10.0),
            new_value=Property.create(PropertyType.FLOAT, 20.0),
        )
        parent = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[parent_prop], children=[child])
        unchanged = NodeDiff(path="Body", type_id="PartDesign::Body")

        diff = DiffResult(old_snapshot_name="v1", new_snapshot_name="v2", node_diffs=[parent, unchanged])

        changed_paths = diff.get_all_changed_paths()
        assert "Body/Pad/Sub" in changed_paths
        assert "Body/Pad" in changed_paths  # Parent included because child changed
        assert "Body" not in changed_paths  # Unchanged with no changed children


class TestDiffEngineComputeDiff:
    """Tests for DiffEngine.compute_diff() with flat Snapshot structure."""

    def test_compute_diff_with_empty_snapshots(self):
        """Test compute_diff with empty snapshots returns empty result."""
        old_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.old_snapshot_name == "old"
        assert result.new_snapshot_name == "new"
        assert result.node_diffs == []
        assert result.has_changes is False

    def test_compute_diff_detect_added_node(self):
        """Test compute_diff detects added nodes with flat structure."""
        old_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )
        new_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            nodes=[new_node],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.has_changes is True
        # The new node should appear as added
        assert len(result.node_diffs) > 0

    def test_compute_diff_detect_deleted_node(self):
        """Test compute_diff detects deleted nodes with flat structure."""
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )
        old_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.has_changes is True

    def test_compute_diff_detect_modified_node(self):
        """Test compute_diff detects modified nodes with flat structure."""
        from freecad.diff_wb.domain import Property

        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={"Length": Property.create(PropertyType.FLOAT, 10.0)},
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
        )
        old_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            nodes=[new_node],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.has_changes is True
        # Should find the modified property
        node_diff = result.node_diffs[0]
        assert len(node_diff.property_diffs) > 0

    def test_compute_diff_with_nested_flat_nodes(self):
        """Test compute_diff with flat nested nodes structure."""
        # Old snapshot with parent and child
        old_parent = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )
        old_child = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={},
        )
        old_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            nodes=[old_parent, old_child],
        )

        # New snapshot with parent and child (same structure)
        new_parent = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )
        new_child = TreeNode(
            id=2,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Body",
            properties={},
        )
        new_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            nodes=[new_parent, new_child],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # No changes expected
        assert result.has_changes is False

    def test_compute_diff_filters_excluded_types(self):
        """Test compute_diff filters out excluded node types."""

        class MockSettingsRepo:
            def get_excluded_types(self):
                return ["PartDesign::Body"]

            def get_excluded_properties(self):
                return []

        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )
        old_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )

        engine = DiffEngine(settings_repo=MockSettingsRepo())
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # With excluded type, should not report changes
        assert result.has_changes is False


class TestDiffEngineCompare:
    """Tests for DiffEngine.compare() with Snapshot objects."""

    def test_compare_with_empty_snapshots(self):
        """Test compare with empty snapshots returns empty result."""
        engine = DiffEngine()
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        result = engine.compare(
            old_snapshot,
            new_snapshot,
            excluded_types=[],
            excluded_properties=[],
        )

        assert result.node_diffs == []
        assert result.has_changes is False

    def test_compare_detect_added_nodes(self):
        """Test compare detects added nodes in snapshot."""
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )

        engine = DiffEngine()
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[new_node],
        )
        result = engine.compare(
            old_snapshot,
            new_snapshot,
            excluded_types=[],
            excluded_properties=[],
        )

        assert result.has_changes is True

    def test_compare_detect_deleted_nodes(self):
        """Test compare detects deleted nodes in snapshot."""
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )

        engine = DiffEngine()
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        result = engine.compare(
            old_snapshot,
            new_snapshot,
            excluded_types=[],
            excluded_properties=[],
        )

        assert result.has_changes is True

    def test_compare_with_modified_properties(self):
        """Test compare detects modified properties in snapshot."""
        from freecad.diff_wb.domain import Property

        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={"Length": Property.create(PropertyType.FLOAT, 10.0)},
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={"Length": Property.create(PropertyType.FLOAT, 20.0)},
        )

        engine = DiffEngine()
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[new_node],
        )
        result = engine.compare(
            old_snapshot,
            new_snapshot,
            excluded_types=[],
            excluded_properties=[],
        )

        assert result.has_changes is True

    def test_compare_filters_excluded_types(self):
        """Test compare filters excluded node types."""
        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={},
        )

        engine = DiffEngine()
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[],
        )
        result = engine.compare(
            old_snapshot,
            new_snapshot,
            excluded_types=["PartDesign::Body"],
            excluded_properties=[],
        )

        # With excluded type, should not report changes
        assert result.has_changes is False

    def test_compare_filters_excluded_properties(self):
        """Test compare filters excluded property names."""
        from freecad.diff_wb.domain import Property

        old_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={
                "Length": Property.create(PropertyType.FLOAT, 10.0),
                "Label": Property.create(PropertyType.STRING, "Body"),
            },
        )
        new_node = TreeNode(
            id=1,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
            properties={
                "Length": Property.create(PropertyType.FLOAT, 20.0),
                "Label": Property.create(PropertyType.STRING, "Body"),
            },
        )

        engine = DiffEngine()
        old_snapshot = Snapshot(
            snapshot_id="old",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            nodes=[old_node],
        )
        new_snapshot = Snapshot(
            snapshot_id="new",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            nodes=[new_node],
        )
        result = engine.compare(
            old_snapshot,
            new_snapshot,
            excluded_types=[],
            excluded_properties=["Length"],
        )

        # Only Label property differs (but it's the same value)
        # Length should be excluded from comparison
        assert result.has_changes is False
