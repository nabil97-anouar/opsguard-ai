"""Small, additive upgrades for evaluation-v2 and watchdog/tool audit v3.

Unknown historical rows deliberately remain legacy_unknown: is_demo identifies the
input's origin, not whether an agent actually ran. Only known seeded UUIDs are
positively classified as fixtures. No old result/report is re-scored.
"""
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlmodel import Session, select


def upgrade_evaluation_integrity(engine: Engine) -> None:
    additions = {
        "tool_calls": {
            "handler_invoked": "BOOLEAN",
            "outcome": "VARCHAR(30) NOT NULL DEFAULT 'legacy_unknown'",
            "origin": "VARCHAR(100) NOT NULL DEFAULT 'legacy_unknown'",
        },
        "ticket_drafts": {
            "lifecycle_state": "VARCHAR(40) NOT NULL DEFAULT 'legacy_unknown'",
            "policy_validation": "VARCHAR(40) NOT NULL DEFAULT 'not_evaluated'",
            "policy_version": "VARCHAR",
        },
        "agent_runs": {
            "provenance": "VARCHAR(30) NOT NULL DEFAULT 'legacy_unknown'",
            "execution_kind": "VARCHAR(30) NOT NULL DEFAULT 'unknown'",
            "provider_version": "VARCHAR",
            "policy_version": "VARCHAR",
        },
        "security_harness_results": {
            "provenance": "VARCHAR(30) NOT NULL DEFAULT 'legacy_unknown'",
            "test_level": "VARCHAR(30) NOT NULL DEFAULT 'unknown'",
            "scenario_version": "VARCHAR(50) NOT NULL DEFAULT 'unknown'",
        },
    }
    with engine.begin() as connection:
        for table, columns in additions.items():
            existing = {column["name"] for column in inspect(connection).get_columns(table)}
            for column, definition in columns.items():
                if column not in existing:
                    # All identifiers and SQL definitions above are internal constants.
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))

    from app.models import AgentRun, SecurityHarnessResult
    from app.services.demo_seed import build_agent_runs, build_harness_results

    with Session(engine) as session:
        for model, fixtures in ((AgentRun, build_agent_runs()), (SecurityHarnessResult, build_harness_results())):
            rows = session.exec(select(model).where(
                model.id.in_([record.id for record in fixtures]), model.provenance == "legacy_unknown"
            )).all()
            for row in rows:
                row.provenance = "fixture"
                if isinstance(row, AgentRun):
                    row.execution_kind = "fixture"
                else:
                    row.scenario_version = "demo-fixture-v1"
                session.add(row)
        session.commit()
