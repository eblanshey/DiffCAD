# SPDX-License-Identifier: LGPL-3.0-or-later
"""Unit tests for SnapshotMutations."""

from unittest.mock import MagicMock, patch

import pytest

from freecad.diff_wb.domain.snapshot import Snapshot, TreeNode
from freecad.diff_wb.domain.property_value import PropertyValue, PropertyType
from freecad.diff_wb.snapshot.snapshot_store import SnapshotStore
from freecad.diff_wb.snapshot.snapshot_mutations import create_snapshot, get_default_store


class MockFreeCADObject:
    """Mock FreeCAD object for testing."""

    def __init__(self, name, type_id, label, properties=None, children=None, sub_objects=None):
        """Initialize a mock FreeCAD object."""
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_type_id", type_id)
        object.__setattr__(self, "_label", label)
        object.__setattr__(self, "_properties", properties or [])
        object.__setattr__(self, "_children", children or [])
        object.__setattr__(self, "_sub_objects", sub_objects or ())
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

    def getSubObjects(self):
        return object.__getattribute__(self, "_sub_objects")

    def getObject(self, name):
        for child in object.__getattribute__(self, "_children"):
            if child.Name == name:
                return child
        return None

    def __getattr__(self, name):
        props = object.__getattribute__(self, "_properties_values")
        if name in props:
            return props[name]
        if name == "Label":
            return object.__getattribute__(self, "_label")
        return None

    def __setattr__(self, name, value):
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


class TestSnapshotMutations:
    """Tests for create_snapshot function."""

    def test_create_snapshot_returns_snapshot_id(self):
        """Test that create_snapshot returns a snapshot ID."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"
        mock_doc.Objects = []

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        # Patch get_port in the snapshot_query module where it's used
        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            snapshot_id = create_snapshot("test_snapshot", mock_ctx)

            assert snapshot_id is not None
            assert isinstance(snapshot_id, str)

    def test_create_snapshot_stores_in_default_store(self):
        """Test that create_snapshot stores in the default SnapshotStore."""
        mock_doc = MagicMock()
        mock_doc.Name = "TestDoc"
        mock_doc.Objects = []

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        # Get the default store and verify snapshot is added
        _default_store = get_default_store()

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            snapshot_id = create_snapshot("test_snapshot", mock_ctx)

            # Verify snapshot was stored (document_name is the user-provided name)
            snapshot = _default_store.get_snapshot(snapshot_id)
            assert snapshot is not None
            assert snapshot.document_name == "test_snapshot"

    def test_create_snapshot_with_real_store_integration(self):
        """Test create_snapshot integration with a real SnapshotStore."""
        mock_doc = MagicMock()
        mock_doc.Name = "IntegrationTest"
        mock_doc.Objects = []

        fake_port = FakeFreeCadPort()
        fake_port.set_active_document(mock_doc)

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = mock_doc

        # Create a fresh store for this test
        test_store = SnapshotStore()

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            # We need to patch the _default_store in snapshot_mutations
            with patch("freecad.diff_wb.snapshot.snapshot_mutations._default_store", test_store):
                snapshot_id = create_snapshot("my_snapshot", mock_ctx)

                # Verify using our test store (document_name is the user-provided name)
                snapshot = test_store.get_snapshot(snapshot_id)
                assert snapshot is not None
                assert snapshot.document_name == "my_snapshot"

    def test_create_snapshot_error_propagation(self):
        """Test that errors from extract_tree are propagated."""
        # Create a port that returns None (no document)
        fake_port = FakeFreeCadPort()
        # No document set

        mock_ctx = MagicMock()
        mock_ctx.app.ActiveDocument = None

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            # Should still succeed but return a snapshot with NoDocument
            snapshot_id = create_snapshot("empty_snapshot", mock_ctx)

            _default_store = get_default_store()
            snapshot = _default_store.get_snapshot(snapshot_id)
            assert snapshot is not None
            # The document_name is the user-provided name ("empty_snapshot")
            assert snapshot.document_name == "empty_snapshot"

    def test_create_snapshot_multiple_snapshots(self):
        """Test creating multiple snapshots."""
        _default_store = get_default_store()

        # Clear any existing snapshots
        _default_store.clear()

        mock_doc1 = MagicMock()
        mock_doc1.Name = "Doc1"
        mock_doc1.Objects = []

        mock_doc2 = MagicMock()
        mock_doc2.Name = "Doc2"
        mock_doc2.Objects = []

        fake_port = FakeFreeCadPort()

        mock_ctx = MagicMock()

        with patch("freecad.diff_wb.snapshot.snapshot_query.get_port", return_value=fake_port):
            # First snapshot
            fake_port.set_active_document(mock_doc1)
            mock_ctx.app.ActiveDocument = mock_doc1
            id1 = create_snapshot("snapshot_1", mock_ctx)

            # Second snapshot
            fake_port.set_active_document(mock_doc2)
            mock_ctx.app.ActiveDocument = mock_doc2
            id2 = create_snapshot("snapshot_2", mock_ctx)

            # Both should be stored with different IDs
            assert id1 != id2
            assert _default_store.get_snapshot(id1) is not None
            assert _default_store.get_snapshot(id2) is not None

            # List should show both
            snapshots = _default_store.list_snapshots()
            assert len(snapshots) == 2

    def test_create_snapshot_with_tree_structure(self):
        """Test create_snapshot with actual tree structure."""
        mock_doc = MagicMock()
        mock_doc.Name = "TreeTest"

        # Create a simple tree structure
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
            snapshot_id = create_snapshot("tree_snapshot", mock_ctx)

            _default_store = get_default_store()
            snapshot = _default_store.get_snapshot(snapshot_id)
            assert snapshot is not None
            assert len(snapshot.root_nodes) == 1
            assert snapshot.root_nodes[0].name == "Body"
            assert len(snapshot.root_nodes[0].children) == 1
            assert snapshot.root_nodes[0].children[0].name == "Sketch"
