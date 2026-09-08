#!/usr/bin/env python3
"""Validate local Markdown file links; external URLs are not fetched."""
from pathlib import Path
import re
from urllib.parse import unquote


def main():
    root = Path(__file__).resolve().parents[1]
    files = [*root.glob("*.md"), *root.joinpath("docs").glob("*.md")]
    checked = 0
    errors = []
    for path in files:
        text = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        for href in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
            href = href.split(' "', 1)[0].strip("<>")
            if re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", href) or href.startswith("#"):
                continue
            checked += 1
            if not (path.parent / unquote(href.split("#", 1)[0])).exists():
                errors.append(f"{path.relative_to(root)}: {href}")
    if errors:
        raise SystemExit("Broken local links:\n" + "\n".join(errors))
    print(f"Validated {checked} local file links in {len(files)} Markdown files.")


if __name__ == "__main__":
    main()
