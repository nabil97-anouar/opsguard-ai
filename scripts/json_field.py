#!/usr/bin/env python3
"""Extract a required dotted JSON field from stdin (code is read from this file)."""
import json
import sys


def extract(value, path):
    for part in path.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    if value is None:
        raise ValueError("field is null")
    return value


if __name__ == "__main__":
    try:
        print(extract(json.load(sys.stdin), sys.argv[1]))
    except (ValueError, KeyError, IndexError, TypeError):
        sys.exit("Could not extract required JSON field; check the API response and field path.")
