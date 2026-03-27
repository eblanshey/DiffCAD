"""File responsibility: Application-level tests for CompareSnapshotsAction.

These tests verify the complete compare snapshots workflow using real domain services
(SnapshotExtractor, DiffEngine) with fake ports (FakeFreeCadPort, InMemorySnapshotRepository).

See AGENTS.md in this directory for more information about application action testing.
"""

from freecad.diff_wb.application.actions.commands.compare_snapshots import CompareSnapshotsAction
from freecad.diff_wb.domain.diff.engine import DiffEngine
from freecad.diff_wb.domain.diff.models import DiffState
from freecad.diff_wb.domain.settings.models import Settings
from freecad.diff_wb.domain.settings.repository import SettingsRepository
from freecad.diff_wb.domain.snapshots.models import Snapshot
from freecad.diff_wb.domain.snapshots.repository import InMemorySnapshotRepository
from freecad.diff_wb.domain.tree.node import TreeNode


class FakeSettingsRepository(SettingsRepository):
    """Fake settings repository for testing."""

    def __init__(self, excluded_types: list[str] | None = None, excluded_properties: list[str] | None = None):
        """Initialize with custom exclusions."""
        self._excluded_types = excluded_types or []
        self._excluded_properties = excluded_properties or []

    def get_excluded_types(self) -> list[str]:
        """Get excluded types."""
        return self._excluded_types.copy()

    def get_excluded_properties(self) -> list[str]:
        """Get excluded properties."""
        return self._excluded_properties.copy()

    def get_settings(self) -> Settings:
        """Get settings."""
        return Settings(
            excluded_types=self._excluded_types.copy(),
            excluded_properties=self._excluded_properties.copy(),
        )


class TestCompareSnapshotsAction:
    """Application-level tests for CompareSnapshotsAction using real domain services."""

    def test_compare_snapshots_with_existing_snapshots(self) -> None:
        """Test successful comparison of two existing snapshots."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        from freecad.diff_wb.domain.tree.property import Property, PropertyType

        # Create and add old snapshot with a Label property
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Part",
                    type_id="Part::Feature",
                    label="OldPart",
                    path="Part",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="OldPart")},
                    children=[],
                )
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        # Create and add new snapshot with a changed Label property
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Part",
                    type_id="Part::Feature",
                    label="NewPart",
                    path="Part",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="NewPart")},
                    children=[],
                )
            ],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert result.error_message is None
        # Verify the diff detected the Label property change
        assert len(result.diff_result.node_diffs) == 1
        node_diff = result.diff_result.node_diffs[0]
        assert node_diff.path == "Part"
        assert node_diff.state == DiffState.MODIFIED
        # Verify property changes
        assert len(node_diff.property_diffs) == 1
        prop_diff = node_diff.property_diffs[0]
        assert prop_diff.property_name == "Label"
        assert prop_diff.state == DiffState.MODIFIED
        assert prop_diff.old_value is not None
        assert prop_diff.old_value.value == "OldPart"
        assert prop_diff.new_value is not None
        assert prop_diff.new_value.value == "NewPart"

    def test_compare_snapshots_old_not_found(self) -> None:
        """Test comparison when old snapshot doesn't exist."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        # Add only a new snapshot (no old one)
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[],
        )
        snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act - use non-existent old ID
        result = action.execute(old_id="non-existent-old", new_id="any-id")

        # Assert
        assert result.success is False
        assert result.diff_result is None
        assert result.error_message == "Old snapshot 'non-existent-old' not found"

    def test_compare_snapshots_new_not_found(self) -> None:
        """Test comparison when new snapshot doesn't exist."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        # Add only old snapshot
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act - use non-existent new ID
        result = action.execute(old_id=old_id, new_id="non-existent-new")

        # Assert
        assert result.success is False
        assert result.diff_result is None
        assert result.error_message == "New snapshot 'non-existent-new' not found"

    def test_compare_snapshots_empty_snapshots(self) -> None:
        """Test comparison of two empty snapshots."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        # Create and add empty snapshots
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert result.diff_result.node_diffs == []
        assert result.diff_result.summary.added_nodes == 0
        assert result.diff_result.summary.deleted_nodes == 0
        assert result.diff_result.summary.modified_nodes == 0

    def test_compare_snapshots_with_exclusions(self) -> None:
        """Test comparison respects exclusion settings."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        # Configure exclusions
        settings_repo = FakeSettingsRepository(
            excluded_types=["App::Origin"],
            excluded_properties=["TimeStamp"],
        )
        diff_engine = DiffEngine(settings_repo=settings_repo)

        # Create snapshots with nodes that should be excluded
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Origin",
                    type_id="App::Origin",  # Should be excluded
                    label="Origin",
                    path="Origin",
                    is_root=True,
                    properties={},
                    children=[],
                )
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Origin",
                    type_id="App::Origin",  # Should be excluded
                    label="Origin",
                    path="Origin",
                    is_root=True,
                    properties={},
                    children=[],
                )
            ],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        # Origin nodes should be excluded from the diff
        for node_diff in result.diff_result.node_diffs:
            assert node_diff.type_id != "App::Origin"

    def test_compare_snapshots_detects_added_node(self) -> None:
        """Test that added nodes are detected in comparison."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        # Old snapshot has one node
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="ExistingPart",
                    type_id="Part::Feature",
                    label="ExistingPart",
                    path="ExistingPart",
                    is_root=True,
                    properties={},
                    children=[],
                )
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        # New snapshot has an additional node
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="ExistingPart",
                    type_id="Part::Feature",
                    label="ExistingPart",
                    path="ExistingPart",
                    is_root=True,
                    properties={},
                    children=[],
                ),
                TreeNode(
                    name="NewPart",
                    type_id="Part::Feature",
                    label="NewPart",
                    path="NewPart",
                    is_root=True,
                    properties={},
                    children=[],
                ),
            ],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        # Find the NewPart node
        new_part_diffs = [n for n in result.diff_result.node_diffs if n.path == "NewPart"]
        assert len(new_part_diffs) == 1
        assert new_part_diffs[0].state == DiffState.ADDED

    def test_compare_snapshots_detects_deleted_node(self) -> None:
        """Test that deleted nodes are detected in comparison."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        # Old snapshot has one node
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="ExistingPart",
                    type_id="Part::Feature",
                    label="ExistingPart",
                    path="ExistingPart",
                    is_root=True,
                    properties={},
                    children=[],
                ),
                TreeNode(
                    name="DeletedPart",
                    type_id="Part::Feature",
                    label="DeletedPart",
                    path="DeletedPart",
                    is_root=True,
                    properties={},
                    children=[],
                ),
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        # New snapshot has one less node (DeletedPart removed)
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="ExistingPart",
                    type_id="Part::Feature",
                    label="ExistingPart",
                    path="ExistingPart",
                    is_root=True,
                    properties={},
                    children=[],
                ),
            ],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        # Find the DeletedPart node
        deleted_part_diffs = [n for n in result.diff_result.node_diffs if n.path == "DeletedPart"]
        assert len(deleted_part_diffs) == 1
        assert deleted_part_diffs[0].state == DiffState.DELETED

    def test_compare_snapshots_multiple_changes(self) -> None:
        """Test detection of multiple nodes with different states."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        from freecad.diff_wb.domain.tree.property import Property, PropertyType

        # Old snapshot
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                # This node will be unchanged
                TreeNode(
                    name="UnchangedPart",
                    type_id="Part::Feature",
                    label="UnchangedPart",
                    path="UnchangedPart",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="UnchangedPart")},
                    children=[],
                ),
                # This node will be modified (Label changed)
                TreeNode(
                    name="ModifiedPart",
                    type_id="Part::Feature",
                    label="ModifiedPart",
                    path="ModifiedPart",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="ModifiedPart")},
                    children=[],
                ),
                # This node will be deleted
                TreeNode(
                    name="DeletedPart",
                    type_id="Part::Feature",
                    label="DeletedPart",
                    path="DeletedPart",
                    is_root=True,
                    properties={},
                    children=[],
                ),
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        # New snapshot
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                # Unchanged
                TreeNode(
                    name="UnchangedPart",
                    type_id="Part::Feature",
                    label="UnchangedPart",
                    path="UnchangedPart",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="UnchangedPart")},
                    children=[],
                ),
                # Modified - Label changed
                TreeNode(
                    name="ModifiedPart",
                    type_id="Part::Feature",
                    label="NewLabel",
                    path="ModifiedPart",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="NewLabel")},
                    children=[],
                ),
                # Added - new node
                TreeNode(
                    name="AddedPart",
                    type_id="Part::Feature",
                    label="AddedPart",
                    path="AddedPart",
                    is_root=True,
                    properties={},
                    children=[],
                ),
            ],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        # Verify summary counts - note: unchanged nodes are NOT included in the diff
        assert result.diff_result.summary.added_nodes == 1
        assert result.diff_result.summary.deleted_nodes == 1
        assert result.diff_result.summary.modified_nodes == 1
        # Unchanged nodes are filtered out by the diff engine
        assert result.diff_result.summary.unchanged_nodes == 0
        # Verify specific changes - total node diffs should be 3 (added, deleted, modified)
        assert len(result.diff_result.node_diffs) == 3
        modified_parts = [n for n in result.diff_result.node_diffs if n.path == "ModifiedPart"]
        assert len(modified_parts) == 1
        assert modified_parts[0].state == DiffState.MODIFIED
        added_parts = [n for n in result.diff_result.node_diffs if n.path == "AddedPart"]
        assert len(added_parts) == 1
        assert added_parts[0].state == DiffState.ADDED
        deleted_parts = [n for n in result.diff_result.node_diffs if n.path == "DeletedPart"]
        assert len(deleted_parts) == 1
        assert deleted_parts[0].state == DiffState.DELETED

    def test_compare_snapshots_nested_children(self) -> None:
        """Test detection of changes in child nodes."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        from freecad.diff_wb.domain.tree.property import Property, PropertyType

        # Old snapshot with child nodes
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Body",
                    type_id="PartDesign::Body",
                    label="Body",
                    path="Body",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="Body")},
                    children=[
                        TreeNode(
                            name="Pad",
                            type_id="PartDesign::Pad",
                            label="Pad",
                            path="Body/Pad",
                            is_root=False,
                            properties={"Label": Property(type_=PropertyType.STRING, value="Pad")},
                            children=[],
                        ),
                        TreeNode(
                            name="Pocket",
                            type_id="PartDesign::Pocket",
                            label="Pocket",
                            path="Body/Pocket",
                            is_root=False,
                            properties={"Label": Property(type_=PropertyType.STRING, value="Pocket")},
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        # New snapshot with changes in children
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Body",
                    type_id="PartDesign::Body",
                    label="Body",
                    path="Body",
                    is_root=True,
                    properties={"Label": Property(type_=PropertyType.STRING, value="Body")},
                    children=[
                        # Pad modified - Label changed
                        TreeNode(
                            name="Pad",
                            type_id="PartDesign::Pad",
                            label="NewPad",
                            path="Body/Pad",
                            is_root=False,
                            properties={"Label": Property(type_=PropertyType.STRING, value="NewPad")},
                            children=[],
                        ),
                        # Pocket deleted (not present in new snapshot)
                        # Added: Fillet child
                        TreeNode(
                            name="Fillet",
                            type_id="PartDesign::Fillet",
                            label="Fillet",
                            path="Body/Fillet",
                            is_root=False,
                            properties={"Label": Property(type_=PropertyType.STRING, value="Fillet")},
                            children=[],
                        ),
                    ],
                ),
            ],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        # The diff should detect changes in child nodes
        # Body is now included as a placeholder parent to preserve hierarchy
        assert len(result.diff_result.node_diffs) == 1
        # Body should be the root with children nested under it
        body_diff = result.diff_result.node_diffs[0]
        assert body_diff.path == "Body"
        assert body_diff.state == DiffState.UNCHANGED
        assert len(body_diff.children) == 3
        # Check that child changes are properly nested under Body
        pad_diffs = [n for n in body_diff.children if n.path == "Body/Pad"]
        assert len(pad_diffs) == 1
        assert pad_diffs[0].state == DiffState.MODIFIED
        pocket_diffs = [n for n in body_diff.children if n.path == "Body/Pocket"]
        assert len(pocket_diffs) == 1
        assert pocket_diffs[0].state == DiffState.DELETED
        fillet_diffs = [n for n in body_diff.children if n.path == "Body/Fillet"]
        assert len(fillet_diffs) == 1
        assert fillet_diffs[0].state == DiffState.ADDED
        # Verify summary counts
        assert result.diff_result.summary.modified_nodes == 1
        assert result.diff_result.summary.deleted_nodes == 1
        assert result.diff_result.summary.added_nodes == 1

    def test_compare_snapshots_property_value_changes(self) -> None:
        """Test detection of numeric and string property value differences."""
        # Arrange
        snapshot_repo = InMemorySnapshotRepository()
        settings_repo = FakeSettingsRepository()
        diff_engine = DiffEngine(settings_repo=settings_repo)

        from freecad.diff_wb.domain.tree.property import Property, PropertyType

        # Old snapshot with various property types
        old_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Part",
                    type_id="Part::Feature",
                    label="Part",
                    path="Part",
                    is_root=True,
                    properties={
                        "Label": Property(type_=PropertyType.STRING, value="OldLabel"),
                        "Length": Property(type_=PropertyType.FLOAT, value=10.0),
                        "Width": Property(type_=PropertyType.FLOAT, value=5.0),
                    },
                    children=[],
                ),
            ],
        )
        old_id = snapshot_repo.add_snapshot(old_snapshot)

        # New snapshot with changed property values
        new_snapshot = Snapshot(
            snapshot_id="",
            document_name="TestDoc",
            timestamp=__import__("datetime").datetime.now(),
            root_nodes=[
                TreeNode(
                    name="Part",
                    type_id="Part::Feature",
                    label="Part",
                    path="Part",
                    is_root=True,
                    properties={
                        "Label": Property(type_=PropertyType.STRING, value="NewLabel"),
                        "Length": Property(type_=PropertyType.FLOAT, value=20.0),
                        "Width": Property(type_=PropertyType.FLOAT, value=5.0),  # Unchanged
                    },
                    children=[],
                ),
            ],
        )
        new_id = snapshot_repo.add_snapshot(new_snapshot)

        action = CompareSnapshotsAction(
            snapshot_repo=snapshot_repo,
            diff_engine=diff_engine,
            settings_repo=settings_repo,
        )

        # Act
        result = action.execute(old_id=old_id, new_id=new_id)

        # Assert
        assert result.success is True
        assert result.diff_result is not None
        assert len(result.diff_result.node_diffs) == 1
        node_diff = result.diff_result.node_diffs[0]
        assert node_diff.state == DiffState.MODIFIED
        # Verify property changes - all properties are included (changed and unchanged)
        changed_props = [p for p in node_diff.property_diffs if p.state != DiffState.UNCHANGED]
        assert len(changed_props) == 2
        # Total property diffs should be 3 (all properties included, including unchanged)
        assert len(node_diff.property_diffs) == 3
        # Find specific property changes
        label_props = [p for p in node_diff.property_diffs if p.property_name == "Label"]
        assert len(label_props) == 1
        assert label_props[0].state == DiffState.MODIFIED
        assert label_props[0].old_value is not None
        assert label_props[0].old_value.value == "OldLabel"
        assert label_props[0].new_value is not None
        assert label_props[0].new_value.value == "NewLabel"
        length_props = [p for p in node_diff.property_diffs if p.property_name == "Length"]
        assert len(length_props) == 1
        assert length_props[0].state == DiffState.MODIFIED
        assert length_props[0].old_value is not None
        assert length_props[0].old_value.value == 10.0
        assert length_props[0].new_value is not None
        assert length_props[0].new_value.value == 20.0
        # Width should be in the diff as unchanged
        width_props = [p for p in node_diff.property_diffs if p.property_name == "Width"]
        assert len(width_props) == 1
        assert width_props[0].state == DiffState.UNCHANGED
