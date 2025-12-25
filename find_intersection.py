#!/usr/bin/env python3
"""
Script to find instance IDs that are in both remaining.json and a provided list.
"""

import json
import re
import sys


def load_json_with_comments(filepath):
    """Load JSON file, removing comments first."""
    with open(filepath, "r") as f:
        content = f.read()

    # Remove single-line comments (// ...)
    content = re.sub(r"//.*?$", "", content, flags=re.MULTILINE)

    # Remove multi-line comments (/* ... */)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    return json.loads(content)


def main():
    # List of instance IDs to check (user will fill this up)
    instance_ids = [
        "astropy__astropy-12907",
        "astropy__astropy-14365",
        "astropy__astropy-14995",
        "astropy__astropy-6938",
        "django__django-10914",
        "django__django-10924",
        "django__django-11001",
        "django__django-11039",
        "django__django-11049",
        "django__django-11099",
        "django__django-11133",
        "django__django-11179",
        "django__django-11583",
        "django__django-11815",
        "django__django-11848",
        "django__django-11964",
        "django__django-11999",
        "django__django-12125",
        "django__django-12284",
        "django__django-12308",
        "django__django-12453",
        "django__django-12497",
        "django__django-12915",
        "django__django-12983",
        "django__django-13028",
        "django__django-13158",
        "django__django-13220",
        "django__django-13230",
        "django__django-13315",
        "django__django-13447",
        "django__django-13551",
        "django__django-13658",
        "django__django-13660",
        "django__django-13710",
        "django__django-13757",
        "django__django-13925",
        "django__django-13933",
        "django__django-14016",
        "django__django-14017",
        "django__django-14238",
        "django__django-14382",
        "django__django-14411",
        "django__django-14534",
        "django__django-14672",
        "django__django-14752",
        "django__django-14787",
        "django__django-14855",
        "django__django-14915",
        "django__django-14999",
        "django__django-15213",
        "django__django-15347",
        "django__django-15790",
        "django__django-15851",
        "django__django-15902",
        "django__django-16041",
        "django__django-16046",
        "django__django-16139",
        "django__django-16255",
        "django__django-16379",
        "django__django-16527",
        "django__django-16595",
        "django__django-16873",
        "django__django-16910",
        "django__django-17087",
        "matplotlib__matplotlib-18869",
        "matplotlib__matplotlib-23314",
        "matplotlib__matplotlib-23562",
        "matplotlib__matplotlib-23913",
        "matplotlib__matplotlib-23987",
        "matplotlib__matplotlib-24334",
        "matplotlib__matplotlib-25079",
        "matplotlib__matplotlib-25332",
        "matplotlib__matplotlib-25442",
        "matplotlib__matplotlib-26020",
        "mwaskom__seaborn-3010",
        "mwaskom__seaborn-3190",
        "pallets__flask-4992",
        "pylint-dev__pylint-6506",
        "pylint-dev__pylint-7114",
        "pylint-dev__pylint-7993",
        "pytest-dev__pytest-5103",
        "pytest-dev__pytest-5227",
        "pytest-dev__pytest-5413",
        "pytest-dev__pytest-5692",
        "pytest-dev__pytest-6116",
        "pytest-dev__pytest-7168",
        "pytest-dev__pytest-7432",
        "pytest-dev__pytest-8906",
        "scikit-learn__scikit-learn-10297",
        "scikit-learn__scikit-learn-10508",
        "scikit-learn__scikit-learn-10949",
        "scikit-learn__scikit-learn-11281",
        "scikit-learn__scikit-learn-12471",
        "scikit-learn__scikit-learn-13241",
        "scikit-learn__scikit-learn-13439",
        "scikit-learn__scikit-learn-13496",
        "scikit-learn__scikit-learn-13584",
        "scikit-learn__scikit-learn-14894",
        "scikit-learn__scikit-learn-14983",
        "scikit-learn__scikit-learn-25570",
        "sphinx-doc__sphinx-10325",
        "sphinx-doc__sphinx-8474",
        "sphinx-doc__sphinx-8506",
        "sphinx-doc__sphinx-8595",
        "sphinx-doc__sphinx-8721",
        "sympy__sympy-13177",
        "sympy__sympy-13471",
        "sympy__sympy-13480",
        "sympy__sympy-13647",
        "sympy__sympy-14396",
        "sympy__sympy-14774",
        "sympy__sympy-15346",
        "sympy__sympy-17655",
        "sympy__sympy-18532",
        "sympy__sympy-18621",
        "sympy__sympy-20212",
        "sympy__sympy-20590",
        "sympy__sympy-21055",
        "sympy__sympy-21614",
        "sympy__sympy-21847",
        "sympy__sympy-22714",
        "sympy__sympy-23117",
        "sympy__sympy-23262",
        "sympy__sympy-24066",
        "sympy__sympy-24213",
    ]

    # Load remaining.json
    remaining_file = "remaining.json"
    try:
        remaining_ids = load_json_with_comments(remaining_file)
    except FileNotFoundError:
        print(f"Error: {remaining_file} not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing {remaining_file}: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert to sets for efficient intersection
    remaining_set = set(remaining_ids)
    instance_set = set(instance_ids)

    # Find intersection
    intersection = remaining_set & instance_set

    # Print results
    if intersection:
        print("Instance IDs in both lists:")
        for instance_id in sorted(intersection):
            print(instance_id)
    else:
        print("No instance IDs found in both lists.")

    # Also print count for convenience
    print(f"\nTotal: {len(intersection)} instance ID(s) in both lists")


if __name__ == "__main__":
    main()
