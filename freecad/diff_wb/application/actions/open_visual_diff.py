# File responsibility: Open visual old/new BREP comparison from FCStd snapshots (orchestration only).
"""Open visual old/new BREP comparison from FCStd snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ...domain.diff.visual_diff import FreeCADVisualDiffPort
from ...domain.freecad_ports import FreeCadFileManagerPort
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...ui.translation_strings import (
    VISUAL_DIFF_IMPORT_FAILURE_MESSAGE,
    VISUAL_DIFF_INVALID_REQUEST_MESSAGE,
    VISUAL_DIFF_MISSING_BREP_MESSAGE,
    VISUAL_DIFF_MISSING_FCSTD_MESSAGE,
)
from ...utils import Log
from .result_models import Result


class VisualDiffRequestType(Enum):
    """Visual diff request source type selected by history UI."""

    WORKING = "working"
    STAGING = "staging"
    COMMIT = "commit"


@dataclass(frozen=True)
class OpenVisualDiffRequest:
    """Request payload for opening one visual feature diff."""

    repo: GitRepository
    git_path: str
    node_path: str
    type: VisualDiffRequestType
    old_commit: str | None = None
    new_commit: str | None = None
    property_name: str = "Shape"


class OpenVisualDiffAction:
    """Orchestrate visual diff: prepare revisions, extract BREPs, open comparison."""

    def __init__(
        self,
        git_service: GitService,
        visual_diff: FreeCADVisualDiffPort,
        file_manager: FreeCadFileManagerPort,
    ) -> None:
        """Initialize action with dependencies."""
        self._git_service = git_service
        self._visual_diff = visual_diff
        self._file_manager = file_manager

    def execute(self, request: OpenVisualDiffRequest) -> Result:
        """Open a visual diff for one feature shape from requested repository state."""
        object_name = request.node_path.rsplit("/", 1)[-1]
        try:
            revisions = self._request_revisions(request)
        except RuntimeError as err:
            Log.warning(f"Invalid visual diff request: {err}")
            return Result.failure(VISUAL_DIFF_INVALID_REQUEST_MESSAGE)

        extract_root_old, extract_root_new = self._prepare_revisions(request, revisions)
        if extract_root_old is None and extract_root_new is None:
            return Result.failure(VISUAL_DIFF_MISSING_FCSTD_MESSAGE)

        old_brep, new_brep = self._find_breps(request, object_name, extract_root_old, extract_root_new)
        if old_brep is None and new_brep is None:
            return Result.failure(VISUAL_DIFF_MISSING_BREP_MESSAGE)

        document_name = self._construct_document_name(request, object_name)
        try:
            self._visual_diff.open_brep_visual_diff(
                str(old_brep) if old_brep is not None else None,
                str(new_brep) if new_brep is not None else None,
                document_name,
            )
        except Exception as err:  # noqa: BLE001
            Log.warning(f"Failed to open visual diff document: {err}")
            return Result.failure(VISUAL_DIFF_IMPORT_FAILURE_MESSAGE)

        return Result.success(True)

    def _prepare_revisions(
        self,
        request: OpenVisualDiffRequest,
        revisions: tuple[str, str],
    ) -> tuple[Path | None, Path | None]:
        """Prepare old and new revision extraction roots."""
        old_revision, new_revision = revisions
        return (
            self._file_manager.prepare_document_revision(request.repo, request.git_path, old_revision),
            self._file_manager.prepare_document_revision(request.repo, request.git_path, new_revision),
        )

    def _find_breps(
        self,
        request: OpenVisualDiffRequest,
        object_name: str,
        extract_root_old: Path | None,
        extract_root_new: Path | None,
    ) -> tuple[Path | None, Path | None]:
        """Find old and new BREP paths in prepared extraction roots."""
        brep_name = f"{object_name}.{request.property_name}.brp"
        old_brep = self._file_manager.find_extracted_file(extract_root_old, brep_name) if extract_root_old else None
        new_brep = self._file_manager.find_extracted_file(extract_root_new, brep_name) if extract_root_new else None
        return old_brep, new_brep

    def _request_revisions(self, request: OpenVisualDiffRequest) -> tuple[str, str]:
        """Map request type to old and new FCStd revision tokens."""
        if request.type is VisualDiffRequestType.WORKING:
            return "staging", "working"
        if request.type is VisualDiffRequestType.STAGING:
            return "HEAD", "staging"
        if request.type is VisualDiffRequestType.COMMIT:
            if request.old_commit is None or request.new_commit is None:
                raise RuntimeError("Commit visual diff request missing old or new commit")
            return request.old_commit, request.new_commit
        raise RuntimeError(f"Unknown visual diff request type: {request.type}")

    def _construct_document_name(self, request: OpenVisualDiffRequest, feature_name: str) -> str:
        """Construct document name as Compare_{File}_{Feature}."""
        filename = Path(request.git_path).stem
        return f"Compare_{filename}_{feature_name}"
