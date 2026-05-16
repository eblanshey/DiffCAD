#!/usr/bin/env bash
# Wrapper script to run Python scripts with FreeCAD AppImage bindings
# The FreeCAD AppImage should be extracted to a directory and set to the $FREECAD_ROOT env variable.

# Check if FREECAD_ROOT is set, otherwise exit with error. This is the source of the extracted freecad appimage.
# Sample value: /home/user/Programs/freecad_extracted/squashfs-root
if [ -z "$FREECAD_ROOT" ]; then
    echo "Error: FREECAD_ROOT environment variable is not set." >&2
    exit 1
fi

# Set PYTHONPATH to include:
# 1. FreeCAD Python packages (freecad/)
export PYTHONPATH="$FREECAD_ROOT/usr/lib/python3.11/site-packages:$PYTHONPATH"
# 2. FreeCAD compiled extension module (FreeCAD.so)
export PYTHONPATH="$FREECAD_ROOT/usr/lib:$PYTHONPATH"

# Set LD_LIBRARY_PATH for FreeCAD shared libraries
export LD_LIBRARY_PATH="$FREECAD_ROOT/usr/lib:$LD_LIBRARY_PATH"

# Run commands using the AppImage's python interpreter
# Handle 'pip' command specially to use python -m pip
if [ "$1" = "pip" ]; then
    shift
    exec "$FREECAD_ROOT/usr/bin/python" -m pip "$@"
# Handle 'python' or 'python3' command to use AppImage's python directly
elif [ "$1" = "python" ] || [ "$1" = "python3" ]; then
    shift
    exec "$FREECAD_ROOT/usr/bin/python" "$@"
else
    # For other commands (like main.py), use python to run them
    exec "$FREECAD_ROOT/usr/bin/python" "$@"
fi
