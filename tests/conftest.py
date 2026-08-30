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
from meeting_ingest.runtime_config import RUNTIME_PIN_RELATIVE_PATH, serialize_pin, sha256_bytes
from meeting_ingest.runtime_release import (
    CLAUDE_AGENT_PATH,
    CLAUDE_SKILL_PATH,
    BootstrappedRuntime,
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
            skill_scope="project",
            agent_path="/test/agent.md",
            agent_sha256="sha256:" + "d" * 64,
            agent_scope="project",
            match=True,
        ),
        channel={"available": True, "update_available": False},
        runtime_mode="approved",
        findings=(),
        runtime_provenance=provenance,
    )


STUB_PIN_BUILD_ID = "meeting-ingest-0.1.0-gaaaaaaaaaaaa-sbbbbbbbbbbbb"


def approved_runtime_bootstrap(root: Path) -> BootstrappedRuntime:
    """Select an approved runtime without a release store, writing what it reports."""
    inspection = approved_runtime_inspection(root)
    executable = Path(inspection.executable["invoked"])
    payload = serialize_pin(
        {
            "schema_version": "1.0",
            "channel": "private-alpha",
            "approved_build_id": STUB_PIN_BUILD_ID,
            "approved_source_commit": inspection.build.source_commit,
            "approved_source_tree_sha256": inspection.build.source_tree_sha256,
            "approved_wheel_sha256": "sha256:" + "c" * 64,
            "approved_receipt_sha256": "sha256:" + "d" * 64,
            "approved_executable": str(executable),
            "workflow_contract_version": inspection.build.workflow_contract_version,
            "claude_skill_template_sha256": "sha256:" + "e" * 64,
            "installed_claude_skill_sha256": inspection.workflow.skill_sha256,
            "claude_agent_sha256": inspection.workflow.agent_sha256,
            "approved_at": "2026-07-20T00:00:00Z",
        }
    )
    pin_path = root.resolve() / RUNTIME_PIN_RELATIVE_PATH
    pin_path.parent.mkdir(parents=True, exist_ok=True)
    pin_path.write_bytes(payload)
    return BootstrappedRuntime(
        build_id=STUB_PIN_BUILD_ID,
        receipt_path=root / "release/receipt.json",
        pin_path=pin_path,
        pin_sha256=sha256_bytes(payload),
        skill_destination=root / CLAUDE_SKILL_PATH,
        agent_destination=root / CLAUDE_AGENT_PATH,
        executable=executable,
    )


@pytest.fixture(autouse=True)
def _inject_approved_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mutating tests opt into typed approved evidence, never environment flags."""
    monkeypatch.setattr("meeting_ingest.readiness._RUNTIME_INSPECTOR", approved_runtime_inspection)
    monkeypatch.setattr("meeting_ingest.pipeline.bootstrap_consumer_runtime", approved_runtime_bootstrap)
