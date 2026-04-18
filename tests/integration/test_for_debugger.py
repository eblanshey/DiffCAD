# SPDX-License-Identifier: LGPL-3.0-or-later
"""File responsibility: Debug helper for exploring snapshot extractor hierarchy with real FreeCAD documents.

This is NOT a test file - it contains no assertions. It's a debug helper that replicates
the explore_paths.py script functionality but runs in the pytest/PyCharm debugging environment.

Usage in PyCharm:
    1. Set breakpoint anywhere in this file
    2. Run/Debug this file as a Python script
    3. Inspect variables in debugger

Run with:
    ./run_integration_tests.sh tests/integration/snapshots/test_debug_explorer.py
"""

from __future__ import annotations

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from freecad.diff_wb.domain.freecad_ports import AppLike, FreeCadContext


class TestForDebugger:
    """Debug helper for exploring document structure - NO ASSERTIONS."""

    def test_explore_basic_file(
        self, freecad_app: AppLike, project_root: object, freecad_context: FreeCadContext
    ) -> None:
        """Explore BasicFile.FCStd document structure for debugging purposes.

        This method replicates the explore_paths.py script but runs in pytest environment.
        Set breakpoints and inspect variables to understand the document structure.

        Key things to inspect:
        - doc.Objects: All objects in document
        - obj.InList: Objects that reference this object
        - obj.OutList: Objects referenced by this object
        - obj._Body: Body property for PartDesign features
        - obj.Group: Group contents for containers
        - obj.OriginFeatures: Origin geometry list
        - children_map: Built parent-child relationships
        """
        from pathlib import Path

        # Open the BasicFile test document
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        try:
            print("=" * 80)
            print(f"Document: {doc.Name}")
            print(f"Total objects: {len(doc.Objects)}")
            print("=" * 80)
            print()

            # Build dictionary of all objects
            all_objects = {}
            for obj in doc.Objects:
                if hasattr(obj, "Name"):
                    all_objects[obj.Name] = obj

            # Print comprehensive information for each object
            for name, obj in all_objects.items():
                print(f"\n{'=' * 40}")
                print(f"{name} ({obj.TypeId})")
                print(f"{'=' * 40}")

                # Hierarchy relationships
                in_list = [o.Name for o in getattr(obj, "InList", []) if hasattr(o, "Name")]
                out_list = [o.Name for o in getattr(obj, "OutList", []) if hasattr(o, "Name")]
                sub_objects = [s.split(".")[0] for s in getattr(obj, "getSubObjects", lambda: ())() if s]

                print(f"  InList:          {in_list}")
                print(f"  OutList:         {out_list}")
                print(f"  getSubObjects(): {sub_objects}")

                # Container-specific properties
                body_prop = getattr(obj, "_Body", None)
                body_name = body_prop.Name if body_prop and hasattr(body_prop, "Name") else None

                group = getattr(obj, "Group", [])
                group_names = [g.Name for g in group if hasattr(g, "Name")]

                origin_features = getattr(obj, "OriginFeatures", [])
                origin_feature_names = [o.Name for o in origin_features if hasattr(o, "Name")]

                tip = getattr(obj, "Tip", None)
                tip_name = tip.Name if tip and hasattr(tip, "Name") else None

                base_feature = getattr(obj, "BaseFeature", None)
                base_feature_name = base_feature.Name if base_feature and hasattr(base_feature, "Name") else None

                if body_name:
                    print(f"  _Body:           {body_name}")
                if base_feature_name:
                    print(f"  BaseFeature:     {base_feature_name}")
                if group_names:
                    print(f"  Group:           {group_names}")
                if origin_feature_names:
                    print(f"  OriginFeatures:  {origin_feature_names}")
                if tip_name:
                    print(f"  Tip:             {tip_name}")

                # Sketch-specific properties
                profile = getattr(obj, "Profile", None)
                if profile:
                    profile_names = []
                    if isinstance(profile, (list, tuple)):
                        for item in profile:
                            if hasattr(item, "Name"):
                                profile_names.append(item.Name)
                    if profile_names:
                        print(f"  Profile:         {profile_names}")

                attachment_support = getattr(obj, "AttachmentSupport", None)
                if attachment_support:
                    support_names = []
                    if isinstance(attachment_support, list):
                        for item in attachment_support:
                            if isinstance(item, (list, tuple)) and len(item) > 0:
                                obj_ref = item[0]
                                if hasattr(obj_ref, "Name"):
                                    support_names.append(obj_ref.Name)
                    if support_names:
                        print(f"  AttachmentSupport: {support_names}")

                # Properties and their visibility status
                print(f"\n  Properties ({len(obj.PropertiesList)} total):")
                visible_props = []
                hidden_props = []
                for prop in obj.PropertiesList:
                    mode = obj.getEditorMode(prop)
                    if "Hidden" in mode:
                        hidden_props.append(prop)
                    else:
                        visible_props.append(prop)
                print(f"    Visible: {visible_props}")
                if hidden_props:
                    print(f"    Hidden:  {hidden_props}")

            print("\n" + "=" * 80)
            print("SIMPLE HIERARCHY (using Group + OriginFeatures + InList):")
            print("=" * 80)

            # First pass: determine parent for each object
            parent_map = {}

            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name

                if name in parent_map:
                    continue

                # Check Group of all containers
                for container_obj in doc.Objects:
                    if not hasattr(container_obj, "Name"):
                        continue
                    container_name = container_obj.Name

                    group = getattr(container_obj, "Group", [])
                    group_names = [g.Name for g in group if hasattr(g, "Name")]
                    if name in group_names:
                        parent_map[name] = container_name
                        break

                    origin_features = getattr(container_obj, "OriginFeatures", [])
                    origin_feature_names = [f.Name for f in origin_features if hasattr(f, "Name")]
                    if name in origin_feature_names:
                        parent_map[name] = container_name
                        break

            # Second pass: check InList for objects still without parent
            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name

                if name in parent_map:
                    continue

                in_list = getattr(obj, "InList", [])
                for parent_obj in in_list:
                    if hasattr(parent_obj, "Name"):
                        parent_name = parent_obj.Name
                        parent_type = getattr(parent_obj, "TypeId", "")
                        # Fix Origins not having parents
                        if parent_type in ("App::Part", "PartDesign::Body"):
                            parent_map[name] = parent_name
                            break

            # Build children map preserving doc.Objects order
            children_map = {}

            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name
                parent_name = parent_map.get(name)

                if parent_name:
                    if parent_name not in children_map:
                        children_map[parent_name] = []
                    children_map[parent_name].append(name)

            def print_tree(parent_name, indent=0):
                prefix = "    " * indent
                children = children_map.get(parent_name, [])
                for i, child_name in enumerate(children):
                    if child_name not in all_objects:
                        continue
                    child_obj = all_objects[child_name]
                    is_last = i == len(children) - 1
                    connector = "└── " if is_last else "├── "
                    print(f"{prefix}{connector}{child_name} ({child_obj.TypeId}) [{child_obj.Label}]")
                    print_tree(child_name, indent + 1)

            roots = []
            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name
                if name not in parent_map:
                    roots.append(name)

            print("\nComputed tree hierarchy:")
            for i, root_name in enumerate(roots):
                root_obj = all_objects[root_name]
                is_last = i == len(roots) - 1
                connector = "└── " if is_last else "├── "
                print(f"{connector}{root_name} ({root_obj.TypeId}) [{root_obj.Label}]")
                print_tree(root_name, 1)

            print("\n" + "=" * 80)
            print("EXPECTED FREECAD GUI TREE VIEW:")
            print("=" * 80)
            print("""
Part_MyPart (App::Part)
├── Origin (App::Origin) [Origin]
│   ├── X_Axis (App::Line) [X_Axis]
│   ├── Y_Axis (App::Line) [Y_Axis]
│   ├── Z_Axis (App::Line) [Z_Axis]
│   ├── XY_Plane (App::Plane) [XY_Plane]
│   ├── XZ_Plane (App::Plane) [XZ_Plane]
│   ├── YZ_Plane (App::Plane) [YZ_Plane]
│   └── Origin001 (App::Point) [Origin001]
├── Body_MyBody (PartDesign::Body) [Body_MyBody]
│   ├── Origin004 (App::Origin) [Origin004]
│   │   ├── X_Axis001 (App::Line) [X_Axis001]
│   │   ├── Y_Axis001 (App::Line) [Y_Axis001]
│   │   ├── Z_Axis001 (App::Line) [Z_Axis001]
│   │   ├── XY_Plane001 (App::Plane) [XY_Plane001]
│   │   ├── XZ_Plane001 (App::Plane) [XZ_Plane001]
│   │   ├── YZ_Plane001 (App::Plane) [YZ_Plane001]
│   │   └── Origin003 (App::Point) [Origin003]
│   ├── Pad_Main (PartDesign::Pad) [Pad_Main]
│   │   └── Sketch_Pad (Sketcher::SketchObject) [Sketch_Pad]
│   └── Pocket_Main (PartDesign::Pocket) [Pocket_Main]
│       └── Sketch_Pocket (Sketcher::SketchObject) [Sketch_Pocket]
└── MyVarSet (App::VarSet) [MyVarSet]
""")

            # Also run the actual extractor to compare
        finally:
            freecad_app.closeDocument(doc.Name)

            print("\nDone! Set breakpoints above to inspect variables.")

    def test_claimchildren_gui_api(
        self, freecad_app: AppLike, project_root: object, freecad_gui: object | None
    ) -> None:
        """Test Option A: Use GUI-level claimChildren() API to build tree.

        This test implements the recommended Option A from the task:
        - Uses FreeCAD's authoritative tree-building logic via claimChildren()
        - Requires FreeCAD GUI to be initialized during extraction

        The algorithm:
        1. Each ViewProvider declares its children via claimChildren() method
        2. Recursive exclusion: If parent A claims child B, and B claims children C1, C2,
           then C1/C2 are EXCLUDED from A's direct children (they appear nested under B)

        This is implemented in ViewProviderGeoFeatureGroupExtension::extensionClaimChildren()
        in the FreeCAD C++ source.
        """
        from pathlib import Path

        # Try to get FreeCADGui from fixture first
        gui = freecad_gui

        if gui is None:
            print("FreeCADGui not available - skipping test")
            return

        # Open the BasicFile test document BEFORE setupWithoutGUI
        # to ensure the GUI document is created
        doc_path = Path(project_root) / "tests/freecad/BasicFile.FCStd"
        doc = freecad_app.open(str(doc_path))

        # Now setup GUI - this may create view providers for already-open document
        if hasattr(gui, "setupWithoutGUI"):
            gui.setupWithoutGUI()

        try:
            print("=" * 80)
            print("OPTION A: Using claimChildren() GUI-level API")
            print("=" * 80)
            print(f"Document: {doc.Name}")
            print()

            # Get GUI document after setupWithoutGUI()
            gui_doc = None
            if hasattr(gui, "getDocument"):
                gui_doc = gui.getDocument(doc.Name)

            print(f"GUI document: {gui_doc}")

            all_objects = {}
            for obj in doc.Objects:
                if hasattr(obj, "Name"):
                    all_objects[obj.Name] = obj

            # Get claimChildren for each object
            claim_children_map = {}

            # Check GUI availability
            gui_available = gui_doc is not None

            for obj in doc.Objects:
                if not hasattr(obj, "Name"):
                    continue
                name = obj.Name

                # Get ViewProvider - try ViewObject property first
                vp = None
                if hasattr(obj, "ViewObject"):
                    view_obj = obj.ViewObject
                    if view_obj is not None:
                        vp = view_obj

                # Also try via gui_doc if available
                if vp is None and gui_doc is not None and hasattr(gui_doc, "getViewProvider"):
                    vp = gui_doc.getViewProvider(obj)

                if vp is not None and hasattr(vp, "claimChildren"):
                    try:
                        claimed = vp.claimChildren()
                        # claimed can be a list of objects or pybind11 proxy
                        if claimed:
                            child_names = []
                            for child in claimed:
                                if hasattr(child, "Name"):
                                    child_names.append(child.Name)
                                elif hasattr(child, "name"):
                                    # Some objects use 'name' instead of 'Name'
                                    child_names.append(child.name)
                            claim_children_map[name] = child_names
                    except (AttributeError, RuntimeError) as e:
                        print(f"  Warning: claimChildren failed for {name}: {e}")

            # Report GUI availability status
            if not gui_available:
                print("NOTE: Running in headless mode - GUI not fully initialized.")
                print("      claimChildren() requires FreeCAD GUI to be running with display.")
                print("      In production, this would work with proper GUI initialization.")
                print()

            print("Claimed children from ViewProviders:")
            for parent, children in claim_children_map.items():
                print(f"  {parent}: {children}")

            print()

            # Now build the tree with recursive exclusion
            # Algorithm: For each parent, exclude children that are claimed by claimed children

            # Build effective children map
            effective_children_map = {}
            for parent_name in claim_children_map:
                direct_claims = claim_children_map.get(parent_name, [])

                result = []
                excluded = set()  # Track objects excluded by nested claims

                # First, get all recursively claimed children
                def get_all_descendants(name: str) -> set:
                    desc = set()
                    children = claim_children_map.get(name, [])
                    for child in children:
                        desc.add(child)
                        desc.update(get_all_descendants(child))
                    return desc

                # For each direct claim, get its descendants
                for child_name in direct_claims:
                    # Add the child itself
                    if child_name not in excluded:
                        result.append(child_name)
                    # Exclude descendants (recursive exclusion)
                    excluded.update(get_all_descendants(child_name))

                effective_children_map[parent_name] = result

            print("Effective children (with recursive exclusion):")
            for parent, children in effective_children_map.items():
                print(f"  {parent}: {children}")

            print()

            # Find root objects (those not claimed by anyone)
            all_claimed = set()
            for children in claim_children_map.values():
                all_claimed.update(children)

            root_objects = []
            for obj in doc.Objects:
                if hasattr(obj, "Name"):
                    name = obj.Name
                    if name not in all_claimed:
                        root_objects.append(name)

            print(f"Root objects: {root_objects}")

            # Build and print the tree
            def print_claim_tree(parent_name: str, indent: int = 0) -> None:
                prefix = "    " * indent
                children = effective_children_map.get(parent_name, [])
                for i, child_name in enumerate(children):
                    if child_name not in all_objects:
                        continue
                    child_obj = all_objects[child_name]
                    is_last = i == len(children) - 1
                    connector = "└── " if is_last else "├── "
                    print(f"{prefix}{connector}{child_name} ({child_obj.TypeId})")
                    print_claim_tree(child_name, indent + 1)

            print()
            print("Built tree using claimChildren():")
            for root_name in root_objects:
                if root_name not in all_objects:
                    continue
                root_obj = all_objects[root_name]
                print(f"{root_name} ({root_obj.TypeId})")
                print_claim_tree(root_name, 1)

            print()
            print("=" * 80)
            print("EXPECTED FREECAD GUI TREE (from task):")
            print("=" * 80)
            print("""
Part_MyPart
├── Origin
│   ├── X_Axis
│   ├── Y_Axis
│   ├── Z_Axis
│   ├── XY_Plane
│   ├── XZ_Plane
│   ├── YZ_Plane
│   └── Origin001
├── Body_MyBody
│   ├── Origin004
│   │   ├── X_Axis001
│   │   ├── Y_Axis001
│   │   ├── Z_Axis001
│   │   ├── XY_Plane001
│   │   ├── XZ_Plane001
│   │   ├── YZ_Plane001
│   │   └── Origin003
│   ├── Pad_Main
│   │   └── Sketch_Pad
│   └── Pocket_Main
│       └── Sketch_Pocket
└── MyVarSet
Page
├── Template
└── View
    ├── Dimension
    ├── Dimension001
    ├── Dimension002
    └── Balloon
""")

        finally:
            freecad_app.closeDocument(doc.Name)

        print("\nDone! Compare the built tree with expected FreeCAD GUI tree.")
