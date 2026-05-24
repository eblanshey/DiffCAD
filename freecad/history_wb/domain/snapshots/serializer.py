# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Snapshot serialization/deserialization domain port contracts.
"""Snapshot serialization/deserialization port contracts."""

from typing import Protocol

from .models import Snapshot


class SnapshotDeserializer(Protocol):
    """Interface for converting snapshot YAML into Snapshot model."""

    def from_yaml(self, yaml_string: str) -> Snapshot:
        """Deserialize snapshot YAML string into Snapshot.

        Args:
            yaml_string: Snapshot YAML content.

        Returns:
            Parsed Snapshot model.
        """
        ...
