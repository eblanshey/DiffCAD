# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the SnapshotExtractor class which extracts
# tree structure from FreeCAD documents and converts them to Snapshot domain models.
# It uses Logger port for logging - implementation injected at runtime.
"""Snapshot extraction from FreeCAD documents."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from ..logging import Logger
from ..tree import Property, TreeNode


if TYPE_CHECKING:
    from .models import Snapshot


class FreeCadPort(Protocol):
    """Interface for FreeCAD document operations (defined in domain for type hints).

    This Protocol defines the minimal set of FreeCAD operations needed
    by the Diff Workbench, allowing for test doubles in unit tests.
    """

    def get_active_document(self) -> object | None: ...

    def get_object(self, doc: object, name: str) -> object | None: ...


def _get_expression_for_property(obj: object, prop_name: str) -> str | None:
    """Extract the expression for a specific property from ExpressionEngine.

    FreeCAD stores expressions (e.g., "Pad.Length * 2") in the ExpressionEngine
    property as a list of [property_name, expression_string] pairs. This function
    searches that list for the given property and returns its expression.

    Example ExpressionEngine value:
        [
            ["Length", "Pad.Length * 2"],
            ["Width", "Sketch.X"],
            ["Height", "10 mm"]
        ]

    Args:
        obj: The FreeCAD object (has ExpressionEngine attribute)
        prop_name: The property name to get expression for

    Returns:
        The expression string if found (e.g., "Pad.Length * 2"), None otherwise
    """
    try:
        expr_engine = getattr(obj, "ExpressionEngine", [])
        if isinstance(expr_engine, list):
            for entry in expr_engine:
                if isinstance(entry, (list, tuple)) and len(entry) >= 2 and entry[0] == prop_name:
                    return str(entry[1])
    except Exception:
        pass
    return None


def _extract_property_value(obj: object, prop_name: str) -> Property | None:
    """Extract a single property value from a FreeCAD object.

    Delegates to Property.from_freecad_property() which handles
    type detection based on property names (e.g., "Placement", "Position")
    and value-based inference for unknown properties.

    Args:
        obj: The FreeCAD object
        prop_name: The property name

    Returns:
        A Property if successful, None if the property couldn't be read
    """
    try:
        # TODO: delay instantiating props until later -- might not even be needed until their raw output is
        #    considered different
        value = getattr(obj, prop_name)
        expression = _get_expression_for_property(obj, prop_name)
        return Property.from_freecad_property(prop_name, value, expression=expression)
    except Exception as e:
        logging.warning("Failed to extract property %s: %s", prop_name, e)
        return None


def _add_sub_object_children(
    obj: object,
    sub_objects: tuple[str, ...],
    children: list[TreeNode],
    port: FreeCadPort,
    doc: object,
    parent_path: str,
    name: str,
) -> None:
    """Add child nodes from getSubObjects() results.

    This is needed because FreeCAD containers (like Part, Body) can have
    nested sub-objects that are only discoverable via getSubObjects(), not
    via OutList. For example, a Part container may have OutList=[Body] but
    getSubObjects()=("Body.", "VarSet.") where VarSet is not in OutList.

    Args:
        obj: The parent FreeCAD object
        sub_objects: Tuple of sub-object name strings (e.g., ("Body.", "VarSet."))
        children: Existing children list (from OutList) to append to
        port: The FreeCadPort for object resolution
        doc: The FreeCAD document
        parent_path: The path of the parent node
        name: The name of the parent object
    """
    existing_names = {c.name for c in children}
    for sub_name in sub_objects:
        # Sub-object names like "Body." need resolution - strip trailing dot
        base_name = sub_name.split(".")[0]
        if not base_name or base_name == name:
            continue

        child_obj = port.get_object(doc, base_name)
        if child_obj is None:
            continue

        if base_name in existing_names:
            continue

        child_node = _build_tree_node(child_obj, port, doc, parent_path, is_root=False)
        if child_node is not None:
            children.append(child_node)


def _build_tree_node(
    obj: object,
    port: FreeCadPort,
    doc: object,
    parent_path: str = "",
    is_root: bool = True,
) -> TreeNode | None:  # noqa: C901
    """Build a TreeNode from a FreeCAD object.

    Args:
        obj: The FreeCAD object to convert
        port: The FreeCadPort instance for object resolution
        doc: The FreeCAD document
        parent_path: The path of the parent node (for building full path)
        is_root: Whether this is a root-level object

    Returns:
        A TreeNode for the object with all properties and children.
    """
    # Get basic attributes
    name = getattr(obj, "Name", "")
    type_id = getattr(obj, "TypeId", "")
    label = getattr(obj, "Label", name)

    # Build the full path
    path = f"{parent_path}/{name}" if parent_path else name

    # Extract all properties (no filtering - snapshots capture everything)
    properties: dict[str, Property] = {}
    try:
        properties_list = getattr(obj, "PropertiesList", [])
        for prop_name in properties_list:
            prop_value = _extract_property_value(obj, prop_name)
            if prop_value is not None:
                properties[prop_name] = prop_value
    except Exception:
        # If we can't read properties, continue with empty dict
        pass

    # Build children from OutList (top-level hierarchy)
    # OutList contains child objects referenced by this object.
    # Example: Part.OutList -> [Origin, Body, VarSet]
    #          Body.OutList -> [Pocket, Origin002, Sketch, Pad, Sketch001]
    children: list[TreeNode] = []
    try:
        out_list = getattr(obj, "OutList", [])
        for child_obj in out_list:
            if hasattr(child_obj, "Name"):
                child_node = _build_tree_node(child_obj, port, doc, path, is_root=False)
                if child_node is not None:
                    children.append(child_node)
    except Exception:
        # If OutList traversal fails, try getSubObjects as fallback
        pass

    # Also check getSubObjects for nested sub-objects within containers
    # getSubObjects() returns tuple of sub-object name strings, NOT actual objects.
    # Example: Part.getSubObjects() -> ("Body.", "VarSet.")
    #          Body.getSubObjects() -> ("Sketch.", "Pad.", "Sketch001.")
    # The trailing "." indicates a sub-object reference; we extract the base name
    # and resolve it via the document (e.g., "Body." -> "Body" -> doc.getObject("Body"))
    try:
        sub_objects = getattr(obj, "getSubObjects", lambda: ())()
    except Exception:
        # getSubObjects failed, continue without it
        pass
    else:
        _add_sub_object_children(obj, sub_objects, children, port, doc, path, name)

    return TreeNode(
        name=name,
        type_id=type_id,
        label=label,
        path=path,
        is_root=is_root,
        properties=properties,
        children=children,
    )


class SnapshotExtractor:
    """Extracts tree structure from FreeCAD documents.

    This class extracts the document tree structure from a live
    FreeCAD document and converts it to Snapshot domain models. Uses Logger port
    for logging - implementation injected at runtime.

    Attributes:
        _logger: Logger instance for logging operations
    """

    def __init__(self, logger: Logger):
        """Initialize the extractor with a logger.

        Args:
            logger: Logger implementation to use for logging
        """
        self._logger = logger

    def extract_tree(self, port: FreeCadPort | None = None) -> Snapshot:
        """Extract the document tree structure from the active FreeCAD document.

        This function traverses the active FreeCAD document and converts it into
        a Snapshot domain object containing TreeNode hierarchy.

        Args:
            port: Optional FreeCadPort instance. If None, returns empty snapshot.

        Returns:
            A Snapshot object containing the document tree structure.
            Returns an empty Snapshot if no port provided or extraction fails.
        """
        from .models import Snapshot

        if port is None:
            self._logger.info("No port provided, returning empty snapshot")
            return Snapshot(
                snapshot_id=str(uuid.uuid4()), document_name="NoPort", timestamp=datetime.now(), root_nodes=[]
            )

        doc = port.get_active_document()

        if doc is None:
            # No document open, return empty snapshot
            self._logger.info("No document open, returning empty snapshot")
            return Snapshot(
                snapshot_id=str(uuid.uuid4()), document_name="NoDocument", timestamp=datetime.now(), root_nodes=[]
            )

        document_name = getattr(doc, "Name", "Unnamed")
        root_nodes: list[TreeNode] = []

        try:
            # Get all top-level objects from the document
            objects = getattr(doc, "Objects", [])

            for obj in objects:
                if not hasattr(obj, "Name"):
                    # Skip invalid objects
                    self._logger.warning("Skipping object without Name attribute")
                    continue

                node = _build_tree_node(obj, port, doc, "", is_root=True)
                if node is not None:
                    root_nodes.append(node)

        except Exception as e:
            self._logger.error(f"Error extracting document tree: {e}")

        # Use current time for timestamp
        timestamp = datetime.now()

        return Snapshot(
            snapshot_id=str(uuid.uuid4()), document_name=document_name, timestamp=timestamp, root_nodes=root_nodes
        )
