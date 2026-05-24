# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for the domain diff models module.
"""Unit tests for domain diff models."""

import pytest
from freecad.history_wb.domain.diff.models import (
    DiffState,
    PropertyDiff,
)
from freecad.history_wb.domain.tree import Property
from freecad.history_wb.domain.tree.data_path import (
    PropertyPathType,
    PropertyPathValue,
    VectorData,
)


class TestPropertyDiffPathDiffs:
    """Tests for PropertyDiff path_diffs (path-based diff semantics)."""

    def test_path_diffs_contains_all_paths_unchanged_included(self) -> None:
        """PropertyDiff.path_diffs contains all paths, including unchanged ones."""
        old_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_vector,
            new_value=new_vector,
        )

        # Should have path diffs for all paths
        # ListData without root path entry produces indexed paths: [0], [1], [2]
        path_names = {pd.path for pd in prop_diff.path_diffs}
        assert "[0]" in path_names
        assert "[1]" in path_names
        assert "[2]" in path_names

        # All should be UNCHANGED
        for pd in prop_diff.path_diffs:
            assert pd.value_state == DiffState.UNCHANGED

    def test_parent_state_becomes_modified_when_descendant_value_changes(self) -> None:
        """Parent PropertyDiff.state becomes MODIFIED when any descendant path value changes."""
        old_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")
        new_vector = Property.from_freecad([10.0, 2.0, 3.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_vector,
            new_value=new_vector,
        )

        # Parent should be MODIFIED because one path changed
        assert prop_diff.state == DiffState.MODIFIED

        # The first path should be MODIFIED
        first_pd = next(pd for pd in prop_diff.path_diffs if pd.path == "[0]")
        assert first_pd.value_state == DiffState.MODIFIED

        # Other paths should be UNCHANGED
        for pd in prop_diff.path_diffs:
            if pd.path != "[0]":
                assert pd.value_state == DiffState.UNCHANGED

    def test_parent_state_becomes_modified_when_only_expression_changes(self) -> None:
        """Parent PropertyDiff.state becomes MODIFIED when only expression changes."""
        pv1 = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="A")
        pv2 = PropertyPathValue(PropertyPathType.FLOAT, 1.0, expression="B")

        old_vector = Property(
            value=VectorData(
                paths={
                    ".": pv1,
                    "x": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
                    "y": PropertyPathValue(PropertyPathType.FLOAT, 2.0),
                    "z": PropertyPathValue(PropertyPathType.FLOAT, 3.0),
                }
            ),
            group="Base",
        )
        new_vector = Property(
            value=VectorData(
                paths={
                    ".": pv2,
                    "x": PropertyPathValue(PropertyPathType.FLOAT, 1.0),
                    "y": PropertyPathValue(PropertyPathType.FLOAT, 2.0),
                    "z": PropertyPathValue(PropertyPathType.FLOAT, 3.0),
                }
            ),
            group="Base",
        )

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_vector,
            new_value=new_vector,
        )

        # Parent should be MODIFIED because expression changed
        assert prop_diff.state == DiffState.MODIFIED

        # The root path expression should be MODIFIED
        root_pd = next(pd for pd in prop_diff.path_diffs if pd.path == ".")
        assert root_pd.expression_state == DiffState.MODIFIED
        # But value should be UNCHANGED
        assert root_pd.value_state == DiffState.UNCHANGED

    def test_added_property_all_path_diffs_added(self) -> None:
        """ADDED property => all path diffs are ADDED."""
        new_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=None,
            new_value=new_vector,
        )

        # Parent should be ADDED
        assert prop_diff.state == DiffState.ADDED

        # All path diffs should be ADDED
        for pd in prop_diff.path_diffs:
            assert pd.value_state == DiffState.ADDED

    def test_deleted_property_all_path_diffs_deleted(self) -> None:
        """DELETED property => all path diffs are DELETED."""
        old_vector = Property.from_freecad([1.0, 2.0, 3.0], {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Vector",
            old_value=old_vector,
            new_value=None,
        )

        # Parent should be DELETED
        assert prop_diff.state == DiffState.DELETED

        # All path diffs should be DELETED
        for pd in prop_diff.path_diffs:
            assert pd.value_state == DiffState.DELETED

    def test_unchanged_primitive_property(self) -> None:
        """Primitive properties have path_diffs with root '.' only."""
        old_value = Property.from_freecad(10.0, {}, "Base")
        new_value = Property.from_freecad(10.0, {}, "Base")

        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.state == DiffState.UNCHANGED
        path_names = {pd.path for pd in prop_diff.path_diffs}
        # PrimitiveData produces only the root "." path
        assert path_names == {"."}

    @pytest.mark.parametrize(
        ("old_val, new_val, expected_state"),
        [
            (10.0, 10.0, DiffState.UNCHANGED),
            (10.0, 20.0, DiffState.MODIFIED),
            (None, 20.0, DiffState.ADDED),
            (10.0, None, DiffState.DELETED),
        ],
    )
    def test_primitive_property_state_variants(
        self,
        old_val,
        new_val,
        expected_state,  # type: ignore[no-untyped-def]
    ) -> None:
        """Parametrized test for primitive property state variants (UNCHANGED/MODIFIED/ADDED/DELETED)."""
        old_value = Property.from_freecad(old_val, {}, "Base") if old_val is not None else None
        new_value = Property.from_freecad(new_val, {}, "Base") if new_val is not None else None

        prop_diff = PropertyDiff(
            property_name="Length",
            old_value=old_value,
            new_value=new_value,
        )

        assert prop_diff.state == expected_state

    def test_both_none_unchanged(self) -> None:
        """PropertyDiff with both None values is UNCHANGED."""
        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=None,
            new_value=None,
        )

        assert prop_diff.state == DiffState.UNCHANGED
        assert prop_diff.path_diffs == []

    def test_path_diffs_sorted_with_root_first(self) -> None:
        """Path diffs are sorted with root '.' first."""
        old_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )
        new_placement = Property.from_freecad(
            {"position": (0.0, 0.0, 0.0), "rotation": (0.0, 0.0, 1.0, 0.0)}, {}, "Base"
        )

        prop_diff = PropertyDiff(
            property_name="Placement",
            old_value=old_placement,
            new_value=new_placement,
        )

        # First path should be "."
        assert prop_diff.path_diffs[0].path == "."
