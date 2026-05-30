# meeting-ingest

`meeting-ingest` is a platform-agnostic meeting and transcript ingestion tool.

It is intended to turn raw meeting artifacts such as `.docx`, `.txt`, and `.vtt` files into structured project knowledge with a strong done process:

- deterministic meeting IDs
- structured markdown meeting summaries
- structured observations / signals
- idempotent source ledgering
- processed archive copies
- inbox reconciliation only after confirmed success

## Direction

This repository is the starting point for rebuilding an existing Claude-first workflow into a host-neutral engine that can work cleanly with:

- Codex
- Claude Code
- T3 harness workflows
- optionally Gemini CLI
- plain shell automation

## Status

Early scaffold. The next step is to define package layout, CLI shape, config model, and provider abstraction.
