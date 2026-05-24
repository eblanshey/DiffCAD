"""File responsibility: Unit tests for CanWriteGlobalGitIdentityAction."""

import pytest
from freecad.history_wb.application.actions.can_write_global_git_identity import CanWriteGlobalGitIdentityAction
from freecad.history_wb.domain.git.git_service import GitService

from tests.fakes import FakeGitPort


class TestCanWriteGlobalGitIdentityAction:
    """Test suite for CanWriteGlobalGitIdentityAction."""

    @pytest.mark.parametrize("can_write", [True, False])
    def test_execute_returns_global_identity_writability(self, can_write: bool) -> None:
        """Action returns global git identity writability as success data."""
        git_port = FakeGitPort()
        git_port.set_can_write_global_identity(can_write)
        action = CanWriteGlobalGitIdentityAction(git_service=GitService(git_port=git_port))

        result = action.execute()

        assert result.is_success is True
        assert result.data is can_write
