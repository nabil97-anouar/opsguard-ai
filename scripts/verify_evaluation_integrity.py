#!/usr/bin/env python3
"""Reproduce Milestone 2 A-H against an isolated temporary SQLite database.

Run: .venv/bin/python scripts/verify_evaluation_integrity.py --output-dir /tmp/opsguard-m2
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient

from app.db import session as db_session
from app.main import app
from app.services.demo_seed import demo_uuid


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="opsguard-evaluation-") as temporary:
        db_session.engine = db_session.build_engine(f"sqlite:///{temporary}/reproduction.db")
        client = TestClient(app)

        def post(path: str, body: dict) -> dict:
            response = client.post(f"/api/v1/{path}", json=body)
            response.raise_for_status()
            return response.json()

        post("demo/seed", {"reset": False})
        fixtures = client.get("/api/v1/harness/results").json()["items"]
        assert len(fixtures) == 6 and all(row["provenance"] == "fixture" for row in fixtures)
        preview = client.get("/api/v1/evaluation/summary").json()
        assert preview["cohort"]["provenance"] == "none"
        assert preview["metrics"]["scenario_pass_rate"]["value"] is None
        harness = post("harness/run", {"reset_demo_data": False})
        assert harness["provenance"] == "executed"
        assert (harness["passed"], harness["failed"], harness["partial"]) == (9, 0, 0)
        evaluation = post("evaluation/run", {"harness_run_id": harness["harness_run_id"], "run_harness_if_empty": False})
        evaluation_id = evaluation["evaluation_run_id"]
        assert evaluation["persisted"]
        suffix = f"?evaluation_run_id={evaluation_id}"
        json_response = client.get(f"/api/v1/evaluation/report.json{suffix}")
        md_response = client.get(f"/api/v1/evaluation/report.md{suffix}")
        json_response.raise_for_status()
        md_response.raise_for_status()
        report = json_response.json()
        assert report["evaluation_run_id"] == evaluation_id
        assert report["cohort"]["harness_run_id"] == harness["harness_run_id"]
        for identity in [evaluation_id, harness["harness_run_id"], report["cohort"]["provider_version"], report["cohort"]["policy_version"]]:
            assert identity in md_response.text
        for scenario in report["cohort"]["scenario_manifest"]:
            assert scenario["scenario_id"] in md_response.text
            assert scenario["scenario_version"] in md_response.text
            assert scenario["test_level"] in md_response.text

        activity = post("agent/runs", {"alert_id": str(demo_uuid("alert:rag-prompt-injection"))})
        assert activity["status"] == "waiting_for_human"
        assert activity["provenance"] == "executed"
        assert activity["agent_run_id"] not in report["cohort"]["agent_run_ids"]
        assert client.get(f"/api/v1/evaluation/report.json{suffix}").content == json_response.content
        assert client.get(f"/api/v1/evaluation/report.md{suffix}").content == md_response.content
        # Another evaluation must not redirect exports pinned to the original ID.
        second = post("harness/run", {"scenario_ids": ["clean_safe_case"], "reset_demo_data": False})
        post("evaluation/run", {"harness_run_id": second["harness_run_id"]})
        assert client.get(f"/api/v1/evaluation/report.json{suffix}").content == json_response.content
        assert client.get(f"/api/v1/evaluation/report.md{suffix}").content == md_response.content
        args.output_dir.joinpath("evaluation.json").write_text(json.dumps(report, indent=2) + "\n")
        args.output_dir.joinpath("evaluation.md").write_text(md_response.text)
        proof = {
            "fixture_count": len(fixtures), "evaluation_run_id": evaluation_id,
            "harness_run_id": harness["harness_run_id"],
            "unrelated_agent_run_id": activity["agent_run_id"],
            "stored_json_unchanged": True, "stored_markdown_unchanged": True,
            "json_sha256": hashlib.sha256(json_response.content).hexdigest(),
            "markdown_sha256": hashlib.sha256(md_response.content).hexdigest(),
            "metrics": report["metrics"],
        }
        args.output_dir.joinpath("reproduction-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
        print(json.dumps(proof, indent=2))
        db_session.engine.dispose()


if __name__ == "__main__":
    main()
