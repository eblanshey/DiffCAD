#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-3.0-or-later
# File responsibility: Run integration tests using FreeCAD's Python interpreter.
#
# This script runs pytest using FreeCAD's Python interpreter instead of the system Python.
# This is necessary because FreeCAD's modules require FreeCAD's specific Python version.
#
# Usage:
#     ./run_integration_tests.sh [pytest-options]
#
# Examples:
#     ./run_integration_tests.sh -v
#     ./run_integration_tests.sh tests/integration/workbench/ -v
#     ./run_integration_tests.sh --tb=long

set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Get FREECAD_ROOT from environment or use default
FREECAD_ROOT="${FREECAD_ROOT:-$HOME/Programs/freecad_extracted/squashfs-root}"

# Path to FreeCAD's Python interpreter
FREECAD_PYTHON="$FREECAD_ROOT/usr/bin/python"

# Check if FreeCAD Python exists
if [ ! -f "$FREECAD_PYTHON" ]; then
    echo "Error: FreeCAD Python not found at $FREECAD_PYTHON"
    echo "Set FREECAD_ROOT environment variable to your FreeCAD installation"
    exit 1
fi

# Set up environment for FreeCAD
export LD_LIBRARY_PATH="$FREECAD_ROOT/usr/lib:${LD_LIBRARY_PATH:-}"

# Add FreeCAD's site-packages and lib to PYTHONPATH
SITE_PACKAGES="$FREECAD_ROOT/usr/lib/python3.11/site-packages"
FREECAD_LIB="$FREECAD_ROOT/usr/lib"
export PYTHONPATH="$PROJECT_ROOT:$SITE_PACKAGES:$FREECAD_LIB:${PYTHONPATH:-}"

# Set offscreen mode for headless testing
export QT_QPA_PLATFORM=offscreen

# Isolate from user-installed FreeCAD workbenches to avoid stale module imports
FREECAD_TEST_HOME="/tmp/kilo/freecad_test_home"
mkdir -p "$FREECAD_TEST_HOME"
export FREECAD_USER_HOME="$FREECAD_TEST_HOME"

# Run pytest with FreeCAD's Python
echo "Running integration tests..."
echo "Python: $FREECAD_PYTHON"
echo "FREECAD_ROOT: $FREECAD_ROOT"
echo ""

exec "$FREECAD_PYTHON" -m pytest "$PROJECT_ROOT/tests/integration" "$@"
