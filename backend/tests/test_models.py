from __future__ import annotations

from sqlmodel import SQLModel

from app.models import (
    AgentRun,
    AgentStep,
    Alert,
    Document,
    DocumentChunk,
    EvaluationScore,
    HumanFeedback,
    Incident,
    KillChainMapping,
    SafetyEvent,
    SecurityHarnessResult,
    SecurityHarnessTest,
    SelfAssessment,
    TicketDraft,
    ToolCall,
)

EXPECTED_TABLES = {
    "agent_runs",
    "agent_steps",
    "alerts",
    "document_chunks",
    "documents",
    "evaluation_scores",
    "human_feedback",
    "incidents",
    "kill_chain_mappings",
    "safety_events",
    "security_harness_results",
    "security_harness_tests",
    "self_assessments",
    "ticket_drafts",
    "tool_calls",
}


def test_models_import_successfully() -> None:
    assert Alert is not None
    assert Incident is not None
    assert Document is not None
    assert DocumentChunk is not None
    assert AgentRun is not None
    assert AgentStep is not None
    assert SelfAssessment is not None
    assert ToolCall is not None
    assert SafetyEvent is not None
    assert KillChainMapping is not None
    assert HumanFeedback is not None
    assert EvaluationScore is not None
    assert TicketDraft is not None
    assert SecurityHarnessTest is not None
    assert SecurityHarnessResult is not None


def test_metadata_contains_expected_tables() -> None:
    assert set(SQLModel.metadata.tables.keys()) == EXPECTED_TABLES
