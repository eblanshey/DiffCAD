#!/usr/bin/env python3
"""Gap analysis script for snapshot extraction.

This script verifies that the existing API exploration covers snapshot needs
and identifies any gaps in tree traversal strategies.

Run with: ./run_with_freecad.sh python scripts/verify_snapshot_extraction.py
"""

import FreeCAD
from freecad.diff_wb.domain.snapshot import TreeNode, Snapshot
from freecad.diff_wb.domain.property_value import PropertyValue


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def test_tree_building_from_outlist(doc: FreeCAD.Document) -> None:
    """Test tree building using OutList relationships.

    Strategy: Use obj.OutList to find children of each object.
    """
    print_section("Tree Building from OutList")

    # Build a map of name -> object
    obj_map = {obj.Name: obj for obj in doc.Objects}

    # Build parent-child relationships using OutList
    children_map: dict[str, list[str]] = {}
    for obj in doc.Objects:
        child_names = []
        for child_obj in getattr(obj, "OutList", []):
            if hasattr(child_obj, "Name"):
                child_names.append(child_obj.Name)
        children_map[obj.Name] = child_names

    print("\nOutList relationships:")
    for name, children in children_map.items():
        if children:
            print(f"  {name} -> {children}")

    # Find root objects (not in any OutList)
    all_children = set()
    for children in children_map.values():
        all_children.update(children)

    root_objects = [obj for obj in doc.Objects if obj.Name not in all_children]
    print(f"\nRoot objects (not referenced by OutList): {[obj.Name for obj in root_objects]}")


def test_tree_building_from_subobjects(doc: FreeCAD.Document) -> None:
    """Test tree building using getSubObjects() method.

    Strategy: Use obj.getSubObjects() to get sub-object names, then resolve them.
    """
    print_section("Tree Building from getSubObjects()")

    print("\nSub-objects per object:")
    for obj in doc.Objects:
        sub_objs = getattr(obj, "getSubObjects", lambda: ())()
        if sub_objs:
            print(f"  {obj.Name} ({obj.TypeId}): {sub_objs}")

    # Test resolving sub-object names to actual objects
    print("\nResolving sub-object names:")
    for obj in doc.Objects:
        sub_objs = getattr(obj, "getSubObjects", lambda: ())()
        if sub_objs:
            print(f"  {obj.Name}:")
            for sub_name in sub_objs:
                # Sub-object names are like "Body.", "Sketch.001.Face3"
                # The first part before '.' is the object name
                base_name = sub_name.split(".")[0]
                resolved = doc.getObject(base_name)
                print(f"    {sub_name} -> {base_name} -> {resolved}")


def test_property_extraction_patterns(doc: FreeCAD.Document) -> None:
    """Test property extraction patterns for different property types.

    Note: ALL properties are extracted for snapshots. Filtering happens during diff computation.
    """
    print_section("Property Extraction Patterns")

    for obj in doc.Objects:
        print(f"\n{obj.Name} ({obj.TypeId}):")

        for prop_name in obj.PropertiesList:
            # Extract ALL properties - no exclusions in snapshot creation

            try:
                value = getattr(obj, prop_name)
                value_type = type(value).__name__

                # Handle special cases
                if value is None:
                    print(f"  {prop_name}: None ({value_type})")
                elif isinstance(value, (list, tuple)):
                    if len(value) > 0:
                        sample = value[0]
                        if hasattr(sample, "Name"):
                            print(f"  {prop_name}: List[{sample.Name}] ({value_type}, len={len(value)})")
                        else:
                            print(f"  {prop_name}: {value_type} (len={len(value)})")
                    else:
                        print(f"  {prop_name}: [] ({value_type})")
                else:
                    # Truncate long strings
                    display_value = str(value)
                    if len(display_value) > 50:
                        display_value = display_value[:47] + "..."
                    print(f"  {prop_name}: {display_value} ({value_type})")
            except Exception as e:
                print(f"  {prop_name}: ERROR - {e}")


def test_treenode_construction(doc: FreeCAD.Document) -> None:
    """Test constructing TreeNode objects from FreeCAD objects.

    Note: ALL properties are extracted - no exclusions in snapshot creation.
    Filtering happens during diff computation.
    """
    print_section("TreeNode Construction Test")

    # Build a simple tree with one root and its children
    test_obj = None
    for obj in doc.Objects:
        if obj.TypeId == "PartDesign::Body":
            test_obj = obj
            break

    if test_obj is None:
        print("No PartDesign::Body found, using first object")
        for obj in doc.Objects:
            test_obj = obj
            break

    if test_obj is None:
        print("No suitable object found")
        return

    print(f"\nBuilding TreeNode for: {test_obj.Name} ({test_obj.TypeId})")

    # Extract ALL properties - no exclusions in snapshot creation
    properties = {}
    for prop_name in test_obj.PropertiesList:
        try:
            value = getattr(test_obj, prop_name)
            # Include all properties (including None values for completeness)
            properties[prop_name] = PropertyValue(value=value, type_name=type(value).__name__)
        except Exception as e:
            print(f"  Warning: Could not extract {prop_name}: {e}")

    # Create TreeNode
    node = TreeNode(
        name=test_obj.Name,
        type_id=test_obj.TypeId,
        label=test_obj.Label,
        path=test_obj.Name,
        is_root=True,
        properties=properties,
        children=[],
    )

    print(f"Created: {node}")
    print(f"Properties count: {len(properties)}")
    print(f"Sample properties: {list(properties.keys())[:5]}")


def test_edge_cases(doc: FreeCAD.Document) -> None:
    """Test edge cases like empty documents, objects with errors, etc."""
    print_section("Edge Case Validation")

    # Check for objects with missing attributes
    print("\nChecking for objects with missing attributes:")
    for obj in doc.Objects:
        issues = []

        if not hasattr(obj, "Name"):
            issues.append("missing Name")
        if not hasattr(obj, "TypeId"):
            issues.append("missing TypeId")
        if not hasattr(obj, "PropertiesList"):
            issues.append("missing PropertiesList")
        if not hasattr(obj, "getSubObjects"):
            issues.append("missing getSubObjects method")

        if issues:
            print(f"  {obj.Name}: {', '.join(issues)}")

    # Check for objects with empty property lists
    empty_prop_objects = [obj for obj in doc.Objects if not getattr(obj, "PropertiesList", [])]
    if empty_prop_objects:
        print(f"\nObjects with empty PropertiesList: {[obj.Name for obj in empty_prop_objects]}")
    else:
        print("\nAll objects have PropertiesList")

    # Check for objects that might have errors
    print("\nChecking for potential error conditions:")
    for obj in doc.Objects[:5]:  # Check first 5 objects
        for prop_name in getattr(obj, "PropertiesList", [])[:3]:  # Check first 3 properties
            try:
                value = getattr(obj, prop_name)
                # Check for problematic values
                if isinstance(value, str) and "Error" in value:
                    print(f"  {obj.Name}.{prop_name}: Contains 'Error' string")
            except Exception as e:
                print(f"  {obj.Name}.{prop_name}: Exception - {e}")


def test_snapshot_domain_model(doc: FreeCAD.Document) -> None:
    """Test creating a complete Snapshot domain object.

    Note: ALL objects and ALL properties are included in snapshots.
    Filtering happens during diff computation, not snapshot creation.
    """
    print_section("Snapshot Domain Model Test")

    # Build root nodes (top-level objects) - INCLUDE ALL OBJECTS
    root_nodes = []

    for obj in doc.Objects:
        # Extract ALL properties - no exclusions in snapshot creation
        properties = {}
        for prop_name in obj.PropertiesList:
            try:
                value = getattr(obj, prop_name)
                # Include all properties (including None values)
                properties[prop_name] = PropertyValue(value=value, type_name=type(value).__name__)
            except Exception as e:
                print(f"  Warning: Could not extract {obj.Name}.{prop_name}: {e}")

        # Create TreeNode
        node = TreeNode(
            name=obj.Name,
            type_id=obj.TypeId,
            label=obj.Label,
            path=obj.Name,
            is_root=True,
            properties=properties,
            children=[],
        )
        root_nodes.append(node)

    # Create Snapshot
    from datetime import datetime

    snapshot = Snapshot(document_name=doc.Name, timestamp=datetime.now(), root_nodes=root_nodes)

    print(f"\nCreated Snapshot: {snapshot}")
    print(f"Root nodes count: {len(snapshot.root_nodes)}")
    print(f"Total nodes (including children): {sum(1 for n in snapshot.get_all_nodes())}")

    # Print tree structure
    print("\nTree structure:")
    for root in snapshot.root_nodes[:5]:  # Show first 5 roots
        print(f"  {root.path} [{root.type_id}]")
        for child in root.children[:3]:  # Show first 3 children
            print(f"    └── {child.name} [{child.type_id}]")


def main():
    """Main gap analysis function."""
    print("=" * 60)
    print("SNAPSHOT EXTRACTION GAP ANALYSIS")
    print("=" * 60)

    # Open the test document
    doc_path = "tests/freecad/BasicFile.FCStd"
    print(f"\nOpening document: {doc_path}")

    doc = FreeCAD.openDocument(doc_path)
    if doc is None:
        print("ERROR: Failed to open document")
        return

    print(f"Document opened: {doc.Name} with {len(doc.Objects)} objects")

    # Run all tests
    test_tree_building_from_outlist(doc)
    test_tree_building_from_subobjects(doc)
    test_property_extraction_patterns(doc)
    test_treenode_construction(doc)
    test_edge_cases(doc)
    test_snapshot_domain_model(doc)

    # Summary
    print_section("GAP ANALYSIS SUMMARY")

    print("""
Identified Gaps:

1. TREE BUILDING STRATEGY:
   - OutList approach: Works for finding parent-child relationships
   - getSubObjects() approach: Returns name strings that need resolution
   - RECOMMENDATION: Use OutList for top-level hierarchy, getSubObjects() for nested sub-objects

2. SUB-OBJECT RESOLUTION:
   - getSubObjects() returns strings like "Body.", "Sketch.001.Face3"
   - Need to resolve base object names using doc.getObject(base_name)
   - For deep sub-objects (e.g., "Face3"), may need to access via obj.getSubObject(sub_name)

3. EDGE CASES TO HANDLE:
   - Objects with missing getSubObjects method (use getattr with default)
   - Empty property lists (should not occur but handle gracefully)
   - Property access exceptions (wrap in try-except)

4. MISSING FreeCAD PORT METHODS:
   - Currently missing: No additional methods needed beyond existing FreeCadPort
   - Existing methods (get_active_document, get_object) are sufficient

CRITICAL CORRECTION - Snapshot vs Diff Filtering:
- Snapshots capture ALL objects and ALL properties (no exclusions)
- Filtering happens during DIFF COMPUTATION only (in the diff/ module)
- Properties like Label2, TimeStamp, Shape are INCLUDED in snapshots
- Object types like App::Origin, App::Line are INCLUDED in snapshots

Recommendations for Implementation:
- Use OutList for building initial tree structure
- Use getSubObjects() for objects that have nested sub-objects
- Wrap all property access in try-except blocks
- DO NOT filter properties or types during snapshot extraction
- Filtering configuration belongs in the diff/ module for diff computation
""")

    # Close document
    FreeCAD.closeDocument(doc.Name)
    print("\nGap analysis complete.")


if __name__ == "__main__":
    main()
