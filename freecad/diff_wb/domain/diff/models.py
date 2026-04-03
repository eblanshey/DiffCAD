# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides models for representing the differences between two
# document snapshots, including property-level and node-level comparisons.
#
# This module contains pure data models with embedded state calculation logic.
# It depends on domain/tree/property.py but has no circular dependencies.
"""Domain models for diff results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from ...utils import Log
from ..tree import Property, PropertyType


class DiffState(Enum):
    """The state of a node or property in a diff comparison.

    This is used for UI highlighting to show changes:
    - ADDED: Node/property exists only in the new snapshot
    - DELETED: Node/property exists only in the old snapshot
    - MODIFIED: Node/property exists in both but has different values
    - UNCHANGED: Node/property is identical in both snapshots
    """

    ADDED = auto()
    DELETED = auto()
    MODIFIED = auto()
    UNCHANGED = auto()


# TODO: The generic attribute-based comparison for UNKNOWN types works for many FreeCAD
# objects (Constraint, Vector, Placement, etc.), but may need refinement for specific types.
# Known edge cases and potential improvements:
# - Some FreeCAD objects may have attributes that aren't captured by dir()/getattr()
# - Nested objects may need deep comparison instead of just attribute comparison
# - Performance: The current implementation iterates all attributes for each comparison,
#   which may be slow for objects with many attributes
# Future work: Consider type-specific comparison strategies for known FreeCAD types


def _unknown_values_equal(old_obj: Any, new_obj: Any, float_tolerance: float = 1e-9, prop_name: str = "") -> bool:
    """Compare two UNKNOWN type objects by their attribute values.

    This provides a generic comparison that works for FreeCAD objects like
    Constraint, Vector, Placement, etc., where string representation alone
    doesn't capture actual value differences.

    Args:
        old_obj: The old object value
        new_obj: The new object value
        float_tolerance: Tolerance for comparing float values
        prop_name: The property name for logging purposes

    Returns:
        True if objects have equal attribute values
    """
    if old_obj is new_obj:
        return True
    if old_obj is None or new_obj is None:
        return old_obj is new_obj

    # Get all public attributes (not starting with underscore, not callable)
    old_attrs = _get_comparable_attrs(old_obj)
    new_attrs = _get_comparable_attrs(new_obj)

    # Must have the same attributes
    if old_attrs.keys() != new_attrs.keys():
        return False

    # Compare each attribute value
    for attr_name in old_attrs:
        old_val = old_attrs[attr_name]
        new_val = new_attrs[attr_name]

        if not _attribute_values_equal(old_val, new_val, float_tolerance, prop_name, attr_name):
            return False

    return True


def _get_comparable_attrs(obj: Any) -> dict[str, Any]:
    """Get a dict of comparable public attributes from an object.

    Filters out methods, private attributes, and built-in properties.

    Args:
        obj: The object to inspect

    Returns:
        Dict of attribute name -> value for comparable attributes
    """
    attrs = {}
    for attr_name in dir(obj):
        # Skip private/magic attributes
        if attr_name.startswith("_"):
            continue
        # Skip methods and callables
        try:
            attr_val = getattr(obj, attr_name)
        except AttributeError:
            continue
        if callable(attr_val) and not isinstance(attr_val, type):
            continue
        # Skip non-comparable types (some FreeCAD objects have complex internal state)
        if hasattr(attr_val, "__dict__") and not hasattr(attr_val, "__iter__"):
            # Skip objects that are themselves complex (like other FreeCAD objects)
            continue
        attrs[attr_name] = attr_val
    return attrs


def _attribute_values_equal(  # noqa: C901
    old_val: Any, new_val: Any, float_tolerance: float, prop_name: str = "", attr_name: str = ""
) -> bool:
    """Compare two attribute values for equality.

    Handles floats with tolerance, and iterables by element comparison.

    Args:
        old_val: First value
        new_val: Second value
        float_tolerance: Tolerance for float comparison
        prop_name: The top-level property name for logging
        attr_name: The attribute name being compared

    Returns:
        True if values are equal
    """
    # Same object identity
    if old_val is new_val:
        return True

    # None check
    if old_val is None or new_val is None:
        if old_val is None and new_val is None:
            return True
        # Log the difference
        if prop_name and attr_name:
            Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val!r} -> {new_val!r}")
        return False

    # Float comparison with tolerance
    if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
        if isinstance(old_val, float) or isinstance(new_val, float):
            if abs(old_val - new_val) >= float_tolerance:
                if prop_name and attr_name:
                    Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val} -> {new_val}")
                return False
            return True
        if old_val != new_val:
            if prop_name and attr_name:
                Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val} -> {new_val}")
            return False
        return True

    # Bool comparison (must be exact)
    if isinstance(old_val, bool) or isinstance(new_val, bool):
        if old_val != new_val:
            if prop_name and attr_name:
                Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val} -> {new_val}")
            return False
        return True

    # Iterable comparison (lists, tuples)
    if isinstance(old_val, (list, tuple)) and isinstance(new_val, (list, tuple)):
        if len(old_val) != len(new_val):
            if prop_name and attr_name:
                Log.debug(
                    f"[DIFF] Property '{prop_name}' attribute '{attr_name}' "
                    f"length changed: {len(old_val)} -> {len(new_val)}"
                )
            return False
        for i, (old_item, new_item) in enumerate(zip(old_val, new_val, strict=True)):
            if not _attribute_values_equal(old_item, new_item, float_tolerance, prop_name, f"{attr_name}[{i}]"):
                return False
        return True

    # Direct equality for other types (str, int, etc.)
    try:
        if old_val == new_val:
            return True
        if prop_name and attr_name:
            Log.debug(f"[DIFF] Property '{prop_name}' attribute '{attr_name}' changed: {old_val!r} -> {new_val!r}")
        return False
    except TypeError:
        # Some objects don't support direct comparison
        return False


def _values_are_equal_ignoring_expression(old_value: Property, new_value: Property, prop_name: str = "") -> bool:
    """Compare two property values ignoring expressions.

    Args:
        old_value: Value in the old snapshot
        new_value: Value in the new snapshot
        prop_name: The property name for logging purposes

    Returns:
        True if values are equal ignoring expression differences
    """
    if old_value.type_ != new_value.type_:
        return False
    if old_value.type_ == PropertyType.FLOAT:
        tolerance = 1e-9
        return bool(abs(old_value.value - new_value.value) < tolerance)
    if old_value.type_ == PropertyType.LIST:
        return Property._compare_lists_as_strings(old_value.value, new_value.value)
    # For UNKNOWN types, compare using a generic attribute-based approach
    # that handles FreeCAD objects (e.g., Constraint, Vector, Placement, etc.)
    if old_value.type_ == PropertyType.UNKNOWN:
        return _unknown_values_equal(old_value.value, new_value.value, prop_name=prop_name)
    return bool(old_value.value == new_value.value)


def _calculate_property_diff_state(
    old_value: Property | None, new_value: Property | None, prop_name: str = ""
) -> DiffState:
    """Calculate the diff state for a property based on old and new values.

    Note: Expression changes are tracked separately. This function compares
    only the actual values (ignoring expressions) to determine if the value changed.

    Args:
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        prop_name: The property name for logging purposes

    Returns:
        The appropriate DiffState based on the values
    """
    # If old_value is None, property was added
    if old_value is None:
        return DiffState.ADDED
    # If new_value is None, property was deleted
    if new_value is None:
        return DiffState.DELETED
    # If values are equal (ignoring expressions), unchanged
    values_equal = _values_are_equal_ignoring_expression(old_value, new_value, prop_name)
    if values_equal:
        return DiffState.UNCHANGED
    # Otherwise, modified
    return DiffState.MODIFIED


def _is_vector_like(value: Any) -> bool:
    """Check if value is Vector-like (has x, y, z attributes)."""
    return hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z") and not isinstance(value, (int, float))


def _is_rotation_like(value: Any) -> bool:
    """Check if value is Rotation-like (has angle and axis)."""
    has_angle = hasattr(value, "angle") or hasattr(value, "Angle")
    has_axis = hasattr(value, "axis") or hasattr(value, "Axis")
    return has_angle and has_axis


def _is_placement_like(value: Any) -> bool:
    """Check if value is Placement-like (has position and rotation)."""
    return hasattr(value, "position") and hasattr(value, "rotation")


def _get_property_type_for_primitive(value: Any) -> PropertyType:
    """Infer PropertyType for primitive Python types."""
    if isinstance(value, bool):
        return PropertyType.BOOL
    if isinstance(value, int):
        return PropertyType.INT
    if isinstance(value, float):
        return PropertyType.FLOAT
    if isinstance(value, str):
        return PropertyType.STRING
    return PropertyType.UNKNOWN


def _create_property_from_child_value(value: Any, group: str = "Base") -> Property:
    """Create a Property from a raw child value.

    This wraps raw values from get_children() into Property objects.
    The type is inferred from the value structure.

    Args:
        value: The raw value (Vector, float, Rotation, etc.)
        group: The property group

    Returns:
        A Property object with inferred type
    """
    if value is None:
        return Property(type_=PropertyType.UNKNOWN, value=None, group=group)

    # Check if it's a Vector object
    if _is_vector_like(value):
        return Property(type_=PropertyType.VECTOR, value=value, group=group)

    # Check if it's a Rotation-like object (has angle and axis)
    if _is_rotation_like(value):
        return Property(type_=PropertyType.PLACEMENT, value=value, group=group)

    # Check if it's a Placement object
    if _is_placement_like(value):
        return Property(type_=PropertyType.PLACEMENT, value=value, group=group)

    # Check if it's a list or tuple
    if isinstance(value, (list, tuple)):
        return Property(type_=PropertyType.LIST, value=value, group=group)

    # Check if it's a dict
    if isinstance(value, dict):
        return Property(type_=PropertyType.UNKNOWN, value=value, group=group)

    # For primitives, infer type from Python type
    prop_type = _get_property_type_for_primitive(value)
    return Property(type_=prop_type, value=value, group=group)


def _compute_property_children(
    old_value: Property | None, new_value: Property | None, parent_prop_name: str = ""
) -> list[PropertyDiff]:
    """Compute child property diffs for expandable properties.

    Args:
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        parent_prop_name: The parent property name for logging purposes

    Returns:
        List of PropertyDiff for child properties
    """
    children: list[PropertyDiff] = []

    old_children = old_value.get_children() if old_value else []
    new_children = new_value.get_children() if new_value else []

    old_child_map = dict(old_children)
    new_child_map = dict(new_children)

    all_child_names = set(old_child_map.keys()) | set(new_child_map.keys())

    for child_name in sorted(all_child_names):
        raw_old_child = old_child_map.get(child_name)
        raw_new_child = new_child_map.get(child_name)

        # Wrap raw values in Property objects
        old_child_prop = _create_property_from_child_value(raw_old_child) if raw_old_child is not None else None
        new_child_prop = _create_property_from_child_value(raw_new_child) if raw_new_child is not None else None

        # For child properties, prepend parent name to create a full path for logging
        full_prop_name = f"{parent_prop_name}[{child_name}]" if parent_prop_name else child_name

        child_diff = PropertyDiff(
            property_name=child_name,
            old_value=old_child_prop,
            new_value=new_child_prop,
            _parent_prop_name=full_prop_name,
        )

        children.append(child_diff)

    return children


def _has_expression_change(old_value: Property | None, new_value: Property | None) -> bool:
    """Check if there's an expression change between two property values."""
    if old_value is None or new_value is None:
        return True
    return old_value.expression != new_value.expression


def _are_properties_modified(property_diffs: list[PropertyDiff], children: list[NodeDiff]) -> bool:
    """Check if any properties or children have modifications.

    A node's properties are considered modified if:
    - Any child node has state != DiffState.UNCHANGED
    - Any property has state != DiffState.UNCHANGED (includes ADDED, DELETED, MODIFIED)
    - Any property has children with state != DiffState.UNCHANGED (e.g., constraint items)
    - Any property has an expression change (even if value is unchanged)

    Args:
        property_diffs: List of property diffs for this node
        children: List of child node diffs

    Returns:
        True if any properties or children are modified, False otherwise
    """
    # Check child node states - if any child node has changes, properties are modified
    if any(child.state != DiffState.UNCHANGED for child in children):
        return True

    # Check if any property has changed (ADDED, DELETED, or MODIFIED)
    if any(prop_diff.state != DiffState.UNCHANGED for prop_diff in property_diffs):
        return True

    # Check if any property has children with changes (e.g., individual constraint items)
    for prop_diff in property_diffs:
        if prop_diff.children and any(child.state != DiffState.UNCHANGED for child in prop_diff.children):
            return True

    # Check if any property has expression changes (value may be unchanged but expression changed)
    return any(_has_expression_change(prop_diff.old_value, prop_diff.new_value) for prop_diff in property_diffs)


@dataclass(frozen=True)
class PropertyDiff:
    """The difference between two property values.

    The state is automatically calculated based on the old and new values
    (including their expressions). This ensures consistency and prevents
    invalid states where the state doesn't match the actual values.

    Attributes:
        property_name: Name of the property
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        state: The diff state (ADDED, DELETED, MODIFIED, UNCHANGED) - auto-calculated
        children: List of child property diffs for expandable properties
        _parent_prop_name: Internal field for full property path (e.g., "Constraints[0]")
    """

    property_name: str
    old_value: Property | None
    new_value: Property | None
    state: DiffState = field(init=False)
    children: list[PropertyDiff] = field(default_factory=list)
    _parent_prop_name: str = field(default="", repr=False, compare=False)

    def __post_init__(self) -> None:
        """Calculate state and children based on old and new values."""
        # Use object.__setattr__ since the dataclass is frozen
        # Use _parent_prop_name if set (for child properties), otherwise use property_name
        full_prop_name = self._parent_prop_name or self.property_name
        object.__setattr__(
            self, "state", _calculate_property_diff_state(self.old_value, self.new_value, full_prop_name)
        )
        # Compute children for expandable properties (pass property_name as parent)
        object.__setattr__(
            self, "children", _compute_property_children(self.old_value, self.new_value, self.property_name)
        )

    def __str__(self) -> str:
        if self.state == DiffState.ADDED:
            return f"{self.property_name}: +{self.new_value}"
        elif self.state == DiffState.DELETED:
            return f"{self.property_name}: -{self.old_value}"
        elif self.state == DiffState.MODIFIED:
            return f"{self.property_name}: {self.old_value} -> {self.new_value}"
        return f"{self.property_name}: {self.old_value}"


@dataclass(frozen=True)
class NodeDiff:
    """The difference between two tree nodes.

    Represents the diff result for a single node in the document tree,
    including its properties and children.

    The state is automatically calculated based on property diffs and children:
    - If `_force_state` is set (by factory functions), that state is used
    - Otherwise, state is MODIFIED if any property/child has changes, UNCHANGED otherwise

    This separates node-level changes (entire node added/deleted) from
    property-level changes (properties modified/added/deleted).

    Attributes:
        path: The path to this node (for backward compatibility, same as new_path)
        type_id: The TypeID of the node
        state: The overall state of this node - auto-calculated or forced
        property_diffs: List of property-level differences
        children: List of child node diffs
        old_path: Path in old snapshot (None for added nodes). Used for move detection.
        new_path: Path in new snapshot (None for deleted nodes). Used for move detection.
        old_after: The 'after' field in old snapshot (None for added/root nodes).
            Used for reorder detection.
        new_after: The 'after' field in new snapshot (None for deleted/root nodes).
            Used for reorder detection.
        _force_state: Internal override for state calculation. Only used by
            factory functions (`create_added_node_diff`, `create_deleted_node_diff`)
            to indicate node-level changes (ADDED/DELETED). When None, state is
            calculated from property_diffs (MODIFIED/UNCHANGED). Not included in
            repr or comparison.
    """

    path: str
    type_id: str
    state: DiffState = field(init=False)
    property_diffs: list[PropertyDiff] = field(default_factory=list)
    children: list[NodeDiff] = field(default_factory=list)
    old_path: str | None = field(default=None)
    new_path: str | None = field(default=None)
    old_after: str | None = field(default=None)
    new_after: str | None = field(default=None)
    _force_state: DiffState | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        """Calculate state based on _force_state or property diffs.

        State calculation logic:
        1. If _force_state is set (node-level change), use that state
        2. Otherwise, check if any properties/children are modified
        3. Return MODIFIED if changes exist, UNCHANGED otherwise
        """
        # Use object.__setattr__ since the dataclass is frozen
        if self._force_state is not None:
            object.__setattr__(self, "state", self._force_state)
        elif _are_properties_modified(self.property_diffs, self.children):
            object.__setattr__(self, "state", DiffState.MODIFIED)
        else:
            object.__setattr__(self, "state", DiffState.UNCHANGED)

    def __str__(self) -> str:
        state_str = self.state.name
        prop_count = len(self.property_diffs)
        child_count = len(self.children)
        return f"NodeDiff({self.path}, {state_str}, {prop_count} props, {child_count} children)"

    @property
    def has_changes(self) -> bool:
        """Check if this node or any children have changes."""
        if self.state != DiffState.UNCHANGED:
            return True
        if self.property_diffs:
            return True
        return any(child.has_changes for child in self.children)

    @property
    def changed_properties(self) -> list[PropertyDiff]:
        """Get only the properties that actually changed."""
        return [p for p in self.property_diffs if p.state != DiffState.UNCHANGED]


@dataclass(frozen=True)
class DiffSummary:
    """A summary of changes in a diff result.

    Provides quick statistics about the scope of changes:
    - Total nodes compared
    - Nodes added, deleted, modified, unchanged
    - Total properties changed
    """

    total_nodes: int = 0
    added_nodes: int = 0
    deleted_nodes: int = 0
    modified_nodes: int = 0
    unchanged_nodes: int = 0
    total_property_changes: int = 0

    def __str__(self) -> str:
        return (
            f"DiffSummary: {self.added_nodes} added, "
            f"{self.deleted_nodes} deleted, "
            f"{self.modified_nodes} modified, "
            f"{self.unchanged_nodes} unchanged"
        )

    @classmethod
    def compute(cls, diff_result: DiffResult) -> DiffSummary:
        """Compute a summary from a diff result.

        Args:
            diff_result: The diff result to summarize

        Returns:
            A DiffSummary with computed statistics
        """
        total_nodes = 0
        added_nodes = 0
        deleted_nodes = 0
        modified_nodes = 0
        unchanged_nodes = 0
        total_property_changes = 0

        for node_diff in diff_result.node_diffs:
            total_nodes += 1
            counts = cls._count_node(node_diff)
            added_nodes += counts["added"]
            deleted_nodes += counts["deleted"]
            modified_nodes += counts["modified"]
            unchanged_nodes += counts["unchanged"]
            total_property_changes += counts["property_changes"]

        return cls(
            total_nodes=total_nodes,
            added_nodes=added_nodes,
            deleted_nodes=deleted_nodes,
            modified_nodes=modified_nodes,
            unchanged_nodes=unchanged_nodes,
            total_property_changes=total_property_changes,
        )

    @staticmethod
    def _count_node(node: NodeDiff) -> dict[str, int]:
        """Recursively count node states and property changes.

        Returns:
            A dict with counts for 'added', 'deleted', 'modified', 'unchanged', 'property_changes'
        """
        # Count this node
        if node.state == DiffState.ADDED:
            added = 1
            deleted = 0
            modified = 0
            unchanged = 0
        elif node.state == DiffState.DELETED:
            added = 0
            deleted = 1
            modified = 0
            unchanged = 0
        elif node.state == DiffState.MODIFIED:
            added = 0
            deleted = 0
            modified = 1
            unchanged = 0
        else:
            added = 0
            deleted = 0
            modified = 0
            unchanged = 1

        # Count property changes
        property_changes = sum(1 for prop_diff in node.property_diffs if prop_diff.state != DiffState.UNCHANGED)

        # Recurse into children
        for child in node.children:
            child_counts = DiffSummary._count_node(child)
            added += child_counts["added"]
            deleted += child_counts["deleted"]
            modified += child_counts["modified"]
            unchanged += child_counts["unchanged"]
            property_changes += child_counts["property_changes"]

        return {
            "added": added,
            "deleted": deleted,
            "modified": modified,
            "unchanged": unchanged,
            "property_changes": property_changes,
        }


@dataclass(frozen=True)
class DiffResult:
    """The complete result of comparing two snapshots.

    Represents all differences between an old and new snapshot, organized
    as a tree structure that mirrors the original document hierarchy.

    Attributes:
        old_snapshot_name: Name/identifier of the old snapshot
        new_snapshot_name: Name/identifier of the new snapshot
        node_diffs: List of root-level node diffs
    """

    old_snapshot_name: str
    new_snapshot_name: str
    node_diffs: list[NodeDiff] = field(default_factory=list)

    def __str__(self) -> str:
        summary = DiffSummary.compute(self)
        return f"DiffResult({self.old_snapshot_name} vs {self.new_snapshot_name}): {summary}"

    @property
    def summary(self) -> DiffSummary:
        """Get a summary of this diff result."""
        return DiffSummary.compute(self)

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes in this diff."""
        summary = self.summary
        return (
            summary.total_property_changes > 0
            or summary.added_nodes > 0
            or summary.deleted_nodes > 0
            or summary.modified_nodes > 0
        )

    def get_all_changed_paths(self) -> list[str]:
        """Get all paths that have changes (for UI highlighting)."""
        changed_paths: list[str] = []
        for node_diff in self.node_diffs:
            self._collect_changed_paths(node_diff, changed_paths)
        return changed_paths

    def _collect_changed_paths(self, node: NodeDiff, result: list[str]) -> None:
        """Recursively collect paths with changes."""
        if node.has_changes:
            result.append(node.path)
        for child in node.children:
            self._collect_changed_paths(child, result)


__all__ = ["DiffResult", "NodeDiff", "PropertyDiff", "DiffState"]
