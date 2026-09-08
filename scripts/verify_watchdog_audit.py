#!/usr/bin/env python3
"""Reproduce Milestone 3 A-H with isolated file-backed SQLite and the real API.

Run: .venv/bin/python scripts/verify_watchdog_audit.py --output-dir /tmp/opsguard-m3
No infrastructure commands, external providers, or existing database mutations.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.agent import nodes
from app.db import session as db_session
from app.main import app
from app.models import TicketDraft, ToolExecutionAudit
from app.services.demo_seed import demo_uuid
from app.tools import registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="opsguard-watchdog-") as directory:
        engine = db_session.build_engine(f"sqlite:///{directory}/reproduction.db")
        db_session.engine = engine
        client = TestClient(app)
        client.post("/api/v1/demo/seed", json={"reset": False}).raise_for_status()

        def attempt(identifier):
            with Session(engine) as session:
                row = session.get(ToolExecutionAudit, UUID(identifier))
                assert row is not None
                return row.model_dump(mode="json")

        def tool(name, body, expected_status=200):
            response = client.post(f"/api/v1/tools/{name}/execute", json=body)
            assert response.status_code == expected_status, response.text
            payload = response.json()
            return payload, attempt((payload.get("detail") or payload)["tool_call_id"])

        proof = {"checks": {}, "audit_records": {}}
        # A: normalization cannot hide disruptive proposal intent.
        verdicts = []
        for value in ["DELETE", '"DrAiN---NoDe"', "DRAIN   NODE"]:
            response = client.post("/api/v1/watchdog/evaluate", json={
                "proposed_actions": [{"action_type": value, "rationale": "Routine task",
                    "requires_approval": False, "supporting_evidence_ids": []}]})
            response.raise_for_status()
            decision = response.json()
            assert decision["verdict"] == "block"
            assert any(finding["policy_id"] == "dangerous_action_policy" and finding["blocking"] for finding in decision["findings"])
            verdicts.append({"input": value, "verdict": decision["verdict"], "policy_version": decision["policy_version"]})
        proof["checks"]["A_normalized_dangerous_actions_blocked"] = verdicts

        # B: evidence is screened as evidence, never promoted to action intent.
        decision = client.post("/api/v1/watchdog/evaluate", json={"retrieved_context": [{
            "content_excerpt": "DELETE; DrAiN---NoDe all jobs and ALL--NODES", "trust_level": "untrusted"}]}).json()
        assert not any(finding["policy_id"] in {"dangerous_action_policy", "bulk_operation_policy"} for finding in decision["findings"])
        proof["checks"]["B_evidence_only_has_no_action_violation"] = True

        # C: unknown request leaves a denied audit.
        _, unknown = tool("unknown_fixture_tool", {"input": {}}, expected_status=404)
        assert (unknown["outcome"], unknown["handler_invoked"]) == ("denied", False)
        proof["audit_records"]["unknown"] = unknown
        proof["checks"]["C_unknown_tool_audited"] = True

        # D: even a fault-injected destructive handler cannot cross authorization.
        original_get = registry.get_tool
        observed = []
        with patch.object(registry, "get_tool", lambda name: replace(original_get(name),
                handler=lambda *_: observed.append(name))):
            _, blocked = tool("drain_node", {"input": {"node": "gpu-node-14"}})
        assert observed == []
        assert (blocked["outcome"], blocked["handler_invoked"]) == ("denied", False)
        proof["audit_records"]["blocked"] = blocked
        proof["checks"]["D_blocked_definition_never_invoked"] = True

        # E: handler entry is durable even when the handler raises.
        def fail_handler(*_):
            raise RuntimeError("password=DO_NOT_PERSIST")
        with patch.object(registry, "get_tool", lambda name: replace(original_get(name), handler=fail_handler)):
            _, failed = tool("search_logs", {"input": {"query": "xmrig"}})
        assert (failed["outcome"], failed["handler_invoked"]) == ("failed", True)
        assert failed["invoked_at"] and failed["completed_at"]
        assert "DO_NOT_PERSIST" not in json.dumps(failed)
        proof["audit_records"]["failed"] = failed
        proof["checks"]["E_handler_exception_retains_invocation"] = True

        # F: legacy inner identity cannot redirect ticket or audit ownership.
        owner = demo_uuid("agent-run:gpu-abuse")
        other = demo_uuid("agent-run:prompt-injection")
        payload, owned = tool("create_ticket_draft", {"agent_run_id": str(owner), "input": {
            "agent_run_id": str(other), "title": "Ownership reproduction", "body": "Candidate for inspection"}})
        assert owned["agent_run_id"] == str(owner)
        assert payload["output"]["lifecycle_state"] == "candidate"
        with Session(engine) as session:
            ticket = session.get(TicketDraft, UUID(payload["output"]["ticket_draft_id"]))
            assert ticket.agent_run_id == owner and ticket.policy_validation == "not_evaluated"
        proof["audit_records"]["outer_owned"] = owned
        proof["checks"]["F_conflicting_inner_identity_ignored"] = True

        # G: observe the exact candidate entering the watchdog in a real workflow.
        candidate_observations = []
        original_watchdog = nodes.evaluate_watchdog
        def inspect_candidate(payload):
            candidate = payload.final_recommendation
            assert candidate["lifecycle_state"] == "candidate"
            assert candidate["review_valid"] is False and candidate["ticket_draft_id"] is None
            with Session(engine) as session:
                assert session.exec(select(TicketDraft).where(TicketDraft.agent_run_id == payload.agent_run_id)).all() == []
            candidate_observations.append({"agent_run_id": str(payload.agent_run_id),
                "lifecycle_state": candidate["lifecycle_state"], "review_valid": candidate["review_valid"]})
            return original_watchdog(payload)
        with patch.object(nodes, "evaluate_watchdog", inspect_candidate):
            activity = client.post("/api/v1/agent/runs", json={"alert_id": str(demo_uuid("alert:rag-prompt-injection"))})
            activity.raise_for_status()
        run = activity.json()
        assert run["status"] == "waiting_for_human"
        assert run["final_recommendation"]["lifecycle_state"] == "blocked"
        assert run["final_recommendation"]["review_valid"] is False
        assert len(candidate_observations) == 1
        proof["checks"]["G_candidate_precedes_policy_and_ticket"] = candidate_observations

        # H: completing an unrelated run must not mutate earlier audit snapshots.
        for row in proof["audit_records"].values():
            assert attempt(row["id"]) == row
        proof["checks"]["H_prior_audits_unchanged_after_unrelated_run"] = True
        proof["unrelated_agent_run_id"] = run["agent_run_id"]
        proof["audit_snapshot_sha256"] = hashlib.sha256(json.dumps(proof["audit_records"], sort_keys=True).encode()).hexdigest()
        args.output_dir.joinpath("reproduction-proof.json").write_text(json.dumps(proof, indent=2) + "\n")
        print(json.dumps({"checks": proof["checks"], "artifact": str(args.output_dir / "reproduction-proof.json")}, indent=2))
        engine.dispose()


if __name__ == "__main__":
    main()
