# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: Persistence adapters for snapshot storage and retrieval using FreeCAD's document system.
"""Persistence infrastructure adapters."""

from freecad.history_wb.infrastructure.persistence.snapshot_yaml import SnapshotYamlSerializer


__all__: list[str] = ["SnapshotYamlSerializer"]
