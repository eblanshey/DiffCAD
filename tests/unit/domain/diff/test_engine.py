# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for DiffEngine and related domain models including
# DiffState, PropertyDiff, NodeDiff, DiffSummary, and DiffResult.
"""Unit tests for DiffEngine and diff domain models."""

from freecad.diff_wb.domain import Property, PropertyType
from freecad.diff_wb.domain.diff import DiffResult, DiffState, NodeDiff, PropertyDiff
from freecad.diff_wb.domain.diff.models import DiffSummary


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
        """Test that expression-only change is detected as modified."""
        old_val = Property.create(PropertyType.FLOAT, 10.0)
        new_val = Property.create(PropertyType.FLOAT, 10.0, expression="Sketch001.X")
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED
        assert "10.0 -> 10.0" in str(diff)  # Values same but expression changed

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
        # String format includes property name, values, and expressions
        assert "Dimension:" in str(diff)
        assert "5.0" in str(diff)
        assert "15.0" in str(diff)
        assert "Sketch001.X" in str(diff)
        assert "Sketch002.Y" in str(diff)

    def test_expression_changed_to_none(self):
        """Test that removing an expression is detected as modified."""
        old_val = Property.create(PropertyType.STRING, "test", expression="Doc.Name")
        new_val = Property.create(PropertyType.STRING, "test")
        diff = PropertyDiff(property_name="Name", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED

    def test_expression_added_from_none(self):
        """Test that adding an expression is detected as modified."""
        old_val = Property.create(PropertyType.INT, 42)
        new_val = Property.create(PropertyType.INT, 42, expression="Some.Expr")
        diff = PropertyDiff(property_name="Value", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED

    def test_different_expressions_same_value(self):
        """Test different expressions with same value detected as modified."""
        old_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch001.X")
        new_val = Property.create(PropertyType.VECTOR, (1.0, 2.0, 3.0), expression="Sketch002.X")
        diff = PropertyDiff(property_name="Position", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED


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
