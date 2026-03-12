#!/usr/bin/env python3
"""
Explore FreeCAD expression support in detail.

This script specifically tests:
1. Which objects have getExpression() method
2. How ExpressionEngine stores expressions
3. How to retrieve expression for a specific property
"""

import sys


def main():
    import FreeCAD

    doc_path = "tests/freecad/BasicFile.FCStd" if len(sys.argv) < 2 else sys.argv[1]

    print(f"Exploring expressions in: {doc_path}")
    print("=" * 80)

    doc = FreeCAD.openDocument(doc_path)

    # Find the Pocket object
    pocket = None
    for obj in doc.Objects:
        if obj.Name == "Pocket":
            pocket = obj
            break

    if pocket is None:
        print("ERROR: Could not find Pocket object!")
        sys.exit(1)

    print(f"\n=== POCKET OBJECT ===")
    print(f"Name: {pocket.Name}")
    print(f"TypeId: {pocket.TypeId}")
    print(f"Label: {pocket.Label}")

    # Check if getExpression method exists
    print(f"\n--- Method Availability ---")
    print(f"Has getExpression: {hasattr(pocket, 'getExpression')}")
    print(f"Has setExpression: {hasattr(pocket, 'setExpression')}")
    print(f"Has ExpressionEngine: {hasattr(pocket, 'ExpressionEngine')}")

    # Check ExpressionEngine
    print(f"\n--- ExpressionEngine ---")
    expr_engine = getattr(pocket, 'ExpressionEngine', [])
    print(f"ExpressionEngine value: {expr_engine}")
    print(f"ExpressionEngine type: {type(expr_engine)}")

    # Try to get expression for Length property using getExpression
    print(f"\n--- Testing getExpression('Length') ---")
    try:
        if hasattr(pocket, 'getExpression'):
            expr = pocket.getExpression("Length")
            print(f"Result: '{expr}'")
        else:
            print("getExpression method does NOT exist on this object type")
    except Exception as e:
        print(f"ERROR: {e}")

    # Parse ExpressionEngine manually
    print(f"\n--- Parsing ExpressionEngine ---")
    if isinstance(expr_engine, list):
        for entry in expr_engine:
            print(f"  Entry: {entry}")
            if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                prop_name = entry[0]
                expression = entry[1]
                print(f"    Property: {prop_name}")
                print(f"    Expression: {expression}")

    # Get actual Length value
    print(f"\n--- Actual Property Value ---")
    length_value = getattr(pocket, 'Length', 'N/A')
    print(f"Length value: {length_value}")

    # Check all objects for getExpression support
    print(f"\n{'=' * 80}")
    print(f"=== ALL OBJECTS - getExpression SUPPORT ===")
    print(f"{'=' * 80}")

    for obj in doc.Objects:
        has_get_expr = hasattr(obj, 'getExpression')
        has_expr_engine = hasattr(obj, 'ExpressionEngine')
        expr_engine_val = getattr(obj, 'ExpressionEngine', [])

        # Only show objects with non-empty ExpressionEngine or no getExpression
        if expr_engine_val or not has_get_expr:
            print(f"\n{obj.Name} ({obj.TypeId}):")
            print(f"  getExpression: {has_get_expr}")
            print(f"  ExpressionEngine: {expr_engine_val}")

    print(f"\n{'=' * 80}")
    print(f"END OF EXPRESSION EXPLORATION")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    main()