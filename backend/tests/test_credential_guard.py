from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_secrets.py"
spec = importlib.util.spec_from_file_location("credential_guard", SCRIPT)
assert spec and spec.loader
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)


def test_guard_identifies_key_without_retaining_value_in_finding():
    sentinel = "sk-" + "x" * 48
    findings = guard.scan_content("example.txt", ("line one\n" + sentinel).encode())
    assert len(findings) == 1
    assert findings[0].line == 2
    assert findings[0].rule == "provider-key"
    assert sentinel not in repr(findings)


@pytest.mark.parametrize("name", [".env", "frontend/.env.local", "opsguard-test.db", "data.sqlite3-wal"])
def test_private_file_names_are_rejected_without_reading_them(name):
    assert guard.forbidden_file(name) is True


def test_empty_example_credentials_pass_but_nonempty_values_fail():
    assert guard.forbidden_file(".env.example") is False
    assert guard.scan_content(".env.example", b"OPENAI_API_KEY=\nINSTITUTIONAL_LLM_API_KEY=\n") == []
    findings = guard.scan_content(".env.example", b"INSTITUTIONAL_LLM_API_KEY=unexpected-value\n")
    assert [item.rule for item in findings] == ["nonempty-example-credential"]


def test_staged_scan_reads_index_instead_of_sanitized_working_copy(tmp_path):
    def git(*args):
        subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    git("init", "--quiet")
    sentinel = "sk-" + "z" * 48
    path = tmp_path / "settings.txt"
    path.write_text(sentinel)
    git("add", "settings.txt")
    path.write_text("sanitized")
    assert guard.check_repository(tmp_path)[1] == []
    findings = guard.check_repository(tmp_path, staged=True)[1]
    assert [item.rule for item in findings] == ["provider-key"]
    assert sentinel not in repr(findings)
