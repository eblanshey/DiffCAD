# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides models for representing the differences between two
# document snapshots, including property-level, node-level, and path-level comparisons.
#
# Path-level diff primitives: PropertyPathDiff, _flatten_data_path, _join_path.
# Property-level diff: PropertyDiff (path-diff based, no legacy children).
# Node-level diff: NodeDiff, DiffHierarchy, DiffResult.
# Path sorting helpers: _path_sort_key, _split_path_for_sort.
#
# This module contains pure data models with embedded state calculation logic.
# It depends on domain/tree/property.py but has no circular dependencies.
"""Domain models for diff results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from ...config import FLOAT_PRECISION
from ...utils import float_values_equal
from ..snapshots import Snapshot
from ..tree import Property
from ..tree.data_path import (
    DataPath,
    ListData,
    PropertyPathType,
    PropertyPathValue,
)


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


# Warning constants for edge cases
WARNING_OLD_SNAPSHOT_MISSING = "Old snapshot missing"


@dataclass(frozen=True)
class PropertyPathDiff:
    """The difference between two property path values.

    Represents a diff at the individual path level (e.g. ``"Base.x"``, ``"[0]"``, ``"."``)
    within a property's structured value.  Value and expression states are computed
    automatically in ``__post_init__`` so they are always consistent with the
    provided ``old_value`` / ``new_value``.

    Attributes:
        path: The flattened path key (e.g. ``"."``, ``"Base.x"``, ``"[0].Value"``).
        old_value: Path value in the old snapshot (``None`` if added).
        new_value: Path value in the new snapshot (``None`` if deleted).
        value_state: Auto-calculated diff state for the raw value.
        expression_state: Auto-calculated diff state for the expression.
    """

    path: str
    old_value: PropertyPathValue | None
    new_value: PropertyPathValue | None
    value_state: DiffState = field(init=False)
    expression_state: DiffState = field(init=False)

    def __post_init__(self) -> None:
        """Calculate value_state and expression_state from old/new values."""
        object.__setattr__(self, "value_state", _calc_value_state(self.old_value, self.new_value))
        old_expr = _path_expression(self.old_value)
        new_expr = _path_expression(self.new_value)
        object.__setattr__(self, "expression_state", _calc_expression_state(old_expr, new_expr))


def _path_expression(value: PropertyPathValue | None) -> str | None:
    """Return the expression string of a ``PropertyPathValue``, or ``None``."""
    return value.expression if value is not None else None


def _calc_value_state(old: PropertyPathValue | None, new: PropertyPathValue | None) -> DiffState:
    """Calculate the diff state for a single path value.

    - ``None -> None``  → UNCHANGED
    - ``None -> Some``  → ADDED
    - ``Some -> None``  → DELETED
    - ``Some -> Some``  → UNCHANGED if equal (float-tolerant), MODIFIED otherwise
    """
    if old is None:
        return DiffState.ADDED if new is not None else DiffState.UNCHANGED
    if new is None:
        return DiffState.DELETED
    return DiffState.UNCHANGED if _path_values_equal(old, new) else DiffState.MODIFIED


def _calc_expression_state(old_expr: str | None, new_expr: str | None) -> DiffState:
    """Calculate the diff state for an expression string.

    Expression state is computed independently of value state:
    - ``None -> None``  → UNCHANGED
    - ``None -> Some``  → ADDED
    - ``Some -> None``  → DELETED
    - ``Some -> Some``  → UNCHANGED if equal, MODIFIED otherwise
    """
    if old_expr is None:
        return DiffState.ADDED if new_expr is not None else DiffState.UNCHANGED
    if new_expr is None:
        return DiffState.DELETED
    return DiffState.UNCHANGED if old_expr == new_expr else DiffState.MODIFIED


def _path_values_equal(old: PropertyPathValue, new: PropertyPathValue) -> bool:
    """Compare two ``PropertyPathValue`` instances for equality.

    Float values are compared after rounding to the configured precision.
    All other types use exact equality.  Expression is NOT compared here
    (expression has its own state).
    """
    if old.type_ != new.type_:
        return False
    if old.type_ == PropertyPathType.FLOAT:
        return float_values_equal(float(old.value), float(new.value), FLOAT_PRECISION)
    return old.value == new.value


def _flatten_data_path(value: DataPath, prefix: str = "") -> dict[str, PropertyPathValue]:
    """Flatten a ``DataPath`` into a ``{path_key: PropertyPathValue}`` dict.

    Every ``DataPath`` subclass has a ``paths`` dict that maps relative
    path keys (``"."``, ``"x"``, ``"Base.x"``, etc.) to ``PropertyPathValue``
    instances.  This function joins those keys with an optional prefix
    and, for ``ListData``, recursively flattens each item.

    Args:
        value: The ``DataPath`` to flatten.
        prefix: An optional path prefix (e.g. ``"[0]"`` for list items).

    Returns:
        A dict mapping fully-qualified path strings to ``PropertyPathValue``.
    """
    if isinstance(value, ListData):
        out: dict[str, PropertyPathValue] = {}
        for rel, pv in value.paths.items():
            out[_join_path(prefix, rel)] = pv
        for i, item in enumerate(value.items):
            item_prefix = _join_path(prefix, f"[{i}]")
            out.update(_flatten_data_path(item, item_prefix))
        return out

    if hasattr(value, "paths"):
        result: dict[str, PropertyPathValue] = {}
        for rel, pv in value.paths.items():
            full = _join_path(prefix, rel)
            result[full] = pv
        return result

    return {}


def _join_path(prefix: str, rel: str) -> str:
    """Join a relative DataPath key into a full flattened path.

    Examples::

        _join_path("", ".")          -> "."
        _join_path("[0]", ".")       -> "[0]"
        _join_path("", "Base.x")     -> "Base.x"
        _join_path("[0]", "Value")   -> "[0].Value"
        _join_path("Constraints", "[2]") -> "Constraints[2]"

    Args:
        prefix: The accumulated path prefix (may be empty).
        rel: A relative key from a ``DataPath.paths`` dict.

    Returns:
        The fully-qualified path string.
    """
    if rel == ".":
        return prefix or "."
    if not prefix:
        return rel
    if rel.startswith("["):
        return f"{prefix}{rel}"
    return f"{prefix}.{rel}"


def _path_sort_key(path: str) -> tuple:
    """Return a sort key for a flattened path string.

    Keeps root ``"."`` first, then orders by natural segment order
    (named segments before indexed segments, numeric indices numerically).

    Args:
        path: A flattened path string (e.g. ``"."``, ``"Base.x"``, ``"[0]"``).

    Returns:
        A tuple suitable for sorting (always a tuple of tuples for consistency).
    """
    if path == ".":
        return ((-1,),)
    segments = _split_path_for_sort(path)
    return tuple(segments)


def _split_path_for_sort(path: str) -> list[tuple[int, str | int]]:
    """Split a flattened path into sortable typed segments.

    Splits paths like ``"Base.x"``, ``"[10].Value"``, ``"[2]"`` into
    segments that sort correctly: named segments first, then indexed
    segments in numeric order.

    Args:
        path: A flattened path string.

    Returns:
        A list of ``(type_key, value)`` tuples where type_key is
        ``0`` for named segments and ``1`` for indexed segments.
    """
    out: list[tuple[int, str | int]] = []
    token: list[str] = []
    i = 0
    while i < len(path):
        ch = path[i]
        if ch == ".":
            if token:
                out.append((0, "".join(token)))
                token = []
            i += 1
            continue
        if ch == "[":
            if token:
                out.append((0, "".join(token)))
                token = []
            j = path.find("]", i)
            idx = int(path[i + 1 : j])
            out.append((1, idx))
            i = j + 1
            continue
        token.append(ch)
        i += 1
    if token:
        out.append((0, "".join(token)))
    return out


def _are_properties_modified(property_diffs: list[PropertyDiff], children: list[NodeDiff]) -> bool:
    """Check if any properties or children have modifications."""
    if any(child.state != DiffState.UNCHANGED for child in children):
        return True
    return any(prop_diff.state != DiffState.UNCHANGED for prop_diff in property_diffs)


@dataclass(frozen=True)
class PropertyDiff:
    """The difference between two property values.

    The state is automatically calculated based on the flattened path diffs.
    This ensures consistency and prevents invalid states where the state
    doesn't match the actual values.

    Attributes:
        property_name: Name of the property
        old_value: Value in the old snapshot (None if added)
        new_value: Value in the new snapshot (None if deleted)
        state: The diff state (ADDED, DELETED, MODIFIED, UNCHANGED) - auto-calculated
        path_diffs: List of path-level diffs for all sub-paths (auto-calculated)
    """

    property_name: str
    old_value: Property | None
    new_value: Property | None
    state: DiffState = field(init=False)
    path_diffs: list[PropertyPathDiff] = field(init=False)

    def __post_init__(self) -> None:
        """Calculate state and path_diffs from flattened path maps."""
        old_paths = _flatten_data_path(self.old_value.value) if self.old_value else {}
        new_paths = _flatten_data_path(self.new_value.value) if self.new_value else {}

        all_paths = sorted(set(old_paths) | set(new_paths), key=_path_sort_key)
        diffs = [PropertyPathDiff(path=p, old_value=old_paths.get(p), new_value=new_paths.get(p)) for p in all_paths]
        object.__setattr__(self, "path_diffs", diffs)

        if self.old_value is None:
            object.__setattr__(self, "state", DiffState.ADDED if self.new_value is not None else DiffState.UNCHANGED)
            return
        if self.new_value is None:
            object.__setattr__(self, "state", DiffState.DELETED)
            return

        has_value_change = any(d.value_state != DiffState.UNCHANGED for d in diffs)
        has_expr_change = any(d.expression_state != DiffState.UNCHANGED for d in diffs)
        object.__setattr__(
            self, "state", DiffState.MODIFIED if (has_value_change or has_expr_change) else DiffState.UNCHANGED
        )

    def __str__(self) -> str:
        if self.state == DiffState.ADDED:
            return f"{self.property_name}: ADDED"
        elif self.state == DiffState.DELETED:
            return f"{self.property_name}: DELETED"
        elif self.state == DiffState.MODIFIED:
            return f"{self.property_name}: MODIFIED"
        return f"{self.property_name}: UNCHANGED"


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
        label: The user-friendly label of the node (from new snapshot for added/modified,
            from old snapshot for deleted)
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
    label: str = ""
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
        # Check if any property diff has changes (not just if property_diffs exists)
        if any(p.state != DiffState.UNCHANGED for p in self.property_diffs):
            return True
        return any(child.has_changes for child in self.children)

    @property
    def changed_properties(self) -> list[PropertyDiff]:
        """Get only the properties that actually changed."""
        return [p for p in self.property_diffs if p.state != DiffState.UNCHANGED]


@dataclass(frozen=True)
class DiffResult:
    """The complete result of comparing two snapshots.

    Represents all differences between an old and new snapshot, organized
    as a tree structure that mirrors the original document hierarchy.

    Attributes:
        old_snapshot: The old snapshot being compared
        new_snapshot: The new snapshot being compared
        warnings: List of warning messages for edge cases
        added_count: Number of added nodes
        deleted_count: Number of deleted nodes
        modified_count: Number of modified nodes
        hierarchy: The DiffHierarchy containing the node diffs in tree form
    """

    old_snapshot: Snapshot
    new_snapshot: Snapshot
    warnings: list[str] = field(default_factory=list)
    added_count: int = 0
    deleted_count: int = 0
    modified_count: int = 0
    hierarchy: DiffHierarchy = field(default_factory=lambda: DiffHierarchy())

    def __str__(self) -> str:
        return (
            f"DiffResult({self.old_snapshot.document_name} vs {self.new_snapshot.document_name}): "
            f"{self.added_count} added, {self.deleted_count} deleted, {self.modified_count} modified"
        )

    @property
    def has_changes(self) -> bool:
        """Check if there are any changes in this diff."""
        return (self.added_count > 0 or self.deleted_count > 0 or self.modified_count > 0) or any(
            node.has_changes for node in self.hierarchy.roots
        )

    def get_all_changed_paths(self) -> list[str]:
        """Get all paths that have changes (for UI highlighting)."""
        changed_paths: list[str] = []
        for node_diff in self.hierarchy.roots:
            self._collect_changed_paths(node_diff, changed_paths)
        return changed_paths

    def _collect_changed_paths(self, node: NodeDiff, result: list[str]) -> None:
        """Recursively collect paths with changes."""
        if node.has_changes:
            result.append(node.path)
        for child in node.children:
            self._collect_changed_paths(child, result)


class DiffHierarchy:
    """Holds hierarchical node diffs as a tree structure.

    This class manages the hierarchical organization of NodeDiff objects,
    providing efficient path-based lookups and parent-child relationships.

    Attributes:
        _hierarchy: Nested dict mapping path segments to NodeDiff objects
        _roots: List of top-level NodeDiff objects
    """

    def __init__(self) -> None:
        """Initialize an empty hierarchy."""
        self._hierarchy: dict[str, Any] = {}
        self._roots: list[NodeDiff] = []

    @property
    def roots(self) -> list[NodeDiff]:
        """Get list of top-level NodeDiff objects."""
        return self._roots

    def find_by_path(self, path: str) -> NodeDiff | None:
        """Find a NodeDiff by its path.

        Args:
            path: The path to search for (e.g., "Body/Pad")

        Returns:
            The NodeDiff at the given path, or None if not found
        """
        if not path:
            return None

        # Split path into segments
        segments = path.split("/")

        # Traverse the hierarchy
        current: dict[str, Any] | None = self._hierarchy
        for i, segment in enumerate(segments):
            if not segment:
                continue
            if isinstance(current, dict) and segment in current:
                value = current[segment]

                if i == len(segments) - 1:
                    # This is the final segment, return the NodeDiff
                    if isinstance(value, NodeDiff):
                        return value
                    elif isinstance(value, dict):
                        # Might have __node__ key
                        return value.get("__node__")
                    return None

                # Move to children
                if isinstance(value, dict):
                    current = value.get("__children__")
                else:
                    # It's a NodeDiff, its children are in NodeDiff.children
                    return None
            else:
                return None
        return None

    def add_node(self, node_diff: NodeDiff) -> None:
        """Add a NodeDiff to the hierarchy.

        Handles parent linking automatically - if the parent exists in the
        hierarchy, the node is added as a child. If no parent exists,
        the node is added to roots.

        Args:
            node_diff: The NodeDiff to add
        """
        path = node_diff.path
        if not path:
            return

        segments = path.split("/")

        if len(segments) == 1:
            # Root level node
            self._roots.append(node_diff)
            self._hierarchy[segments[0]] = node_diff
            return

        # Find or create parent path
        parent_segments = segments[:-1]
        parent_path = "/".join(parent_segments)

        # Try to find parent in hierarchy
        parent_node = self.find_by_path(parent_path)

        if parent_node is not None:
            # Add as child to existing parent, but only if not already present
            # (to avoid infinite loops when node_diffs already has children set)
            if node_diff not in parent_node.children:
                parent_node.children.append(node_diff)
        else:
            # No parent found, add to roots
            self._roots.append(node_diff)

        # Store in hierarchy dict
        self._ensure_parent_segments(path, segments, parent_node)
        self._store_node_in_hierarchy(segments, node_diff)

    def _ensure_parent_segments(self, path: str, segments: list[str], parent_node: NodeDiff | None) -> None:
        """Ensure parent segment dict containers exist in hierarchy.

        Args:
            path: Full path of the node being added
            segments: Path segments
            parent_node: Parent NodeDiff if found, None otherwise
        """
        current = self._hierarchy
        for segment in segments[:-1]:  # Process all but last segment
            if segment not in current:
                # Only raise error if parent NodeDiff was supposed to exist
                if parent_node is not None:
                    raise ValueError(
                        f"Parent segment '{segment}' not found in hierarchy for path '{path}'. "
                        f"Parent paths must be created before adding child nodes."
                    )
                # Create dict container for orphaned child (no parent NodeDiff)
                current[segment] = {"__children__": {}}
            elif isinstance(current[segment], NodeDiff):
                existing_node = current[segment]
                current[segment] = {"__children__": {}, "__node__": existing_node}

            # Move to children dict
            if isinstance(current[segment], dict):
                current = current[segment].get("__children__", {})
            else:
                break

    def _store_node_in_hierarchy(self, segments: list[str], node_diff: NodeDiff) -> None:
        """Store the final node in the hierarchy dict.

        Args:
            segments: Path segments
            node_diff: The node to store
        """
        current = self._hierarchy
        # Navigate to parent dict
        for segment in segments[:-1]:
            if isinstance(current.get(segment), dict):
                current = current[segment].get("__children__", {})
            else:
                break

        # Store the final node
        final_segment = segments[-1]
        if final_segment not in current:
            current[final_segment] = node_diff


__all__ = [
    "DiffResult",
    "DiffHierarchy",
    "NodeDiff",
    "PropertyDiff",
    "PropertyPathDiff",
    "DiffState",
    "WARNING_OLD_SNAPSHOT_MISSING",
]
