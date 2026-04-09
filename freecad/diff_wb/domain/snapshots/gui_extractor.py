# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the SnapshotExtractor class which extracts
# tree structure from FreeCAD documents and converts them to Snapshot domain models.
# It uses FreeCAD's GUI-level claimChildren() API to match the FreeCAD tree structure.
# Requires FreeCAD GUI. Raises GuiNotAvailableError if unavailable.
"""Snapshot extraction from FreeCAD documents using GUI-level claimChildren() API."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ...utils import Log
from ..freecad_ports import DocumentLike, FreeCadPort
from ..tree import Property, TreeNode


if TYPE_CHECKING:
    from .models import Snapshot


class GuiNotAvailableError(Exception):
    """Exception raised when FreeCAD GUI is not available.

    This exception is raised by _init_gui_and_get_doc() when:
    - FreeCADGui module cannot be imported
    - setupWithoutGUI() fails
    - getDocument() fails
    """

    pass


# Property type IDs that have no editor (getEditorName() returns "")
# Comprehensive list from FreeCAD source analysis (src/App, src/Mod/*)
# These properties are hidden in FreeCAD's property editor
# Format: Full TypeId as returned by getTypeIdOfProperty()
# All types VERIFIED against FreeCAD source code for getEditorName() implementation
# To add a new type: check FreeCAD source for getEditorName() returning ""
#   Example: Materials::PropertyMaterial::getEditorName() always returns ""
# Note: PropertyQuantity and ALL its subclasses HAVE editors (e.g., Length, Angle, Mass)
NO_EDITOR_PROPERTY_TYPES: frozenset[str] = frozenset(
    {
        # Core App properties without editors (NO getEditorName override)
        # Base classes that lack editors
        "App::PropertyGeometry",  # Abstract base - no override
        "App::PropertyComplexGeoData",  # Inherits from PropertyGeometry - no override
        "App::PropertyLists",  # Base list class - no override
        "App::PropertyMap",  # Verified: Part.Meta - commented out in source
        "Materials::PropertyMaterial",  # ShapeMaterial - no editor (verified in runtime)
        "App::PropertyIntegerSet",  # No getEditorName override
        "App::PropertyPersistentObject",  # No override
        "App::PropertyFile",  # No override (PropertyFileIncluded has one)
        # Link variants without editors (only PropertyLink, PropertyLinkSub, PropertyXLinkSub have them)
        "App::PropertyLinkBase",
        "App::PropertyLinkChild",
        "App::PropertyLinkGlobal",
        "App::PropertyLinkHidden",  # Verified: Body._Body
        "App::PropertyLinkList",
        "App::PropertyLinkListBase",
        "App::PropertyLinkListChild",
        "App::PropertyLinkListGlobal",
        "App::PropertyLinkListHidden",
        "App::PropertyLinkSubChild",
        "App::PropertyLinkSubGlobal",
        "App::PropertyLinkSubHidden",
        "App::PropertyLinkSubList",  # Verified: Sketch.AttachmentSupport
        "App::PropertyLinkSubListChild",
        "App::PropertyLinkSubListGlobal",
        "App::PropertyLinkSubListHidden",
        "App::PropertyXLink",
        "App::PropertyXLinkContainer",
        "App::PropertyXLinkList",
        "App::PropertyXLinkSubHidden",
        # Note: PropertyXLinkSubList HAS an editor (verified in source)
        # Placement/vector lists without editors
        "App::PropertyPlacementLink",
        "App::PropertyPlacementList",
        "App::PropertyVector",
        "App::PropertyVectorList",
        "App::PropertyPosition",
        "App::PropertyDirection",
        "App::PropertyBoolList",
        "App::PropertyColorList",
        "App::PropertyFloatList",
        "App::PropertyStringList",
        # PropertyQuantity subclasses WITHOUT constraints (they inherit editor from PropertyQuantity)
        # But these don't override and PropertyQuantity DOES have an editor
        # So PropertyLength, PropertyAngle, PropertyMass, etc. ALL HAVE EDITORS
        # Only include non-Quantity properties here
        "App::PropertyExpressionEngine",  # Verified: Pad.ExpressionEngine (also has Prop_Hidden bit)
    }
)

# Part module properties without editors
NO_EDITOR_PART_TYPES: frozenset[str] = frozenset(
    {
        "Part::PropertyPartShape",  # Verified: Pad.Shape - inherits from PropertyComplexGeoData
        "Part::PropertyTopoShapeList",  # Inherits from PropertyLists
        "Part::PropertyGeometryList",  # Verified: Sketch.Geometry - inherits from PropertyLists
        "Part::PropertyShapeHistory",  # Inherits from PropertyLists
        "Part::PropertyFilletEdges",  # Inherits from PropertyLists
        "Part::PropertyShapeCache",  # Inherits from Property
    }
)

# TechDraw properties without editors
NO_EDITOR_TECHDRAW_TYPES: frozenset[str] = frozenset(
    {
        "TechDraw::PropertyCenterLineList",  # Verified: View.CenterLines - inherits from PropertyLists
        "TechDraw::PropertyCosmeticEdgeList",  # Verified: View.CosmeticEdges - inherits from PropertyLists
        "TechDraw::PropertyCosmeticVertexList",  # Verified: View.CosmeticVertexes - inherits from PropertyLists
        "TechDraw::PropertyGeomFormatList",  # Verified: View.GeomFormats - inherits from PropertyLists
    }
)

# Mesh properties without editors
NO_EDITOR_MESH_TYPES: frozenset[str] = frozenset(
    {
        "Mesh::PropertyCurvatureList",  # Inherits from PropertyLists
        "Mesh::PropertyNormalList",  # Inherits from PropertyLists
    }
)

# Combined set for efficient lookup
_ALL_NO_EDITOR_TYPES: frozenset[str] = (
    NO_EDITOR_PROPERTY_TYPES | NO_EDITOR_PART_TYPES | NO_EDITOR_TECHDRAW_TYPES | NO_EDITOR_MESH_TYPES
)


def _get_view_provider(obj: Any, gui_doc: Any) -> Any:
    """Get the ViewProvider for a FreeCAD object.

    Args:
        obj: The FreeCAD object
        gui_doc: The GUI document

    Returns:
        The ViewProvider for the object, or None if not available
    """
    if hasattr(obj, "ViewObject"):
        view_obj = obj.ViewObject
        if view_obj is not None:
            return view_obj
    if gui_doc is not None and hasattr(gui_doc, "getViewProvider"):
        return gui_doc.getViewProvider(obj)
    return None


def _get_claimed_children(vp: Any) -> list[str]:
    """Get children claimed by a ViewProvider.

    Args:
        vp: The ViewProvider

    Returns:
        List of child object names
    """
    if not hasattr(vp, "claimChildren"):
        return []
    try:
        claimed = vp.claimChildren()
        if not claimed:
            return []
        result: list[str] = []
        for child in claimed:
            # Handle string names directly (some ViewProviders return string names)
            if isinstance(child, str):
                result.append(child)
            # Handle object references with Name attribute
            elif hasattr(child, "Name"):
                result.append(child.Name)
            # Handle object references with name attribute (lowercase)
            elif hasattr(child, "name"):
                result.append(child.name)
        return result
    except Exception as e:
        Log.exception(f"claimChildren() raised: {e}")
        return []


def _init_gui_and_get_doc(doc: Any) -> Any:
    """Initialize FreeCAD GUI and get the GUI document.

    This function directly imports FreeCADGui in the domain layer. This is a
    deliberate architectural choice:

    - The function `_init_gui_and_get_doc` is isolated and easily patchable
    - Unit tests successfully mock it via `unittest.mock.patch`
    - The pattern follows pragmatic architecture over strict layered separation

    For future improvement, a `GuiPort` protocol could be added to `domain/ports.py`
    and injected into `SnapshotExtractor`, but this adds overhead without significant
    benefit given the current testing approach works well.

    Args:
        doc: The FreeCAD App document

    Returns:
        The GUI document

    Raises:
        GuiNotAvailableError: If FreeCAD GUI is not available
    """
    try:
        import FreeCADGui as Gui
    except Exception as e:  # pylint: disable=broad-exception-caught
        Log.warning(f"FreeCADGui not available: {e}")
        raise GuiNotAvailableError(f"FreeCADGui not available - cannot use claimChildren(): {e}") from e

    if hasattr(Gui, "setupWithoutGUI"):
        try:
            Gui.setupWithoutGUI()
        except Exception as e:
            raise GuiNotAvailableError(f"Failed to setup GUI without display: {e}") from e

    gui_doc = None
    if hasattr(Gui, "getDocument"):
        try:
            doc_name = getattr(doc, "Name", None)
            if doc_name is not None:
                gui_doc = Gui.getDocument(doc_name)
        except Exception as e:
            raise GuiNotAvailableError(f"Failed to get GUI document: {e}") from e

    return gui_doc


def _get_expression_for_property(obj: object, prop_name: str) -> str | None:
    """Get the expression string for a property from ExpressionEngine.

    The ExpressionEngine attribute (when present) is a list of lists like:
        [
            ["Height", "10 mm"]
        ]

    Args:
        obj: The FreeCAD object (has ExpressionEngine attribute)
        prop_name: The property name to get expression for

    Returns:
        The expression string if found (e.g., "Pad.Length * 2"), None otherwise
    """
    expr_engine = getattr(obj, "ExpressionEngine", [])
    if not isinstance(expr_engine, list):
        return None
    for entry in expr_engine:
        if isinstance(entry, (list, tuple)) and len(entry) >= 2 and entry[0] == prop_name:
            return str(entry[1])
    return None


def _get_property_group(obj: object, prop_name: str) -> str:
    """Get the group name for a property.

    FreeCAD properties can belong to different groups (like "Base", "Format", "Data", etc.).
    Empty group strings should map to "Base".

    Args:
        obj: The FreeCAD object
        prop_name: Name of the property

    Returns:
        The group name, or "Base" if empty or not available
    """
    get_group = getattr(obj, "getGroupOfProperty", None)
    if get_group is not None:
        group = get_group(prop_name)
        return group if group else "Base"
    return "Base"


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
        group = _get_property_group(obj, prop_name)
        property_obj = Property.from_freecad_property(prop_name, value, expression=expression, group=group)

        return property_obj
    except Exception as e:
        Log.exception(f"Failed to extract property {prop_name}: {e}")
        return None


def _is_property_hidden(obj: object, prop_name: str) -> tuple[bool, str]:  # noqa: C901
    """Check if a property should be hidden from the property editor.

    This function replicates FreeCAD's property visibility logic to ensure
    our snapshots show the same properties visible in FreeCAD's property editor.

    Properties are hidden based on these checks:

    1. getEditorMode() returns ['Hidden'] - explicit editor mode hiding
    2. getPropertyStatus() contains "Hidden" string or status codes 3/26
       (from src/Gui/PropertyView.cpp line 242-246)
    3. getTypeOfProperty() returns a list containing 'Hidden'
    4. Property type has no editor (getEditorName() returns "")
       - In FreeCAD C++ source (src/Gui/propertyeditor/PropertyModel.cpp line 252-268),
         properties with empty getEditorName() are hidden from the property editor
       - Since getEditorName() is not exposed to Python bindings, we check the
         property TypeId against a comprehensive list of types known to lack editors
       - This list was generated by analyzing all getEditorName() overrides across
         FreeCAD source (src/App, src/Mod/*)

    Note: Empty group does NOT mean hidden - properties with empty group
    are visible and map to "Base" group in FreeCAD's UI.

    Args:
        obj: The FreeCAD object
        prop_name: Name of the property to check

    Returns:
        Tuple of (is_hidden, reason_for_hiding)
    """
    # Check 1: getEditorMode() returns ['Hidden']
    get_editor_mode = getattr(obj, "getEditorMode", None)
    if get_editor_mode is not None:
        try:
            editor_mode = get_editor_mode(prop_name)
            if isinstance(editor_mode, list) and "Hidden" in editor_mode:
                return True, "editor_mode_hidden"
        except Exception as e:
            Log.exception(f"Failed to get editor mode for {prop_name}: {e}")

    # Check 2: getPropertyStatus() contains "Hidden" string or integer 26
    # From FreeCAD source (src/App/PropertyContainerPyImp.cpp line 311-356):
    # getPropertyStatus() returns a Py::List where each set bit in the property's
    # status bitmask is converted to either:
    #   - A string name if the bit has a named entry in statusMap (bits 1-13)
    #     Examples: "Hidden" (bit 3), "Output" (bit 7), "Transient" (bit 4)
    #   - An integer if the bit has no named entry (bits 14-31)
    #     Examples: 23 (PropNoRecompute), 24 (PropReadOnly), 26 (PropHidden), 27 (PropOutput)
    # The function iterates through bits 1-31 and appends to the list if that bit is set.
    # To detect hidden properties, we check for:
    #   - String "Hidden" (bit 3) - runtime status hiding via testStatus(Property::Hidden)
    #   - Integer 26 (PropHidden) - compile-time type flag Prop_Hidden (bit 4) mirrored to bit 26
    # Both are checked by FreeCAD's PropertyView::isPropertyHidden() (src/Gui/PropertyView.cpp:245):
    #   (prop->getType() & App::Prop_Hidden) || prop->testStatus(App::Property::Hidden)
    get_property_status = getattr(obj, "getPropertyStatus", None)
    if get_property_status is not None:
        try:
            status = get_property_status(prop_name)
            if isinstance(status, list) and ("Hidden" in status or 26 in status):
                return True, "prop_hidden_bit"
        except Exception as e:
            Log.exception(f"Failed to get property status for {prop_name}: {e}")

    # Check 3: getTypeOfProperty() returns a list containing 'Hidden'
    get_type_of_property = getattr(obj, "getTypeOfProperty", None)
    if get_type_of_property is not None:
        try:
            prop_types = get_type_of_property(prop_name)
            if isinstance(prop_types, list) and "Hidden" in prop_types:
                return True, "type_hidden"
        except Exception as e:
            Log.exception(f"Failed to get type of property {prop_name}: {e}")

    # Check 4: Property type has no editor (workaround for missing getEditorName())
    # In FreeCAD C++, properties are hidden if getEditorName() returns ""
    # Since this method isn't available in Python, we check the TypeId against
    # NO_EDITOR_PROPERTY_TYPES which contains all property types without editors
    get_type_id = getattr(obj, "getTypeIdOfProperty", None)
    if get_type_id is not None:
        try:
            type_id = get_type_id(prop_name)
            if isinstance(type_id, str) and type_id in _ALL_NO_EDITOR_TYPES:
                return True, f"{type_id.lower()}_no_editor"
        except Exception as e:
            Log.exception(f"Failed to get type ID of property {prop_name}: {e}")

    return False, ""


def _extract_visible_properties(obj: object) -> dict[str, Property]:
    """Extract only visible properties from a FreeCAD object.

    Filters out hidden properties based on editor mode and property group.

    Args:
        obj: The FreeCAD object
        obj_name: Name of the object (for logging)

    Returns:
        Dictionary of property name to property value
    """
    properties: dict[str, Property] = {}
    properties_list = getattr(obj, "PropertiesList", [])

    for prop_name in properties_list:
        is_hidden, skip_reason = _is_property_hidden(obj, prop_name)

        if is_hidden:
            continue

        prop_value = _extract_property_value(obj, prop_name)
        if prop_value is not None:
            properties[prop_name] = prop_value

    return properties


def _build_tree_node(
    obj: object,
    port: FreeCadPort,
    doc: DocumentLike,
    parent_path: str,
    children_map: dict[str, list[str]],
    after: str | None,
    all_nodes: list[TreeNode],
) -> None:
    """Build a TreeNode from a FreeCAD object.

    Uses FreeCAD's GUI-level claimChildren() API to match the visual tree
    structure shown in FreeCAD's tree view. claimChildren() returns only
    direct children, so no recursive exclusion is needed.

    Args:
        obj: The FreeCAD object to convert
        port: The FreeCadPort instance for object resolution
        doc: The FreeCAD document
        parent_path: The path of the parent node (for building full path)
        children_map: Pre-built children map from _build_parent_map().
                     Must be provided - built once in extract_tree() for efficiency.
        after: The name of the preceding sibling, or None if first child/root
        all_nodes: List to collect all nodes (modified in place)
    """
    # Get basic attributes
    name = getattr(obj, "Name", None)
    # Skip objects without Name attribute - they are invalid
    if name is None:
        Log.warning("Skipping object without Name attribute")
        return

    # Get the unique ID from the FreeCAD object
    node_id: int = getattr(obj, "ID", 0)

    type_id = getattr(obj, "TypeId", "")
    label = getattr(obj, "Label", name)

    # Build the full path
    path = f"{parent_path}/{name}" if parent_path else name

    # Extract only visible properties
    properties: dict[str, Property] = {}
    try:
        properties = _extract_visible_properties(obj)
    except Exception as e:
        Log.exception(f"[EXTRACTOR] {name}: error extracting properties: {e}")

    # Create the node with flat structure (no children)
    node = TreeNode(
        id=node_id,
        name=name,
        type_id=type_id,
        label=label,
        path=path,
        after=after,
        properties=properties,
    )
    all_nodes.append(node)

    # Build children TreeNodes from the pre-built children map
    child_names = children_map.get(name, [])
    for i, child_name in enumerate(child_names):
        child_obj = port.get_object(doc, child_name)
        if child_obj is not None:
            # Calculate 'after' for this child (first child has after=None)
            child_after = child_names[i - 1] if i > 0 else None
            _build_tree_node(child_obj, port, doc, path, children_map, child_after, all_nodes)


def _build_parent_to_child_map(doc: DocumentLike, gui_doc: Any) -> dict[str, list[str]]:
    """Build the map from document objects using ViewProvider.claimChildren().

    Args:
        doc: The FreeCAD document
        gui_doc: The GUI document for ViewProvider access

    Returns:
        Dictionary mapping parent name to list of claimed child names
    """
    parent_to_child_map: dict[str, list[str]] = {}

    if gui_doc is not None:
        for obj in doc.Objects:
            if not hasattr(obj, "Name"):
                continue
            vp = _get_view_provider(obj, gui_doc)
            if vp is not None:
                children = _get_claimed_children(vp)
                if children:
                    parent_to_child_map[obj.Name] = children

    return parent_to_child_map


def _build_flat_node_list(
    doc: DocumentLike,
    child_to_parent_map: dict[str, str],
    parent_to_child_map: dict[str, list[str]],
    name_to_obj_map: dict[str, object],
) -> list[TreeNode]:
    """Build the flat node list using BFS.

    Args:
        doc: The FreeCAD document
        child_to_parent_map: Map of child name to parent name
        parent_to_child_map: Map of parent name to list of child names from claimChildren() (O(1) lookup)
        name_to_obj_map: Map of object name to object

    Returns:
        List of TreeNode objects in BFS order
    """
    nodes: list[TreeNode] = []
    queue: list[tuple[object, str, str | None]] = []
    visited: set[str] = set()

    # Find roots (objects not in parent_map) and add to queue
    root_names: list[str] = [name for name in name_to_obj_map if name not in child_to_parent_map]

    # Add roots to queue with their "after" value
    for i, name in enumerate(root_names):
        obj = name_to_obj_map.get(name)
        if obj:
            after = root_names[i - 1] if i > 0 else None
            queue.append((obj, name, after))

    # Process queue (BFS)
    while queue:
        obj, path, after = queue.pop(0)
        obj_name: str | None = getattr(obj, "Name", None)
        # Skip objects without Name attribute - they are invalid
        if obj_name is None or obj_name in visited:
            continue
        visited.add(obj_name)

        # Extract properties
        properties = _extract_visible_properties(obj)

        # Create node
        node = TreeNode(
            id=getattr(obj, "ID", 0),
            name=obj_name,
            type_id=getattr(obj, "TypeId", ""),
            label=getattr(obj, "Label", obj_name),
            path=path,
            after=after,
            properties=properties,
        )
        nodes.append(node)

        # Get children using O(1) lookup from parent_to_child_map
        children_names = parent_to_child_map.get(obj_name, [])
        for i, child_name in enumerate(children_names):
            if child_name not in visited:
                child_obj = name_to_obj_map.get(child_name)
                if child_obj:
                    child_path = f"{path}/{child_name}"
                    child_after = children_names[i - 1] if i > 0 else None
                    queue.append((child_obj, child_path, child_after))

    return nodes


def _extract_tree_single_pass(
    port: FreeCadPort,
    doc: DocumentLike,
    gui_doc: Any,
    document_name: str,
) -> Snapshot:
    """Extract tree using single-pass BFS algorithm.

    This replaces the multi-pass approach with a single BFS pass that builds
    the flat node list directly. FreeCAD's claimChildren() returns only
    direct children, so no recursive exclusion is needed.

    Args:
        port: The FreeCadPort instance
        doc: The FreeCAD document
        gui_doc: The GUI document for ViewProvider access (can be None)
        document_name: Name of the document

    Returns:
        Snapshot containing the flat node list
    """
    from .models import Snapshot

    # Step 1: Build parent_to_child_map (parent -> direct children from claimChildren())
    parent_to_child_map = _build_parent_to_child_map(doc, gui_doc)

    # Step 2: Build child_to_parent_map from parent_to_child_map
    child_to_parent_map: dict[str, str] = {}
    for parent_name, children in parent_to_child_map.items():
        for child_name in children:
            if child_name not in child_to_parent_map:
                child_to_parent_map[child_name] = parent_name
            else:
                Log.warning(
                    f"[DEBUG] Overwriting child '{child_name}' parent: "
                    f"{child_to_parent_map[child_name]} -> {parent_name}"
                )

    # Step 3: Build name to object map for quick lookup
    name_to_obj: dict[str, object] = {}
    for obj in doc.Objects:
        name = getattr(obj, "Name", None)
        if name:
            name_to_obj[name] = obj

    # Step 4: Single BFS pass to build flat node list
    nodes = _build_flat_node_list(doc, child_to_parent_map, parent_to_child_map, name_to_obj)

    return Snapshot(snapshot_id=str(uuid.uuid4()), document_name=document_name, timestamp=datetime.now(), nodes=nodes)


class SnapshotExtractor:
    """Extracts tree structure from FreeCAD documents.

    This class extracts the document tree structure from a live
    FreeCAD document and converts it to Snapshot domain models. Uses the
    unified Log class from utils for logging.
    """

    def __init__(self) -> None:
        """Initialize the extractor."""
        pass

    def extract_tree(self, port: FreeCadPort | None = None) -> Snapshot:
        """Extract the document tree structure from the active FreeCAD document.

        This function traverses the active FreeCAD document and converts it into
        a Snapshot domain object containing TreeNode hierarchy. It uses FreeCAD's
        GUI-level claimChildren() API to match the visual tree structure.

        Args:
            port: Optional FreeCadPort instance. If None, returns empty snapshot.

        Returns:
            A Snapshot object containing the document tree structure.
            Returns an empty Snapshot if no port provided or extraction fails.
        """
        from .models import Snapshot

        if port is None:
            Log.info("No port provided, returning empty snapshot")
            return Snapshot(snapshot_id=str(uuid.uuid4()), document_name="NoPort", timestamp=datetime.now(), nodes=[])

        doc = port.get_active_document()

        if doc is None:
            # No document open, return empty snapshot
            Log.info("No document open, returning empty snapshot")
            return Snapshot(
                snapshot_id=str(uuid.uuid4()), document_name="NoDocument", timestamp=datetime.now(), nodes=[]
            )

        document_name = getattr(doc, "Name", "Unnamed")

        try:
            # Initialize FreeCAD GUI and get GUI document for claimChildren()
            gui_doc = _init_gui_and_get_doc(doc)

            # Use single-pass BFS algorithm for better performance
            return _extract_tree_single_pass(port, doc, gui_doc, document_name)

        except Exception as e:
            Log.exception(f"Error extracting document tree: {e}")

        # Use current time for timestamp
        timestamp = datetime.now()

        return Snapshot(snapshot_id=str(uuid.uuid4()), document_name=document_name, timestamp=timestamp, nodes=[])
