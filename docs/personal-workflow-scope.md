# Personal Workflow Scope

## Purpose

The first serious build of `meeting-ingest` is intentionally scoped around the maintainer's personal and professional workflows.

This does not prevent a broader product later. It means early design should optimize for the real ingestion jobs, communication needs, and agentic harnesses that already exist, instead of designing prematurely for a generic audience.

## Product Stance

Early `meeting-ingest` should be:

- personal-workflow first
- host-neutral
- fast enough to use often
- consistent enough to trust
- configurable without becoming heavy
- easy to initialize inside any active project

The existing Claude meeting skill is a useful reference, but it is not the target experience. The rebuild should keep what works and fix the parts that are slow, inconsistent, or hard to control.

## Primary Use Environments

The primary use case is agentic harness operation.

Initial target harnesses:

- Supa Code
- T3 Code

Initial model/operator contexts:

- Claude through those harnesses
- Codex through those harnesses
- plain CLI use when needed

The engine should make these hosts feel like thin wrappers over the same behavior. A meeting ingested through Claude in one harness and a meeting ingested through Codex in another should produce the same classes of artifacts and follow the same done process.

## Agentic Operation

The user likes that the existing workflow is handled by a sub-agent and wants to preserve that interaction model.

The practical user experience requirement is that the user should be able to ask the active agent inside Supa Code or T3 Code to ingest a meeting. The user should not need to exit the harness into a raw terminal session for normal ingestion.

Design implication:

- the CLI/library should be host-neutral
- agent instructions should remain thin and explicit
- a harness-specific wrapper may delegate ingestion work to a dedicated sub-agent
- the sub-agent should call the same underlying engine instead of reimplementing extraction, archive, ledger, or reconciliation behavior
- the repo should provide reusable agent-facing instructions or wrapper entry points that make this easy from Supa Code and T3 Code
- subscription-backed active sessions should be able to perform model extraction without requiring a separate API key when the user is already operating inside Claude Code, Codex, Supa Code, or T3 Code
- subscription-backed model extraction should be delegated to a dedicated sub-agent when practical so transcript-heavy context does not pollute the main session
- API-backed providers should still exist for portability, automation, and future marketability

The sub-agent should be right-sized for the job. It should not default to the largest or most expensive model when a deterministic step, small model, or template pass is sufficient.

## Speed And Consistency Goals

The current workflow is moderately satisfying but too slow and inconsistent.

The rebuild should improve this by separating work into phases:

1. deterministic source handling
2. transcript normalization
3. optional verbatim transcript cleanup
4. structured extraction
5. output rendering
6. ledger/archive/reconcile

Only the phases that need model judgment should call a provider.

Potential optimizations:

- use deterministic parsing for `.txt`, `.vtt`, and `.docx` extraction where possible
- avoid reprocessing sources already known by content hash
- support a fast templated mode for routine meetings
- support provider/model selection by output mode
- cache normalized transcript text by source hash where appropriate
- validate model output against a schema before finalizing
- retry only the failed provider step instead of restarting the whole ingest

Consistency should come from stable schemas and renderers, not from asking a model to invent the final document shape each time.

## Output Modes

The user needs an easy way to choose between different output depths.

### Smart Summary

Use when the desired output is a structured, reusable meeting summary.

Expected content:

- attendees
- key topics
- decisions
- dependencies
- commitments
- action items
- risks or concerns
- open questions
- stakeholder asks
- communication signals

This mode should produce a polished templated summary that can be used as-is or combined with other project context.

### Summary Plus Verbatim

Use when the transcript itself is part of the durable project record.

This should be the default output mode because the maintainer more often wants both a smart summary and a transcript record.

Expected content:

- the same templated smart summary
- a word-for-word or minimally cleaned transcript section
- clear source/provenance metadata
- speaker labels when available
- notes about transcript quality or uncertain speaker attribution

Preferred artifact shape:

- one file containing both the smart summary and the verbatim transcript
- summary first
- verbatim transcript second
- stable headings so downstream tools can parse or split it later

The existing skill sometimes produces a combined file and sometimes separate files. The rebuild should make this an explicit mode choice.

This mode is especially important for one-on-one or small-group sessions involving substantive explanation, knowledge transfer, build decisions, design decisions, or detailed implementation reasoning. In those meetings, the exact words and details matter.

### Verbatim Only

This may be useful for rare cases where the user wants a normalized transcript record without summary extraction.

Expected content:

- source metadata
- normalized transcript text
- speaker labels when available
- minimal cleanup only

This should avoid unnecessary model use unless speaker cleanup or transcript repair requires it.

### Mode Selection Heuristics

Default mode:

- `summary-plus-verbatim`

Common overrides:

- use `summary` for large structured meetings where the transcript is less important, such as daily standups or broad status meetings
- use `summary-plus-verbatim` for one-on-ones, design/build conversations, knowledge-transfer sessions, decisions, and technical explanations
- use `verbatim` when only a cleaned transcript record is needed

The tool may later support `--mode auto`, but explicit user choice and project defaults should remain easy.

## Artifact Expectations

Generated meeting files should be human-readable and stable.

The markdown output is often intended to be shared with another agent for follow-on work. Human readability matters, but the artifact should be optimized for agent consumption through stable metadata, stable headings, explicit identifiers, clear structured sections, and predictable transcript boundaries.

File names should be intentionally scannable. At a glance, the user should be able to identify:

- meeting date
- meeting or conversation identity
- primary topic
- one-on-one counterpart when the meeting is clearly the user plus one other person

The file name should not include a full attendee list. For one-on-one meetings, it should usually include the other person's name or stable short identifier.

Good filename shape:

```text
2026-06-12-kushali-adbook-fact-revenue-detail.md
2026-07-01-spelman-data-infrastructure-rfp-prep.md
2026-06-10-jim-haley-historical-revenue-dedup.md
```

Low-signal fallback names such as `generic-<hash>` should be avoided unless the tool cannot confidently infer a better title. When a fallback is necessary, the output should surface a clear rename suggestion.

Renaming after ingest is acceptable. If the tool can infer a better title after reading or extracting the transcript, it should be able to update the artifact filename and ledger references through a controlled repair/rename step.

Preferred structure for `summary-plus-verbatim`:

1. metadata block
2. meeting overview
3. attendees and identity notes
4. key topics
5. decisions
6. commitments and action items
7. dependencies and risks
8. stakeholder asks
9. communication signals
10. open questions
11. verbatim transcript

The exact schema can evolve, but the headings should be predictable enough for people and tools.

Generated markdown should live directly in the meetings root by default so it is easy to scan and hand to agents. Raw inputs, processed copies, signals, cache files, quarantine records, and derived aggregate outputs should live in their own underscore-prefixed directories.

## Stakeholder Communication Intelligence

A major personal workflow goal is not just summarization. The tool should help the user communicate more effectively with stakeholders in the user's own voice.

The ingest process should identify and preserve:

- what stakeholders asked for
- how they framed the ask
- what outcomes they appear to care about
- risks, pressures, or constraints they emphasized
- preferred communication style cues
- recurring concerns across meetings
- commitments made by or to that stakeholder
- phrases or framing that may be useful when responding later

This should not become manipulative profiling. The useful boundary is practical communication memory:

- speak to the stakeholder's equities
- reflect their stated priorities accurately
- avoid losing nuance from the original conversation
- tailor updates to what they have already identified as important
- preserve enough provenance to check claims against the source

The desired end state is a rolling stakeholder playbook that gets smarter over time as more meetings are ingested. Per-meeting signals should feed durable stakeholder profiles that capture evolving priorities, communication patterns, recurring asks, and useful framing guidance.

The primary meeting markdown should be produced first. If playbook updates require additional work, that work can continue after the main meeting output is ready so the user can start using the artifact immediately.

Important stakeholder voice also appears outside meetings. Emails, memos, Teams messages/threads, screenshots of communications, and attachments can contain explicit asks, commitments, decisions, and communication-style signals. This is a valuable future extension for the rolling stakeholder playbook, but the first build should remain meeting/transcript-first.

## Communication Signal Categories

Candidate signal categories:

- stakeholder priority
- explicit ask
- decision rationale
- commitment
- concern or risk
- dependency
- language/framing cue
- preferred level of detail
- urgency cue
- relationship or trust cue
- follow-up expectation

Each signal should include:

- source meeting ID
- speaker or stakeholder, when known
- short summary
- supporting quote or paraphrase
- confidence level
- whether the signal is one-off or recurring, if known

## Voice And Messaging Support

Future features may use meeting outputs and the rolling stakeholder playbook to help draft stakeholder communication.

Examples:

- "Draft an update to this stakeholder using the priorities they raised."
- "Show me what this person has asked for across the last few meetings."
- "What tone and level of detail should I use with this group?"
- "Which commitments should I acknowledge before proposing the next step?"

For now, `meeting-ingest` should focus on producing the source artifacts, communication signals, and rolling playbook inputs needed for those workflows. It should not become a full messaging assistant in this repo.

## Configuration Direction

The tool should make output mode selection easy.

Candidate CLI examples:

```sh
meeting-ingest ingest path/to/transcript.vtt --mode summary
meeting-ingest ingest path/to/transcript.docx --mode summary-plus-verbatim
meeting-ingest ingest path/to/transcript.txt --mode verbatim
```

Potential config defaults:

```toml
default_mode = "summary-plus-verbatim"

[providers.summary]
provider = "anthropic"
model = "balanced"

[providers.verbatim]
provider = "local"
model = "none"

[providers.signals]
provider = "openai"
model = "small-reasoning"
```

The actual provider names and model aliases should be designed later. The important requirement is that users can choose mode and quality/cost posture without rewriting prompts.

## Open Design Questions

1. Should output mode be part of the ledger key, or should the ledger track one source hash with multiple generated artifact variants?
2. Should `summary-plus-verbatim` store one canonical combined markdown file only, or also create optional derived split files for downstream tools?
3. How much verbatim cleanup is allowed before it is no longer word-for-word?
4. Should communication signals be extracted in the same provider call as the summary, or as a separate right-sized pass?
5. What model tiers are needed for fast, balanced, and high-quality modes?
6. How should harness wrappers request sub-agent execution while preserving the same underlying CLI behavior?
7. What project-local defaults should be initialized for a personal workflow without making the setup feel overbuilt?
