#!/usr/bin/env python3
"""pip-audit with a high/critical gate; enrich advisory severity from GitHub.

Unrated advisories and scanner/feed failures require review and fail the check.
Low/moderate findings are printed, not silently ignored or treated as failures.
"""
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen


def advisory_severity(vulnerability, fetch):
    identifiers = {vulnerability["id"], *vulnerability.get("aliases", [])}
    ghsa_ids = sorted(identifier for identifier in identifiers if identifier.startswith("GHSA-"))
    if not ghsa_ids:
        return "unknown"
    levels = [fetch(identifier).get("severity", "unknown") for identifier in ghsa_ids]
    order = {"low": 0, "medium": 1, "moderate": 1, "high": 2, "critical": 3, "unknown": 4}
    return max(levels, key=lambda level: order.get(level, 4))


def blocks(severity):
    return severity not in {"low", "medium", "moderate"}


def fetch_advisory(identifier):
    request = Request(f"https://api.github.com/advisories/{identifier}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "opsguard-dependency-audit"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def main():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, "-m", "pip_audit", "-r", str(root / "backend/requirements-dev.txt"),
        "--no-deps", "--disable-pip", "--format=json"], capture_output=True, text=True)
    if result.returncode not in {0, 1}:
        raise SystemExit("Python dependency scanner failed; no clean audit result is available.")
    try:
        report = json.loads(result.stdout)
        findings = []
        for dependency in report["dependencies"]:
            if dependency.get("skip_reason"):
                raise ValueError("Dependency could not be audited")
            for vulnerability in dependency["vulns"]:
                severity = advisory_severity(vulnerability, fetch_advisory)
                findings.append({"package": dependency["name"], "version": dependency["version"],
                    "advisory": vulnerability["id"], "severity": severity,
                    "fix_versions": vulnerability.get("fix_versions", [])})
        print(json.dumps({"dependencies_checked": len(report["dependencies"]), "findings": findings}, indent=2))
        if any(blocks(finding["severity"]) for finding in findings):
            raise SystemExit("High/critical or unrated Python advisories require resolution/review.")
    except (ValueError, KeyError, OSError):
        raise SystemExit("Dependency/advisory lookup failed; no clean audit result is available.") from None


if __name__ == "__main__":
    main()
