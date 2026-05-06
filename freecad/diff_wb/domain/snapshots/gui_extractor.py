# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains the SnapshotExtractor class which extracts
# tree structure from FreeCAD documents and converts them to Snapshot domain models.
# It uses FreeCAD's GUI-level claimChildren() API to match the FreeCAD tree structure.
# Requires FreeCAD GUI. Raises GuiNotAvailableError if unavailable.
"""Snapshot extraction from FreeCAD documents using GUI-level claimChildren() API.

This module provides expression path normalization for FreeCAD ExpressionEngine
entries, building expression maps with normalized keys for nested property paths.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from ...utils import Log
from ..freecad_ports import DocumentLike, DocumentObjectLike
from ..tree import Property


if TYPE_CHECKING:
    from .models import Snapshot, SnapshotOccurrence


class GuiNotAvailableError(Exception):
    """Exception raised when FreeCAD GUI is not available.

    This exception is raised by _init_gui_and_get_doc() when:
    - FreeCADGui module cannot be imported
    - setupWithoutGUI() fails
    - getDocument() fails
    """

    pass


FREECAD_ACCESS_ERRORS = (AttributeError, TypeError, ValueError, RuntimeError, ReferenceError)
EXTRACTION_ERRORS = (GuiNotAvailableError, AttributeError, TypeError, ValueError, RuntimeError, ReferenceError)


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
    except FREECAD_ACCESS_ERRORS as e:
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
    except ImportError as e:
        Log.warning(f"FreeCADGui not available: {e}")
        raise GuiNotAvailableError(f"FreeCADGui not available - cannot use claimChildren(): {e}") from e

    if hasattr(Gui, "setupWithoutGUI"):
        try:
            Gui.setupWithoutGUI()
        except FREECAD_ACCESS_ERRORS as e:
            raise GuiNotAvailableError(f"Failed to setup GUI without display: {e}") from e

    gui_doc = None
    if hasattr(Gui, "getDocument"):
        try:
            doc_name = getattr(doc, "Name", None)
            if doc_name is not None:
                gui_doc = Gui.getDocument(doc_name)
        except FREECAD_ACCESS_ERRORS as e:
            raise GuiNotAvailableError(f"Failed to get GUI document: {e}") from e

    return gui_doc


def _normalize_expression_path_for_property(prop_name: str, raw_path: str) -> str | None:
    """Normalize a raw expression path relative to the given property name.

    FreeCAD expression paths can be dotted (e.g., '.Length') or undotted
    (e.g., 'Length') for the same target. This function strips the property
    name prefix and returns the relative path.

    Args:
        prop_name: The property name (e.g., 'Placement', 'Constraints', 'Length')
        raw_path: The raw path from ExpressionEngine (e.g., '.Placement.Base.x')

    Returns:
        The normalized relative path, or None if unrelated.
        - '.' for root-level expressions (e.g., '.Length' -> '.')
        - Relative path for sub-paths (e.g., '.Placement.Base.x' -> 'Base.x')
        - Bracket key for list items (e.g., '.Constraints[0]' -> '[0]')
    """
    p = raw_path.lstrip(".")

    if p == prop_name:
        return "."
    if p.startswith(prop_name + "."):
        return p[len(prop_name) + 1 :]
    if p.startswith(prop_name + "["):
        # keep bracket relative key, e.g. Constraints[0] -> [0]
        return p[len(prop_name) :]
    return None


def _build_expression_map_for_property(prop_name: str, expr_engine: Any) -> dict[str, str]:
    """Build an expression map for a property from its ExpressionEngine.

    The ExpressionEngine is a list of [path, expression] pairs. This function
    normalizes paths relative to the given property name and builds a map
    of relative keys to expression strings.

    Duplicate resolution: when both dotted (e.g., '.Length') and undotted
    (e.g., 'Length') forms exist for the same relative key, the dotted form
    wins (is kept).

    Args:
        prop_name: The property name to build expressions for
        expr_engine: The ExpressionEngine list from a FreeCAD object

    Returns:
        Dictionary mapping normalized relative keys to expression strings.
        The key '.' represents a root-level expression.
    """
    result: dict[str, str] = {}
    if not isinstance(expr_engine, list):
        return result

    for entry in expr_engine:
        if not isinstance(entry, (list, tuple)) or len(entry) < 2:
            continue
        raw_path = str(entry[0])
        expr = str(entry[1])

        rel = _normalize_expression_path_for_property(prop_name, raw_path)
        if rel is None:
            continue

        # deterministic duplicate resolution: dotted form wins when both exist
        if rel not in result or raw_path.startswith("."):
            result[rel] = expr

    return result


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

    Builds an expression map from the object's ExpressionEngine and delegates
    to Property.from_freecad() which handles type detection and wraps the
    value in the appropriate DataPath subclass.

    Args:
        obj: The FreeCAD object
        prop_name: The property name

    Returns:
        A Property if successful, None if the property couldn't be read
    """
    try:
        value = getattr(obj, prop_name)
        expr_map = _build_expression_map_for_property(prop_name, getattr(obj, "ExpressionEngine", []))
        group = _get_property_group(obj, prop_name)
        return Property.from_freecad(value, expr_map, group)
    except FREECAD_ACCESS_ERRORS as e:
        Log.exception(f"Failed to extract property {prop_name}: {e}")
        return None


def _is_property_hidden(obj: object, prop_name: str) -> tuple[bool, str]:
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
    checks = [
        _check_editor_mode_hidden,
        _check_property_status_hidden,
        _check_type_hidden,
        _check_no_editor_type,
    ]
    for check in checks:
        is_hidden, reason = check(obj, prop_name)
        if is_hidden:
            return is_hidden, reason
    return False, ""


def _check_editor_mode_hidden(obj: object, prop_name: str) -> tuple[bool, str]:
    """Check 1: getEditorMode() returns ['Hidden']."""
    get_editor_mode = getattr(obj, "getEditorMode", None)
    if get_editor_mode is not None:
        try:
            editor_mode = get_editor_mode(prop_name)
            if isinstance(editor_mode, list) and "Hidden" in editor_mode:
                return True, "editor_mode_hidden"
        except FREECAD_ACCESS_ERRORS as e:
            Log.exception(f"Failed to get editor mode for {prop_name}: {e}")
    return False, ""


def _check_property_status_hidden(obj: object, prop_name: str) -> tuple[bool, str]:
    """Check 2: getPropertyStatus() contains 'Hidden' string or integer 26.

    From FreeCAD source (src/App/PropertyContainerPyImp.cpp line 311-356):
    getPropertyStatus() returns a Py::List where each set bit in the property's
    status bitmask is converted to either:
      - A string name if the bit has a named entry in statusMap (bits 1-13)
        Examples: "Hidden" (bit 3), "Output" (bit 7), "Transient" (bit 4)
      - An integer if the bit has no named entry (bits 14-31)
        Examples: 23 (PropNoRecompute), 24 (PropReadOnly), 26 (PropHidden), 27 (PropOutput)
    The function iterates through bits 1-31 and appends to the list if that bit is set.
    To detect hidden properties, we check for:
      - String "Hidden" (bit 3) - runtime status hiding via testStatus(Property::Hidden)
      - Integer 26 (PropHidden) - compile-time type flag Prop_Hidden (bit 4) mirrored to bit 26
    Both are checked by FreeCAD's PropertyView::isPropertyHidden() (src/Gui/PropertyView.cpp:245):
      (prop->getType() & App::Prop_Hidden) || prop->testStatus(App::Property::Hidden)
    """
    get_property_status = getattr(obj, "getPropertyStatus", None)
    if get_property_status is not None:
        try:
            status = get_property_status(prop_name)
            if isinstance(status, list) and ("Hidden" in status or 26 in status):
                return True, "prop_hidden_bit"
        except FREECAD_ACCESS_ERRORS as e:
            Log.exception(f"Failed to get property status for {prop_name}: {e}")
    return False, ""


def _check_type_hidden(obj: object, prop_name: str) -> tuple[bool, str]:
    """Check 3: getTypeOfProperty() returns a list containing 'Hidden'."""
    get_type_of_property = getattr(obj, "getTypeOfProperty", None)
    if get_type_of_property is not None:
        try:
            prop_types = get_type_of_property(prop_name)
            if isinstance(prop_types, list) and "Hidden" in prop_types:
                return True, "type_hidden"
        except FREECAD_ACCESS_ERRORS as e:
            Log.exception(f"Failed to get type of property {prop_name}: {e}")
    return False, ""


def _check_no_editor_type(obj: object, prop_name: str) -> tuple[bool, str]:
    """Check 4: Property type has no editor (workaround for missing getEditorName()).

    In FreeCAD C++, properties are hidden if getEditorName() returns ""
    Since this method isn't available in Python, we check the TypeId against
    NO_EDITOR_PROPERTY_TYPES which contains all property types without editors
    """
    get_type_id = getattr(obj, "getTypeIdOfProperty", None)
    if get_type_id is not None:
        try:
            type_id = get_type_id(prop_name)
            if isinstance(type_id, str) and type_id in _ALL_NO_EDITOR_TYPES:
                return True, f"{type_id.lower()}_no_editor"
        except FREECAD_ACCESS_ERRORS as e:
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
            if _should_skip_claim_children_parent(obj):
                continue
            vp = _get_view_provider(obj, gui_doc)
            if vp is not None:
                children = _get_claimed_children(vp)
                if children:
                    parent_to_child_map[obj.Name] = children

    return parent_to_child_map


def _build_occurrence_list_bfs(
    child_to_parents_map: dict[str, set[str]],
    parent_to_child_map: dict[str, list[str]],
    name_to_obj_map: dict[str, DocumentObjectLike],
) -> list[SnapshotOccurrence]:
    """Build occurrence rows using BFS.

    Args:
        child_to_parents_map: Map of child name to parent names
        parent_to_child_map: Map of parent name to list of child names from claimChildren() (O(1) lookup)
        name_to_obj_map: Map of object name to object

    Returns:
        List of SnapshotOccurrence rows in BFS order.
    """
    from .models import SnapshotOccurrence

    occurrences: list[SnapshotOccurrence] = []
    queue = _initialize_bfs_queue(child_to_parents_map, name_to_obj_map)

    while queue:
        obj, path, after, ancestors = queue.pop(0)
        obj_name = getattr(obj, "Name", None)
        if obj_name is None:
            continue

        occurrences.append(SnapshotOccurrence(path=path, after=after))
        _enqueue_children(obj_name, path, ancestors, parent_to_child_map, name_to_obj_map, queue)

    return occurrences


def _initialize_bfs_queue(
    child_to_parents_map: dict[str, set[str]],
    name_to_obj_map: dict[str, DocumentObjectLike],
) -> list[tuple[DocumentObjectLike, str, str | None, tuple[str, ...]]]:
    """Initialize BFS queue with root objects."""
    queue: list[tuple[DocumentObjectLike, str, str | None, tuple[str, ...]]] = []
    root_names = [name for name in name_to_obj_map if name not in child_to_parents_map]
    for i, name in enumerate(root_names):
        obj = name_to_obj_map.get(name)
        if obj:
            after = root_names[i - 1] if i > 0 else None
            queue.append((obj, name, after, (name,)))
    return queue


def _enqueue_children(
    obj_name: str,
    path: str,
    ancestors: tuple[str, ...],
    parent_to_child_map: dict[str, list[str]],
    name_to_obj_map: dict[str, DocumentObjectLike],
    queue: list[tuple[DocumentObjectLike, str, str | None, tuple[str, ...]]],
) -> None:
    """Enqueue children of the current object for BFS processing."""
    children_names = parent_to_child_map.get(obj_name, [])
    previous_child_path: str | None = None
    for child_name in children_names:
        if child_name in ancestors:
            continue
        child_obj = name_to_obj_map.get(child_name)
        if child_obj:
            child_path = f"{path}/{child_name}"
            child_after = previous_child_path
            queue.append((child_obj, child_path, child_after, (*ancestors, child_name)))
            previous_child_path = child_path


def _bool_attr(obj: DocumentObjectLike, attr_name: str) -> bool:
    """Get a boolean-like attribute or callable result safely."""
    try:
        attr = getattr(obj, attr_name, None)
        if callable(attr):
            return bool(attr())
        return bool(attr)
    except (AttributeError, TypeError, RuntimeError):
        return False


def _is_derived_from(obj: DocumentObjectLike, type_id: str) -> bool:
    """Return True when object reports FreeCAD type derivation."""
    try:
        is_derived = getattr(obj, "isDerivedFrom", None)
        if callable(is_derived):
            return bool(is_derived(type_id))
    except (AttributeError, TypeError, RuntimeError):
        return False
    return False


def _should_skip_claim_children_parent(obj: DocumentObjectLike) -> bool:
    """Return whether claimChildren() should be skipped for this parent.

    Policy:
    - Keep Assembly::AssemblyLink expansion (its children are synchronized local structure).
    - Skip generic link wrappers (App::Link, App::LinkElement, link-capable wrappers).
    """
    if _is_derived_from(obj, "Assembly::AssemblyLink"):
        return False

    type_id = getattr(obj, "TypeId", "")
    if type_id in {"App::Link", "App::LinkElement", "App::LinkGroup"}:
        return True

    if _is_derived_from(obj, "App::LinkElement") or _is_derived_from(obj, "App::Link"):
        return True

    return _bool_attr(obj, "isLink")


def _extract_tree_single_pass(
    doc: DocumentLike,
    gui_doc: Any,
    document_name: str,
    git_path: str = "",  # NEW
) -> Snapshot:
    """Extract tree using single-pass BFS algorithm.

    This replaces the multi-pass approach with a single BFS pass that builds
    occurrence rows directly. FreeCAD's claimChildren() returns only
    direct children, so no recursive exclusion is needed.

    Args:
        doc: The FreeCAD document
        gui_doc: The GUI document for ViewProvider access (can be None)
        document_name: Name of the document
        git_path: Relative path from git root to the document file

    Returns:
        Snapshot containing normalized objects and occurrence rows
    """
    from .models import Snapshot

    # Step 1: Build parent_to_child_map (parent -> direct children from claimChildren())
    parent_to_child_map = _build_parent_to_child_map(doc, gui_doc)

    # Step 2: Build child_to_parents_map from parent_to_child_map
    child_to_parents_map: dict[str, set[str]] = {}
    for parent_name, children in parent_to_child_map.items():
        for child_name in children:
            if child_name not in child_to_parents_map:
                child_to_parents_map[child_name] = set()
            child_to_parents_map[child_name].add(parent_name)

    # Step 3: Build name to object map for quick lookup
    name_to_obj: dict[str, DocumentObjectLike] = {}
    for obj in doc.Objects:
        name = getattr(obj, "Name", None)
        if name:
            name_to_obj[name] = obj

    # Step 4: Build unique object payloads once (name-keyed)
    from .models import SnapshotObject

    objects: list[SnapshotObject] = []
    for obj in doc.Objects:
        name = getattr(obj, "Name", None)
        if not name:
            continue
        if name not in name_to_obj:
            continue
        properties = _extract_visible_properties(obj)
        objects.append(
            SnapshotObject(
                name=name,
                id=getattr(obj, "ID", 0),
                type_id=getattr(obj, "TypeId", ""),
                properties=properties,
            )
        )

    # Step 5: Single BFS pass to build occurrences
    occurrences = _build_occurrence_list_bfs(child_to_parents_map, parent_to_child_map, name_to_obj)

    return Snapshot(
        snapshot_id=str(uuid.uuid4()),
        document_name=document_name,
        timestamp=datetime.now(),
        objects=objects,
        occurrences=occurrences,
        git_path=git_path,
    )


class SnapshotExtractor:
    """Extracts tree structure from FreeCAD documents.

    This class extracts the document tree structure from a live
    FreeCAD document and converts it to Snapshot domain models. Uses the
    unified Log class from utils for logging.
    """

    def __init__(self) -> None:
        """Initialize the extractor."""
        pass

    def extract_tree(self, doc: DocumentLike, git_path: str = "") -> Snapshot:
        """Extract the document tree structure from a FreeCAD document.

        This function traverses a FreeCAD document and converts it into
        a normalized Snapshot domain object containing object payloads and occurrences.
        GUI-level claimChildren() API to match the visual tree structure.

        Args:
            doc: Required DocumentLike instance representing the FreeCAD document.
            git_path: Optional relative path from git root to the document file.

        Returns:
            A Snapshot object containing the document tree structure.
            Returns an empty Snapshot if extraction fails.
        """
        from .models import Snapshot

        document_name = getattr(doc, "Name", "Unnamed")

        try:
            # Initialize FreeCAD GUI and get GUI document for claimChildren()
            gui_doc = _init_gui_and_get_doc(doc)

            # Use single-pass BFS algorithm for better performance
            return _extract_tree_single_pass(doc, gui_doc, document_name, git_path)

        except EXTRACTION_ERRORS as e:
            Log.exception(f"Error extracting document tree: {e}")

        # Use current time for timestamp
        timestamp = datetime.now()

        return Snapshot(
            snapshot_id=str(uuid.uuid4()),
            document_name=document_name,
            timestamp=timestamp,
            objects=[],
            occurrences=[],
            git_path=git_path,
        )
