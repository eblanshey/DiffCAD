# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Shared parsing and serialization helpers for line-based
# Diff Workbench settings text persisted in preferences and edited in UI.
"""Shared codecs for line-based settings text formats."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence


def parse_list_lines(raw: str) -> list[str]:
    """Parse one-value-per-line text into normalized list values."""
    return [line.strip() for line in raw.splitlines() if line.strip()]


def serialize_list_lines(values: Iterable[str]) -> str:
    """Serialize list values into one-value-per-line normalized text."""
    normalized = [value.strip() for value in values if value.strip()]
    return "\n".join(normalized)


def parse_by_type_lines(raw: str) -> dict[str, list[str]]:
    """Parse ``TypeId -> Property`` lines into mapping values."""
    parsed: dict[str, list[str]] = {}
    for line in parse_list_lines(raw):
        parsed_line = _parse_by_type_line(line)
        if parsed_line is None:
            continue
        type_id, property_name = parsed_line
        parsed.setdefault(type_id, []).append(property_name)
    return parsed


def serialize_by_type_lines(values: Mapping[str, Sequence[str]]) -> str:
    """Serialize mapping values into ``TypeId -> Property`` lines."""
    lines: list[str] = []
    for type_id in sorted(values):
        properties = [prop.strip() for prop in values[type_id] if prop.strip()]
        lines.extend(f"{type_id} -> {property_name}" for property_name in properties)
    return "\n".join(lines)


def _parse_by_type_line(line: str) -> tuple[str, str] | None:
    if "->" not in line:
        return None
    type_id, property_name = [part.strip() for part in line.split("->", 1)]
    if not type_id or not property_name:
        return None
    return type_id, property_name
