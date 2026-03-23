"""File responsibility: Take snapshot action orchestration."""

import datetime

from ....domain.snapshots.extractor import SnapshotExtractor
from ....domain.snapshots.repository import SnapshotRepository
from ....infrastructure.freecad.ports import FreeCadPort
from ..result_models import SnapshotResult


class TakeSnapshotAction:
    """Orchestrate snapshot creation workflow.

    This action handles the complete flow of:
    1. Getting the active document via FreeCadPort
    2. Extracting the tree structure via SnapshotExtractor
    3. Saving to repository via SnapshotRepository
    4. Returning result

    Dependencies are injected for testability.
    """

    def __init__(
        self,
        freecad_port: FreeCadPort,
        extractor: SnapshotExtractor,
        snapshot_repo: SnapshotRepository,
    ) -> None:
        """Initialize with required dependencies.

        Args:
            freecad_port: Port to interact with FreeCAD application
            extractor: Service to extract tree from document
            snapshot_repo: Repository to save snapshots
        """
        self._freecad_port = freecad_port
        self._extractor = extractor
        self._snapshot_repo = snapshot_repo

    def execute(self, name: str | None = None) -> SnapshotResult:
        """Create a snapshot of the active document.

        Args:
            name: Optional custom snapshot name. Auto-generated if not provided.

        Returns:
            SnapshotResult with success status and snapshot details.
        """
        # Step 1: Get active document
        doc = self._freecad_port.get_active_document()
        if doc is None:
            error_msg = "No active document available"
            self._freecad_port.message(error_msg)
            return SnapshotResult(
                success=False,
                snapshot_id=None,
                snapshot_name=None,
                error_message=error_msg,
            )

        # Step 2: Generate name if not provided
        if name is None:
            name = self._generate_default_name(doc)

        # Step 3: Extract tree structure using the port (extractor needs port)
        try:
            snapshot = self._extractor.extract_tree(self._freecad_port)
        except (ValueError, TypeError, AttributeError) as e:
            error_msg = f"Failed to extract snapshot: {str(e)}"
            self._freecad_port.message(error_msg)
            return SnapshotResult(
                success=False,
                snapshot_id=None,
                snapshot_name=None,
                error_message=error_msg,
            )
        except Exception as e:
            # Catch-all for unexpected errors during extraction
            error_msg = f"Unexpected error during snapshot extraction: {str(e)}"
            self._freecad_port.message(error_msg)
            return SnapshotResult(
                success=False,
                snapshot_id=None,
                snapshot_name=None,
                error_message=error_msg,
            )

        # Step 4: Save to repository
        try:
            snapshot_id = self._snapshot_repo.add_snapshot(snapshot)
        except (ValueError, KeyError) as e:
            error_msg = f"Failed to save snapshot: {str(e)}"
            self._freecad_port.message(error_msg)
            return SnapshotResult(
                success=False,
                snapshot_id=None,
                snapshot_name=None,
                error_message=error_msg,
            )
        except Exception as e:
            # Catch-all for unexpected errors during save
            error_msg = f"Unexpected error during snapshot save: {str(e)}"
            self._freecad_port.message(error_msg)
            return SnapshotResult(
                success=False,
                snapshot_id=None,
                snapshot_name=None,
                error_message=error_msg,
            )

        # Step 5: Return success
        success_msg = f"Snapshot '{name}' created successfully"
        self._freecad_port.message(success_msg)
        return SnapshotResult(
            success=True,
            snapshot_id=snapshot_id,
            snapshot_name=name,
            error_message=None,
        )

    def _generate_default_name(self, doc: object) -> str:
        """Generate a default name that ALWAYS includes timestamp.

        Format: {document_name}_{timestamp}
        Example: "MyPart_20240319_143022"

        This ensures uniqueness and chronological ordering without verbose names.

        Args:
            doc: FreeCAD document object

        Returns:
            Generated snapshot name with timestamp
        """
        # Try to get document name for readability
        try:
            doc_name = getattr(doc, "Name", None)
            if doc_name is None or doc_name == "":
                doc_name = "snapshot"
        except (AttributeError, TypeError):
            doc_name = "snapshot"

        # Always include timestamp for uniqueness and traceability
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{doc_name}_{timestamp}"
