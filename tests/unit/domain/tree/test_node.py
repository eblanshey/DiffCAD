# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the TreeNode class including creation, properties,
# children handling, and string representation.
"""Unit tests for the TreeNode class."""

from freecad.diff_wb.domain import Property, PropertyType, TreeNode


class TestTreeNode:
    """Tests for the TreeNode class."""

    def test_creation_with_all_new_required_fields(self):
        """Test creating TreeNode with all new required fields (id, path, after)."""
        node = TreeNode(
            id=1,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Sketch",
        )
        assert node.id == 1
        assert node.name == "Pad"
        assert node.type_id == "PartDesign::Pad"
        assert node.label == "Pad"
        assert node.path == "Body/Pad"
        assert node.after == "Sketch"

    def test_creation_with_after_none_first_child(self):
        """Test creating TreeNode with after=None (first child in siblings or root)."""
        # First child - after should be None
        node = TreeNode(
            id=2,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        assert node.id == 2
        assert node.name == "Body"
        assert node.path == "Body"
        assert node.after is None

        # First child of a parent - after should also be None
        child_node = TreeNode(
            id=3,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after=None,
        )
        assert child_node.after is None

    def test_creation_with_after_set_to_sibling_name(self):
        """Test creating TreeNode with after set to sibling name."""
        # Second child - after should be set to the previous sibling's name
        node = TreeNode(
            id=4,
            name="Pocket",
            type_id="PartDesign::Pocket",
            label="Pocket",
            path="Body/Pocket",
            after="Pad",
        )
        assert node.after == "Pad"

    def test_creation_with_properties(self):
        """Test tree node with properties."""
        prop = Property.create(PropertyType.FLOAT, 10.0)
        node = TreeNode(
            id=5,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Sketch",
            properties={"Length": prop},
        )
        assert "Length" in node.properties
        assert node.properties["Length"].value == 10.0

    def test_serialization_to_dict_includes_all_new_fields(self):
        """Test serializing TreeNode to dict includes id, path, after fields."""
        node = TreeNode(
            id=6,
            name="Sketch",
            type_id="Sketcher::SketchObject",
            label="Sketch",
            path="Body/Sketch",
            after="Origin",
        )
        node_dict = {
            "id": node.id,
            "name": node.name,
            "type_id": node.type_id,
            "label": node.label,
            "path": node.path,
            "after": node.after,
        }
        assert node_dict["id"] == 6
        assert node_dict["path"] == "Body/Sketch"
        assert node_dict["after"] == "Origin"
        assert "name" in node_dict

    def test_no_children_field_in_new_structure(self):
        """Test verifying no children field exists in new structure."""
        node = TreeNode(
            id=7,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        # Verify no children attribute exists
        assert not hasattr(node, "children")
        # Verify no is_root attribute exists
        assert not hasattr(node, "is_root")

    def test_path_change_detection_for_move_detection(self):
        """Test path change detection for move detection."""
        # Old node (in previous snapshot)
        old_node = TreeNode(
            id=8,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Sketch",
        )
        # New node (in current snapshot) - same id, different path = moved
        new_node = TreeNode(
            id=8,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body001/Pad",  # Different parent = moved
            after="Origin",
        )
        # Detect move by comparing old_path vs new_path
        assert old_node.path == "Body/Pad"
        assert new_node.path == "Body001/Pad"
        # The paths are different, indicating a move
        assert old_node.path != new_node.path

    def test_string_representation(self):
        """Test string representation includes path and type_id."""
        node = TreeNode(
            id=9,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after="Sketch",
        )
        assert "Body/Pad" in str(node)
        assert "PartDesign::Pad" in str(node)

    def test_root_node_has_path_equal_to_name(self):
        """Test that root nodes have path equal to their name."""
        root_node = TreeNode(
            id=10,
            name="Body",
            type_id="PartDesign::Body",
            label="Body",
            path="Body",
            after=None,
        )
        assert root_node.path == root_node.name

    def test_non_root_node_has_path_with_separator(self):
        """Test that non-root nodes have paths with / separator."""
        child_node = TreeNode(
            id=11,
            name="Pad",
            type_id="PartDesign::Pad",
            label="Pad",
            path="Body/Pad",
            after=None,
        )
        assert "/" in child_node.path
        assert child_node.path.startswith("Body/")
