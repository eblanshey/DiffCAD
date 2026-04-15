# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Fake GitPort implementation for testing git repository detection.
# This provides an in-memory simulation of git repository paths without requiring
# actual git repositories or subprocess calls.
"""Fake GitPort implementation for testing."""


class FakeGitPort:
    """Fake implementation of GitPort for testing purposes.

    This fake implementation simulates git repository detection without
    requiring actual git repositories or subprocess calls. It uses an
    in-memory mapping of paths to their git roots.

    Attributes:
        _git_roots: Dictionary mapping paths to their git root paths.
    """

    def __init__(self) -> None:
        """Initialize the fake git port with empty mappings."""
        self._git_roots: dict[str, str] = {}

    def add_git_repo(self, root_path: str) -> None:
        """Add a simulated git repository root.

        Args:
            root_path: The absolute path to the git repository root.
        """
        self._git_roots[root_path] = root_path

    def find_top_level_git_path(self, path: str) -> str | None:
        """Find git root by checking if path is within a known git repo.

        This implementation checks if the given path or any of its parent
        directories match a known git root.

        Args:
            path: Starting path (file or directory) to check.

        Returns:
            Absolute path to git root as string if path is in a known git repo,
            or None if not in a known git repo.
        """
        # Normalize the path
        normalized_path = path.rstrip("/")

        # Check if the path itself is a git root
        if normalized_path in self._git_roots:
            return self._git_roots[normalized_path]

        # Traverse up the directory tree to find a git root
        current_path = normalized_path
        while True:
            # Get parent directory
            parent_path = "/".join(current_path.split("/")[:-1])

            # If we've reached the root, stop searching
            if parent_path == "" or parent_path == "/":
                # Check root explicitly
                if "/" in self._git_roots:
                    return self._git_roots["/"]
                break

            # Check if parent is a git root
            if parent_path in self._git_roots:
                return self._git_roots[parent_path]

            current_path = parent_path

        return None
