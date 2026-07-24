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

## Claude Code Review

Use [docs/claude-code-review-prompt.md](docs/claude-code-review-prompt.md) when asking Claude Code to review the working tree.

The former CodeRabbit review and autofix workflow is retired. Do not invoke CodeRabbit, check its authentication, or wait for its PR feedback. At every review-before-commit checkpoint, generate a ready-to-paste Claude Code prompt for the human using the maintained prompt document.

Claude Code review is read-only by default. It may inspect the current working tree and report findings, but it must not edit files, stage changes, commit changes, or update `.iq-context/` state unless the human explicitly hands off writer ownership.

## Source Control

See [docs/decisions/iq-context-source-control-policy.md](docs/decisions/iq-context-source-control-policy.md) for the durable iQ Context source-control policy.

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

Reusable agent affordances live alongside these repo-local instructions:

- Claude Code: `~/.claude/skills/meeting-ingest` plus `~/.claude/agents/meeting-ingest-session-provider`
- Codex: `~/.codex/skills/meeting-ingest`

The skill is the natural-language trigger surface. The `meeting-ingest` CLI is the reliability layer.

## Meeting Ingest Inbox Processing

When the user asks an agent to process the Meeting Ingest inbox, assume the intended provider is `session` unless the user explicitly asks for another provider.

Do not use `mock` for real workflow tests. Do not switch to an API-backed provider just because it is available. The normal personal workflow is subscription-backed session extraction inside the active agent host.

Before processing the inbox, verify the project config under `_local/project-context/meetings/meeting-ingest.toml` has:

```toml
default_provider = "session"

[privacy]
allow_session_provider = true
```

If the config is missing or still defaults to `mock`, update it for this local workflow before processing.

`meeting-ingest session-inbox --json` is the active-agent wrapper surface. It scans existing provider requests first, completes ready responses before creating fresh requests, and skips fresh phase 1 while unresolved handoffs remain. In plain CLI use it reports `pending_provider_response` entries because the CLI cannot invoke the active model session by itself.

`meeting-ingest ingest-inbox --provider session --json` is the lower-level batch phase-1 command. It creates session-provider requests for each direct inbox file. It does not complete session extraction by itself because the active agent must produce the provider response JSON.

Claude Code is the reference host for the approved runtime. On Claude Code, invoke the CLI only through the approved executable recorded in the consumer pin, not through `uv run meeting-ingest` or ambient PATH:

```bash
MEETING_INGEST="/Users/kmgdev/.local/bin/meeting-ingest"
```

Codex, Supa Code, and T3 Code are not reference hosts. Their runs are development/non-release evidence until separately approved, and they run the equivalent repo-checkout development invocation `uv run meeting-ingest <args>` in place of `"$MEETING_INGEST"` below.

Process the inbox with this loop:

0. Check runtime readiness with `"$MEETING_INGEST" readiness --host claude-code --json`. Continue only when `verdict` is `ready` or `ready_with_history_warnings`, or when the user has explicitly authorized a `development_override` reason (then pass `--development-override "<reason>"` on every mutating command and mark the results development-generated). On `blocked` (exit `12`), stop and report the findings; read-only `status`, `doctor`, `readiness`, and `runtime inspect` remain usable while blocked.
1. Run `"$MEETING_INGEST" session-inbox --quality balanced --json`.
2. For each result with `status: "pending_provider_response"`, read the generated request file from `details.request_path`.
3. Produce the expected provider response JSON at `details.expected_response_path`.
4. Run `"$MEETING_INGEST" ingest <source> --provider session --provider-response <expected_response_path> --json`.
5. Confirm the run summary reports `status: "success"`, `provider: "session"`, a markdown artifact path, signal artifact path, archive path, and completed reconcile path.
6. Record the meeting in iQ Context — one capture per successfully processed meeting, after ledger/signal writes succeed (not per intermediate artifact):

   ```bash
   iq-context capture \
     --file _local/project-context/meetings/<final-meeting-doc>.md \
     --note "Processed meeting: <title> (<meeting date>). Key outcomes: <1-2 line takeaways>. Decisions: <ids or 'none'>."
   ```

   Lead the note with the meeting title and effective date, summarize outcomes in one or two lines, and name decisions or action items explicitly — those are what future sessions search for.
7. Continue until no direct files remain in `_inbox/` except files under `_inbox/_done/`.

The agent may act as the session extraction agent when no dedicated sub-agent is available, but the response must still be provider-level JSON only. The engine must remain responsible for validation, markdown rendering, signal enrichment, ledger writes, archive, and reconcile.

Use [docs/session-provider-inbox-agent-workflow.md](docs/session-provider-inbox-agent-workflow.md) for the exact operational workflow.

For Codex specifically, the reusable skill source is maintained at [docs/codex-skills/meeting-ingest/SKILL.md](docs/codex-skills/meeting-ingest/SKILL.md) and installed to `~/.codex/skills/meeting-ingest/SKILL.md`. Keep those in sync when changing Codex-facing behavior.

This is currently a lightweight local continuity layer. Semantic retrieval and richer host integrations are future work.

## Tool Distribution

The `meeting-ingest` CLI used outside this repo is a frozen approved-wheel install, never an editable one or a working-tree snapshot. Consumer projects only run an explicitly approved, reviewed, and pinned build. Installing or updating that build is the maintainer-only release flow documented in the [README Release Flow](README.md#release-flow): build twice-reproducibly, publish to the advisory private-alpha channel, install the frozen wheel, render and install the workflow artifacts, pin the consumer, and verify with `readiness`.

Git hooks never build, publish, install, pin, or update the consumer tool. On main-moving commits or merges they may only print an informational reminder that a release candidate may exist. The old automatic `uv tool install --reinstall` hook is retired.
