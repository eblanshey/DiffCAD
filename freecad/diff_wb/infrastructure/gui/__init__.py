# SPDX-License-Identifier: LGPL-3.0-or-later
# Module responsibility: GUI adapters implementing Qt interface for workbench interaction and user feedback.
"""GUI infrastructure adapters."""

from .qt_adapter import GuiPort, GuiPortAdapter, get_gui_port


__all__ = ["GuiPort", "GuiPortAdapter", "get_gui_port"]
