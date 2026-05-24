# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Tests for DiffEngine and related domain models including
# DiffState, PropertyDiff, NodeDiff, and DiffResult.
"""Unit tests for DiffEngine and diff domain models."""

import datetime
import uuid
from typing import Any

from freecad.history_wb.domain import Property
from freecad.history_wb.domain.diff import (
    DiffHierarchy,
    DiffResult,
    DiffState,
    NodeDiff,
    PropertyDiff,
)
from freecad.history_wb.domain.diff.engine import DiffEngine
from freecad.history_wb.domain.snapshots import Snapshot
from freecad.history_wb.domain.snapshots.models import SnapshotObject, SnapshotOccurrence


class _MockSettingsRepo:
    """Configurable mock settings repository for DiffEngine tests."""

    def __init__(
        self,
        excluded_types: list[str] | None = None,
        excluded_properties: list[str] | None = None,
        excluded_by_type: dict[str, list[str]] | None = None,
        float_precision: int = 2,
    ) -> None:
        self._excluded_types = excluded_types or []
        self._excluded_properties = excluded_properties or []
        self._excluded_by_type = excluded_by_type or {}
        self._float_precision = float_precision

    def get_excluded_types(self) -> list[str]:
        return self._excluded_types

    def get_excluded_properties(self) -> list[str]:
        return self._excluded_properties

    def get_excluded_properties_by_type(self) -> dict[str, list[str]]:
        return self._excluded_by_type

    def get_float_precision(self) -> int:
        return self._float_precision


def snapshot_from_rows(
    *,
    snapshot_id: str,
    document_name: str,
    timestamp: datetime.datetime,
    tree: list[dict[str, Any]] | None = None,
    objects: list[SnapshotObject] | None = None,
    occurrences: list[SnapshotOccurrence] | None = None,
) -> Snapshot:
    """Build normalized Snapshot from flat dict fixtures."""
    if tree is not None:
        objects = [
            SnapshotObject(
                name=str(n["name"]),
                id=int(n["id"]),
                type_id=str(n["type_id"]),
                properties=n.get("properties", {}),  # type: ignore[arg-type]
            )
            for n in tree
        ]
        occurrences = [
            SnapshotOccurrence(
                path=str(n["path"]),
                after=(str(n["after"]) if n["after"] is not None else None),
            )
            for n in tree
        ]
    return Snapshot(
        snapshot_id=snapshot_id,
        document_name=document_name,
        timestamp=timestamp,
        objects=objects or [],
        occurrences=occurrences or [],
    )


class TestPropertyDiff:
    """Tests for the PropertyDiff class."""

    def test_added_property(self) -> None:
        """Test added property diff - state auto-calculated."""
        new_val = Property.from_freecad(10.0, {}, "Base")
        diff = PropertyDiff(property_name="Length", old_value=None, new_value=new_val)
        assert diff.state == DiffState.ADDED

    def test_deleted_property(self) -> None:
        """Test deleted property diff - state auto-calculated."""
        old_val = Property.from_freecad(5.0, {}, "Base")
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=None)
        assert diff.state == DiffState.DELETED

    def test_modified_property(self) -> None:
        """Test modified property diff - state auto-calculated."""
        old_val = Property.from_freecad(5.0, {}, "Base")
        new_val = Property.from_freecad(10.0, {}, "Base")
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED

    def test_unchanged_property(self) -> None:
        """Test unchanged property diff - state auto-calculated."""
        val = Property.from_freecad(10.0, {}, "Base")
        diff = PropertyDiff(property_name="Length", old_value=val, new_value=val)
        assert diff.state == DiffState.UNCHANGED

    # =====================================================================
    # Expression Change Tests in PropertyDiff
    # =====================================================================

    def test_expression_only_change_detected(self) -> None:
        """Test that expression-only change shows as MODIFIED."""
        old_val = Property.from_freecad(10.0, {}, "Base")
        new_val = Property.from_freecad(10.0, {".": "Sketch001.X"}, "Base")
        diff = PropertyDiff(property_name="Length", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED  # Expression change makes property modified

    def test_value_only_change_detected(self) -> None:
        """Test that value-only change is detected as modified."""
        old_val = Property.from_freecad(10, {".": "Sketch001.Count"}, "Base")
        new_val = Property.from_freecad(20, {".": "Sketch001.Count"}, "Base")
        diff = PropertyDiff(property_name="Count", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED

    def test_both_expression_and_value_change(self) -> None:
        """Test that both expression and value change is detected."""
        old_val = Property.from_freecad(5.0, {".": "Sketch001.X"}, "Base")
        new_val = Property.from_freecad(15.0, {".": "Sketch002.Y"}, "Base")
        diff = PropertyDiff(property_name="Dimension", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED

    def test_expression_changed_to_none(self) -> None:
        """Test that removing expression with same value shows MODIFIED."""
        old_val = Property.from_freecad("test", {".": "Doc.Name"}, "Base")
        new_val = Property.from_freecad("test", {}, "Base")
        diff = PropertyDiff(property_name="Name", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED  # Expression change makes property modified

    def test_expression_added_from_none(self) -> None:
        """Test that adding expression with same value shows MODIFIED."""
        old_val = Property.from_freecad(42, {}, "Base")
        new_val = Property.from_freecad(42, {".": "Some.Expr"}, "Base")
        diff = PropertyDiff(property_name="Value", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED  # Expression change makes property modified

    def test_different_expressions_same_value(self) -> None:
        """Test different expressions with same value shows MODIFIED."""
        old_val = Property.from_freecad((1.0, 2.0, 3.0), {".": "Sketch001.X"}, "Base")
        new_val = Property.from_freecad((1.0, 2.0, 3.0), {".": "Sketch002.X"}, "Base")
        diff = PropertyDiff(property_name="Position", old_value=old_val, new_value=new_val)
        assert diff.state == DiffState.MODIFIED  # Expression change makes property modified


class TestNodeDiff:
    """Tests for the NodeDiff class."""

    def test_creation(self) -> None:
        """Test node diff creation - state auto-calculated from empty property_diffs and children."""
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad")
        assert diff.path == "Body/Pad"
        # With no property diffs or children, state should be UNCHANGED
        assert diff.state == DiffState.UNCHANGED

    def test_state_auto_calculated_from_property_diffs(self) -> None:
        """Test that state is auto-calculated based on property diffs."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(5.0, {}, "Base"),
            new_value=Property.from_freecad(10.0, {}, "Base"),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        # State should be MODIFIED because there's a changed property
        assert diff.state == DiffState.MODIFIED
        assert diff.has_own_changes is True
        assert diff.has_deep_changes is True

    def test_state_auto_calculated_unchanged(self) -> None:
        """Test that state is UNCHANGED when no property diffs."""
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[])
        assert diff.state == DiffState.UNCHANGED
        assert diff.has_own_changes is False
        assert diff.has_deep_changes is False

    def test_has_own_and_deep_changes_with_property_diffs(self) -> None:
        """Test own/deep change flags when there are property diffs."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(5.0, {}, "Base"),
            new_value=Property.from_freecad(10.0, {}, "Base"),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        assert diff.has_own_changes is True
        assert diff.has_deep_changes is True

    def test_changed_properties(self) -> None:
        """Test getting only changed properties."""
        changed = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(5.0, {}, "Base"),
            new_value=Property.from_freecad(10.0, {}, "Base"),
        )
        unchanged = PropertyDiff(
            property_name="Type",
            old_value=Property.from_freecad("Dimension", {}, "Base"),
            new_value=Property.from_freecad("Dimension", {}, "Base"),
        )
        diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[changed, unchanged])
        changed_props = diff.changed_properties
        assert len(changed_props) == 1
        assert changed_props[0].property_name == "Length"

    def test_parent_has_deep_changes_after_hierarchy_rollup(self) -> None:
        """Parent can be own-unchanged but deep-changed via child."""
        child_prop = PropertyDiff(
            property_name="Width",
            old_value=Property.from_freecad(5.0, {}, "Base"),
            new_value=Property.from_freecad(15.0, {}, "Base"),
        )
        child = NodeDiff(path="Body/Pad/Sub", type_id="Part::Feature", property_diffs=[child_prop])
        parent = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad")

        hierarchy = DiffHierarchy()
        hierarchy.add_node(parent)
        hierarchy.add_node(child)
        hierarchy.compute_deep_change_flags()

        assert parent.has_own_changes is False
        assert parent.has_deep_changes is True


class TestDiffResult:
    """Tests for the DiffResult class."""

    def test_creation_with_snapshots(self) -> None:
        """Test DiffResult created with old_snapshot and new_snapshot parameters."""
        old_snapshot = snapshot_from_rows(
            snapshot_id="old-id",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id="new-id",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        diff = DiffResult(old_snapshot=old_snapshot, new_snapshot=new_snapshot)
        assert diff.old_snapshot is old_snapshot
        assert diff.new_snapshot is new_snapshot

    def test_default_counts_initialized(self) -> None:
        """Test default counters are initialized."""
        old_snapshot = snapshot_from_rows(
            snapshot_id="old-id",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id="new-id",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        diff = DiffResult(old_snapshot=old_snapshot, new_snapshot=new_snapshot)
        assert diff.added_count == 0
        assert diff.deleted_count == 0
        assert diff.modified_count == 0

    def test_same_snapshot_instance_allowed(self) -> None:
        """Test same snapshot instance for old/new is valid."""
        snapshot = snapshot_from_rows(
            snapshot_id="same-id",
            document_name="SameDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        diff = DiffResult(old_snapshot=snapshot, new_snapshot=snapshot)
        assert diff.old_snapshot is snapshot

    def test_has_changes_false(self) -> None:
        """Test has_changes when no changes."""
        old_snapshot = snapshot_from_rows(
            snapshot_id="old-id",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id="new-id",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        diff = DiffResult(old_snapshot=old_snapshot, new_snapshot=new_snapshot)
        assert diff.has_changes is False

    def test_has_changes_true(self) -> None:
        """Test has_changes when there are changes."""
        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {}, "Base"),
            new_value=Property.from_freecad(20.0, {}, "Base"),
        )
        node_diff = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[prop_diff])
        hierarchy = DiffHierarchy()
        hierarchy._roots.append(node_diff)
        old_snapshot = snapshot_from_rows(
            snapshot_id="old-id",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id="new-id",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        diff = DiffResult(old_snapshot=old_snapshot, new_snapshot=new_snapshot, hierarchy=hierarchy)
        assert diff.has_changes is True

    def test_get_all_changed_paths(self) -> None:
        """Test getting all changed paths."""
        child_prop = PropertyDiff(
            property_name="Width",
            old_value=Property.from_freecad(5.0, {}, "Base"),
            new_value=Property.from_freecad(15.0, {}, "Base"),
        )
        child = NodeDiff(path="Body/Pad/Sub", type_id="Part::Feature", property_diffs=[child_prop])
        parent_prop = PropertyDiff(
            property_name="Length",
            old_value=Property.from_freecad(10.0, {}, "Base"),
            new_value=Property.from_freecad(20.0, {}, "Base"),
        )
        parent = NodeDiff(path="Body/Pad", type_id="PartDesign::Pad", property_diffs=[parent_prop], children=[child])
        unchanged = NodeDiff(path="Body", type_id="PartDesign::Body")

        hierarchy = DiffHierarchy()
        hierarchy._roots.extend([parent, unchanged])
        old_snapshot = snapshot_from_rows(
            snapshot_id="old-id",
            document_name="OldDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id="new-id",
            document_name="NewDoc",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        diff = DiffResult(old_snapshot=old_snapshot, new_snapshot=new_snapshot, hierarchy=hierarchy)

        changed_paths = diff.get_all_changed_paths()
        assert "Body/Pad/Sub" in changed_paths
        assert "Body/Pad" in changed_paths  # Parent included because child changed
        assert "Body" not in changed_paths  # Unchanged with no changed children


class TestDiffEngineComputeDiff:
    """Tests for DiffEngine.compute_diff() with flat Snapshot structure."""

    def test_compute_diff_with_empty_snapshots(self) -> None:
        """Test compute_diff with empty snapshots returns empty result."""
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.old_snapshot.document_name == "old"
        assert result.new_snapshot.document_name == "new"
        assert result.hierarchy.roots == []
        assert result.has_changes is False

    def test_compute_diff_detect_added_node(self) -> None:
        """Test compute_diff detects added nodes with flat structure."""
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )
        new_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {},
        }
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            tree=[new_node],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.has_changes is True
        # The new node should appear as added
        assert len(result.hierarchy.roots) > 0

    def test_compute_diff_detect_deleted_node(self) -> None:
        """Test compute_diff detects deleted nodes with flat structure."""
        old_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {},
        }
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_node],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.has_changes is True

    def test_compute_diff_detect_modified_node(self) -> None:
        """Test compute_diff detects modified nodes with flat structure."""
        from freecad.history_wb.domain import Property

        old_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {"Length": Property.from_freecad(10.0, {}, "Base")},
        }
        new_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {"Length": Property.from_freecad(20.0, {}, "Base")},
        }
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_node],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            tree=[new_node],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        assert result.has_changes is True
        # Should find the modified property
        node_diff = result.hierarchy.roots[0]
        assert len(node_diff.property_diffs) > 0

    def test_compute_diff_with_nested_flat_nodes(self) -> None:
        """Test compute_diff with flat nested nodes structure."""
        # Old snapshot with parent and child
        old_parent = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {},
        }
        old_child = {
            "id": 2,
            "name": "Pad",
            "type_id": "PartDesign::Pad",
            "label": "Pad",
            "path": "Body/Pad",
            "after": "Body",
            "properties": {},
        }
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_parent, old_child],
        )

        # New snapshot with parent and child (same structure)
        new_parent = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {},
        }
        new_child = {
            "id": 2,
            "name": "Pad",
            "type_id": "PartDesign::Pad",
            "label": "Pad",
            "path": "Body/Pad",
            "after": "Body",
            "properties": {},
        }
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            tree=[new_parent, new_child],
        )

        engine = DiffEngine()
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # No changes expected
        assert result.has_changes is False

    def test_compute_diff_filters_excluded_types(self) -> None:
        """Test compute_diff filters out excluded node types."""
        settings_repo = _MockSettingsRepo(excluded_types=["PartDesign::Body"])

        old_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {},
        }
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_node],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            objects=[],
            occurrences=[],
        )

        engine = DiffEngine(settings_repo=settings_repo)
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # With excluded type, should not report changes
        assert result.has_changes is False


class TestDiffEngineComputeDiffWithNone:
    """Tests for DiffEngine.compute_diff() when old snapshot is None."""

    def test_compute_diff_with_none_old_snapshot(self) -> None:
        """Test compute_diff with None for old snapshot compares against itself."""
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="TestDoc",
            timestamp=datetime.datetime.now(),
            tree=[],
        )

        engine = DiffEngine()
        result = engine.compute_diff(None, new_snapshot)

        # Should use same snapshot for both
        assert result.old_snapshot is new_snapshot
        assert result.new_snapshot is new_snapshot
        assert result.has_changes is False


class TestDiffEngineComputeDiffWithSettings:
    """Tests for DiffEngine.compute_diff() with custom settings."""

    def test_compute_diff_with_custom_excluded_types(self) -> None:
        """Test compute_diff with custom excluded types filters correctly."""
        old_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {},
        }
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_node],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            tree=[],
        )

        # Use mock settings repo to exclude PartDesign::Body
        settings_repo = _MockSettingsRepo(excluded_types=["PartDesign::Body"])

        engine = DiffEngine(settings_repo=settings_repo)
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # With excluded type, should not report changes
        assert result.has_changes is False

    def test_compute_diff_with_custom_excluded_properties(self) -> None:
        """Test compute_diff with custom excluded properties filters correctly."""
        from freecad.history_wb.domain import Property

        old_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {
                "Length": Property.from_freecad(10.0, {}, "Base"),
                "Label": Property.from_freecad("Body", {}, "Base"),
            },
        }
        new_node = {
            "id": 1,
            "name": "Body",
            "type_id": "PartDesign::Body",
            "label": "Body",
            "path": "Body",
            "after": None,
            "properties": {
                "Length": Property.from_freecad(20.0, {}, "Base"),
                "Label": Property.from_freecad("Body", {}, "Base"),
            },
        }

        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_node],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            tree=[new_node],
        )

        # Use mock settings repo to exclude Length property
        settings_repo = _MockSettingsRepo(excluded_properties=["Length"])

        engine = DiffEngine(settings_repo=settings_repo)
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # Only Label property differs (but it's the same value)
        # Length should be excluded from comparison
        assert result.has_changes is False


class TestDiffEngineTypeSpecificExclusions:
    """Tests for DiffEngine with type-specific property exclusions."""

    def test_engine_passes_type_specific_exclusions(self) -> None:
        """Test that engine passes type-specific exclusions from settings repo to comparator."""
        from freecad.history_wb.domain import Property

        old_node = {
            "id": 1,
            "name": "Template",
            "type_id": "TechDraw::DrawSVGTemplate",
            "label": "Template",
            "path": "Template",
            "after": None,
            "properties": {
                "Template": Property.from_freecad("old_data", {}, "Base"),
                "Label": Property.from_freecad("MyTemplate", {}, "Base"),
            },
        }
        new_node = {
            "id": 1,
            "name": "Template",
            "type_id": "TechDraw::DrawSVGTemplate",
            "label": "MyTemplate",
            "path": "Template",
            "after": None,
            "properties": {
                "Template": Property.from_freecad("new_data", {}, "Base"),
                "Label": Property.from_freecad("MyTemplate", {}, "Base"),
            },
        }
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_node],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            tree=[new_node],
        )

        settings_repo = _MockSettingsRepo(excluded_by_type={"TechDraw::DrawSVGTemplate": ["Template"]})

        engine = DiffEngine(settings_repo=settings_repo)
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # Template property should be excluded for this type
        assert result.has_changes is False
        assert result.modified_count == 0

    def test_engine_with_non_matching_type_includes_property(self) -> None:
        """Test that engine does not apply type-specific exclusion for non-matching types."""
        from freecad.history_wb.domain import Property

        old_node = {
            "id": 1,
            "name": "Feature",
            "type_id": "Part::Feature",
            "label": "Feature",
            "path": "Feature",
            "after": None,
            "properties": {
                "Template": Property.from_freecad("data", {}, "Base"),
                "Label": Property.from_freecad("Feature", {}, "Base"),
            },
        }
        new_node = {
            "id": 1,
            "name": "Feature",
            "type_id": "Part::Feature",
            "label": "Feature",
            "path": "Feature",
            "after": None,
            "properties": {
                "Template": Property.from_freecad("different_data", {}, "Base"),
                "Label": Property.from_freecad("Feature", {}, "Base"),
            },
        }
        old_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="old",
            timestamp=datetime.datetime.now(),
            tree=[old_node],
        )
        new_snapshot = snapshot_from_rows(
            snapshot_id=str(uuid.uuid4()),
            document_name="new",
            timestamp=datetime.datetime.now(),
            tree=[new_node],
        )

        settings_repo = _MockSettingsRepo(excluded_by_type={"TechDraw::DrawSVGTemplate": ["Template"]})

        engine = DiffEngine(settings_repo=settings_repo)
        result = engine.compute_diff(old_snapshot, new_snapshot)

        # Template property should NOT be excluded for Part::Feature
        assert result.has_changes is True
        assert result.modified_count == 1
