"""File responsibility: Compare snapshots action orchestration."""

from ....domain.diff.engine import DiffEngine
from ....domain.settings.repository import SettingsRepository
from ....domain.snapshots.repository import SnapshotRepository
from ....utils import Log
from ..result_models import CompareResult


class CompareSnapshotsAction:
    """Orchestrate snapshot comparison workflow.

    This action handles the complete flow of:
    1. Retrieving old snapshot from repository
    2. Retrieving new snapshot from repository
    3. Getting settings for exclusions
    4. Computing diff via DiffEngine
    5. Returning result

    Dependencies are injected for testability. Uses the unified Log class
    from utils for logging.
    """

    def __init__(
        self,
        snapshot_repo: SnapshotRepository,
        diff_engine: DiffEngine,
        settings_repo: SettingsRepository,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            snapshot_repo: Repository to retrieve snapshots
            diff_engine: Service to compute differences
            settings_repo: Repository for exclusion settings
        """
        self._snapshot_repo = snapshot_repo
        self._diff_engine = diff_engine
        self._settings_repo = settings_repo

    def execute(self, old_id: str, new_id: str) -> CompareResult:
        """Compare two snapshots.

        Args:
            old_id: ID of older snapshot to compare from
            new_id: ID of newer snapshot to compare to

        Returns:
            CompareResult with diff data or error message.
        """
        # Step 1: Retrieve old snapshot
        old_snapshot = self._snapshot_repo.get_snapshot(old_id)
        if old_snapshot is None:
            error_msg = f"Old snapshot '{old_id}' not found"
            Log.error(error_msg)
            return CompareResult(
                success=False,
                diff_result=None,
                error_message=error_msg,
            )

        # Step 2: Retrieve new snapshot
        new_snapshot = self._snapshot_repo.get_snapshot(new_id)
        if new_snapshot is None:
            error_msg = f"New snapshot '{new_id}' not found"
            Log.error(error_msg)
            return CompareResult(
                success=False,
                diff_result=None,
                error_message=error_msg,
            )

        # Step 3: Get settings for exclusions
        Log.info("Loading exclusion settings")
        settings = self._settings_repo.get_settings()

        # Step 4: Compute diff
        Log.info(f"Comparing snapshots: {old_id} vs {new_id}")
        try:
            diff_result = self._diff_engine.compare(
                old_snapshot,
                new_snapshot,
                excluded_types=settings.excluded_types,
                excluded_properties=settings.excluded_properties,
            )
        except (ValueError, TypeError, AttributeError) as e:
            error_msg = f"Failed to compute diff: {str(e)}"
            Log.error(error_msg)
            return CompareResult(
                success=False,
                diff_result=None,
                error_message=error_msg,
            )
        except Exception as e:
            # Catch-all for unexpected errors during diff computation
            error_msg = f"Unexpected error during diff computation: {str(e)}"
            Log.exception(error_msg)
            return CompareResult(
                success=False,
                diff_result=None,
                error_message=error_msg,
            )

        # Step 5: Return success
        Log.info("Diff computation completed successfully")
        return CompareResult(
            success=True,
            diff_result=diff_result,
            error_message=None,
        )
