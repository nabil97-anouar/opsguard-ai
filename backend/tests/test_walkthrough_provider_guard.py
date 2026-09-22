"""The offline walkthrough must refuse external inference before any mutation."""
from pathlib import Path
import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("provider", ["openai", "institutional", "anthropic", "ollama", "unknown"])
def test_walkthrough_rejects_non_deterministic_backend_before_writes(tmp_path, provider):
    log = tmp_path / "requests.txt"
    curl = tmp_path / "curl"
    curl.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
from pathlib import Path
url = next(value for value in sys.argv if value.startswith("http"))
with Path(os.environ["REQUEST_LOG"]).open("a") as stream:
    stream.write(url + "\\n")
if url.endswith("/ready"):
    print(json.dumps({"status": "ready"}))
elif url.endswith("/runtime/reasoning"):
    print(json.dumps({"provider": os.environ["TEST_PROVIDER"], "mode": "external"}))
else:
    sys.exit("Unexpected mutation or inference")
''')
    curl.chmod(0o755)
    result = subprocess.run(["bash", str(ROOT / "scripts/demo_walkthrough.sh")],
        env={**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}",
             "TEST_PROVIDER": provider, "REQUEST_LOG": str(log)}, capture_output=True, text=True)
    assert result.returncode == 1
    assert "requires LLM_PROVIDER=deterministic" in result.stderr
    assert [url.rsplit("/api/v1", 1)[1] for url in log.read_text().splitlines()] == [
        "/ready", "/runtime/reasoning"]
