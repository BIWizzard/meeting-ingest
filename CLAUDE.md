# Claude Instructions

This repo uses iQ Context for session-to-session and agent-to-agent continuity.

Run this from the Meeting Ingest repo root before substantial work:

```bash
iq-context go
```

Then check the relay intake lane with `gh issue list --label relay --state open` and surface any open relay issues alongside the briefing. See [AGENTS.md Relay Intake](AGENTS.md#relay-intake) for the triage procedure.

Use [AGENTS.md](AGENTS.md) as the canonical shared instruction file for Claude, Codex, Supa Code, T3 Code, and other agents working in this repository.

Claude agents should use iQ Context from this repo root, not from the iQ Context source repo. Save or wrap meaningful progress so updates can surface to future agents in future sessions.

## North Star Board

Binding records: [docs/north-star-board/board-log.md](docs/north-star-board/board-log.md). Record 002 (Just Works Continuity, approved-runtime policies) and record 003 (consumer classes, update policy, adoption path — amends 002's consumer policy) govern product direction; contract deviation is a halting smell.

<!-- north-star-board:open-obligations -->
- OB-002-1: corpus adoption ratification — no corpus adoption or mutation without a deterministic fingerprinted adoption plan and separate owner approval; a proposed plan convenes the board.
- OB-003-1: release/update command pair (issue #16) — due when the next release ships.
- OB-003-3: product-truth activation accounting — the next release's evidence cites it.
- OB-003-4: single-owner candor precondition — summary/analysis artifacts are not shared with anyone until a share-safe output form exists; a decision or act extending brief/signal audience beyond the owner, or a reference-consumer role transfer, is a check-in trigger.
- OB-003-6: auto-update deferral — a broadening intent or distribution-transition plan convenes the board per Decision 35.
<!-- /north-star-board:open-obligations -->

