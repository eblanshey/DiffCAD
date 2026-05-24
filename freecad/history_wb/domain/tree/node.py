# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the TreeNode class, which represents
# a node in the FreeCAD document tree structure. It is used by both the snapshot
# and diff domains to represent document objects in a flat structure.
"""Tree node model for document snapshots."""

from dataclasses import dataclass, field

from .property import Property


@dataclass(frozen=True)
class TreeNode:
    """A node in the document tree (flat structure).

    Represents an object or sub-object in a FreeCAD document, with its
    properties. The flat structure uses `path` to derive parent-child
    relationships and `after` to maintain sibling ordering.

    Attributes:
        id: The unique integer identifier for this node
        name: The name of this node (object name or sub-object name)
        type_id: The FreeCAD TypeID of the object (e.g., "PartDesign::Body")
        label: The user-friendly label of the object
        path: The full path to this node (e.g., "Body/Pad"). Root nodes have
            path equal to their name (e.g., "Body").
        after: The name of the preceding sibling, or None if this is the first
            child in its group or a root node
        properties: Mapping of property name to value
    """

    id: int
    name: str
    type_id: str
    label: str
    path: str
    after: str | None = None
    properties: dict[str, Property] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"TreeNode({self.path} [{self.type_id}])"


__all__ = ["TreeNode"]
