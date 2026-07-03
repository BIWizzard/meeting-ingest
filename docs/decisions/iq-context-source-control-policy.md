# iQ Context Source Control Policy

This repo uses iQ Context for project-local continuity. Some `.iq-context/` files are durable project memory and should be committed when useful. Other files are local runtime state and should stay untracked or ignored.

## Commit These

Commit durable shared project context:

- `AGENTS.md`
- `CLAUDE.md` if present and intentionally maintained
- `.iq-context/config.yaml`
- `.iq-context/project-state.json`
- `.iq-context/workstreams/<workstream-id>/state.json`
- `.iq-context/workstreams/<workstream-id>/resume-state.json`
- `.iq-context/workstreams/<workstream-id>/captures.jsonl` after reviewing for sensitive or disposable content
- `.iq-context/captures.jsonl` after reviewing for sensitive or disposable content
- `docs/sessions/*.md` when the wrap output has durable continuation value
- `docs/decisions/*.md`
- `docs/discoveries/*.md`
- `docs/assumptions/*.md`
- `docs/sessions/README.md`
- `docs/decisions/README.md`
- `docs/discoveries/README.md`
- `docs/assumptions/README.md`

## Do Not Routinely Commit

Keep local/runtime state untracked or ignored:

- `.iq-context/focus-state.json`
- `.iq-context/workstreams/current.txt`
- `.iq-context/workstreams/<workstream-id>/host-bindings.json`
- `.iq-context/logs/`
- `.iq-context/logs/query-log.jsonl`

These files describe the current local machine, session, or host state. They are useful while working, but they should not usually become shared repo history.

## Recommended `.gitignore` Entries

Add these if they are not already present:

```gitignore
# iQ Context runtime state local to one user/environment
.iq-context/focus-state.json
.iq-context/logs/
.iq-context/workstreams/current.txt
.iq-context/workstreams/*/host-bindings.json
```

## Review Before Committing Captures

Capture logs can contain raw notes, pasted text, or file references. Before committing:

```bash
git diff -- .iq-context/captures.jsonl
git diff -- .iq-context/workstreams/*/captures.jsonl
```

Commit capture logs only when they contain durable, shareable project memory.

## Typical First Commit After `iq-context init`

Usually include:

- `AGENTS.md`
- `.gitignore`
- `.iq-context/config.yaml`
- `.iq-context/project-state.json`
- `.iq-context/workstreams/default/state.json`
- `.iq-context/workstreams/default/resume-state.json`
- `docs/sessions/README.md`
- `docs/decisions/README.md`
- `docs/discoveries/README.md`
- `docs/assumptions/README.md`

Usually exclude:

- `.iq-context/focus-state.json`
- `.iq-context/workstreams/current.txt`
- `.iq-context/workstreams/default/host-bindings.json`
- `.iq-context/logs/query-log.jsonl`
