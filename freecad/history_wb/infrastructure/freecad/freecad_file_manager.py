# File responsibility: FreeCAD document revision file management (storage, extraction, lookup).
"""FreeCAD document revision file management."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from ...domain.freecad_ports import FreeCadFileManagerPort
from ...domain.git.git_service import GitService
from ...domain.git.models import GitRepository
from ...utils import Log


_VISUAL_DIFF_CACHE_ROOT = Path(tempfile.gettempdir()) / "diffcad" / "visual_diff"


class FreeCadFileManagerAdapter(FreeCadFileManagerPort):
    """Infrastructure adapter for FreeCAD document revision file management."""

    def __init__(self, git_service: GitService) -> None:
        """Initialize adapter with git service."""
        self._git_service = git_service

    def prepare_document_revision(self, repo: GitRepository, git_path: str, revision: str) -> Path | None:
        """Materialize and extract requested document revision."""
        revision_type, archive_path, extract_dir = self._compute_paths(repo, git_path, revision)
        if not self._materialize(repo, git_path, revision, revision_type, archive_path):
            return None
        if not self._extract_safely(archive_path, extract_dir, revision_type):
            return None
        return extract_dir

    def find_extracted_file(self, extract_root: Path, file_name: str) -> Path | None:
        """Find file by name inside extracted document tree."""
        try:
            for path in extract_root.rglob(file_name):
                if path.name == file_name:
                    return path
            return None
        except OSError as err:
            Log.warning(f"Failed to search for file in extracted tree: {err}")
            return None

    def _compute_paths(self, repo: GitRepository, git_path: str, revision: str) -> tuple[str, Path, Path]:
        """Compute storage paths for working, staging, or commit revision."""
        file_name = Path(git_path).name
        if revision == "working":
            archive_path = _VISUAL_DIFF_CACHE_ROOT / "working" / file_name
            return "working", archive_path, archive_path.with_suffix("")
        if revision == "staging":
            archive_path = _VISUAL_DIFF_CACHE_ROOT / "staging" / file_name
            return "staging", archive_path, archive_path.with_suffix("")

        resolved_hash = self._git_service.resolve_ref(repo, revision)
        if resolved_hash is None:
            Log.warning(f"Failed to resolve commit ref for visual diff: {revision}")
            return "commits", Path(), Path()

        archive_path = _VISUAL_DIFF_CACHE_ROOT / "commits" / resolved_hash[:7] / file_name
        return "commits", archive_path, archive_path.with_suffix("")

    def _materialize(
        self,
        repo: GitRepository,
        git_path: str,
        revision: str,
        revision_type: str,
        archive_path: Path,
    ) -> bool:
        """Materialize document archive for working, staging, or commit revision."""
        if revision_type == "commits":
            if archive_path.exists():
                return True
            return self._git_service.write_file_from_ref(repo, revision, git_path, str(archive_path))
        if revision_type == "working":
            return self._copy_working_tree_file(repo, git_path, archive_path)
        return self._git_service.write_file_from_ref(repo, None, git_path, str(archive_path))

    def _copy_working_tree_file(self, repo: GitRepository, git_path: str, archive_path: Path) -> bool:
        """Copy working tree file to internal storage."""
        try:
            archive_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(repo.absolute_path) / git_path, archive_path)
            return True
        except OSError as err:
            Log.warning(f"Failed to copy working tree file: {err}")
            return False

    def _extract_safely(self, archive_path: Path, extract_dir: Path, revision_type: str) -> bool:
        """Extract document archive safely with zip-slip validation."""
        if revision_type in ("staging", "working"):
            shutil.rmtree(extract_dir, ignore_errors=True)
        else:
            if extract_dir.exists():
                return True
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                for member in archive.infolist():
                    self._validate_member_path(extract_dir, member.filename)
                archive.extractall(extract_dir)
            return True
        except (OSError, zipfile.BadZipFile, ValueError) as err:
            Log.warning(f"Failed to extract document archive: {err}")
            return False

    def _validate_member_path(self, destination: Path, member_name: str) -> None:
        """Validate archive member path prevents zip-slip attack."""
        target = destination / member_name
        try:
            target.resolve().relative_to(destination.resolve())
        except ValueError as e:
            raise ValueError(f"Unsafe archive path: {member_name}") from e
