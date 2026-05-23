"""Module responsibility: Centralized translation strings for the UI layer.

This module contains all translation templates used across the UI layer.
All user-facing strings should be defined here to provide a single source
of truth for translators and prevent duplication.

Translation Strategy:
- Templates use Qt-style placeholders: %1, %2, %3, etc.
- Views handle both translation AND parameter substitution
- Presenters pass raw data only (no message formatting)
- Translation happens at view creation time for performance

Usage Example:
    # In a view implementation:
    from freecad.diff_wb.ui.translation_strings import SNAPSHOT_SUCCESS_TEMPLATE

    template = QCoreApplication.translate("SnapshotView", SNAPSHOT_SUCCESS_TEMPLATE)
    translated = template % snapshot_name  # %1 is replaced with snapshot_name
    self._label.setText(translated)
"""

# ============================================================================
# SNAPSHOT VIEW STRINGS
# ============================================================================
# Context: "SnapshotView"
# These strings are used by the snapshot view component for success/error/loading states.

SNAPSHOT_SUCCESS_TEMPLATE = "Snapshot '%1' created successfully"
"""Success message after creating a snapshot.

Placeholder:
    %1 - The snapshot name (str)

Example:
    "Snapshot 'my_snapshot' created successfully"
"""

SNAPSHOT_LOADING_DEFAULT = "Creating snapshot..."
"""Default loading message shown while snapshot is being created.

No placeholders. This is a static message.
"""

# ============================================================================
# DIFF VIEW STRINGS
# ============================================================================
# Context: "DiffView"
# These strings are used by the diff view component for displaying results.

DIFF_SUMMARY_CHANGED_LABEL = "Changed:"
"""Label for the changed-documents count in the diff summary.

No placeholders. The view appends the count after this label.

Example:
    "Changed: 2"
"""

DIFF_LOADING_MESSAGE = "Computing diff..."
"""Loading message shown while diff is being computed.

No placeholders. This is a static message.
"""

STAGE_ALL_LABEL = "+ Mark All Reviewed"
"""Label for the Mark All Reviewed button in the In Progress view.

No placeholders. This is a static label displayed above the diff tree.
"""

STAGE_LABEL = "+ Reviewed"
"""Label for a single-document reviewed button in the In Progress view.

No placeholders. This is a static label displayed in document rows.
"""

DOC_STATUS_NEW_DOCUMENT_TOOLTIP = "New document"
DOC_STATUS_OLD_SNAPSHOT_MISSING_TOOLTIP = "Cannot find old snapshot. Tree comparison cannot be generated."
DOC_STATUS_SNAPSHOT_MISSING_TOOLTIP = "The selected iteration does not have a snapshot for this document"
DOC_STATUS_INVALID_SNAPSHOT_TOOLTIP = "The older snapshot is invalid, so a tree comparison cannot be generated."
VISUAL_DIFF_TOOLTIP = "Open 3D comparison"
VISUAL_DIFF_MISSING_FCSTD_MESSAGE = "Could not load FCStd from old or new side for 3D comparison."
VISUAL_DIFF_MISSING_BREP_MESSAGE = "Could not find Shape BREP for this object in old or new document."
VISUAL_DIFF_IMPORT_FAILURE_MESSAGE = "Could not import shape BREP files for 3D comparison."
VISUAL_DIFF_INVALID_REQUEST_MESSAGE = "Could not determine old and new revisions for 3D comparison."

# ============================================================================
# COMMON STRINGS
# ============================================================================
# Context: "Common"
# These strings are shared across multiple views for common error/loading states.

ERROR_UNKNOWN = "Unknown error occurred"
"""Generic error message when no specific error information is available.

No placeholders. This is a static message.
"""

ERROR_NO_DOCUMENT = "No active document available"
"""Error message when no document is open in FreeCAD.

No placeholders. This is a static message.
"""

DIALOG_OK = "OK"
"""Generic OK button label for dialogs.

No placeholders. This is a static label.
"""

DIALOG_CANCEL = "Cancel"
"""Generic Cancel button label for dialogs.

No placeholders. This is a static label.
"""

# ============================================================================
# GIT REPOSITORY STRINGS
# ============================================================================
# Context: "Common"
# These strings are used for displaying git repository information in the UI.

REPOSITORY_INFO_TEMPLATE = "Project: %1"
"""Template for displaying project info.

Placeholders:
    %1 - Project name (str)

The absolute path is stored separately for use as a tooltip.

Example:
    "Project: my_project"
"""

REPOSITORY_NO_REPO_MESSAGE = "No project detected"
"""Message shown when no git repository is detected for the active document.

No placeholders. This is a static message.
"""

ITERATION_LABEL = "Iterations"
"""Label for the iterations/commit list widget.

No placeholders. This is a static label.
"""

HISTORY_WORKING_TREE_LABEL = "In Progress"
"""Label for the synthetic history row representing current work in progress."""

HISTORY_STAGING_LABEL = "Reviewed"
"""Label for the synthetic history row representing reviewed items."""

REFRESH_REPOSITORY_TOOLTIP = "Refresh Project and Iterations"
"""Tooltip for project refresh button."""

# ============================================================================
# ITERATION SAVE STRINGS
# ============================================================================
# Context: "Commit"
# These strings are used for iteration save-related UI messages in entry points.

COMMIT_NO_REPOSITORY_TITLE = "No Project"
"""Title for the warning when no git repository is detected.

No placeholders. This is a static message.
"""

COMMIT_NO_REPOSITORY_MESSAGE = "No project detected. Please open a document from a project."
"""Message shown when no git repository is detected for the active document.

No placeholders. This is a static message.
"""

COMMIT_NO_STAGED_FILES_TITLE = "No Reviewed Files"
"""Title for the info message when there are no reviewed files to save.

No placeholders. This is a static message.
"""

COMMIT_NO_STAGED_FILES_MESSAGE = "There are no reviewed files to save."
"""Message shown when there are no reviewed files to save.

No placeholders. This is a static message.
"""

COMMIT_DIALOG_TITLE = "Save Iteration"
"""Title for the iteration notes input dialog.

No placeholders. This is a static message.
"""

CONFIGURE_GIT_DIALOG_TITLE = "Configure Git"
"""Title for git identity configuration dialog."""

CONFIGURE_GIT_IDENTITY_PROMPT = (
    "Enter the name and email you'd like to use for your git identity, which is used for authoring git commits."
)
"""Prompt shown in the git identity configuration dialog."""

CONFIGURE_GIT_GLOBAL_SAVE_FAILED_MESSAGE = (
    "Could not save git identity for all repositories. Uncheck the global option to save it only for this repository."
)
"""Message shown when global git identity save fails and local save is available."""

CONFIGURE_GIT_GLOBAL_CONFIG_NOT_WRITABLE_MESSAGE = (
    "Global configuration option disabled because global config file not writable."
)
"""Message shown when global git config cannot be written."""

COMMIT_DIALOG_PROMPT = "Enter iteration notes:"
"""Prompt text for the iteration notes input dialog.

No placeholders. This is a static message.
"""

COMMIT_NAME_LABEL = "Name:"
"""Label for git author name field in the iteration save dialog."""

COMMIT_EMAIL_LABEL = "Email:"
"""Label for git author email field in the iteration save dialog."""

COMMIT_REMEMBER_IDENTITY_LABEL = "Configure globally for all projects"
"""Checkbox label for saving git author identity globally."""

CONFIGURE_GIT_IDENTITY_PROMPT = (
    "Enter the name and email you'd like to use for your git identity, which is used for authoring project iterations."
)
"""Prompt shown in the git identity configuration dialog."""

CONFIGURE_GIT_GLOBAL_SAVE_FAILED_MESSAGE = (
    "Could not save git identity for all projects. Uncheck the global option to save it only for this project."
)
"""Message shown when global git identity save fails and local save is available."""

CONFIGURE_GIT_GLOBAL_CONFIG_NOT_WRITABLE_MESSAGE = (
    "Global configuration option disabled because global config file not writable."
)
"""Message shown when global git config cannot be written."""

COMMIT_EMPTY_MESSAGE_TITLE = "Empty Notes"
"""Title for the warning when iteration notes is empty.

No placeholders. This is a static message.
"""

COMMIT_EMPTY_MESSAGE = "Iteration notes cannot be empty"
"""Message shown when the user provides an empty iteration notes.

No placeholders. This is a static message.
"""

COMMIT_IDENTITY_REQUIRED_MESSAGE = "Name and email are required to save iteration"
"""Message shown when git author identity is missing from the iteration save dialog."""

COMMIT_IDENTITY_SAVE_FAILED_MESSAGE = "Git identity could not be saved"
"""Message shown when saving git author identity fails."""

COMMIT_FAILED_TITLE = "Save Iteration Failed"
"""Title for the error dialog when iteration save fails.

No placeholders. This is a static message.
"""

COMMIT_DIALOG_PLACEHOLDER = "Enter iteration notes (subject and optional body)..."
"""Placeholder text for the iteration notes text area.

No placeholders. This is a static message shown in the empty text field.
"""

# ============================================================================
# OPEN ALL PROJECT DOCUMENTS STRINGS
# ============================================================================
# Context: "OpenAllDocuments"

OPEN_ALL_DOCUMENTS_NO_REPOSITORY_TITLE = "No Project"
OPEN_ALL_DOCUMENTS_NO_REPOSITORY_MESSAGE = "No project detected. Open a FreeCAD document in a project first."

# ============================================================================
# INITIALIZE PROJECT STRINGS
# ============================================================================
# Context: "InitializeGitRepository"

INITIALIZE_REPOSITORY_MENU_TEXT = "Initialize Project"
INITIALIZE_REPOSITORY_TOOLTIP = "Initialize a new project from open saved document directories"
INITIALIZE_REPOSITORY_DIALOG_TITLE = "Initialize Project"
INITIALIZE_REPOSITORY_DIALOG_PROMPT = (
    "Choose a directory to initialize based on currently open documents. The selected "
    "directory will be the root of your project:"
)
INITIALIZE_REPOSITORY_BUTTON = "Initialize"
INITIALIZE_REPOSITORY_DISABLED_REASON = "Already inside project"
INITIALIZE_REPOSITORY_NO_CANDIDATES_TITLE = "No Directories Available"
INITIALIZE_REPOSITORY_NO_CANDIDATES_MESSAGE = (
    "No open documents are available for project initialization. "
    "Please open at least one saved document in the root location you'd "
    "like to initialize a new project."
)
INITIALIZE_REPOSITORY_NO_AVAILABLE_MESSAGE = "All listed directories are already inside projects."
INITIALIZE_REPOSITORY_SUCCESS_TITLE = "Project Initialized"
INITIALIZE_REPOSITORY_SUCCESS_TEMPLATE = "Initialized project: %1"
INITIALIZE_REPOSITORY_FAILED_TITLE = "Initialization Failed"

# ============================================================================
# PREFERENCES VIEW STRINGS
# ============================================================================
# Context: "PreferencesView"

PREFERENCES_RUNTIME_ONLY_NOTICE = (
    "Settings apply only during tree comparisons. Saved tree snapshots are unaffected by these settings."
)
"""Notice shown at top of preferences page clarifying runtime-only behavior."""

PREFERENCES_GROUP_EXCLUDED_OBJECT_TYPES = "Excluded object types"
PREFERENCES_GROUP_EXCLUDED_PROPERTIES = "Excluded properties"
PREFERENCES_GROUP_TYPE_SPECIFIC_EXCLUDED_PROPERTIES = "Type-specific excluded properties"
PREFERENCES_GROUP_NUMERIC_COMPARISON = "Numeric comparison"
PREFERENCES_PAGE_GENERAL = "General"

PREFERENCES_FLOAT_PRECISION_LABEL = "Float precision"

PREFERENCES_RADIO_USE_DEFAULT_EXCLUSION_LIST = "Use default exclusion list"
PREFERENCES_RADIO_USE_CUSTOM_EXCLUSION_LIST = "Use custom exclusion list"

PREFERENCES_HELPER_TYPE_ID_PER_LINE = "One TypeId per line."
PREFERENCES_HELPER_PROPERTY_NAME_PER_LINE = "One property name per line."
PREFERENCES_HELPER_TYPE_PROPERTY_MAPPING_PER_LINE = "One line per mapping: TypeId -> Property"


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Snapshot View
    "SNAPSHOT_SUCCESS_TEMPLATE",
    "SNAPSHOT_LOADING_DEFAULT",
    # Diff View
    "DIFF_SUMMARY_CHANGED_LABEL",
    "DIFF_LOADING_MESSAGE",
    "STAGE_ALL_LABEL",
    "DOC_STATUS_NEW_DOCUMENT_TOOLTIP",
    "DOC_STATUS_OLD_SNAPSHOT_MISSING_TOOLTIP",
    "DOC_STATUS_SNAPSHOT_MISSING_TOOLTIP",
    "DOC_STATUS_INVALID_SNAPSHOT_TOOLTIP",
    # Common
    "ERROR_UNKNOWN",
    "ERROR_NO_DOCUMENT",
    # Git Repository
    "REPOSITORY_INFO_TEMPLATE",
    "REPOSITORY_NO_REPO_MESSAGE",
    "ITERATION_LABEL",
    "HISTORY_WORKING_TREE_LABEL",
    "HISTORY_STAGING_LABEL",
    "REFRESH_REPOSITORY_TOOLTIP",
    # Commit
    "COMMIT_NO_REPOSITORY_TITLE",
    "COMMIT_NO_REPOSITORY_MESSAGE",
    "COMMIT_NO_STAGED_FILES_TITLE",
    "COMMIT_NO_STAGED_FILES_MESSAGE",
    "COMMIT_DIALOG_TITLE",
    "COMMIT_DIALOG_PROMPT",
    "COMMIT_EMPTY_MESSAGE_TITLE",
    "COMMIT_EMPTY_MESSAGE",
    "COMMIT_FAILED_TITLE",
    "COMMIT_DIALOG_PLACEHOLDER",
    "DIALOG_OK",
    "DIALOG_CANCEL",
    # Open All Documents
    "OPEN_ALL_DOCUMENTS_NO_REPOSITORY_TITLE",
    "OPEN_ALL_DOCUMENTS_NO_REPOSITORY_MESSAGE",
    # Initialize Repository
    "INITIALIZE_REPOSITORY_MENU_TEXT",
    "INITIALIZE_REPOSITORY_TOOLTIP",
    "INITIALIZE_REPOSITORY_DIALOG_TITLE",
    "INITIALIZE_REPOSITORY_DIALOG_PROMPT",
    "INITIALIZE_REPOSITORY_BUTTON",
    "INITIALIZE_REPOSITORY_DISABLED_REASON",
    "INITIALIZE_REPOSITORY_NO_CANDIDATES_TITLE",
    "INITIALIZE_REPOSITORY_NO_CANDIDATES_MESSAGE",
    "INITIALIZE_REPOSITORY_NO_AVAILABLE_MESSAGE",
    "INITIALIZE_REPOSITORY_SUCCESS_TITLE",
    "INITIALIZE_REPOSITORY_SUCCESS_TEMPLATE",
    "INITIALIZE_REPOSITORY_FAILED_TITLE",
    # Preferences View
    "PREFERENCES_RUNTIME_ONLY_NOTICE",
    "PREFERENCES_GROUP_EXCLUDED_OBJECT_TYPES",
    "PREFERENCES_GROUP_EXCLUDED_PROPERTIES",
    "PREFERENCES_GROUP_TYPE_SPECIFIC_EXCLUDED_PROPERTIES",
    "PREFERENCES_GROUP_NUMERIC_COMPARISON",
    "PREFERENCES_PAGE_GENERAL",
    "PREFERENCES_FLOAT_PRECISION_LABEL",
    "PREFERENCES_RADIO_USE_DEFAULT_EXCLUSION_LIST",
    "PREFERENCES_RADIO_USE_CUSTOM_EXCLUSION_LIST",
    "PREFERENCES_HELPER_TYPE_ID_PER_LINE",
    "PREFERENCES_HELPER_PROPERTY_NAME_PER_LINE",
    "PREFERENCES_HELPER_TYPE_PROPERTY_MAPPING_PER_LINE",
]
