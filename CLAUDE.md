# Claude Instructions

This repo uses iQ Context for session-to-session and agent-to-agent continuity.

Run this from the Meeting Ingest repo root before substantial work:

```bash
iq-context go
```

Use [AGENTS.md](AGENTS.md) as the canonical shared instruction file for Claude, Codex, Supa Code, T3 Code, and other agents working in this repository.

Claude agents should use iQ Context from this repo root, not from the iQ Context source repo. Save or wrap meaningful progress so updates can surface to future agents in future sessions.

## North Star Board

Binding records: [docs/north-star-board/board-log.md](docs/north-star-board/board-log.md). Record 002 (Just Works Continuity, approved-runtime policies) governs product direction; contract deviation is a halting smell.

<!-- north-star-board:open-obligations -->
- OB-002-1: corpus adoption ratification — no corpus adoption or mutation without a deterministic fingerprinted adoption plan and separate owner approval; a proposed plan convenes the board.
- OB-002-2: close the ready-with-history-warnings later-decision — record 002 addendum owed; trigger fired 2026-07-24 when Tasks 9–10 ran production ingest under that verdict.
<!-- /north-star-board:open-obligations -->

