# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for presentation models.

import dataclasses

import pytest
from freecad.history_wb.domain.diff.models import DiffState
from freecad.history_wb.ui.presenters.presentation_models import (
    DiffTreePresentation,
    NodePresentation,
    PropertyPresentation,
    SnapshotPresentation,
)


@pytest.mark.parametrize(
    ("model", "attr_name", "new_value"),
    [
        (
            NodePresentation(
                path="Part", type_id="Part::Feature", label="Part", state=DiffState.MODIFIED, has_changes=True
            ),
            "path",
            "X",
        ),
        (PropertyPresentation(name="Length", state=DiffState.MODIFIED), "name", "X"),
        (SnapshotPresentation(id="snap-1", name="v1", created_at="2024-01-01T00:00:00Z", node_count=10), "id", "X"),
        (DiffTreePresentation(nodes=[], git_path="doc.FCStd", indicators=[]), "git_path", "X"),
    ],
)
def test_presentation_models_are_frozen(model, attr_name: str, new_value: str) -> None:
    """All presentation models are frozen dataclasses."""
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(model, attr_name, new_value)  # type: ignore[arg-type]


def test_node_presentation_children_independence() -> None:
    """NodePresentation instances have independent children lists."""
    node1 = NodePresentation(path="A", type_id="Part::Feature", label="A", state=DiffState.UNCHANGED, has_changes=False)
    node2 = NodePresentation(path="B", type_id="Part::Feature", label="B", state=DiffState.UNCHANGED, has_changes=False)

    assert node1.children is not node2.children
    assert node1.children == []


def test_property_presentation_children_independence() -> None:
    """PropertyPresentation instances have independent children lists."""
    prop1 = PropertyPresentation(name="Length1", state=DiffState.MODIFIED)
    prop2 = PropertyPresentation(name="Length2", state=DiffState.MODIFIED)

    assert prop1.children is not prop2.children
    assert prop1.children == []


def test_diff_tree_presentation_indicators_independence() -> None:
    """DiffTreePresentation instances have independent indicators lists."""
    tree1 = DiffTreePresentation(nodes=[], git_path="a.FCStd", indicators=[])
    tree2 = DiffTreePresentation(nodes=[], git_path="b.FCStd", indicators=[])

    assert tree1.indicators is not tree2.indicators


def test_diff_tree_presentation_fields_defaults() -> None:
    """DiffTreePresentation fields and defaults used by presenters and views."""
    tree = DiffTreePresentation(nodes=[], git_path="doc.FCStd", indicators=[])

    assert tree.nodes == []
    assert tree.git_path == "doc.FCStd"
    assert tree.indicators == []
    assert tree.stage_button_enabled is False
