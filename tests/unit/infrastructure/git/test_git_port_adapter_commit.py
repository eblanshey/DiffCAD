# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module contains unit tests for GitPortAdapter commit and identity methods.
# Tests use subprocess mocking to verify git commit invocation, error handling,
# and logging behavior without actual git commands.
"""Unit tests for GitPortAdapter commit and identity methods."""

import subprocess
from pathlib import Path
from unittest.mock import call, patch

import pytest
from freecad.history_wb.domain.git.models import GitIdentity
from freecad.history_wb.infrastructure.git import GitPortAdapter
from freecad.history_wb.utils import Log


class TestGitPortAdapterCommit:
    """Tests for the commit method of GitPortAdapter."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_commit_success(self) -> None:
        """Test successful commit returns True.

        When git commit returns exit code 0, the adapter should return True.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Add feature"],
            returncode=0,
            stdout=" 1 file changed, 10 insertions(+)\n",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is True

    def test_commit_failure_logs_warning(self) -> None:
        """Test that git commit failure logs the stderr message.

        When git commit returns non-zero exit code, the adapter should log
        a warning with the stderr content and return False.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Empty message"],
            returncode=1,
            stdout="",
            stderr="error: pathspec 'commit' did not match any file(s) known to git",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Empty message")

            assert result is False
            mock_warning.assert_called_once_with(
                "Git commit failed: error: pathspec 'commit' did not match any file(s) known to git"
            )

    @pytest.mark.parametrize(
        ("side_effect", "expected_log"),
        [
            (subprocess.TimeoutExpired(cmd="git", timeout=30), "Git commit command timed out"),
            (FileNotFoundError("git"), "Git command not found"),
        ],
    )
    def test_commit_handles_errors(self, side_effect: Exception, expected_log: str) -> None:
        """Test that timeout and git-not-found return False with warning."""
        with (
            patch.object(subprocess, "run", side_effect=side_effect),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is False
            mock_warning.assert_called_once_with(expected_log)

    def test_commit_passes_correct_command_args(self) -> None:
        """Test that subprocess.run receives the correct command arguments.

        The commit method should invoke git with: ["git", "commit", "-m", "<message>"]
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "My commit message"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.commit("/path/to/repo", "My commit message")

            assert mock_run.call_args_list[-1] == call(
                ["git", "commit", "-m", "My commit message"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

    def test_commit_passes_git_root_as_cwd(self) -> None:
        """Test that cwd parameter is set to git_root.

        The commit method should pass git_root as the cwd to subprocess.run.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "test"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.commit("/custom/repo/path", "test")

            assert mock_run.call_args_list[-1] == call(
                ["git", "commit", "-m", "test"],
                cwd="/custom/repo/path",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )

    def test_commit_success_logs_debug_message(self) -> None:
        """Test that successful commit logs a debug message with stdout.

        When git commit succeeds, the adapter should log the stdout content.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Add feature"],
            returncode=0,
            stdout=" 1 file changed, 10 insertions(+)\n",
            stderr="",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "debug") as mock_debug,
        ):
            self.adapter.commit("/path/to/repo", "Add feature")

            mock_debug.assert_called_once_with("Commit successful: 1 file changed, 10 insertions(+)")

    def test_commit_handles_no_staged_files(self) -> None:
        """Test git returns False when nothing is staged.

        When git commit fails because there are no staged files (exit code 1),
        the adapter should return False and log the error.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Add feature"],
            returncode=1,
            stdout="",
            stderr="error: nothing added to commit but untracked files present\n",
        )

        with (
            patch.object(subprocess, "run", return_value=mock_result),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is False
            mock_warning.assert_called_once()
            assert "nothing added to commit" in mock_warning.call_args[0][0]

    @pytest.mark.parametrize(
        ("side_effect",),
        [
            (NotADirectoryError(),),
            (OSError("Permission denied"),),
        ],
    )
    def test_commit_handles_os_errors(self, side_effect: Exception) -> None:
        """Test that OS errors return False with warning."""
        with (
            patch.object(subprocess, "run", side_effect=side_effect),
            patch.object(Log, "warning") as mock_warning,
        ):
            result = self.adapter.commit("/path/to/repo", "Add feature")

            assert result is False
            assert mock_warning.called

    @pytest.mark.parametrize(
        "returncode",
        [1, 2, 128],
    )
    def test_commit_various_error_codes(self, returncode: int) -> None:
        """Test handling of various non-zero exit codes.

        Any non-zero exit code should result in False being returned.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "test"],
            returncode=returncode,
            stdout="",
            stderr=f"error {returncode}",
        )

        with patch.object(subprocess, "run", return_value=mock_result):
            result = self.adapter.commit("/path/to/repo", "test")

            assert result is False

    def test_commit_with_message_containing_special_characters(self) -> None:
        """Test commit with special characters in message.

        The commit message is passed directly to git without escaping,
        which is the expected behavior for subprocess.run with text mode.
        """
        mock_result = subprocess.CompletedProcess(
            args=["git", "commit", "-m", "Fix: update | value in config"],
            returncode=0,
            stdout="",
            stderr="",
        )

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            self.adapter.commit("/path/to/repo", "Fix: update | value in config")

            assert mock_run.call_args_list[-1] == call(
                ["git", "commit", "-m", "Fix: update | value in config"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )


class TestGitPortAdapterIdentity:
    """Tests for git identity config methods."""

    def setup_method(self) -> None:
        """Set up test fixtures before each test method."""
        self.adapter = GitPortAdapter()
        self.adapter._git_executable = "git"

    def test_get_identity_returns_local_identity(self) -> None:
        """Local repo identity is returned when name and email are configured."""
        name_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="Local User\n", stderr="")
        email_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="local@example.com\n", stderr="")

        with patch.object(subprocess, "run", side_effect=[name_result, email_result]):
            identity = self.adapter.get_identity("/path/to/repo")

        assert identity == GitIdentity(name="Local User", email="local@example.com")

    def test_get_identity_in_snap_uses_global_config_path(self, tmp_path: Path) -> None:
        """Snap identity lookup uses real-home global config path."""
        (tmp_path / ".gitconfig").write_text("[user]\n", encoding="utf-8")
        name_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="Global User\n", stderr="")
        email_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="global@example.com\n", stderr="")

        with (
            patch.dict("os.environ", {"SNAP_REAL_HOME": str(tmp_path)}, clear=False),
            patch.object(
                subprocess,
                "run",
                side_effect=[name_result, email_result],
            ) as mock_run,
        ):
            identity = self.adapter.get_identity("/path/to/repo")

        assert identity == GitIdentity(name="Global User", email="global@example.com")
        assert mock_run.call_args.kwargs["env"]["GIT_CONFIG_GLOBAL"] == str(tmp_path / ".gitconfig")

    def test_save_identity_local_writes_local_config(self) -> None:
        """Local save writes user.name and user.email to repo config."""
        ok_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with patch.object(subprocess, "run", return_value=ok_result) as mock_run:
            result = self.adapter.save_identity(
                "/path/to/repo",
                GitIdentity(name="Local User", email="local@example.com"),
                should_save_globally=False,
            )

        assert result is True
        assert mock_run.call_args_list == [
            call(
                ["git", "config", "--local", "user.name", "Local User"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            ),
            call(
                ["git", "config", "--local", "user.email", "local@example.com"],
                cwd="/path/to/repo",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            ),
        ]

    def test_save_identity_global_uses_global_config_path(self, tmp_path: Path) -> None:
        """Global save writes user.name and user.email to ~/.gitconfig when writable."""
        ok_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

        with (
            patch.dict("os.environ", {"SNAP_REAL_HOME": str(tmp_path)}, clear=False),
            patch.object(subprocess, "run", return_value=ok_result) as mock_run,
        ):
            result = self.adapter.save_identity(
                "/path/to/repo",
                GitIdentity(name="Global User", email="global@example.com"),
                should_save_globally=True,
            )

        assert result is True
        expected_config_path = str(tmp_path / ".gitconfig")
        assert mock_run.call_args_list[0].kwargs["env"]["GIT_CONFIG_GLOBAL"] == expected_config_path
        assert mock_run.call_args_list[1].kwargs["env"]["GIT_CONFIG_GLOBAL"] == expected_config_path

    def test_save_identity_global_returns_false_when_global_config_path_not_writable(self) -> None:
        """Global save fails when global config path is not writable."""
        with (
            patch.object(self.adapter, "_can_write_config_file", return_value=False),
            patch.object(subprocess, "run") as mock_run,
        ):
            result = self.adapter.save_identity(
                "/path/to/repo",
                GitIdentity(name="Global User", email="global@example.com"),
                should_save_globally=True,
            )

        assert result is False
        mock_run.assert_not_called()

    @pytest.mark.parametrize(
        ("writable_path", "expected"),
        [
            ("/home/user/.gitconfig", True),
            (None, False),
        ],
    )
    def test_can_write_global_identity_uses_writable_global_config_path(
        self,
        writable_path: str | None,
        expected: bool,
    ) -> None:
        """Global identity is writable when adapter finds a writable global config path."""
        with patch.object(self.adapter, "_writable_global_git_config_path", return_value=writable_path):
            result = self.adapter.can_write_global_identity()

        assert result is expected
