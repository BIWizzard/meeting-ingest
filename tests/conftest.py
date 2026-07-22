from __future__ import annotations

from pathlib import Path

import pytest

from meeting_ingest.runtime import (
    BuildIdentity,
    InstallEvidence,
    RuntimeInspection,
    RuntimeProvenance,
    WorkflowEvidence,
)


def approved_runtime_inspection(root: Path) -> RuntimeInspection:
    build = BuildIdentity(
        schema_version="1.0",
        semantic_version="0.1.0",
        build_id="meeting-ingest-test-approved",
        source_commit="a" * 40,
        source_tree_sha256="sha256:" + "b" * 64,
        workflow_contract_version="claude-code-session-v1",
        build_kind="approved-candidate",
    )
    provenance = RuntimeProvenance(
        semantic_version=build.semantic_version,
        build_id=build.build_id,
        source_commit=build.source_commit,
        source_tree_sha256=build.source_tree_sha256,
        install_mode="approved_frozen",
        runtime_mode="approved",
        workflow_contract_version=build.workflow_contract_version,
    )
    return RuntimeInspection(
        executable={"invoked": "/test/meeting-ingest", "python": "/test/python", "module": "/test/meeting_ingest/__init__.py"},
        build=build,
        distribution={"record_integrity": "valid"},
        install=InstallEvidence(mode="approved_frozen"),
        receipt={"match": True},
        pin={
            "match": True,
            "comparisons": [{"field": "approved_build_id", "expected": build.build_id, "actual": build.build_id, "match": True}],
        },
        workflow=WorkflowEvidence(
            contract_version=build.workflow_contract_version,
            skill_path="/test/SKILL.md",
            skill_sha256="sha256:" + "c" * 64,
            agent_path="/test/agent.md",
            agent_sha256="sha256:" + "d" * 64,
            match=True,
        ),
        channel={"available": True, "update_available": False},
        runtime_mode="approved",
        findings=(),
        runtime_provenance=provenance,
    )


@pytest.fixture(autouse=True)
def _inject_approved_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating tests opt into typed approved evidence, never environment flags."""
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", approved_runtime_inspection)
