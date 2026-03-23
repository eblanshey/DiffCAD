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

DIFF_SUMMARY_ADDED_LABEL = "Added:"
"""Label for the added nodes count in the diff summary.

No placeholders. The view appends the count after this label.

Example:
    "Added: 5"
"""

DIFF_SUMMARY_DELETED_LABEL = "Deleted:"
"""Label for the deleted nodes count in the diff summary.

No placeholders. The view appends the count after this label.

Example:
    "Deleted: 3"
"""

DIFF_SUMMARY_MODIFIED_LABEL = "Modified:"
"""Label for the modified nodes count in the diff summary.

No placeholders. The view appends the count after this label.

Example:
    "Modified: 2"
"""

DIFF_LOADING_MESSAGE = "Computing diff..."
"""Loading message shown while diff is being computed.

No placeholders. This is a static message.
"""

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

# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Snapshot View
    "SNAPSHOT_SUCCESS_TEMPLATE",
    "SNAPSHOT_LOADING_DEFAULT",
    # Diff View
    "DIFF_SUMMARY_ADDED_LABEL",
    "DIFF_SUMMARY_DELETED_LABEL",
    "DIFF_SUMMARY_MODIFIED_LABEL",
    "DIFF_LOADING_MESSAGE",
    # Common
    "ERROR_UNKNOWN",
    "ERROR_NO_DOCUMENT",
]
