# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Composes UI components and registers them in UIRegistry.
# This module is responsible for creating UI views, UIState, wiring presenters
# to views and state, registering presenters globally, and connecting callbacks.
"""UI Composer - Composes and registers UI components."""

from ..application.di.container import ApplicationContainer
from ..ui.registry import ui_registry
from ..ui.state import UIState
from ..ui.views.diff_panel_view import DiffPanelView
from .presenters.diff_presenter import DiffPresenter
from .presenters.git_repository_presenter import GitRepositoryPresenter
from .presenters.snapshot_presenter import SnapshotPresenter


__all__ = ["compose_and_register_ui"]


def compose_and_register_ui(container: ApplicationContainer) -> DiffPanelView:
    """Create UI components and register them globally.

    This function is the composition root for the UI layer. It creates all
    UI components (views, presenters, state) and wires them together,
    then registers the presenters in the global UI registry for access
    by entry points (commands).

    Args:
        container: Application container with actions wired (backend only)

    Returns:
        The configured DiffPanelView

    Side Effects:
        - Creates UIState (frontend state)
        - Registers presenters in UIRegistry
        - Connects all callbacks
        - Initializes git repository detection
    """
    # Create UI state (frontend state, like Pinia/Redux)
    ui_state = UIState(git_repository=None)

    # Create view
    view = DiffPanelView()

    # Create and register snapshot_presenter (doesn't need ui_state)
    snapshot_presenter = SnapshotPresenter(
        view=view,
        list_snapshots_action=container.list_snapshots_action,
    )
    ui_registry.register_snapshot_presenter(snapshot_presenter)

    # Create and register diff_presenter (needs ui_state for git_repository)
    diff_presenter = DiffPresenter(
        view=view,
        ui_state=ui_state,
        get_eligible_docs_action=container.get_open_eligible_docs_action,
        create_working_snapshot_action=container.create_working_snapshot_action,
        create_commit_snapshot_action=container.create_commit_snapshot_action,
        create_diff_action=container.create_diff_action,
        stage_documents_action=container.stage_documents_action,
        get_dirty_documents_action=container.get_dirty_documents_action,
    )
    ui_registry.register_diff_presenter(diff_presenter)

    # Connect tree widget callback using the new callback method
    view.set_node_selection_callback(diff_presenter.on_node_selected)

    # Connect add button callback
    view.set_add_button_callback(diff_presenter.on_add_button_clicked)

    # Lifecycle presenter - creates git detection + refresh behavior
    # Does NOT need to be registered - it sets up ui_state
    git_repo_presenter = GitRepositoryPresenter(
        view=view,
        find_git_repo_action=container.find_active_git_repository_action,
        get_commits_action=container.get_commits_action,
        ui_state=ui_state,
    )
    # Trigger git repository detection on workbench activation
    git_repo_presenter.on_workbench_activated()

    return view
