<!-- iq-context:agent-instructions:start -->
# iQ Context Agent Instructions

Use these instructions when working in this repository through Codex, Claude Code, Supacode, or another agentic coding environment.

## Session Protocol

- Start each session with `iq-context go` from the project root.
- During work, checkpoint meaningful progress with `iq-context save --summary "..." --file <path> --next "..."`.
- Capture loose notes or references with `iq-context capture "..."`.
- Before ending a session, run `iq-context wrap --summary "..." --next "..."`.
- Files and artifacts describe where the work is right now. Artifacts are restated each checkpoint. Files, blockers, questions and next actions accumulate until you clear them.
- Before changing any list, read the stored state first (the go briefing or iq-context status), so a replace never destroys entries you have not seen.
- When the user says one item is done, retire it alone with `--done <next|blockers|questions>:<n>` by the number the briefing or `iq-context status` printed, or a consecutive run with `<field>:<a>-<b>`, and read the removed lines the confirmation echoes back (a range echoes them as the lines of its restore command). Use `--clear <files|artifacts|blockers|questions|next>` only when the whole list is being restated, then re-pass the items still open. `wrap --complete` clears next actions regardless and ignores any `--next` passed with it.
- If a save or wrap exits 4 with a message beginning `Write conflict: another session wrote`, that session wrote this workstream while you were composing yours and nothing of yours was written — there is nothing to undo. Do not re-run the same command unchanged: run `iq-context status --workstream <id>` for the workstream the refusal names, read the state that is there now, then re-issue the write against it following the remedies the refusal itself names — they differ between `save` and `wrap`, and the refusal states the ones the command you ran can take. Tell the user what the other session had changed. An exit 4 carrying any other message is a different failure and this branch does not apply: read the message, because it names a problem with the file being written rather than a competing session, and some of the command's writes may already have landed.
- Use `iq-context status` when current state or staleness is unclear.
- Use `iq-context find "..."` to retrieve prior context with provenance.

## Shortcuts (optional)

- If the iq-context agent shortcuts are installed on this machine (`iq-context agents install`), the session protocol is also available as `/iq-go`, `/iq-save`, `/iq-cap`, `/iq-wrap`, `/iq-status`, and `/iq-find` in Claude Code, and as `$iq-go`, `$iq-save`, `$iq-cap`, `$iq-wrap`, `$iq-status`, and `$iq-find` in Codex.
- The raw `iq-context` CLI commands above are always the canonical fallback.

## Where This Project's Memory Lives

- This project's memory is in-repo: its state lives in `.iq-context/` at the project root and travels with the code — committed, pushed, visible to anyone who has the repository.
- `iq-context state info` prints the posture and the state directory. It is the answer to "where does this project's state live?" — read it rather than inferring a path.
- If this project's memory should stop travelling with the code, `iq-context state separate` moves it to a state home outside the checkout. It never touches this repository's git: where the state was tracked, it prints the commands to run and leaves them to the user.

## State Safety

- Treat `.iq-context/` JSON files as tool-owned state.
- Never hand-edit `.iq-context` state; go through the `iq-context` CLI. The only exception is repair: correcting state that does not match reality. A capability the CLI lacks is never grounds to hand-edit.
- Prefer `iq-context save`, `iq-context capture`, `iq-context wrap`, and `iq-context workstream` commands over direct state edits.
- Keep host-specific notes in host bindings or captures rather than changing core state shape.
<!-- iq-context:agent-instructions:end -->
