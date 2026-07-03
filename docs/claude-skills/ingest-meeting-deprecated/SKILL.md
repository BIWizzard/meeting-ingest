---
name: ingest-meeting
description: Deprecated legacy meeting ingestion skill. If this skill is selected, stop and use the meeting-ingest skill and meeting-ingest CLI instead.
---

# ingest-meeting is deprecated

This legacy skill has been replaced by `meeting-ingest`.

Do not use the old `ingest_meeting` Python package. Do not follow the old legacy workflow.

When the user asks to process transcripts, ingest a meeting, or process the Meeting Ingest inbox:

1. Switch to the `meeting-ingest` skill.
2. Use the `meeting-ingest` CLI from the active project root.
3. Default to `provider=session`.
4. Follow the session-provider inbox workflow.

In the Meeting Ingest repo, the detailed workflow is documented at:

```text
docs/session-provider-inbox-agent-workflow.md
```

The CLI engine owns transcript extraction, validation, markdown rendering, signal enrichment, ledger writes, archive, and reconcile behavior.
