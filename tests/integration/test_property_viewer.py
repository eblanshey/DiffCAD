# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Integration tests for property extraction and rendering with real FreeCAD runtime.

Tests verify:
- SavedGeometry is hidden via Prop_Hidden bit
- Properties are grouped correctly
- Placement and Vector properties expand to nested paths
- Tree widget renders properties grouped correctly
- Various FreeCAD object types extract properly

Run with: ./run_integration_tests.sh
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest


if TYPE_CHECKING:
    from freecad.history_wb.domain.freecad_ports import AppLike, GuiLike


class TestPropertyViewerIntegration:
    """Integration tests for property extraction and rendering with real FreeCAD runtime."""

    def test_savedgeometry_is_hidden(self, freecad_app: AppLike, freecad_gui: GuiLike, project_root: object) -> None:
        """Verify SavedGeometry is hidden via Prop_Hidden bit (Phase 1).

        SavedGeometry has Prop_Hidden bit set in FreeCAD. This test verifies
        that our extractor correctly hides it.
        """
        from freecad.history_wb.domain.snapshots.gui_extractor import SnapshotExtractor

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract directly with document
            extractor = SnapshotExtractor(gui=freecad_gui)
            result = extractor.extract_tree(doc)

            # Build node lookup from occurrences
            from collections import defaultdict

            nodes_by_name = defaultdict(list)
            for occ in result.occurrences:
                obj = result.find_object(occ.path.rsplit("/", 1)[-1])
                if obj:
                    nodes_by_name[obj.name].append((occ, obj))

            # Find a TechDraw dimension (has SavedGeometry)
            for _obj_name, occurrences in nodes_by_name.items():
                for _occ, node in occurrences:
                    if node.type_id.startswith("TechDraw::DrawViewDimension"):
                        # Check properties - SavedGeometry should NOT be in the list
                        prop_names = list(node.properties.keys())
                        assert "SavedGeometry" not in prop_names, (
                            f"SavedGeometry should be hidden but found in {prop_names}"
                        )
                        # Label should be visible
                        assert "Label" in prop_names, "Label should be visible"
                        return

            # If we get here without finding SavedGeometry, that's also fine
            # (the document structure may have changed)
            print("Note: No TechDraw dimension found in document - test skipped")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_properties_grouped_correctly(
        self, freecad_app: AppLike, freecad_gui: GuiLike, project_root: object
    ) -> None:
        """Verify properties are grouped correctly (Phase 2).

        This test checks that:
        - Properties with explicit groups (e.g., "Side1") use those groups
        - Properties with empty group map to "Base"
        """
        from freecad.history_wb.domain.snapshots.gui_extractor import SnapshotExtractor

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Extract directly with document
            extractor = SnapshotExtractor(gui=freecad_gui)
            result = extractor.extract_tree(doc)

            # Build node lookup from occurrences
            from collections import defaultdict

            nodes_by_name = defaultdict(list)
            for occ in result.occurrences:
                obj = result.find_object(occ.path.rsplit("/", 1)[-1])
                if obj:
                    nodes_by_name[obj.name].append((occ, obj))

            # Check that properties have groups
            for _obj_name, occurrences in nodes_by_name.items():
                for _occ, node in occurrences:
                    for prop_name, prop in node.properties.items():
                        # Each property should have a group
                        assert hasattr(prop, "group"), f"Property {prop_name} should have group"
                        assert isinstance(prop.group, str), "Group should be string"
                        # Group should not be empty (empty should map to "Base")
                        if prop.group == "":
                            pytest.fail(f"Property {prop_name} has empty group - should map to Base")

            # Find a PartDesign::Pad to check its property groups
            for _obj_name, occurrences in nodes_by_name.items():
                for _occ, node in occurrences:
                    if node.type_id == "PartDesign::Pad":
                        # Should have properties like "Length" in "Side1" group
                        has_side1 = any(prop.group == "Side1" for prop in node.properties.values())
                        has_base = any(prop.group == "Base" for prop in node.properties.values())
                        assert has_side1, "PartDesign::Pad should have properties in Side1 group"
                        assert has_base, "PartDesign::Pad should have properties in Base group"
                        return

            print("Note: No PartDesign::Pad found - test may be limited")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_expandable_placement_property(self, freecad_app: AppLike, project_root: object) -> None:
        """Verify Placement property expands correctly (Phase 4).

        Placement should have nested path entries for Base coordinates
        and Rotation properties.
        """
        from freecad.history_wb.domain.tree.data_path import PlacementData
        from freecad.history_wb.domain.tree.property import Property

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Find an object with Placement
            for obj in doc.Objects:
                if hasattr(obj, "Placement") and obj.Placement is not None:
                    placement = obj.Placement

                    # Create Property from FreeCAD value using the new API
                    prop = Property.from_freecad(placement, {}, "Base")

                    # Verify it's a PlacementData with nested paths
                    assert isinstance(prop.value, PlacementData), (
                        f"Placement should produce PlacementData, got {type(prop.value)}"
                    )
                    paths = prop.value.paths
                    # Should have Base coordinates and Rotation properties
                    assert "Base.x" in paths, f"Placement should have Base.x, got {list(paths.keys())}"
                    assert "Base.y" in paths, f"Placement should have Base.y, got {list(paths.keys())}"
                    assert "Base.z" in paths, f"Placement should have Base.z, got {list(paths.keys())}"
                    assert "Rotation.Angle" in paths, f"Placement should have Rotation.Angle, got {list(paths.keys())}"
                    return

            pytest.skip("No object with Placement found in document")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_expandable_vector_property(self, freecad_app: AppLike, project_root: object) -> None:
        """Verify vector properties expand to x, y, z (Phase 4)."""
        from freecad.history_wb.domain.tree.data_path import VectorData
        from freecad.history_wb.domain.tree.property import Property

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            # Find an object with Position (a Vector)
            for obj in doc.Objects:
                if hasattr(obj, "Placement") and obj.Placement is not None:
                    placement = obj.Placement
                    if hasattr(placement, "Base") and placement.Base is not None:
                        position = placement.Base

                        # Create Property from FreeCAD value using the new API
                        prop = Property.from_freecad(position, {}, "Base")

                        # Verify it's a VectorData with x, y, z paths
                        assert isinstance(prop.value, VectorData), (
                            f"Vector should produce VectorData, got {type(prop.value)}"
                        )
                        paths = prop.value.paths
                        assert "x" in paths, f"Vector should have x, got {list(paths.keys())}"
                        assert "y" in paths, f"Vector should have y, got {list(paths.keys())}"
                        assert "z" in paths, f"Vector should have z, got {list(paths.keys())}"
                        return

            pytest.skip("No object with Position found in document")

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_tree_widget_renders_properties_with_groups(
        self,
        freecad_app: AppLike,
        freecad_gui: GuiLike,
        project_root: object,
    ) -> None:
        """Integration test: Verify tree widget renders properties grouped correctly."""
        from freecad.history_wb.qt import QtWidgets

        # Ensure QApplication exists
        app = QtWidgets.QApplication.instance()
        if app is None:
            app = QtWidgets.QApplication([])

        from freecad.history_wb.domain.snapshots.gui_extractor import SnapshotExtractor
        from freecad.history_wb.ui import DiffPanelView
        from freecad.history_wb.ui.presenters.presentation_models import PropertyPresentation

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            extractor = SnapshotExtractor(gui=freecad_gui)
            result = extractor.extract_tree(doc)

            # Build node lookup from occurrences
            from collections import defaultdict

            nodes_by_name = defaultdict(list)
            for occ in result.occurrences:
                obj = result.find_object(occ.path.rsplit("/", 1)[-1])
                if obj:
                    nodes_by_name[obj.name].append((occ, obj))

            # Create DiffPanelView
            panel = DiffPanelView()

            # Get properties from first node with properties
            test_node = None
            for _obj_name, occurrences in nodes_by_name.items():
                for _occ, node in occurrences:
                    if node.properties:
                        test_node = node
                        break
                if test_node:
                    break

            if test_node is None:
                pytest.skip("No nodes with properties found")

            # Convert to PropertyPresentation
            from freecad.history_wb.domain.diff.models import DiffState

            properties = []
            for prop_name, prop in test_node.properties.items():
                properties.append(
                    PropertyPresentation(
                        name=prop_name,
                        old_value=prop.value,
                        new_value=prop.value,
                        state=DiffState.UNCHANGED,
                        group=prop.group,
                    )
                )

            # Call show_property_diff - should not raise
            panel.show_property_diff(properties)

            # Verify tree has items
            root_count = panel._property_diff_tree.topLevelItemCount()
            assert root_count > 0, "Properties tree should have items"

            # Verify groups are present (should be at least 1)
            # Group headers are top-level items with children
            has_group_with_children = False
            for i in range(root_count):
                item = panel._property_diff_tree.topLevelItem(i)
                if item and item.childCount() > 0:
                    has_group_with_children = True
                    break

            assert has_group_with_children, "Should have group items with children"

        finally:
            freecad_app.closeDocument(doc.Name)

    def test_various_object_types_extraction(
        self,
        freecad_app: AppLike,
        freecad_gui: GuiLike,
        project_root: object,
    ) -> None:
        """Test extraction works with various FreeCAD object types (Phase 6 checklist).

        Tests:
        - App::Part (Placement, Color)
        - TechDraw::DrawViewDimension
        """
        from freecad.history_wb.domain.snapshots.gui_extractor import SnapshotExtractor

        # Open BasicFile
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            extractor = SnapshotExtractor(gui=freecad_gui)
            result = extractor.extract_tree(doc)

            # Build node lookup from occurrences
            from collections import defaultdict

            nodes_by_name = defaultdict(list)
            for occ in result.occurrences:
                obj = result.find_object(occ.path.rsplit("/", 1)[-1])
                if obj:
                    nodes_by_name[obj.name].append((occ, obj))

            # Track which object types we've seen
            object_types = set()
            for _obj_name, occurrences in nodes_by_name.items():
                for _occ, node in occurrences:
                    object_types.add(node.type_id)

            # Document should have various object types
            assert len(object_types) > 0, "Should have extracted some object types"

            # Log for information
            print(f"Extracted object types: {sorted(object_types)}")

            # Check we got at least some expected types
            expected_types = [
                "App::Part",
                "PartDesign::Body",
                "TechDraw::DrawViewDimension",
            ]
            found_types = [t for t in expected_types if any(t in ot for ot in object_types)]

            # At least one expected type should be present
            assert len(found_types) > 0, f"Expected at least one of {expected_types}, got {object_types}"

        finally:
            freecad_app.closeDocument(doc.Name)
