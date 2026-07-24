# meeting-ingest

`meeting-ingest` turns each meeting into a trustworthy project record and keeps accumulated meeting history usable and explainable through one approved agent workflow.

It turns raw `.docx`, `.txt`, and `.vtt` meeting artifacts into structured project knowledge with a strong done process.

## Why

Meeting transcripts often contain real project value:

- decisions
- action items
- asks
- dependencies
- risks
- communication signals
- stakeholder intent

But raw transcripts are noisy and hard to reuse directly.

`meeting-ingest` exists to transform those artifacts into durable, structured project outputs that are consistent, idempotent, and easy to integrate into broader workflows.

## Product Direction

The current release posture is a maintainer-only private alpha. Claude Code is the reference host for the approved **Just Works Continuity** milestone. Broader productization may come later, but the current work must first prove the maintainer's real workflow and accumulated history.

The long-term architecture remains host-neutral. The following are design targets, not current support claims:

- Codex
- Claude Code
- Codex via T3 harness
- Supa Code
- optionally Gemini CLI
- plain shell automation

The tool should support:

- project-local first-run initialization
- deterministic meeting IDs
- structured markdown outputs
- selectable output modes, including summary-only and summary-plus-verbatim
- structured signals / observations
- stakeholder communication signals
- source-ledger idempotency
- processed archives
- inbox reconciliation only after confirmed success

## Design Principles

- One engine, many wrappers
- Strong done process
- Provenance matters
- Idempotency by content hash, not filename
- Provider-backed extraction should be swappable
- Human-readable project artifacts remain important

## Relationship To iQ Context

`meeting-ingest` is separate from `iQ Context`.

- `meeting-ingest` = specialized artifact producer
- `iQ Context` = session/context operating system

They should integrate cleanly, but they should not be collapsed into one codebase prematurely.

## Repo Focus

This repo is for the ingestion tool itself.

It should stay focused on:

- transcript extraction
- structured meeting summarization
- signal extraction
- roster/identity resolution
- project-local ingest directories and config
- archive/ledger/reconcile behavior
- host-neutral CLI and provider model

## Current Status

Python CLI/library implementation with:

- project initialization
- single-file ingest
- sequential inbox batch ingest
- mock provider for local deterministic tests
- Anthropic provider adapter behind an explicit privacy gate
- session provider handoff for subscription-backed host sessions
- cleaned-verbatim transcript extraction for `.txt`, `.vtt`, and `.docx`
- markdown artifact rendering
- signal JSONL output
- append-only ledger
- archive/reconcile behavior
- doctor/status/reconcile and `repair-date` commands

## Development

Run the current scaffold tests with:

```bash
python3 -m pytest
```

Initialize a project-local meetings layout with:

```bash
python3 -m meeting_ingest.cli init --root . --json
```

Ingest one source:

```bash
python3 -m meeting_ingest.cli ingest _local/project-context/meetings/_inbox/example.vtt --json
```

When the meeting occurrence date is known, override inferred date evidence before ingest:

```bash
python3 -m meeting_ingest.cli ingest _local/project-context/meetings/_inbox/example.vtt --meeting-date 2026-07-10 --json
```

Ingest every direct file in `_inbox/`:

```bash
python3 -m meeting_ingest.cli ingest-inbox --json
```

Prepare session-provider inbox handoffs:

```bash
python3 -m meeting_ingest.cli session-inbox --quality balanced --json
```

Repair the occurrence date of an already-ingested meeting through the engine:

```bash
python3 -m meeting_ingest.cli repair-date mtg-20260703-abc12345 --date 2026-07-10 --json
```

## Providers

The default provider is `mock`, which never sends transcript content outside the local process.

Anthropic is available only when remote provider use is explicitly enabled:

```toml
[privacy]
allow_remote_provider = true
```

Set the API key in the environment:

```bash
export ANTHROPIC_API_KEY=...
```

Then request Anthropic explicitly:

```bash
python3 -m meeting_ingest.cli ingest _local/project-context/meetings/_inbox/example.vtt --provider anthropic --json
```

Quality aliases map to Anthropic models as follows:

- `fast`: `claude-haiku-4-5`
- `balanced`: `claude-sonnet-5`
- `deep`: `claude-opus-4-8`

Session-backed extraction is available only when the session provider privacy gate is enabled:

```toml
[privacy]
allow_session_provider = true
```

Use `provider-request` to create a transcript-bearing request for the active host session:

```bash
python3 -m meeting_ingest.cli provider-request _local/project-context/meetings/_inbox/example.vtt --provider session --quality balanced --json
```

Add `--meeting-date YYYY-MM-DD` to `provider-request` when the occurrence date is known. The persisted request carries that override into session phase 2; phase 2 does not accept a new date override.

The command returns `request_path` and `expected_response_path`. The request embeds the complete request-bound JSON Schema at `response_contract.json_schema`, including exact nested fields, enum values, and identity `const` values. A dedicated extraction agent should follow that schema and write the expected response envelope. The response envelope must use `provider.name: "session"` and place the structured meeting extraction under `response`:

```json
{
  "schema_version": "1.1",
  "handoff_type": "provider_response",
  "provider_contract": "meeting-ingest-provider-response-v1",
  "meeting_id": "mtg-20260703-abc12345",
  "ingest_run_id": "ingest-20260703-20260703T120000Z-abcd",
  "source_sha256": "...",
  "normalized_transcript_sha256": "...",
  "runtime_provenance_sha256": "sha256:...",
  "provider": {
    "name": "session",
    "host": "codex",
    "model_alias": "balanced",
    "model_id": "codex-session",
    "generated_at": "2026-07-03T12:00:00Z"
  },
  "response": {
    "title": "Example meeting",
    "tl_dr": "Short grounded summary.",
    "meeting_type": "unknown",
    "attendees": [],
    "topics": [],
    "decisions": [],
    "action_items": [],
    "stakeholder_asks": [],
    "dependencies_risks": [],
    "communication_signals": [],
    "open_questions": [],
    "cross_references": []
  }
}
```

Validate the response without producing ingest side effects:

```bash
python3 -m meeting_ingest.cli validate-response _local/project-context/meetings/_cache/provider-responses/ingest-20260703-20260703T120000Z-abcd.response.json --source _local/project-context/meetings/_inbox/example.vtt --json
```

Validation exit `6` reports all independently detectable payload issues under `errors[0].details.issues`. Correct them before phase 2. If phase 1 reports low date confidence, confirm the occurrence date and create a fresh request with `--meeting-date` before extraction.

Proceed only when preflight reports `status: "success"`, `provider_response.status: "valid"`, and a non-blocked `runtime_readiness.verdict`. A valid response under blocked runtime/project readiness returns exit `12`; resolve `runtime_readiness.findings` before phase 2.

After upgrading, request schema `1.0` handoffs cannot be completed or migrated because they lack bound runtime provenance. Inspect the exact pair with `status --json`; restore a reviewed schema `1.1` request when available, or explicitly remove only its reported `request_path` and `expected_response_path` before rerunning `session-inbox`. Never clear the entire provider cache as an upgrade shortcut.

Complete the ingest with the response file:

```bash
python3 -m meeting_ingest.cli ingest _local/project-context/meetings/_inbox/example.vtt --provider session --provider-response _local/project-context/meetings/_cache/provider-responses/ingest-20260703-20260703T120000Z-abcd.response.json --json
```

Phase 2 requires the persisted request file that matches the response `ingest_run_id`; arbitrary response-only ingests are rejected. The response path may be absolute or relative and does not have to live under `_cache/provider-responses`, though that cache path is the default. If `--mode` or `--quality` is supplied during phase 2 and differs from the persisted request, the engine uses the persisted request values and emits a warning.

For a reusable extraction sub-agent prompt, see [Session Provider Sub-Agent Prompt](docs/session-provider-subagent-prompt.md). For host-specific wrapper starting points, see [Session Provider Host Wrapper Snippets](docs/session-provider-host-wrappers.md). For the current agent-operated inbox workflow, see [Session Provider Inbox Agent Workflow](docs/session-provider-inbox-agent-workflow.md).

## Release Flow

`meeting-ingest` ships to consumers as an explicitly approved, frozen wheel — never a working-tree snapshot or editable install. Claude Code is the reference host for the approved runtime. Codex remains development/non-release evidence until separately approved.

The maintainer-only release flow is explicit end to end:

1. Review and approve an exact commit.
2. Build twice-reproducibly from that commit, producing a wheel and an external receipt:

   ```bash
   scripts/build-approved-runtime.py \
     --commit <sha> \
     --output-dir <dir> \
     --approved-by owner \
     --approved-at <utc> \
     --source-commit-reviewed
   ```

3. Publish the receipt, atomically advancing the advisory private-alpha channel:

   ```bash
   scripts/publish-approved-runtime.py --receipt <path> --published-at <utc>
   ```

   The channel manifest is advisory. It identifies the latest approved receipt/build and retained rollback artifacts, but it never installs, selects, or repins a consumer.
4. Install the frozen wheel explicitly:

   ```bash
   uv tool install <published-wheel-path>
   ```

5. Render and install the workflow artifacts:

   ```bash
   scripts/install-approved-skill.py \
     --receipt <receipt> \
     --template docs/claude-skills/meeting-ingest/SKILL.md \
     --executable /Users/kmgdev/.local/bin/meeting-ingest \
     --skill-destination ~/.claude/skills/meeting-ingest/SKILL.md \
     --agent docs/claude-agents/meeting-ingest-session-provider.md \
     --agent-destination ~/.claude/agents/meeting-ingest-session-provider.md \
     --json
   ```

   The installer verifies the template hash against the receipt, substitutes only the `{{MEETING_INGEST_APPROVED_EXECUTABLE}}` marker with the machine-local absolute path, copies the agent byte-identical, and writes atomically. It reports the rendered skill hash; the pin step below records that hash in the consumer pin.
6. Pin the consumer to the approved receipt:

   ```bash
   meeting-ingest runtime pin --receipt <path> --root <consumer-root>
   ```

7. Verify:

   ```bash
   meeting-ingest readiness --host claude-code --json
   ```

Release-store publishing, installation, and `runtime pin` are bootstrap/release mutations outside project readiness. They use strict receipt/build/workflow verification and atomic writes instead of bypassing themselves through the project guard.

Git hooks never build, publish, install, pin, or update the consumer tool. On main-moving commits or merges they may only print an informational reminder that a release candidate may exist. The old automatic `uv tool install --reinstall` hook is retired.

## Start Here

- [Product Status](docs/product-status.md)
- [Context Primer](docs/context-primer.md)
- [Claude Code Review Prompt](docs/claude-code-review-prompt.md)
- [Personal Workflow Scope](docs/personal-workflow-scope.md)
- [Current Output Evaluation](docs/current-output-evaluation.md)
- [Design Proposal](docs/design-proposal.md)
- [Stakeholder Playbook Design](docs/stakeholder-playbook-design.md)
- [Artifact Contract](docs/artifact-contract.md)
- [Implementation Plan](docs/implementation-plan.md)

The product status is the current audited accounting of what is built, partial, and not started. The context primer is the agent-optimized starting point for architecture and roadmap exploration. The personal workflow scope captures the initial product requirements that should guide near-term design. The current output evaluation summarizes what to preserve and improve from real Claude skill outputs. The design proposal turns those findings into an initial implementation shape. The stakeholder playbook design is the accepted baseline for Stakeholder Briefing V1, Playbook Guidance V1.1, and later communication sources. The artifact contract defines the markdown, signal, ledger, and run-summary surfaces for implementation. The implementation plan translates those contracts into build milestones and agent work lanes.
