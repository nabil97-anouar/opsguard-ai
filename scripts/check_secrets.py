#!/usr/bin/env python3
"""Targeted credential guard; prints locations and rule names, never matching text.

Default: tracked and non-ignored untracked working files. --staged: index blobs,
so a clean working copy cannot conceal a secret already staged for commit.
This is a limited local guard, not comprehensive secret detection or key validation.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    rule: str


PATTERNS = (
    ("provider-key", re.compile(rb"\bsk-[A-Za-z0-9_-]{20,}")),
    ("github-token", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")),
    ("private-key", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("aws-access-key", re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
)
SECRET_SETTING = re.compile(rb"^\s*(?:export\s+)?[A-Z0-9_]*(?:API_KEY|ACCESS_TOKEN|AUTH_TOKEN|CLIENT_SECRET)\s*=\s*(.*?)\s*$")


def forbidden_file(path: str) -> bool:
    name = Path(path).name
    return (name == ".env" or name.startswith(".env.") and name != ".env.example"
            or bool(re.search(r"\.(?:db|sqlite3?)(?:-wal|-shm|-journal)?$", name)))


def scan_content(path: str, content: bytes) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(content.splitlines(), 1):
        for rule, pattern in PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path, line_number, rule))
        if Path(path).name == ".env.example":
            match = SECRET_SETTING.match(line)
            # Keep credential examples empty; comments explain how to fill .env.
            if match and match.group(1).strip(b"\"'"):
                findings.append(Finding(path, line_number, "nonempty-example-credential"))
    return findings


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def check_repository(root: Path, *, staged: bool = False) -> tuple[int, list[Finding]]:
    names = git(root, "ls-files", "-z", "--cached") if staged else git(
        root, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    findings: list[Finding] = []
    count = 0
    for raw in sorted(set(names.split(b"\0")) - {b""}):
        name = raw.decode("utf-8", errors="surrogateescape")
        if forbidden_file(name):
            findings.append(Finding(name, 1, "private-local-file"))
            continue  # Do not open local secret files or databases, even if tracked.
        if staged:
            content = git(root, "show", f":{name}")
        else:
            file = root / name
            if not file.is_file() or file.is_symlink():
                continue
            content = file.read_bytes()
        count += 1
        findings.extend(scan_content(name, content))
    return count, findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="inspect index content, not working files")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        count, findings = check_repository(root, staged=args.staged)
    except (OSError, subprocess.CalledProcessError):
        print("Credential check could not read the repository; check failed.")
        return 2
    for finding in findings:
        print(f"{finding.path}:{finding.line}: {finding.rule} (value redacted)")
    if findings:
        print("Remove credentials/private local files before committing. Revoke any exposed real key.")
        return 1
    print(f"Credential guard passed for {count} {'index' if args.staged else 'working'} files (limited known-pattern checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
