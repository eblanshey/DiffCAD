# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for SnapshotQuery with FakeFreeCadPort."""

from unittest.mock import MagicMock, patch

from freecad.diff_wb.domain.snapshot import Snapshot
from freecad.diff_wb.snapshot.snapshot_query import extract_tree


class MockFreeCADObject:
    """Mock FreeCAD object for testing."""

    def __init__(self, name, type_id, label, properties=None, children=None, sub_objects=None, expression_engine=None):
        """Initialize a mock FreeCAD object.

        Args:
            name: Object name
            type_id: FreeCAD type ID
            label: Display label
            properties: List of property names
            children: Child objects (for OutList)
            sub_objects: Sub-object names (for getSubObjects)
            expression_engine: List of [prop_name, expression] pairs
        """
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_type_id", type_id)
        object.__setattr__(self, "_label", label)
        object.__setattr__(self, "_properties", properties or [])
        object.__setattr__(self, "_children", children or [])
        object.__setattr__(self, "_sub_objects", sub_objects or ())
        object.__setattr__(self, "_expression_engine", expression_engine or [])
        object.__setattr__(self, "_properties_values", {})

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
    def OutList(self):
        return object.__getattribute__(self, "_children")

    @property
    def ExpressionEngine(self):
        return object.__getattribute__(self, "_expression_engine")

    def getSubObjects(self):
        return object.__getattribute__(self, "_sub_objects")

    def getObject(self, name):
        for child in object.__getattribute__(self, "_children"):
            if child.Name == name:
                return child
        return None

    def __getattr__(self, name):
        # Return stored property values or default
        props = object.__getattribute__(self, "_properties_values")
        if name in props:
            return props[name]
        # Default values based on property name
        if name == "Label":
            return object.__getattribute__(self, "_label")
        return None

    def __setattr__(self, name, value):
        # Store property values
        props = object.__getattribute__(self, "_properties_values")
        props[name] = value


class FakeFreeCadPort:
    """Fake implementation of FreeCadPort for unit testing."""

    def __init__(self):
        """Initialize the fake port with empty document state."""
        self._documents = {}
        self._messages = []

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

    def try_update_gui(self):
        """No-op for GUI update."""
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


class TestSnapshotQuery:
    """Tests for extract_tree function."""

    def test_extract_tree_with_empty_document(self):
        """Test extraction from an empty document."""
        mock_doc = MagicMock()
        mock_doc.Objects = []
        mock_doc.Name = "EmptyDocument"

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

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

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

            assert isinstance(result, Snapshot)
            assert result.document_name == "TestDoc"
            assert len(result.root_nodes) == 1
            assert result.root_nodes[0].name == "Body"
            assert result.root_nodes[0].type_id == "PartDesign::Body"

    def test_extract_tree_with_nested_children(self):
        """Test extraction with nested child objects via OutList."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create parent object with children
        child_obj = MockFreeCADObject(
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="My Sketch",
            properties=["Label"],
        )
        child_obj.Label = "My Sketch"

        parent_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
            children=[child_obj],
        )
        parent_obj.Label = "My Body"

        mock_doc.Objects = [parent_obj]

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

            assert len(result.root_nodes) == 1
            parent = result.root_nodes[0]
            assert parent.name == "Body"
            assert len(parent.children) == 1
            assert parent.children[0].name == "Sketch"
            assert parent.children[0].path == "Body/Sketch"

    def test_extract_tree_handles_no_document(self):
        """Test that extract_tree handles no document gracefully."""
        fake_port = FakeFreeCadPort()
        # No document set

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = None

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

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
        )
        obj.Label = "Test Pad"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

            assert len(result.root_nodes) == 1
            node = result.root_nodes[0]
            # Properties should be extracted (may include Label, Length)
            assert "Label" in node.properties or "Length" in node.properties

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
        )
        obj.Label = "Test Pocket"
        obj.Length = 10.0

        mock_doc.Objects = [obj]

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

            assert len(result.root_nodes) == 1
            node = result.root_nodes[0]
            # Length property should have expression
            assert "Length" in node.properties
            length_prop = node.properties["Length"]
            assert length_prop.expression == "Sketch.Length * 0.5"
            assert length_prop.value == 10.0

    def test_extract_tree_discovers_sub_objects_via_getSubObjects(self):
        """Test that getSubObjects() fallback discovers children not in OutList.

        This tests the scenario where a container object (like Part) has:
        - OutList = [Body] (direct child references)
        - getSubObjects() = ("Body.", "VarSet.") (all sub-objects)

        The VarSet is only discoverable via getSubObjects(), not OutList.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create VarSet object (only discoverable via getSubObjects)
        varset_obj = MockFreeCADObject(
            name="VarSet",
            type_id="App::VarSet",
            label="Variable Set",
            properties=["Label"],
        )
        varset_obj.Label = "Variable Set"

        # Create Body object (in both OutList and getSubObjects)
        body_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        body_obj.Label = "My Body"

        # Create Part container with OutList=[Body] but getSubObjects=("Body.", "VarSet.")
        part_obj = MockFreeCADObject(
            name="Part",
            type_id="App::Part",
            label="My Part",
            properties=["Label"],
            children=[body_obj],  # OutList only has Body
            sub_objects=("Body.", "VarSet."),  # getSubObjects has both
        )
        part_obj.Label = "My Part"

        # Only Part is a root-level object; Body and VarSet are discovered via
        # OutList and getSubObjects respectively
        mock_doc.Objects = [part_obj]

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        # Configure get_object to return the correct objects
        def mock_get_object(doc, name):
            if name == "Body":
                return body_obj
            elif name == "VarSet":
                return varset_obj
            return None

        fake_port.get_object = mock_get_object

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

            assert len(result.root_nodes) == 1
            part_node = result.root_nodes[0]
            assert part_node.name == "Part"

            # Should have both Body (from OutList) and VarSet (from getSubObjects)
            assert len(part_node.children) == 2

            child_names = {child.name for child in part_node.children}
            assert "Body" in child_names
            assert "VarSet" in child_names

            # Verify VarSet was discovered via getSubObjects fallback
            varset_node = next(c for c in part_node.children if c.name == "VarSet")
            assert varset_node.type_id == "App::VarSet"
            assert varset_node.path == "Part/VarSet"

    def test_extract_tree_avoids_duplicates_from_outlist_and_subobjects(self):
        """Test that objects in both OutList and getSubObjects are not duplicated.

        When an object appears in both OutList and getSubObjects(), it should
        only appear once in the children list.
        """
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"

        # Create Body object
        body_obj = MockFreeCADObject(
            name="Body",
            type_id="PartDesign::Body",
            label="My Body",
            properties=["Label"],
        )
        body_obj.Label = "My Body"

        # Create Part container where Body is in BOTH OutList and getSubObjects
        part_obj = MockFreeCADObject(
            name="Part",
            type_id="App::Part",
            label="My Part",
            properties=["Label"],
            children=[body_obj],  # OutList has Body
            sub_objects=("Body.",),  # getSubObjects also has Body
        )
        part_obj.Label = "My Part"

        # Only Part is a root-level object; Body is discovered via OutList
        mock_doc.Objects = [part_obj]

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        def mock_get_object(doc, name):
            if name == "Body":
                return body_obj
            return None

        fake_port.get_object = mock_get_object

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            result = extract_tree(mock_ctx)

            assert len(result.root_nodes) == 1
            part_node = result.root_nodes[0]

            # Body should appear only once, not twice
            assert len(part_node.children) == 1
            assert part_node.children[0].name == "Body"
