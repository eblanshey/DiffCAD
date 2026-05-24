# File responsibility: Unit tests for FreeCAD visual diff document creation.

from __future__ import annotations

import sys
from types import ModuleType
from typing import Any

import pytest
from freecad.history_wb.infrastructure.freecad.freecad_visual_diff_creator import FreeCADVisualDiffCreator


class FakeShape:
    def __init__(self, name: str = "") -> None:
        self.name = name
        self.read_path = ""
        self.Placement: object | None = None

    def read(self, path: str) -> None:
        self.read_path = path
        self.name = path

    def cut(self, other: object) -> FakeShape:
        other_shape = other
        if not isinstance(other_shape, FakeShape):
            raise TypeError
        return FakeShape(f"{self.name} at {self.Placement} - {other_shape.name} at {other_shape.Placement}")

    def common(self, other: object) -> FakeShape:
        other_shape = other
        if not isinstance(other_shape, FakeShape):
            raise TypeError
        return FakeShape(f"{self.name} at {self.Placement} & {other_shape.name} at {other_shape.Placement}")


class FakeViewObject:
    def __init__(self) -> None:
        self.ShapeColor: tuple[float, float, float, float] | None = None
        self.LineColor: tuple[float, float, float, float] | None = None
        self.PointColor: tuple[float, float, float, float] | None = None
        self.Transparency: int | None = None
        self.Visibility = True


class FakeFeature:
    def __init__(self, name: str) -> None:
        self.name = name
        self.Label = ""
        self.Shape: object | None = None
        self.Placement: object | None = None
        self.ViewObject = FakeViewObject()
        self.children: list[FakeFeature] = []

    def addObject(self, feature: FakeFeature) -> None:
        self.children.append(feature)


class FakeDocument:
    def __init__(self, name: str) -> None:
        self.name = name
        self.features: list[FakeFeature] = []
        self.recomputed = False

    def addObject(self, _type_name: str, name: str) -> FakeFeature:
        feature = FakeFeature(name)
        self.features.append(feature)
        return feature

    def recompute(self) -> None:
        self.recomputed = True


class FakeApp:
    def __init__(self) -> None:
        self.documents: list[FakeDocument] = []

    def newDocument(self, name: str) -> FakeDocument:
        document = FakeDocument(name)
        self.documents.append(document)
        return document


class FakeContext:
    def __init__(self) -> None:
        self.app = FakeApp()


class FakeFreeCADGui(ModuleType):
    def __init__(self) -> None:
        super().__init__("FreeCADGui")
        self.commands: list[tuple[str, int]] = []

    def runCommand(self, name: str, mode: int) -> None:
        self.commands.append((name, mode))


class FakeVector:
    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FakeVector) and (self.x, self.y, self.z) == (other.x, other.y, other.z)

    def __repr__(self) -> str:
        return f"Vector({self.x}, {self.y}, {self.z})"


class FakeRotation:
    def __init__(self, axis: FakeVector, angle: float) -> None:
        self.axis = axis
        self.angle = angle

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FakeRotation) and (self.axis, self.angle) == (other.axis, other.angle)

    def __repr__(self) -> str:
        return f"Rotation({self.axis}, {self.angle})"


class FakePlacement:
    def __init__(self, base: FakeVector, rotation: FakeRotation) -> None:
        self.base = base
        self.rotation = rotation

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FakePlacement) and (self.base, self.rotation) == (other.base, other.rotation)

    def __repr__(self) -> str:
        return f"Placement({self.base}, {self.rotation})"


def test_visual_diff_creates_reference_and_colored_boolean_difference_features(
    monkeypatch: Any,
) -> None:
    fake_freecad_gui = _install_freecad_fakes(monkeypatch)

    ctx = FakeContext()
    document = FreeCADVisualDiffCreator(ctx).open_brep_visual_diff("old.brep", "new.brep", "Diff_Test_working")

    feature_by_name = {feature.name: feature for feature in document.features}
    expected_names = ["Old_Visual", "New_Visual", "Diff", "Unchanged_Visual", "Added_Visual", "Removed_Visual"]
    expected_labels = {name: name for name in expected_names}
    expected_shapes = {
        "Unchanged_Visual": "old.brep at Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), 0)) & new.brep at Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), 0))",
        "Added_Visual": "new.brep at Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), 0)) - old.brep at Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), 0))",
        "Removed_Visual": "old.brep at Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), 0)) - new.brep at Placement(Vector(0, 0, 0), Rotation(Vector(0, 0, 1), 0))",
    }
    expected_colors = {
        "Unchanged_Visual": (0.6, 0.6, 0.6, 1.0),
        "Added_Visual": (0.0, 0.8, 0.0, 1.0),
        "Removed_Visual": (0.9, 0.0, 0.0, 1.0),
    }
    expected_diff_children = ["Unchanged_Visual", "Added_Visual", "Removed_Visual"]

    assert list(feature_by_name) == expected_names
    assert {name: feature.Label for name, feature in feature_by_name.items()} == expected_labels
    assert {name: feature_by_name[name].Shape.name for name in expected_shapes} == expected_shapes
    assert _shape_colors_by_name(feature_by_name, expected_colors) == expected_colors
    assert _line_colors_by_name(feature_by_name, expected_colors) == expected_colors
    assert _point_colors_by_name(feature_by_name, expected_colors) == expected_colors
    assert _feature_transparency_by_name(feature_by_name) == {
        "Unchanged_Visual": 50,
        "Added_Visual": 50,
        "Removed_Visual": 50,
    }
    assert _feature_visibility_by_name(feature_by_name) == {"Old_Visual": False, "New_Visual": False}
    assert _feature_child_names(feature_by_name["Diff"]) == expected_diff_children
    assert document.recomputed is True
    assert fake_freecad_gui.commands == [("Std_ViewIsometric", 0), ("Std_ViewFitAll", 0)]


@pytest.mark.parametrize(
    ("old_brep_path", "new_brep_path", "expected_name", "expected_shape"),
    [
        ("old.brep", None, "Old_Visual", "old.brep"),
        (None, "new.brep", "New_Visual", "new.brep"),
    ],
)
def test_visual_diff_creates_single_visual_when_one_side_missing(
    monkeypatch: Any,
    old_brep_path: str | None,
    new_brep_path: str | None,
    expected_name: str,
    expected_shape: str,
) -> None:
    fake_freecad_gui = _install_freecad_fakes(monkeypatch)
    ctx = FakeContext()

    document = FreeCADVisualDiffCreator(ctx).open_brep_visual_diff(old_brep_path, new_brep_path, "Diff_Test_working")

    assert [feature.name for feature in document.features] == [expected_name]
    assert document.features[0].Label == expected_name
    assert document.features[0].Shape.name == expected_shape
    assert document.recomputed is True
    assert fake_freecad_gui.commands == [("Std_ViewIsometric", 0), ("Std_ViewFitAll", 0)]


def test_visual_diff_rejects_missing_old_and_new_paths() -> None:
    ctx = FakeContext()

    with pytest.raises(ValueError, match="At least one BREP path is required"):
        FreeCADVisualDiffCreator(ctx).open_brep_visual_diff(None, None, "Diff_Test_working")


def _install_freecad_fakes(monkeypatch: Any) -> FakeFreeCADGui:
    fake_part = ModuleType("Part")
    fake_part.Shape = FakeShape  # type: ignore[attr-defined]
    fake_freecad = ModuleType("FreeCAD")
    fake_freecad.Vector = FakeVector  # type: ignore[attr-defined]
    fake_freecad.Rotation = FakeRotation  # type: ignore[attr-defined]
    fake_freecad.Placement = FakePlacement  # type: ignore[attr-defined]
    fake_freecad_gui = FakeFreeCADGui()
    monkeypatch.setitem(sys.modules, "Part", fake_part)
    monkeypatch.setitem(sys.modules, "FreeCAD", fake_freecad)
    monkeypatch.setitem(sys.modules, "FreeCADGui", fake_freecad_gui)
    return fake_freecad_gui


def _feature_child_names(feature: FakeFeature) -> list[str]:
    return [child.name for child in feature.children]


def _shape_colors_by_name(
    feature_by_name: dict[str, FakeFeature], expected_colors: dict[str, tuple[float, float, float, float]]
) -> dict[str, tuple[float, float, float, float] | None]:
    return {name: feature_by_name[name].ViewObject.ShapeColor for name in expected_colors}


def _line_colors_by_name(
    feature_by_name: dict[str, FakeFeature], expected_colors: dict[str, tuple[float, float, float, float]]
) -> dict[str, tuple[float, float, float, float] | None]:
    return {name: feature_by_name[name].ViewObject.LineColor for name in expected_colors}


def _point_colors_by_name(
    feature_by_name: dict[str, FakeFeature], expected_colors: dict[str, tuple[float, float, float, float]]
) -> dict[str, tuple[float, float, float, float] | None]:
    return {name: feature_by_name[name].ViewObject.PointColor for name in expected_colors}


def _feature_transparency_by_name(feature_by_name: dict[str, FakeFeature]) -> dict[str, int]:
    return {
        name: feature.ViewObject.Transparency
        for name, feature in feature_by_name.items()
        if feature.ViewObject.Transparency is not None
    }


def _feature_visibility_by_name(feature_by_name: dict[str, FakeFeature]) -> dict[str, bool]:
    return {
        name: feature.ViewObject.Visibility
        for name, feature in feature_by_name.items()
        if not feature.ViewObject.Visibility
    }
