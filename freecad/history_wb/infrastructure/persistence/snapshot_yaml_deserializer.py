# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Infrastructure adapter implementing snapshot YAML deserialization port.
"""Infrastructure snapshot deserializer backed by SnapshotYamlSerializer."""

from ...domain.snapshots.models import Snapshot
from ...domain.snapshots.serializer import SnapshotDeserializer
from .snapshot_yaml import SnapshotYamlSerializer


class SnapshotYamlDeserializer(SnapshotDeserializer):
    """Deserialize snapshot YAML using infrastructure serializer implementation."""

    def from_yaml(self, yaml_string: str) -> Snapshot:
        """Deserialize YAML text into Snapshot domain model."""
        return SnapshotYamlSerializer.from_yaml(yaml_string)
