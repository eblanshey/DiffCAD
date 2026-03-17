# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the TreeNode class including creation, properties,
# children handling, and string representation.
"""Unit tests for the TreeNode class."""

from freecad.diff_wb.domain import Property, PropertyType, TreeNode


class TestTreeNode:
    """Tests for the TreeNode class."""

    def test_creation(self):
        """Test tree node creation."""
        node = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", is_root=False)
        assert node.name == "Pad"
        assert node.path == "Body/Pad"
        assert node.is_root is False

    def test_creation_with_properties(self):
        """Test tree node with properties."""
        prop = Property.create(PropertyType.FLOAT, 10.0)
        node = TreeNode(
            name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", properties={"Length": prop}
        )
        assert "Length" in node.properties
        assert node.properties["Length"].value == 10.0

    def test_creation_with_children(self):
        """Test tree node with children."""
        child = TreeNode(name="Sub", type_id="Part::Feature", label="Sub", path="Body/Pad/Sub")
        node = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad", children=[child])
        assert len(node.children) == 1
        assert node.children[0].name == "Sub"

    def test_string_representation(self):
        """Test string representation."""
        node = TreeNode(name="Pad", type_id="PartDesign::Pad", label="Pad", path="Body/Pad")
        assert "Body/Pad" in str(node)
        assert "PartDesign::Pad" in str(node)
