<!-- iq-context:agent-instructions:start -->
# iQ Context Agent Instructions

Use these instructions when working in this repository through Codex, Claude Code, Supacode, or another agentic coding environment.

## Session Protocol

- Start each session with `iq-context go` from the project root.
- During work, checkpoint meaningful progress with `iq-context save --summary "..." --file <path> --next "..."`.
- Capture loose notes or references with `iq-context capture "..."`.
- Before ending a session, run `iq-context wrap --summary "..." --next "..."`.
- Files and artifacts describe where the work is right now and are restated each checkpoint. Blockers, questions and next actions accumulate until you clear them.
- Before changing any list, read the stored state first (the go briefing or iq-context status), so a replace never destroys entries you have not seen.
- Use `--clear <files|artifacts|blockers|questions|next>` only when the user explicitly says an item is resolved, then re-pass the items still open. `wrap --complete` clears next actions regardless and ignores any `--next` passed with it.
- If a save or wrap exits 4 with a message beginning `Write conflict: another session wrote`, that session wrote this workstream while you were composing yours and nothing of yours was written — there is nothing to undo. Do not re-run the same command unchanged: run `iq-context status --workstream <id>` for the workstream the refusal names, read the state that is there now, then re-issue the write against it following the remedies the refusal itself names — they differ between `save` and `wrap`, and the refusal states the ones the command you ran can take. Tell the user what the other session had changed. An exit 4 carrying any other message is a different failure and this branch does not apply: read the message, because it names a problem with the file being written rather than a competing session, and some of the command's writes may already have landed.
- Use `iq-context status` when current state or staleness is unclear.
- Use `iq-context find "..."` to retrieve prior context with provenance.

## Shortcuts (optional)

- If the iq-context agent shortcuts are installed on this machine (`iq-context agents install`), the session protocol is also available as `/iq-go`, `/iq-save`, `/iq-cap`, `/iq-wrap`, `/iq-status`, and `/iq-find` in Claude Code, and as `$iq-go`, `$iq-save`, `$iq-cap`, `$iq-wrap`, `$iq-status`, and `$iq-find` in Codex.
- The raw `iq-context` CLI commands above are always the canonical fallback.

## State Safety

- Treat `.iq-context/` JSON files as tool-owned state.
- Never hand-edit `.iq-context` state; go through the `iq-context` CLI. The only exception is repair: correcting state that does not match reality. A capability the CLI lacks is never grounds to hand-edit.
- Prefer `iq-context save`, `iq-context capture`, `iq-context wrap`, and `iq-context workstream` commands over direct state edits.
- Keep host-specific notes in host bindings or captures rather than changing core state shape.
<!-- iq-context:agent-instructions:end -->
