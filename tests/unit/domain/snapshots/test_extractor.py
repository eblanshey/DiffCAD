# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for SnapshotExtractor using FakeFreeCadPort, including
# tree extraction from documents, nested children (via ViewProvider.claimChildren()),
# property extraction, and expression handling.
"""Unit tests for SnapshotExtractor."""

from unittest.mock import MagicMock, patch

from freecad.diff_wb.domain.snapshots.gui_extractor import (
    GuiNotAvailableError,
    SnapshotExtractor,
    _get_property_group,
    _is_property_hidden,
)
from freecad.diff_wb.domain.snapshots.models import Snapshot


class MockViewProvider:
    """Mock ViewProvider for testing claimChildren() functionality.

    This mimics FreeCAD's GUI-level ViewProvider that provides the
    claimChildren() method to return child objects for tree display.
    """

    def __init__(self, claimed_children=None):
        """Initialize mock ViewProvider.

        Args:
            claimed_children: List of child objects claimed by this ViewProvider
        """
        object.__setattr__(self, "_claimed_children", claimed_children or [])

    def claimChildren(self):
        """Return claimed children."""
        return object.__getattribute__(self, "_claimed_children")


class MockFreeCADObject:
    """Mock FreeCAD object for testing.

    Uses Group + OriginFeatures + InList for hierarchy (matching the simplified
    extractor logic), not OutList which represents dependencies not containment.
    """

    def __init__(
        self,
        name,
        type_id,
        label,
        properties=None,
        group=None,
        origin_features=None,
        in_list=None,
        expression_engine=None,
        property_editor_modes=None,
        property_groups=None,
        property_status=None,
        property_types=None,
    ):
        """Initialize a mock FreeCAD object.

        Args:
            name: Object name
            type_id: FreeCAD type ID
            label: Display label
            properties: List of property names
            group: Child objects in this container's Group
            origin_features: Origin geometry objects
            in_list: Objects that reference this one (for parent detection)
            expression_engine: List of [prop_name, expression] pairs
            property_editor_modes: Dict mapping property name to editor mode list
                e.g., {"HiddenProp": ["Hidden"], "VisibleProp": []}
            property_groups: Dict mapping property name to group name
                e.g., {"Shape": "", "Length": "Side1"}
            property_status: Dict mapping property name to status integer
                e.g., {"SavedGeometry": 4} for Prop_Hidden bit (value 4)
                See FreeCAD's Prop_Hidden constant (value 4)
            property_types: Dict mapping property name to type list from getTypeOfProperty()
                e.g., {"Shape": ["Hidden", "Link"], "Label": ["App::Property"]}
        """
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_type_id", type_id)
        object.__setattr__(self, "_label", label)
        object.__setattr__(self, "_properties", properties or [])
        object.__setattr__(self, "_group", group or [])
        object.__setattr__(self, "_origin_features", origin_features or [])
        object.__setattr__(self, "_in_list", in_list or [])
        object.__setattr__(self, "_expression_engine", expression_engine or [])
        object.__setattr__(self, "_properties_values", {})
        object.__setattr__(self, "_property_editor_modes", property_editor_modes or {})
        object.__setattr__(self, "_property_groups", property_groups or {})
        object.__setattr__(self, "_property_status", property_status or {})
        object.__setattr__(self, "_property_types", property_types or {})
        object.__setattr__(self, "_view_object", None)

    @property
    def Name(self):
        return object.__getattribute__(self, "_name")

    @property
    def TypeId(self):
        return object.__getattribute__(self, "_type_id")

    @property
    def Label(self):
        return object.__getattribute__(self, "_label")

    @property
    def PropertiesList(self):
        return object.__getattribute__(self, "_properties")

    @property
    def Group(self):
        return object.__getattribute__(self, "_group")

    @property
    def OriginFeatures(self):
        return object.__getattribute__(self, "_origin_features")

    @property
    def InList(self):
        return object.__getattribute__(self, "_in_list")

    @property
    def ExpressionEngine(self):
        return object.__getattribute__(self, "_expression_engine")

    def getEditorMode(self, prop_name):
        modes = object.__getattribute__(self, "_property_editor_modes")
        return modes.get(prop_name, [])

    def getGroupOfProperty(self, prop_name):
        groups = object.__getattribute__(self, "_property_groups")
        return groups.get(prop_name, "")

    def getPropertyStatus(self, prop_name):
        """Get property status bits.

        Args:
            prop_name: Name of the property

        Returns:
            List containing status integer, or empty list if not found.
            Prop_Hidden = 4 (bit value for hidden properties like SavedGeometry)
        """
        status_dict = object.__getattribute__(self, "_property_status")
        status_value = status_dict.get(prop_name, None)
        if status_value is not None:
            return [status_value]
        return []

    def getTypeOfProperty(self, prop_name):
        """Get property type from getTypeOfProperty().

        This replicates FreeCAD's getTypeOfProperty() which returns a list
        of strings describing the property type. Some properties like Shape
        and ShapeMaterial return lists containing 'Hidden'.

        Args:
            prop_name: Name of the property

        Returns:
            List of type strings, e.g., ["Hidden", "Link"] or ["App::Property"]
        """
        types_dict = object.__getattribute__(self, "_property_types")
        return types_dict.get(prop_name, [])

    def __getattr__(self, name):
        props = object.__getattribute__(self, "_properties_values")
        if name in props:
            return props[name]
        if name == "Label":
            return object.__getattribute__(self, "_label")
        return None

    @property
    def ViewObject(self):
        """Get the ViewObject (ViewProvider) for this object."""
        return object.__getattribute__(self, "_view_object")

    @ViewObject.setter
    def ViewObject(self, value):
        """Set the ViewObject (ViewProvider) for this object."""
        object.__setattr__(self, "_view_object", value)

    def __setattr__(self, name, value):
        # Handle ViewObject specially to work with the property setter
        if name == "ViewObject":
            object.__setattr__(self, "_view_object", value)
            return
        props = object.__getattribute__(self, "_properties_values")
        props[name] = value


class FakePortAndLogger:
    """Fake implementation combining FreeCadPort and Logger for unit testing."""

    def __init__(self):
        """Initialize the fake port with empty document state."""
        self._documents = {}
        self._messages = []
        self._gui_doc = None

    def get_active_document(self):
        """Get the active document, or None if no document is open."""
        return self._documents.get("active")

    def get_object(self, doc, name):
        """Get a document object by name."""
        if hasattr(doc, "getObject"):
            return doc.getObject(name)
        return None

    def try_recompute_active_document(self):
        """No-op for recompute."""
        pass

    def log(self, text):
        """Log a message."""
        self._messages.append(("log", text))

    def warn(self, text):
        """Show a warning message."""
        self._messages.append(("warn", text))

    def message(self, text):
        """Show an informational message."""
        self._messages.append(("message", text))

    def set_active_document(self, doc):
        """Set the active document for testing."""
        self._documents["active"] = doc

    def set_gui_document(self, gui_doc):
        """Set the GUI document for testing claimChildren() functionality.

        Args:
            gui_doc: Mock GUI document with getViewProvider method
        """
        self._gui_doc = gui_doc

    def get_gui_document(self):
        """Get the GUI document."""
        return self._gui_doc

    def info(self, message):
        """Log an info message."""
        self._messages.append(("info", message))

    def warning(self, message):
        """Log a warning message."""
        self._messages.append(("warning", message))

    def error(self, message):
        """Log an error message."""
        self._messages.append(("error", message))


class TestSnapshotExtractor:
    """Tests for SnapshotExtractor class."""

    def test_extract_tree_with_empty_document(self):
        """Test extraction from an empty document."""
        mock_doc = MagicMock()
        mock_doc.Objects = []
        mock_doc.Name = "EmptyDocument"

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        assert isinstance(result, Snapshot)
        assert result.document_name == "EmptyDocument"
        assert result.root_nodes == []

    def test_extract_tree_with_root_object(self):
        """Test extraction with a single root object."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        root_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label", "Placement"],
        )
        root_obj.Label = "My Body"
        root_obj.Placement = "mock_placement"

        mock_doc.Objects = [root_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        assert isinstance(result, Snapshot)
        assert result.document_name == "TestDoc"
        assert len(result.root_nodes) == 1
        assert result.root_nodes[0].name == "Body"
        assert result.root_nodes[0].type_id == "PartDesign::Body"

    def test_extract_tree_with_nested_children_via_group(self):
        """Test extraction with nested child objects via ViewProvider.claimChildren()."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create child object
        child_obj = MockFreeCADObject(
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="My Sketch",
            properties=["Label"],
        )
        child_obj.Label = "My Sketch"

        # Create parent with ViewProvider claiming the child via claimChildren()
        parent_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        parent_obj.Label = "My Body"
        # Use ViewProvider.claimChildren() instead of Group property
        parent_obj.ViewObject = MockViewProvider(claimed_children=[child_obj])

        # Both objects must be in doc.Objects for hierarchy detection
        mock_doc.Objects = [parent_obj, child_obj]

        # Create mock GUI document for getViewProvider
        mock_gui_doc = MagicMock()

        # Set up getViewProvider to return our ViewProviders
        # Must check obj.ViewObject first (like real _get_view_provider implementation)
        def mock_get_view_provider(obj):
            # First check if object has ViewObject directly set (like real implementation)
            if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
                return obj.ViewObject
            # Fall back to gui_doc.getViewProvider
            if obj.Name == "Body":
                return parent_obj.ViewObject
            elif obj.Name == "Sketch":
                return child_obj.ViewObject
            return None

        mock_gui_doc.getViewProvider = mock_get_view_provider

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        # Set up get_object to resolve child names to actual objects
        def mock_get_object(doc, name):
            if name == "Body":
                return parent_obj
            elif name == "Sketch":
                return child_obj
            return None

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return our mock gui_doc
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = mock_gui_doc
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        parent = result.root_nodes[0]
        assert parent.name == "Body"
        assert len(parent.children) == 1
        assert parent.children[0].name == "Sketch"
        assert parent.children[0].path == "Body/Sketch"

    def test_extract_tree_handles_no_document(self):
        """Test that extract_tree handles no document gracefully."""
        fake_port = FakePortAndLogger()
        # No document set

        extractor = SnapshotExtractor()
        result = extractor.extract_tree(fake_port)

        # Should return a Snapshot with empty root_nodes when no document
        assert isinstance(result, Snapshot)
        assert result.document_name == "NoDocument"
        assert result.root_nodes == []

    def test_extract_tree_property_extraction(self):
        """Test that properties are correctly extracted."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="TestObj",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length"],
            property_groups={"Label": "Base", "Length": "Side1"},
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]
        # Properties should be extracted (with non-empty groups)
        assert "Label" in node.properties
        assert "Length" in node.properties

    def test_extract_tree_captures_expressions(self):
        """Test that expressions are correctly captured from ExpressionEngine."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create object with expression engine
        obj = MockFreeCADObject(
            name="Pocket",
            type_id="PartDesign::Pocket",
            label="Test Pocket",
            properties=["Label", "Length"],
            expression_engine=[["Length", "Sketch.Length * 0.5"]],
            property_groups={"Label": "Base", "Length": "Side1"},
        )
        obj.Label = "Test Pocket"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]
        # Length property should have expression (with non-empty group)
        assert "Length" in node.properties
        length_prop = node.properties["Length"]
        assert length_prop.expression == "Sketch.Length * 0.5"
        assert length_prop.value == 10.0

    def test_extract_tree_discovers_children_via_group(self):
        """Test that ViewProvider.claimChildren() discovers children correctly.

        This tests the scenario where a Part container has Body and VarSet in its
        claimed children. The hierarchy is built from claimChildren(), not OutList.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create VarSet object
        varset_obj = MockFreeCADObject(
            name="VarSet",
            type_id="App::VarSet",
            label="Variable Set",
            properties=["Label"],
        )
        varset_obj.Label = "Variable Set"

        # Create Body object
        body_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        body_obj.Label = "My Body"

        # Create Part container with ViewProvider claiming Body and VarSet
        part_obj = MockFreeCADObject(
            name="Part",
            type_id="App::Part",
            label="My Part",
            properties=["Label"],
        )
        part_obj.Label = "My Part"
        # Use ViewProvider.claimChildren() instead of Group property
        part_obj.ViewObject = MockViewProvider(claimed_children=[body_obj, varset_obj])

        # All objects must be in doc.Objects for hierarchy detection
        mock_doc.Objects = [part_obj, body_obj, varset_obj]

        # Create mock GUI document for getViewProvider
        mock_gui_doc = MagicMock()

        # Set up getViewProvider to return our ViewProviders
        # Must check obj.ViewObject first (like real _get_view_provider implementation)
        def mock_get_view_provider(obj):
            # First check if object has ViewObject directly set (like real implementation)
            if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
                return obj.ViewObject
            # Fall back to gui_doc.getViewProvider
            if obj.Name == "Part":
                return part_obj.ViewObject
            elif obj.Name == "Body":
                return body_obj.ViewObject
            elif obj.Name == "VarSet":
                return varset_obj.ViewObject
            return None

        mock_gui_doc.getViewProvider = mock_get_view_provider

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        # Set up get_object to resolve child names to actual objects
        object_map = {"Part": part_obj, "Body": body_obj, "VarSet": varset_obj}

        def mock_get_object(doc, name):
            return object_map.get(name)

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return our mock gui_doc
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = mock_gui_doc
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        part_node = result.root_nodes[0]
        assert part_node.name == "Part"

        # Should have both Body and VarSet from claimChildren()
        assert len(part_node.children) == 2

        child_names = {child.name for child in part_node.children}
        assert "Body" in child_names
        assert "VarSet" in child_names

        # Verify children paths
        varset_node = next(c for c in part_node.children if c.name == "VarSet")
        assert varset_node.type_id == "App::VarSet"
        assert varset_node.path == "Part/VarSet"

    def test_extract_tree_handles_nested_hierarchy(self):
        """Test nested hierarchy: Part -> Body -> Sketch.

        This verifies that the hierarchy detection correctly builds
        multi-level hierarchies using ViewProvider.claimChildren().
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create leaf Sketch object
        sketch_obj = MockFreeCADObject(
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="My Sketch",
            properties=["Label"],
        )
        sketch_obj.Label = "My Sketch"

        # Create Body with Sketch claimed via ViewProvider
        body_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        body_obj.Label = "My Body"
        body_obj.ViewObject = MockViewProvider(claimed_children=[sketch_obj])

        # Create Part with Body claimed via ViewProvider
        part_obj = MockFreeCADObject(
            name="Part",
            type_id="App::Part",
            label="My Part",
            properties=["Label"],
        )
        part_obj.Label = "My Part"
        part_obj.ViewObject = MockViewProvider(claimed_children=[body_obj])

        # All objects must be in doc.Objects for hierarchy detection
        mock_doc.Objects = [part_obj, body_obj, sketch_obj]

        # Create mock GUI document for getViewProvider
        mock_gui_doc = MagicMock()

        # Set up getViewProvider to return our ViewProviders
        # Must check obj.ViewObject first (like real _get_view_provider implementation)
        def mock_get_view_provider(obj):
            # First check if object has ViewObject directly set (like real implementation)
            if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
                return obj.ViewObject
            # Fall back to gui_doc.getViewProvider
            if obj.Name == "Part":
                return part_obj.ViewObject
            elif obj.Name == "Body":
                return body_obj.ViewObject
            elif obj.Name == "Sketch":
                return sketch_obj.ViewObject
            return None

        mock_gui_doc.getViewProvider = mock_get_view_provider

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        # Set up get_object to resolve child names to actual objects
        object_map = {"Part": part_obj, "Body": body_obj, "Sketch": sketch_obj}

        def mock_get_object(doc, name):
            return object_map.get(name)

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return our mock gui_doc
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = mock_gui_doc
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        part_node = result.root_nodes[0]
        assert part_node.name == "Part"

        # Part should have Body as child
        assert len(part_node.children) == 1
        body_node = part_node.children[0]
        assert body_node.name == "Body"
        assert body_node.path == "Part/Body"

        # Verify recursive exclusion: Sketch should NOT be in Part's direct children
        # (it should only be in Body's children, not directly under Part)
        part_child_names = {child.name for child in part_node.children}
        assert "Sketch" not in part_child_names, (
            "Sketch should not be in Part's direct children (recursive exclusion failed)"
        )

        # Body should have Sketch as child
        assert len(body_node.children) == 1
        sketch_node = body_node.children[0]
        assert sketch_node.name == "Sketch"
        assert sketch_node.path == "Part/Body/Sketch"

    def test_extract_tree_handles_origin_features(self):
        """Test that ViewProvider.claimChildren() correctly identifies origin children.

        App::Origin containers store their geometry (axes, planes, points) and
        claim them via ViewProvider.claimChildren() instead of OriginFeatures.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create origin geometry objects
        x_axis_obj = MockFreeCADObject(
            name="X_Axis",
            type_id="App::Line",
            label="X_Axis",
            properties=["Label"],
        )
        x_axis_obj.Label = "X_Axis"

        xy_plane_obj = MockFreeCADObject(
            name="XY_Plane",
            type_id="App::Plane",
            label="XY_Plane",
            properties=["Label"],
        )
        xy_plane_obj.Label = "XY_Plane"

        # Create Origin container with ViewProvider claiming the geometry
        origin_obj = MockFreeCADObject(
            name="Origin",
            type_id="App::Origin",
            label="Origin",
            properties=["Label"],
        )
        origin_obj.Label = "Origin"
        # Use ViewProvider.claimChildren() instead of OriginFeatures property
        origin_obj.ViewObject = MockViewProvider(claimed_children=[x_axis_obj, xy_plane_obj])

        # All objects must be in doc.Objects
        mock_doc.Objects = [origin_obj, x_axis_obj, xy_plane_obj]

        # Create mock GUI document for getViewProvider
        mock_gui_doc = MagicMock()

        # Set up getViewProvider to return our ViewProviders
        # Must check obj.ViewObject first (like real _get_view_provider implementation)
        def mock_get_view_provider(obj):
            # First check if object has ViewObject directly set (like real implementation)
            if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
                return obj.ViewObject
            # Fall back to gui_doc.getViewProvider
            if obj.Name == "Origin":
                return origin_obj.ViewObject
            elif obj.Name == "X_Axis":
                return x_axis_obj.ViewObject
            elif obj.Name == "XY_Plane":
                return xy_plane_obj.ViewObject
            return None

        mock_gui_doc.getViewProvider = mock_get_view_provider

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        # Set up get_object to resolve child names to actual objects
        object_map = {"Origin": origin_obj, "X_Axis": x_axis_obj, "XY_Plane": xy_plane_obj}

        def mock_get_object(doc, name):
            return object_map.get(name)

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return our mock gui_doc
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = mock_gui_doc
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        origin_node = result.root_nodes[0]
        assert origin_node.name == "Origin"

        # Origin should have X_Axis and XY_Plane as children
        assert len(origin_node.children) == 2
        child_names = {child.name for child in origin_node.children}
        assert "X_Axis" in child_names
        assert "XY_Plane" in child_names

    def test_extract_tree_filters_hidden_properties_by_editor_mode(self):
        """Test that properties with ['Hidden'] editor mode are filtered out."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create object with some hidden and visible properties
        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "BaseFeature", "ExpressionEngine", "Visibility"],
            # Editor modes: some hidden, some visible
            property_editor_modes={
                "BaseFeature": ["Hidden"],
                "ExpressionEngine": ["Hidden"],
                "Visibility": ["Hidden"],
                "Label": [],
                "Length": [],
            },
            # All properties have non-empty groups
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "BaseFeature": "Base",
                "ExpressionEngine": "Base",
                "Visibility": "Base",
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # Visible properties should be present
        assert "Label" in node.properties
        assert "Length" in node.properties

        # Hidden properties should be filtered out
        assert "BaseFeature" not in node.properties
        assert "ExpressionEngine" not in node.properties
        assert "Visibility" not in node.properties

    def test_extract_tree_properties_with_empty_group_are_visible(self):
        """Test that properties with empty group ARE visible.

        Properties with getGroupOfProperty() returning empty string ARE visible
        in FreeCAD's property editor - they map to "Base" group. The old behavior
        of treating empty group as hidden was incorrect.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "Shape", "SuppressedShape", "AddSubShape", "ShapeMaterial"],
            # Property groups: empty groups ARE visible (map to "Base")
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Shape": "",  # Empty group = visible (maps to Base)
                "SuppressedShape": "",  # Empty group = visible
                "AddSubShape": "",  # Empty group = visible
                "ShapeMaterial": "",  # Empty group = visible
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0
        obj.Shape = "shape_data"
        obj.SuppressedShape = "suppressed"
        obj.AddSubShape = "subshape"
        obj.ShapeMaterial = "material"

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # All properties should be present (including those with empty groups)
        assert "Label" in node.properties
        assert "Length" in node.properties
        assert "Shape" in node.properties
        assert "SuppressedShape" in node.properties
        assert "AddSubShape" in node.properties
        assert "ShapeMaterial" in node.properties

    def test_extract_tree_filters_combined_hidden_conditions(self):
        """Test filtering with both editor mode and property status conditions."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "Shape", "Visibility", "Placement", "_ElementMapVersion"],
            property_editor_modes={
                "Visibility": ["Hidden"],
                "Placement": ["ReadOnly", "Hidden"],
                "_ElementMapVersion": ["Hidden"],
            },
            # Empty group is now visible - Shape should be visible
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Shape": "",  # Empty group = visible (maps to Base)
                "Visibility": "Base",
                "Placement": "Base",
                "_ElementMapVersion": "Base",
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # Visible: Label, Length, Shape (empty group is visible now)
        # Hidden: Visibility, Placement, _ElementMapVersion (hidden by editor mode)
        assert "Label" in node.properties
        assert "Length" in node.properties
        assert "Shape" in node.properties, "Shape with empty group should be visible"
        assert "Visibility" not in node.properties
        assert "Placement" not in node.properties
        assert "_ElementMapVersion" not in node.properties
        assert len(node.properties) == 3

    def test_extract_tree_includes_properties_with_non_empty_group(self):
        """Test that properties with non-empty groups are included."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "Type", "TaperAngle", "Refine"],
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Type": "Side1",
                "TaperAngle": "Side1",
                "Refine": "Part Design",
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0
        obj.Type = "Length"
        obj.TaperAngle = 0.0
        obj.Refine = False

        mock_doc.Objects = [obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        node = result.root_nodes[0]

        # All properties with non-empty groups should be present
        assert "Label" in node.properties
        assert "Length" in node.properties
        assert "Type" in node.properties
        assert "TaperAngle" in node.properties
        assert "Refine" in node.properties

    def test_extract_tree_viewprovider_returns_string_names(self):
        """Test when ViewProvider.claimChildren() returns string names.

        Some FreeCAD ViewProviders return string names instead of object
        references from claimChildren(). This test verifies that the extractor
        handles both cases correctly.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create child object
        child_obj = MockFreeCADObject(
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="My Sketch",
            properties=["Label"],
        )
        child_obj.Label = "My Sketch"

        # Create parent with ViewProvider returning STRING names instead of objects
        parent_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        parent_obj.Label = "My Body"
        # Return string names instead of object references
        parent_obj.ViewObject = MockViewProvider(claimed_children=["Sketch"])

        mock_doc.Objects = [parent_obj, child_obj]

        # Create mock GUI document
        mock_gui_doc = MagicMock()

        # Must check obj.ViewObject first (like real _get_view_provider implementation)
        def mock_get_view_provider(obj):
            # First check if object has ViewObject directly set (like real implementation)
            if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
                return obj.ViewObject
            # Fall back to gui_doc.getViewProvider
            if obj.Name == "Body":
                return parent_obj.ViewObject
            elif obj.Name == "Sketch":
                return child_obj.ViewObject
            return None

        mock_gui_doc.getViewProvider = mock_get_view_provider

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        def mock_get_object(doc, name):
            if name == "Body":
                return parent_obj
            elif name == "Sketch":
                return child_obj
            return None

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()

        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = mock_gui_doc
            result = extractor.extract_tree(fake_port)

        assert len(result.root_nodes) == 1
        parent = result.root_nodes[0]
        assert parent.name == "Body"
        assert len(parent.children) == 1
        assert parent.children[0].name == "Sketch"

    def test_extract_tree_handles_gui_unavailable(self):
        """Test exception when FreeCADGui is not available.

        When FreeCADGui is not available (e.g., headless environment without
        display), claimChildren() cannot be used. The extractor should raise
        GuiNotAvailableError to make the failure explicit instead of silently
        returning an empty tree.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create objects that would have ViewProviders
        parent_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        parent_obj.Label = "My Body"
        parent_obj.ViewObject = MockViewProvider(claimed_children=[])

        child_obj = MockFreeCADObject(
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="My Sketch",
            properties=["Label"],
        )
        child_obj.Label = "My Sketch"

        mock_doc.Objects = [parent_obj, child_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to raise GuiNotAvailableError
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.side_effect = GuiNotAvailableError("FreeCADGui not available")
            # Should raise the exception
            result = extractor.extract_tree(fake_port)

        # The extractor catches exceptions internally and returns an empty snapshot
        # This is the expected behavior - the exception should be logged
        assert result.document_name == "TestDoc"

    def test_extract_tree_handles_claimchildren_exception(self):
        """Test that exceptions in claimChildren() are handled gracefully.

        Some ViewProviders may throw exceptions when claimChildren() is called.
        The extractor should catch these exceptions and continue processing.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create a ViewProvider that throws an exception
        class FailingViewProvider:
            def claimChildren(self):
                raise RuntimeError("ViewProvider claimChildren failed")

        parent_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        parent_obj.Label = "My Body"
        parent_obj.ViewObject = FailingViewProvider()

        mock_doc.Objects = [parent_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        # Create mock GUI doc
        mock_gui_doc = MagicMock()
        mock_gui_doc.getViewProvider = lambda obj: parent_obj.ViewObject

        extractor = SnapshotExtractor()

        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = mock_gui_doc
            # Should not raise, should handle exception gracefully
            result = extractor.extract_tree(fake_port)

        # Should still return the object even though claimChildren() failed
        assert len(result.root_nodes) == 1
        assert result.root_nodes[0].name == "Body"

    def test_extract_tree_handles_circular_claims(self):
        """Test that circular claims (A claims B, B claims A) don't cause infinite loops.

        This is an edge case where object A claims object B as a child, and
        object B claims object A as a child. The extractor should handle this
        without infinite recursion. When A claims B and B claims A, both become
        children of each other, so neither can be a root (this is expected behavior).
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create object A that claims B
        obj_a = MockFreeCADObject(
            name="ObjectA",
            type_id="App::DocumentObject",
            label="Object A",
            properties=["Label"],
        )
        obj_a.Label = "Object A"

        # Create object B that claims A (circular!)
        obj_b = MockFreeCADObject(
            name="ObjectB",
            type_id="App::DocumentObject",
            label="Object B",
            properties=["Label"],
        )
        obj_b.Label = "Object B"

        # A claims B, B claims A - circular reference
        obj_a.ViewObject = MockViewProvider(claimed_children=[obj_b])
        obj_b.ViewObject = MockViewProvider(claimed_children=[obj_a])

        mock_doc.Objects = [obj_a, obj_b]

        # Create mock GUI document
        mock_gui_doc = MagicMock()

        # Must check obj.ViewObject first (like real _get_view_provider implementation)
        def mock_get_view_provider(obj):
            # First check if object has ViewObject directly set (like real implementation)
            if hasattr(obj, "ViewObject") and obj.ViewObject is not None:
                return obj.ViewObject
            # Fall back to gui_doc.getViewProvider
            if obj.Name == "ObjectA":
                return obj_a.ViewObject
            elif obj.Name == "ObjectB":
                return obj_b.ViewObject
            return None

        mock_gui_doc.getViewProvider = mock_get_view_provider

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        object_map = {"ObjectA": obj_a, "ObjectB": obj_b}

        def mock_get_object(doc, name):
            return object_map.get(name)

        fake_port.get_object = mock_get_object

        extractor = SnapshotExtractor()

        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = mock_gui_doc
            # Should not hang or cause infinite recursion - this is the key test
            result = extractor.extract_tree(fake_port)

        # Should complete without hanging (no recursion error)
        # With circular claims, both objects become children of each other,
        # so neither can be a root - this is expected behavior
        # The important thing is it doesn't cause infinite recursion
        assert result.document_name == "TestDoc"
        # The test passes if we get here without RecursionError

    def test_extract_tree_filters_objects_without_name(self):
        """Test that objects without Name attribute are filtered out.

        Invalid FreeCAD objects (e.g., some internal objects) may not have
        a Name attribute. These should be skipped during extraction.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create a valid object
        valid_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        valid_obj.Label = "My Body"

        # Create an object without Name attribute
        class ObjectWithoutName:
            TypeId = "App::Feature"
            Label = "Invalid Object"
            PropertiesList = []

            def getEditorMode(self, prop_name):
                return []

            def getGroupOfProperty(self, prop_name):
                return "Base"

            def __getattr__(self, name):
                return None

        invalid_obj = ObjectWithoutName()

        mock_doc.Objects = [valid_obj, invalid_obj]

        fake_port = FakePortAndLogger()
        fake_port.set_active_document(mock_doc)

        extractor = SnapshotExtractor()

        # Patch _init_gui_and_get_doc to return None (GUI unavailable)
        with patch("freecad.diff_wb.domain.snapshots.gui_extractor._init_gui_and_get_doc") as mock_init_gui:
            mock_init_gui.return_value = None
            result = extractor.extract_tree(fake_port)

        # Only the valid object should be in the result
        assert len(result.root_nodes) == 1
        assert result.root_nodes[0].name == "Body"

    def test_build_effective_children_map_order_independent(self):
        """Test that _build_effective_children_map is order-independent.

        This tests the order-dependent bug fix where processing children in
        different orders would produce different results. For example, with:
            claim_map = {"Part": ["Sketch", "Body"], "Body": ["Sketch"]}

        Before the fix, if "Sketch" appeared before "Body" in the list, the
        algorithm would incorrectly include "Sketch" because it was processed
        before "Body" (so Body's descendants weren't in the exclusion set yet).

        After the fix, the two-pass algorithm correctly identifies that Sketch
        should be excluded because it's claimed by Body, regardless of order.
        """
        from freecad.diff_wb.domain.snapshots.gui_extractor import (
            _build_effective_children_map,
        )

        # Test case from the bug report: Sketch appears BEFORE Body
        # Bug: incorrectly includes Sketch because Body hasn't been processed yet
        claim_map = {"Part": ["Sketch", "Body"], "Body": ["Sketch"]}
        result = _build_effective_children_map(claim_map)

        # Correct result: only Body should be Part's child
        # (Sketch is excluded because it's claimed by Body)
        assert result["Part"] == ["Body"], (
            f"Expected ['Body'], got {result['Part']}. Sketch should be excluded because it's claimed by Body."
        )

        # Test with reversed order - should produce same result
        claim_map_reversed = {"Part": ["Body", "Sketch"], "Body": ["Sketch"]}
        result_reversed = _build_effective_children_map(claim_map_reversed)

        # Same result regardless of order
        assert result_reversed["Part"] == ["Body"]
        assert result["Part"] == result_reversed["Part"], "Order should not affect the result"

        # Test a more complex case: Part -> [A, B, C], B -> [D], C -> [D, E]
        # A, B, C are all children of Part. D is a descendant of B, E is a
        # descendant of C. All three (A, B, C) should remain as direct children
        # because they themselves are not descendants of each other.
        # The descendants (D, E) would be excluded from being direct children
        # of Part, but B and C remain as direct children.
        complex_map = {
            "Part": ["A", "B", "C"],
            "B": ["D"],
            "C": ["D", "E"],
        }
        complex_result = _build_effective_children_map(complex_map)

        # A, B, C should all remain as direct children (they're not descendants
        # of each other). D and E are grandchildren, not direct children.
        assert complex_result["Part"] == ["A", "B", "C"], (
            f"Expected ['A', 'B', 'C'], got {complex_result['Part']}. A, B, C should remain as direct children."
        )


class TestIsPropertyHidden:
    """Tests for hidden property detection logic."""

    def test_hidden_property_detection_savedgeometry_has_prop_hidden_bit(self):
        """Test that SavedGeometry is detected as hidden via Prop_Hidden bit.

        SavedGeometry has Prop_Hidden bit set (value 4), which should be detected
        by checking getPropertyStatus().
        """

        # Create object with SavedGeometry having Prop_Hidden bit (value 4)
        obj = MockFreeCADObject(
            name="TestObj",
            type_id="App::DocumentObject",
            label="Test",
            properties=["Label", "SavedGeometry", "Placement"],
            property_status={
                "SavedGeometry": 4,  # Prop_Hidden = 4
            },
            # SavedGeometry has empty group in real FreeCAD (maps to "Base")
            property_groups={
                "Label": "Base",
                "SavedGeometry": "",
                "Placement": "Base",
            },
        )
        obj.Label = "Test"
        obj.SavedGeometry = "geometry_data"
        obj.Placement = "placement"

        # SavedGeometry should be hidden due to Prop_Hidden bit
        is_hidden, reason = _is_property_hidden(obj, "SavedGeometry")
        assert is_hidden, "SavedGeometry should be hidden (has Prop_Hidden bit)"
        assert "prop_hidden_bit" in reason, f"Reason should mention prop_hidden_bit, got: {reason}"

    def test_hidden_property_detection_label_is_visible(self):
        """Test that Label is visible (no Prop_Hidden bit, no Hidden editor mode)."""

        obj = MockFreeCADObject(
            name="TestObj",
            type_id="App::DocumentObject",
            label="Test",
            properties=["Label", "Placement"],
            property_groups={
                "Label": "Base",
                "Placement": "Base",
            },
        )
        obj.Label = "Test"

        # Label should be visible
        is_hidden, reason = _is_property_hidden(obj, "Label")
        assert not is_hidden, "Label should be visible (no Prop_Hidden bit)"
        assert reason == "", f"Reason should be empty for visible property, got: {reason}"

    def test_hidden_property_detection_editor_mode_hidden(self):
        """Test that properties with getEditorMode=["Hidden"] are hidden."""

        obj = MockFreeCADObject(
            name="TestObj",
            type_id="App::DocumentObject",
            label="Test",
            properties=["Label", "Visibility", "Placement"],
            property_editor_modes={
                "Visibility": ["Hidden"],
            },
            property_groups={
                "Label": "Base",
                "Visibility": "Base",
                "Placement": "Base",
            },
        )
        obj.Label = "Test"
        obj.Visibility = True

        # Visibility with ["Hidden"] editor mode should be hidden
        is_hidden, reason = _is_property_hidden(obj, "Visibility")
        assert is_hidden, "Visibility should be hidden (editor mode = Hidden)"
        assert "editor_mode" in reason.lower(), f"Reason should mention editor_mode, got: {reason}"

        # Label should still be visible
        is_hidden_label, _ = _is_property_hidden(obj, "Label")
        assert not is_hidden_label, "Label should be visible"

    def test_hidden_property_detection_empty_group_is_visible(self):
        """Test that properties with empty group are VISIBLE (not hidden).

        This is the BUG FIX: Properties with empty getGroupOfProperty() should
        be visible (they map to "Base" group in FreeCAD's UI). The old logic
        incorrectly treated empty group as hidden.
        """

        # Properties with empty group (like Shape in Part::Feature)
        obj = MockFreeCADObject(
            name="TestObj",
            type_id="Part::Feature",
            label="Test",
            properties=["Label", "Shape", "Placement"],
            # Empty group - should be VISIBLE (maps to "Base")
            property_groups={
                "Label": "Base",
                "Shape": "",  # Empty group should be visible, not hidden!
                "Placement": "Base",
            },
        )
        obj.Label = "Test"
        obj.Shape = "shape_data"

        # Shape with empty group should be VISIBLE (this is the fix!)
        is_hidden, reason = _is_property_hidden(obj, "Shape")
        assert not is_hidden, "Shape with empty group should be VISIBLE (maps to Base)"
        assert reason == "", f"Reason should be empty for visible property, got: {reason}"

    def test_hidden_property_detection_combined_conditions(self):
        """Test detection when both editor mode and property status are checked."""

        # Object with both hidden by editor mode and hidden by Prop_Hidden bit
        obj = MockFreeCADObject(
            name="TestObj",
            type_id="App::DocumentObject",
            label="Test",
            properties=["Label", "SavedGeometry", "Visibility", "Placement", "Shape"],
            property_editor_modes={
                "Visibility": ["Hidden"],
            },
            property_status={
                "SavedGeometry": 4,  # Prop_Hidden
            },
            property_groups={
                "Label": "Base",
                "SavedGeometry": "",
                "Visibility": "Base",
                "Placement": "Base",
                "Shape": "",  # Empty but no Prop_Hidden - should be visible
            },
        )
        obj.Label = "Test"

        # Label: visible
        is_hidden, reason = _is_property_hidden(obj, "Label")
        assert not is_hidden, "Label should be visible"

        # SavedGeometry: hidden by Prop_Hidden bit
        is_hidden, reason = _is_property_hidden(obj, "SavedGeometry")
        assert is_hidden, "SavedGeometry should be hidden (Prop_Hidden bit)"

        # Visibility: hidden by editor mode
        is_hidden, reason = _is_property_hidden(obj, "Visibility")
        assert is_hidden, "Visibility should be hidden (editor mode)"

        # Shape: empty group but no Prop_Hidden - should be VISIBLE
        is_hidden, reason = _is_property_hidden(obj, "Shape")
        assert not is_hidden, "Shape with empty group but no Prop_Hidden should be visible"

    def test_hidden_property_detection_prop_hidden_bit_value(self):
        """Test that Prop_Hidden bit (value 4) is correctly detected.

        FreeCAD's Prop_Hidden constant has value 4. Properties with this bit
        set in their status should be hidden.
        """

        # Test with Prop_Hidden bit set (value 4)
        obj = MockFreeCADObject(
            name="TestObj",
            type_id="App::DocumentObject",
            label="Test",
            properties=["Label", "HiddenProp", "VisibleProp"],
            property_status={
                "HiddenProp": 4,  # Prop_Hidden = 4
                "VisibleProp": 0,  # No bits set
            },
            property_groups={
                "Label": "Base",
                "HiddenProp": "Base",
                "VisibleProp": "Base",
            },
        )

        # Property with status=4 should be hidden
        is_hidden, reason = _is_property_hidden(obj, "HiddenProp")
        assert is_hidden, "Property with status=4 (Prop_Hidden) should be hidden"

        # Property with status=0 should be visible
        is_hidden, reason = _is_property_hidden(obj, "VisibleProp")
        assert not is_hidden, "Property with status=0 should be visible"

    def test_hidden_property_detection_no_getpropertystatus(self):
        """Test behavior when getPropertyStatus is not available."""

        # Create a minimal mock object without getPropertyStatus method
        class MinimalMockObject:
            """Minimal mock object without getPropertyStatus."""

            def __init__(self):
                self._properties = ["Label"]

            @property
            def PropertiesList(self):
                return self._properties

            def getEditorMode(self, prop_name):
                return []

        obj = MinimalMockObject()

        # Should handle gracefully and not crash
        is_hidden, reason = _is_property_hidden(obj, "Label")
        assert not is_hidden, "Label should be visible when getPropertyStatus is not available"

    def test_hidden_property_detection_mixed_status_list(self):
        """Test detection with mixed list containing both strings and integers.

        FreeCAD can return a mixed list like ["Hidden", 27] or just [27].
        The function should handle both cases.
        """
        from freecad.diff_wb.domain.snapshots.gui_extractor import _is_property_hidden

        # Update mock to return lists with mixed content
        class MockObjectWithMixedStatus:
            """Mock object returning mixed status lists."""

            def __init__(self):
                self._properties = ["Label", "HiddenByString", "HiddenByBit", "Visible"]

            @property
            def PropertiesList(self):
                return self._properties

            def getEditorMode(self, prop_name):
                return []

            def getGroupOfProperty(self, prop_name):
                return "Base"

            def getPropertyStatus(self, prop_name):
                # FreeCAD can return mixed lists like ["Hidden", 27]
                status_map = {
                    "HiddenByString": ["Hidden", 27],
                    "HiddenByBit": [28],  # 28 = 16 + 8 + 4 (Prop_Hidden is 4)
                    "Visible": [0],
                }
                return status_map.get(prop_name, [])

        obj = MockObjectWithMixedStatus()

        # HiddenByString: should be hidden due to string "Hidden"
        is_hidden, reason = _is_property_hidden(obj, "HiddenByString")
        assert is_hidden, "Property with 'Hidden' string in status should be hidden"

        # HiddenByBit: should be hidden due to Prop_Hidden bit (value 4)
        is_hidden, reason = _is_property_hidden(obj, "HiddenByBit")
        assert is_hidden, "Property with Prop_Hidden bit should be hidden"

        # Visible: should be visible
        is_hidden, reason = _is_property_hidden(obj, "Visible")
        assert not is_hidden, "Property with no hidden bits should be visible"

    def test_hidden_property_detection_gettypeofproperty_returns_hidden(self):
        """Test that properties with getTypeOfProperty returning ['Hidden'] are detected as hidden.

        This replicates FreeCAD's PropertyView::isPropertyHidden() logic from
        src/Gui/PropertyView.cpp line 242-246:
        - Checks if prop->getType() & App::Prop_Hidden is true
        - Maps to getTypeOfProperty() returning a list containing 'Hidden'
        """
        from freecad.diff_wb.domain.snapshots.gui_extractor import _is_property_hidden

        # Create object where Shape has "Hidden" in its getTypeOfProperty result
        obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="Test Body",
            properties=["Label", "Placement", "Shape", "ShapeMaterial"],
            property_groups={
                "Label": "Base",
                "Placement": "Base",
                "Shape": "",
                "ShapeMaterial": "",
            },
            # getTypeOfProperty returns lists with 'Hidden' for Shape and ShapeMaterial
            property_types={
                "Label": ["App::Property"],
                "Placement": ["App::Property"],
                "Shape": ["Hidden", "Link"],
                "ShapeMaterial": ["Hidden"],
            },
        )
        obj.Label = "Test Body"

        # Shape should be hidden due to "Hidden" in getTypeOfProperty result
        is_hidden, reason = _is_property_hidden(obj, "Shape")
        assert is_hidden, "Shape should be hidden (getTypeOfProperty returns 'Hidden')"
        assert reason == "type_hidden", f"Reason should be 'type_hidden', got: {reason}"

        # ShapeMaterial should also be hidden
        is_hidden, reason = _is_property_hidden(obj, "ShapeMaterial")
        assert is_hidden, "ShapeMaterial should be hidden (getTypeOfProperty returns 'Hidden')"
        assert reason == "type_hidden"

        # Label and Placement should still be visible
        is_hidden, reason = _is_property_hidden(obj, "Label")
        assert not is_hidden, "Label should be visible"
        is_hidden, reason = _is_property_hidden(obj, "Placement")
        assert not is_hidden, "Placement should be visible"

    def test_hidden_property_detection_gettypeofproperty_filters_in_extraction(self):
        """Test that properties with Hidden in getTypeOfProperty are filtered out during extraction."""
        from freecad.diff_wb.domain.snapshots.gui_extractor import _extract_visible_properties

        # Create object mimicking a PartDesign::Body with Shape and ShapeMaterial
        obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label", "Length", "Shape", "ShapeMaterial", "Result"],
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Shape": "",
                "ShapeMaterial": "",
                "Result": "",
            },
            # getTypeOfProperty returns 'Hidden' for Shape and ShapeMaterial
            property_types={
                "Label": ["App::Property"],
                "Length": ["App::Property"],
                "Shape": ["Hidden", "Link"],
                "ShapeMaterial": ["Hidden"],
                "Result": ["Hidden", "Link"],
            },
        )
        obj.Label = "My Body"
        obj.Length = 10.0
        obj.Shape = "shape_data"
        obj.ShapeMaterial = "material_data"
        obj.Result = "result_data"

        # Extract visible properties
        properties = _extract_visible_properties(obj, "Body")

        # Visible properties should be present
        assert "Label" in properties, "Label should be extracted"
        assert "Length" in properties, "Length should be extracted"

        # Hidden properties (via getTypeOfProperty) should be filtered out
        assert "Shape" not in properties, "Shape should be filtered (type_hidden)"
        assert "ShapeMaterial" not in properties, "ShapeMaterial should be filtered (type_hidden)"
        assert "Result" not in properties, "Result should be filtered (type_hidden)"

        # Verify we got exactly 2 visible properties
        assert len(properties) == 2, f"Expected 2 visible properties, got {len(properties)}"


class TestGetPropertyGroup:
    """Tests for property group extraction."""

    def test_property_group_returns_correct_group_name(self):
        """Test that properties return the correct group name from getGroupOfProperty."""

        obj = MockFreeCADObject(
            name="TestObj",
            type_id="App::DocumentObject",
            label="Test",
            properties=["Label", "Placement", "Shape", "Length"],
            property_groups={
                "Label": "Base",
                "Placement": "Base",
                "Shape": "Input",
                "Length": "Side1",
            },
        )

        # Test various property groups
        group_label = _get_property_group(obj, "Label")
        assert group_label == "Base", f"Expected 'Base', got '{group_label}'"

        group_placement = _get_property_group(obj, "Placement")
        assert group_placement == "Base", f"Expected 'Base', got '{group_placement}'"

        group_shape = _get_property_group(obj, "Shape")
        assert group_shape == "Input", f"Expected 'Input', got '{group_shape}'"

        group_length = _get_property_group(obj, "Length")
        assert group_length == "Side1", f"Expected 'Side1', got '{group_length}'"

    def test_empty_group_returns_base(self):
        """Test that empty group strings return 'Base'.

        FreeCAD properties with no explicit group have getGroupOfProperty()
        returning an empty string. These should map to "Base" group in our
        property viewer.
        """

        obj = MockFreeCADObject(
            name="TestObj",
            type_id="Part::Feature",
            label="Test",
            properties=["Label", "Shape", "Placement", "MapPath"],
            property_groups={
                "Label": "Base",
                "Shape": "",  # Empty group should map to "Base"
                "Placement": "Base",
                "MapPath": "",  # Empty group should map to "Base"
            },
        )

        # Empty group should return "Base"
        group_shape = _get_property_group(obj, "Shape")
        assert group_shape == "Base", f"Empty group should map to 'Base', got '{group_shape}'"

        group_mappath = _get_property_group(obj, "MapPath")
        assert group_mappath == "Base", f"Empty group should map to 'Base', got '{group_mappath}'"

        # Non-empty group should return as-is
        group_label = _get_property_group(obj, "Label")
        assert group_label == "Base", f"Expected 'Base', got '{group_label}'"

    def test_property_group_no_method_returns_base(self):
        """Test that objects without getGroupOfProperty return 'Base'."""

        # Object without getGroupOfProperty method
        class NoGroupMethod:
            pass

        obj = NoGroupMethod()
        group = _get_property_group(obj, "AnyProperty")
        assert group == "Base", f"Expected 'Base' for objects without getGroupOfProperty, got '{group}'"

    def test_property_group_in_extracted_properties(self):
        """Test that extracted properties include the group field."""
        from freecad.diff_wb.domain.snapshots.gui_extractor import _extract_visible_properties

        obj = MockFreeCADObject(
            name="Pad",
            type_id="PartDesign::Pad",
            label="Test Pad",
            properties=["Label", "Length", "Type", "Shape"],
            property_groups={
                "Label": "Base",
                "Length": "Side1",
                "Type": "Side1",
                "Shape": "",  # Empty group -> "Base"
            },
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0
        obj.Type = "Length"
        obj.Shape = "shape_data"

        # Extract visible properties
        properties = _extract_visible_properties(obj, "Pad")

        # Verify groups are correctly extracted
        assert properties["Label"].group == "Base", f"Expected 'Base', got '{properties['Label'].group}'"
        assert properties["Length"].group == "Side1", f"Expected 'Side1', got '{properties['Length'].group}'"
        assert properties["Type"].group == "Side1", f"Expected 'Side1', got '{properties['Type'].group}'"
        assert properties["Shape"].group == "Base", (
            f"Empty group should map to 'Base', got '{properties['Shape'].group}'"
        )
