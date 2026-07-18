# iQ Context Agent Instructions

Use these instructions when working in this repository through Codex, Claude Code, Supacode, or another agentic coding environment.

## Session Protocol

- Start each session with `iq-context go` from the project root.
- During work, checkpoint meaningful progress with `iq-context save --summary "..." --file <path> --next "..."`.
- Capture loose notes or references with `iq-context capture "..."`.
- Before ending a session, run `iq-context wrap --summary "..." --next "..."`.
- Use `iq-context status` when current state or staleness is unclear.
- Use `iq-context find "..."` to retrieve prior context with provenance.

## Shortcuts (optional)

- If the iq-context agent shortcuts are installed on this machine (`iq-context agents install`), the session protocol is also available as `/iq-go`, `/iq-save`, `/iq-cap`, `/iq-wrap`, `/iq-status`, and `/iq-find` in Claude Code, and as `$iq-go`, `$iq-save`, `$iq-cap`, `$iq-wrap`, `$iq-status`, and `$iq-find` in Codex.
- The raw `iq-context` CLI commands above are always the canonical fallback.

## State Safety

- Treat `.iq-context/` JSON files as tool-owned state.
- Do not hand-edit `.iq-context/**/*.json` unless the user explicitly asks for manual repair.
- Prefer `iq-context save`, `iq-context capture`, `iq-context wrap`, and `iq-context workstream` commands over direct state edits.
- Keep host-specific notes in host bindings or captures rather than changing core state shape.
