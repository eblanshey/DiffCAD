# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: This module provides the GitPort implementation using git CLI.
# It exports the GitPortAdapter class which implements the GitPort protocol from
# the domain layer, enabling git repository detection via subprocess calls.
"""Git infrastructure components."""

from .git_port_adapter import GitPortAdapter


__all__ = ["GitPortAdapter"]
