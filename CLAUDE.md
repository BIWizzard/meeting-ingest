# Claude Instructions

This repo uses iQ Context for session-to-session and agent-to-agent continuity.

Run this from the Meeting Ingest repo root before substantial work:

```bash
iq-context go
```

Use [AGENTS.md](AGENTS.md) as the canonical shared instruction file for Claude, Codex, Supa Code, T3 Code, and other agents working in this repository.

Claude agents should use iQ Context from this repo root, not from the iQ Context source repo. Save or wrap meaningful progress so updates can surface to future agents in future sessions.
