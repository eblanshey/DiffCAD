#!/usr/bin/env python3
"""
FreeCAD Document Structure Exploration Script

This script explores a FreeCAD document and outputs COMPLETE API responses
for all objects, properties, expressions, and hierarchy information.
The output is designed to inform domain object design for snapshots and diffing.

Output format: YAML (for collapsible sections in viewers)

Usage:
    ./run_with_freecad.sh python scripts/explore_document_structure.py <document_path>

If no document path is provided, uses the test document: tests/freecad/BasicFile.FCStd
"""

import sys
from datetime import datetime


def safe_repr(value, max_depth=3, current_depth=0):
    """Safely convert complex values to string representation."""
    if current_depth > max_depth:
        return "<max depth exceeded>"

    if value is None:
        return "None"

    try:
        # Handle common FreeCAD types
        value_type = type(value).__name__

        # For vectors and placements
        if hasattr(value, 'x') and hasattr(value, 'y') and hasattr(value, 'z'):
            return f"Vector(x={value.x}, y={value.y}, z={value.z})"

        # For placements
        if hasattr(value, 'Base') and hasattr(value, 'Rotation'):
            base = safe_repr(value.Base, max_depth, current_depth + 1)
            rotation = safe_repr(value.Rotation, max_depth, current_depth + 1)
            return f"Placement(Base={base}, Rotation={rotation})"

        # For rotations
        if hasattr(value, 'Axis') and hasattr(value, 'Angle'):
            axis = safe_repr(value.Axis, max_depth, current_depth + 1)
            angle = value.Angle
            return f"Rotation(Axis={axis}, Angle={angle} rad)"

        # For matrices
        if hasattr(value, 'A11'):
            attrs = ['A11', 'A12', 'A13', 'A14', 'A21', 'A22', 'A23', 'A24',
                     'A31', 'A32', 'A33', 'A34', 'A41', 'A42', 'A43', 'A44']
            matrix_str = ', '.join(f"{a}={getattr(value, a, '?')}" for a in attrs)
            return f"Matrix({matrix_str})"

        # For lists/tuples
        if isinstance(value, (list, tuple)):
            if len(value) == 0:
                return "[]"
            if len(value) > 20:
                items = [safe_repr(v, max_depth, current_depth + 1) for v in value[:20]]
                return f"[{', '.join(items)}, ... ({len(value) - 20} more)]"
            items = [safe_repr(v, max_depth, current_depth + 1) for v in value]
            return f"[{', '.join(items)}]"

        # For dicts
        if isinstance(value, dict):
            if len(value) == 0:
                return "{}"
            items = [f"{k!r}: {safe_repr(v, max_depth, current_depth + 1)}" for k, v in list(value.items())[:20]]
            if len(value) > 20:
                items.append(f"... ({len(value) - 20} more keys)")
            return '{' + ', '.join(items) + '}'

        # For strings, limit length
        if isinstance(value, str):
            if len(value) > 200:
                return f'"{value[:200]}... (truncated)"'
            return repr(value)

        # For other types, try str first, then repr
        return repr(value)

    except Exception as e:
        return f"<error converting to string: {e}>"


def get_property_type_name(obj, prop_name):
    """Get the property type name for a given property."""
    try:
        # Try to get the property info tuple
        if hasattr(obj, 'getPropertyInterface'):
            try:
                interface = obj.getPropertyInterface(prop_name)
                if interface:
                    return interface.__name__
            except:
                pass

        # Try TypeId of the property value
        prop_value = getattr(obj, prop_name)
        if hasattr(prop_value, 'TypeId'):
            return f"Value.TypeId={prop_value.TypeId}"

        # Return Python type
        return type(prop_value).__name__

    except Exception as e:
        return f"<error: {e}>"


def explore_object(obj, doc):
    """Explore a single document object and return detailed information."""
    result = {}

    # Basic object info
    result['Name'] = obj.Name
    result['TypeId'] = obj.TypeId
    result['Label'] = obj.Label

    # UUID if available
    try:
        result['UUID'] = str(obj.UUID)
    except:
        result['UUID'] = "<not available>"

    # Position/Placement if available
    try:
        if hasattr(obj, 'Placement'):
            result['Placement'] = safe_repr(obj.Placement)
    except Exception as e:
        result['Placement'] = f"<error: {e}>"

    try:
        if hasattr(obj, 'Position'):
            result['Position'] = safe_repr(obj.Position)
    except Exception as e:
        result['Position'] = f"<error: {e}>"

    try:
        if hasattr(obj, 'Rotation'):
            result['Rotation'] = safe_repr(obj.Rotation)
    except Exception as e:
        result['Rotation'] = f"<error: {e}>"

    try:
        if hasattr(obj, 'Scale'):
            result['Scale'] = safe_repr(obj.Scale)
    except Exception as e:
        result['Scale'] = f"<error: {e}>"

    # Properties - DETAILED exploration
    properties = {}
    try:
        props_list = obj.PropertiesList
        for prop_name in props_list:
            prop_info = {
                'Type': get_property_type_name(obj, prop_name),
            }

            # Get value
            try:
                prop_info['Value'] = safe_repr(getattr(obj, prop_name))
            except Exception as e:
                prop_info['Value'] = f"<error reading: {e}>"

            # Get expression from ExpressionEngine list
            # Note: getExpression() method does NOT exist in this FreeCAD version
            # Expressions are stored in ExpressionEngine as [(prop_name, expression), ...]
            try:
                expr_engine = getattr(obj, 'ExpressionEngine', [])
                expr = None
                if isinstance(expr_engine, list):
                    for entry in expr_engine:
                        if isinstance(entry, (list, tuple)) and len(entry) >= 2:
                            if entry[0] == prop_name:
                                expr = entry[1]
                                break
                prop_info['Expression'] = expr if expr else "(none)"
                prop_info['HasExpression'] = bool(expr)
            except Exception as e:
                prop_info['Expression'] = f"<error: {e}>"
                prop_info['HasExpression'] = False

            properties[prop_name] = prop_info
    except Exception as e:
        properties['<error>'] = f"Could not enumerate properties: {e}"

    result['Properties'] = properties
    result['PropertyCount'] = len(properties)

    # Hierarchy information
    hierarchy = {}

    # InList (objects that reference this object)
    try:
        in_list = obj.InList
        hierarchy['InList'] = [o.Name for o in in_list] if in_list else []

        # Detailed InList with relationship info
        in_list_details = []
        for parent in (in_list or []):
            try:
                # Try to find the property name that references this object
                ref_props = []
                for prop_name in parent.PropertiesList:
                    try:
                        val = getattr(parent, prop_name)
                        if val is obj:
                            ref_props.append(prop_name)
                    except:
                        pass
                in_list_details.append({
                    'Name': parent.Name,
                    'TypeId': parent.TypeId,
                    'ReferencingProperties': ref_props
                })
            except Exception as e:
                in_list_details.append({'Name': parent.Name, 'error': str(e)})
        hierarchy['InListDetailed'] = in_list_details
    except Exception as e:
        hierarchy['InList'] = f"<error: {e}>"

    # OutList (objects referenced by this object)
    try:
        out_list = obj.OutList
        hierarchy['OutList'] = [o.Name for o in out_list] if out_list else []

        # Detailed OutList
        out_list_details = []
        for child in (out_list or []):
            try:
                # Try to find the property name that references the child
                ref_props = []
                for prop_name in obj.PropertiesList:
                    try:
                        val = getattr(obj, prop_name)
                        if val is child:
                            ref_props.append(prop_name)
                    except:
                        pass
                out_list_details.append({
                    'Name': child.Name,
                    'TypeId': child.TypeId,
                    'ReferencingProperties': ref_props
                })
            except Exception as e:
                out_list_details.append({'Name': child.Name, 'error': str(e)})
        hierarchy['OutListDetailed'] = out_list_details
    except Exception as e:
        hierarchy['OutList'] = f"<error: {e}>"

    # SubObjects
    try:
        sub_objects = obj.SubObjects
        hierarchy['SubObjects'] = sub_objects if sub_objects else []
    except Exception as e:
        hierarchy['SubObjects'] = f"<error: {e}>"

    # getSubObjects() method
    try:
        sub_objs_method = obj.getSubObjects()
        hierarchy['getSubObjects()'] = sub_objs_method if sub_objs_method else []
    except Exception as e:
        hierarchy['getSubObjects()'] = f"<error: {e}>"

    result['Hierarchy'] = hierarchy

    # Property Groups
    property_groups = {}
    try:
        if hasattr(obj, 'getPropertyGroups'):
            groups = obj.getPropertyGroups()
            for group_name in (groups or []):
                try:
                    props_in_group = obj.getPropertiesInGroup(group_name)
                    property_groups[group_name] = props_in_group if props_in_group else []
                except Exception as e:
                    property_groups[group_name] = f"<error: {e}>"
    except Exception as e:
        property_groups['<error>'] = f"Could not enumerate groups: {e}"

    result['PropertyGroups'] = property_groups

    # Additional object-specific attributes
    additional_attrs = {}
    common_attrs = ['Shape', 'ViewProvider', 'Document', 'FullName',
                    'GroupName', 'InListDepth', 'OutListDepth']

    for attr in common_attrs:
        try:
            if hasattr(obj, attr):
                value = getattr(obj, attr)
                # Skip ViewProvider for now (GUI only)
                if attr == 'ViewProvider' and value is not None:
                    additional_attrs[attr] = "<ViewProvider (GUI only)>"
                else:
                    additional_attrs[attr] = safe_repr(value)
        except Exception as e:
            additional_attrs[attr] = f"<error: {e}>"

    result['AdditionalAttributes'] = additional_attrs

    return result


def format_yaml_output(doc_path, doc_info):
    """Format the exploration output as YAML."""
    import yaml

    output_data = {
        'metadata': {
            'generator': 'FreeCAD Document Structure Exploration Script',
            'generated_at': datetime.now().isoformat(),
            'document_path': doc_path,
        },
        'document_info': {
            'name': doc_info.get('DocumentName', 'N/A'),
            'path': doc_info.get('DocumentPath', 'N/A'),
            'object_count': doc_info.get('ObjectCount', 0),
        },
        'objects': doc_info.get('Objects', []),
        'summary': {
            'object_types': {},
            'property_names': {},
            'property_types': {},
            'properties_with_expressions': [],
            'potential_excluded_properties': {},
        }
    }

    # Calculate summary statistics
    type_counts = {}
    all_props = {}
    prop_types = {}
    expr_props = []

    for obj_info in doc_info.get('Objects', []):
        # Object types
        t = obj_info['TypeId']
        type_counts[t] = type_counts.get(t, 0) + 1

        # Property names
        for prop_name, prop_info in obj_info.get('Properties', {}).items():
            if prop_name != '<error>':
                all_props[prop_name] = all_props.get(prop_name, 0) + 1
                ptype = prop_info.get('Type', 'Unknown')
                prop_types[ptype] = prop_types.get(ptype, 0) + 1

                if prop_info.get('HasExpression', False):
                    expr_props.append(f"{obj_info['Name']}.{prop_name}")

    output_data['summary']['object_types'] = dict(sorted(type_counts.items()))
    output_data['summary']['property_names'] = dict(sorted(all_props.items(), key=lambda x: -x[1]))
    output_data['summary']['property_types'] = dict(sorted(prop_types.items(), key=lambda x: -x[1]))
    output_data['summary']['properties_with_expressions'] = expr_props

    # Potential excluded properties
    auto_props = ['TimeStamp', 'LastModified', 'Label2', 'FullName',
                  'InList', 'OutList', 'InListDepth', 'OutListDepth']
    found_auto = {p: all_props[p] for p in auto_props if p in all_props}
    output_data['summary']['potential_excluded_properties'] = found_auto

    # Convert to YAML
    yaml_output = yaml.dump(output_data, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return yaml_output


def main():
    """Main exploration function."""
    import FreeCAD

    # Get document path from args or use default
    if len(sys.argv) > 1:
        doc_path = sys.argv[1]
    else:
        doc_path = "tests/freecad/BasicFile.FCStd"

    print(f"Exploring document: {doc_path}")
    print()

    try:
        # Open the document
        doc = FreeCAD.openDocument(doc_path)

        if doc is None:
            print(f"ERROR: Could not open document: {doc_path}")
            sys.exit(1)

        # Collect document info
        doc_info = {
            'DocumentName': doc.Name,
            'DocumentPath': getattr(doc, 'FileName', doc_path),
            'ObjectCount': len(doc.Objects),
            'Objects': []
        }

        # Explore each object
        for obj in doc.Objects:
            try:
                obj_info = explore_object(obj, doc)
                doc_info['Objects'].append(obj_info)
            except Exception as e:
                print(f"WARNING: Error exploring object {obj.Name}: {e}")
                doc_info['Objects'].append({
                    'Name': obj.Name,
                    'TypeId': obj.TypeId,
                    'Label': obj.Label,
                    'Properties': {'<error>': f'Could not explore: {e}'}
                })

        # Format and print YAML output
        output = format_yaml_output(doc_path, doc_info)
        print(output)

        # Also save to file
        output_file = "docs/api-exploration/examples/basic-file-output.yaml"
        try:
            import os
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"\nYAML output saved to: {output_file}")
        except Exception as e:
            print(f"\nWARNING: Could not save to file: {e}")

        # Note: doc.close() doesn't exist in FreeCAD API - just let it be garbage collected

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
