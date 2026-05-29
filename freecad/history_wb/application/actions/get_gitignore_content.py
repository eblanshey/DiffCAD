# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Read repository .gitignore content or provide default template.
"""Application action for loading repository .gitignore content."""

from __future__ import annotations

from pathlib import Path

from ...domain.git.models import GitRepository
from ...utils import Log
from .result_models import Result


DEFAULT_GITIGNORE_CONTENT = """# FreeCAD backups
*.FCBak

# OS metadata
.DS_Store
Thumbs.db
Desktop.ini

# Editor and IDE settings
.idea/
.vscode/
"""


class GetGitIgnoreContentAction:
    """Get current repository .gitignore content with fallback default."""

    def execute(self, repo: GitRepository) -> Result:
        """Return existing .gitignore text, else default template."""
        gitignore_path = Path(repo.absolute_path) / ".gitignore"
        if not gitignore_path.exists():
            return Result.success(DEFAULT_GITIGNORE_CONTENT)

        try:
            return Result.success(gitignore_path.read_text(encoding="utf-8"))
        except OSError as error:
            Log.exception(f"Failed reading .gitignore at {gitignore_path}: {error}")
            return Result.failure("Failed to read .gitignore file")
