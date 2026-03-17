# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the TreeNode class, which represents
# a node in the FreeCAD document tree structure. It is used by both the snapshot
# and diff domains to represent hierarchical document objects.
"""Tree node model for document snapshots."""

from dataclasses import dataclass, field

from .property import Property


@dataclass(frozen=True)
class TreeNode:
    """A node in the document tree.

    Represents an object or sub-object in a FreeCAD document, with its
    properties and children. The tree structure reflects the document's
    hierarchy (objects contain sub-objects via GetSubObjects).

    Attributes:
        name: The name of this node (object name or sub-object name)
        type_id: The FreeCAD TypeID of the object (e.g., "PartDesign::Body")
        label: The user-friendly label of the object
        path: The full path to this node (e.g., "Body/Pad")
        is_root: True if this is a root-level object (not a sub-object)
        properties: Mapping of property name to value
        children: Child nodes (sub-objects)
    """

    name: str
    type_id: str
    label: str
    path: str
    is_root: bool = True
    properties: dict[str, Property] = field(default_factory=dict)
    children: list["TreeNode"] = field(default_factory=list)

    def __str__(self) -> str:
        return f"TreeNode({self.path} [{self.type_id}])"

    def add_child(self, child: "TreeNode") -> None:
        """Add a child node (creates a new tree with the child added)."""
        # Since the dataclass is frozen, we can't modify children directly
        # This method is for documentation; actual tree building happens outside
        raise NotImplementedError("TreeNode is immutable. Build the tree during construction.")


__all__ = ["TreeNode"]
