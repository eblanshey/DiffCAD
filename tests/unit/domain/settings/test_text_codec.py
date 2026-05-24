# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Unit tests for shared line-based settings text codec helpers.
"""Tests for settings text codec helpers."""

from freecad.history_wb.domain.settings.text_codec import (
    parse_by_type_lines,
    parse_list_lines,
    serialize_by_type_lines,
    serialize_list_lines,
)


def test_parse_list_lines_normalizes_whitespace_and_blanks() -> None:
    assert parse_list_lines("  App::Part\n\n App::Link  \n") == ["App::Part", "App::Link"]


def test_parse_by_type_lines_ignores_invalid_lines() -> None:
    assert parse_by_type_lines("App::Part -> Label\nInvalid\nSketcher::SketchObject -> Geometry") == {
        "App::Part": ["Label"],
        "Sketcher::SketchObject": ["Geometry"],
    }


def test_serialize_helpers_emit_deterministic_line_format() -> None:
    assert serialize_list_lines(["  Label2  ", "", " TimeStamp "]) == "Label2\nTimeStamp"
    assert (
        serialize_by_type_lines(
            {
                "Sketcher::SketchObject": [" Geometry "],
                "App::Part": [" Label ", "", " Tip "],
            }
        )
        == "App::Part -> Label\nApp::Part -> Tip\nSketcher::SketchObject -> Geometry"
    )
