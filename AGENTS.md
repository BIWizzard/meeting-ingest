# Agent Instructions

## iQ Context

This repo uses iQ Context for session-to-session and agent-to-agent continuity.

iQ Context is here so Codex, Claude Code, Supa Code, T3 Code, and occasional iTerm2 sessions can share lightweight project memory across workstreams. The current goal is continuity, not full semantic retrieval. Meeting Ingest is related because generated meeting artifacts may become important captures or durable project memory for future agent work.

Project-local state lives under `.iq-context/`.

Durable memory artifacts may live under:

- `docs/sessions/`
- `docs/decisions/`
- `docs/discoveries/`
- `docs/assumptions/`

Use iQ Context from the Meeting Ingest repo root, not from the iQ Context source repo.

## Start Here

Before substantial work, run this from the repo root:

```bash
iq-context go
```

## Workflow

Use these commands as the normal local continuity loop:

```bash
iq-context go
iq-context status
iq-context save --summary "..." --next "..."
iq-context capture "..."
iq-context capture --file path/to/file --note "..."
iq-context wrap --summary "..." --next "..."
iq-context find "..."
```

Use `save` for checkpoints, `capture` for useful facts or artifacts, `wrap` when ending a session, and `find` when looking for prior project memory.

## Source Control

Commit durable memory when useful:

- `AGENTS.md`
- `.iq-context/config.yaml`
- `.iq-context/project-state.json`
- `.iq-context/workstreams/<id>/state.json`
- `.iq-context/workstreams/<id>/resume-state.json`
- reviewed `.iq-context/**/captures.jsonl`
- meaningful docs under `docs/sessions/`, `docs/decisions/`, `docs/discoveries/`, `docs/assumptions/`

Do not routinely commit volatile local runtime state:

- `.iq-context/focus-state.json`
- `.iq-context/workstreams/current.txt`
- `.iq-context/workstreams/<id>/host-bindings.json`
- `.iq-context/logs/`

Review iQ Context changes before staging. Do not commit local runtime files just because they changed during a session.

## Meeting Ingest Agent Notes

The Meeting Ingest engine remains the source of truth for transcript extraction, validation, markdown rendering, signal enrichment, ledger writes, archive, and reconcile behavior.

Subscription-backed provider workflows should use dedicated sub-agents for model extraction so large transcript context stays out of the main planning/coding session. Those sub-agents should return structured provider JSON for the engine to validate and render; they should not manually implement archive, ledger, signal, or reconcile behavior.

API-backed providers remain important for portability and productization. Host/session-backed providers exist to support personal workflows in active subscription-backed Claude Code, Codex, Supa Code, and T3 Code sessions without requiring a separate API call.

This is currently a lightweight local continuity layer. Semantic retrieval and richer host integrations are future work.
