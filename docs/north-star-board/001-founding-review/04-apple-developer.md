# Apple Developer Seat

## 1. Verdict

Meeting Ingest is a strong reliability engine wrapped in an unfinished product experience.

For its maintainer in a correctly configured agent session, it turns real `.txt`, `.vtt`, and `.docx` sources into useful Markdown, signals, ledger history, archives, and reconciled inbox state. Duplicate handling, partial-state preservation, retry behavior, validation, and provenance are substantive strengths.

It does not yet just work. Consumer installation is undocumented, initialization produces a safe but non-useful real-work default, the primary workflow is a multi-stage agent protocol, CLI help does not teach it, and a pending provider response is reported as overall success. The promise is process the inbox; the operational reality is config editing, request generation, response production, preflight, phase two, verification, and separate capture.

Release should remain an internal technical-owner preview until one selected host demonstrates a fresh-install, natural-language, real-meeting workflow without maintainer intervention.

## 2. Evidence

- Intended experience: say there are files in the inbox and ask the agent to process them (`docs/session-provider-inbox-agent-workflow.md:3-12`).
- Actual procedure includes date inspection, request reading, exact JSON, validation, phase two, output checks, and iQ capture (`docs/session-provider-inbox-agent-workflow.md:85-179`; `docs/codex-skills/meeting-ingest/SKILL.md:49-215`).
- Init and upward project discovery are well bounded; missing init produces an actionable command (`src/meeting_ingest/paths.py:72-115`; `tests/test_config_paths.py:10-38`). No issue was found with discovery.
- Default config uses `mock` and disables real providers; the personal workflow requires `session` and consent (`src/meeting_ingest/config.py:42-83`; `docs/session-provider-inbox-agent-workflow.md:21-35`).
- Packaging exposes a dependency-light console script, but README lacks consumer install/upgrade guidance and uses module invocation; frozen `uv tool` distribution appears only in agent instructions (`pyproject.toml:5-17`; `README.md:97-132`; `AGENTS.md:136-146`).
- CLI help lacks descriptions, examples, defaults, supported values, next steps, and `--version` (`src/meeting_ingest/cli.py:17-125`).
- Plain human output collapses rich results to status and sometimes root; useful diagnosis effectively requires `--json` (`src/meeting_ingest/cli.py:225-280`).
- `session-inbox` with unresolved provider work can return overall success/exit 0; plain output can say success while no artifact exists (`src/meeting_ingest/session_inbox.py:148-180`; `tests/test_session_inbox.py:16-32`).
- Resume behavior is strong: ready responses complete first, pending requests are not reminted, stale evidence is retained, and extractor failure preserves source (`tests/test_session_inbox.py:85-228`). No issue was found with pending-handoff preservation.
- Provider/validation failures generally preserve source and avoid archive/reconcile side effects (`tests/test_pipeline_ingest.py:379-499`).
- Archive/reconcile failures preserve primary-ready state and later retry repairs it (`tests/test_pipeline_ingest.py:533-580`, `tests/test_pipeline_ingest.py:823-877`).
- Duplicate content is a safe no-op and re-dropped sources reconcile to `_done` (`tests/test_pipeline_ingest.py:722-820`). No issue was found with examined retry semantics.
- A primary ledger failure can leave orphan artifact/signal outputs without a first-class repair path (`tests/test_pipeline_ingest.py:502-530`).
- The response-contract fix is real, but no fresh external UAT proves the improved experience (`README.md:185-234`).
- Real artifacts are useful and inspectable; the corpus spans all three formats.
- README mode direction exceeds actual support: only summary-plus-verbatim is valid and rendered (`README.md:36-46`; `src/meeting_ingest/schema.py:11-15`; `src/meeting_ingest/pipeline.py:818-840`).
- Workflow content is duplicated across README, AGENTS, workflow docs, Codex/Claude skills, installed copies, and host prompts, creating maintenance drift.
- Current health reports a valid ingest corpus but exit 1 for missing playbook and three low-confidence dates.

## 3. What is working

- **Complete and demonstrated:** explicit init, discovery, extraction, stable combined rendering, typed JSON, idempotency, archive/reconcile, duplicate repair, date control, request binding, validation, resume-safe handoffs, and real artifacts.
- **Useful output:** human-readable, evidence-bearing, provenance-rich documents with preserved transcript.
- **Trustworthy unhappy paths:** provider, validation, archive, reconcile, duplicate, stale handoff, and extractor failures have explicit tested behavior.
- **Correct integration boundary:** the skill makes the CLI engine own render/ledger/archive/reconcile (`docs/codex-skills/meeting-ingest/SKILL.md:6-10`, `docs/codex-skills/meeting-ingest/SKILL.md:184-193`).
- **Privacy defaults:** remote and session use require explicit gates. No issue was found there.

## 4. Gaps and risks

1. No coherent consumer first run from install through a real artifact.
2. Safe `mock` default conflicts with the primary product story and can create a fake-success impression.
3. Pending is mislabeled as success; human output conceals essential next action.
4. No independent post-remediation proof exists.
5. Human CLI ergonomics lag far behind machine JSON ergonomics.
6. Stale-handoff recovery requires filesystem judgment and deletion.
7. Partial-write recovery is uneven; ledger-write orphans lack a first-class path.
8. Health conflates blockers and advisories.
9. Documentation duplication is already producing truth drift.
10. Playbook breadth adds cognitive weight before core ingest is release-ready.

## 5. Recommendations in priority order

1. Make one host's first real meeting the next milestone. Fresh consumer repo: install, version check, init, natural-language request, date handling, extraction, completion, archive/reconcile, and report without source inspection or hand-built JSON.
2. Define one onboarding contract: install, upgrade, `--version`, init, config outcome, inbox, natural-language invocation, expected result, and recovery entry point.
3. Correct completion semantics. Distinguish completed, pending, partial success, and failed; human output must show artifacts and next actions without `--json`.
4. Make init outcome-aware. Preserve consent, but guide or preflight the session workflow and never silently fall back to mock.
5. Turn recovery into safe, previewable commands for stale handoffs and orphan outputs.
6. Separate doctor blockers, recoverable incomplete work, and advisories.
7. Collapse workflow duplication into one canonical contract with generated or mechanically verified host variants.
8. Narrow claims to one mode and one selected host/audience.
9. After core proof, populate reviewed identity and demonstrate one real Stakeholder Briefing.

## 6. What to stop, defer, or simplify

- Stop adding provider, host, Guidance, corpus, or new-source surface until the first-real-meeting gate passes.
- Stop presenting planned modes as current.
- Stop making `--json` the only useful operator experience.
- Defer additional host adapters until one establishes the pattern.
- Defer Guidance V1.1, broader sources, global identity, and deeper iQ integration.
- Defer alternate modes unless evidence ranks them above onboarding and completion clarity.
- Simplify to: initialize once, place transcript, ask agent, receive artifact and completion proof.
- Simplify documentation ownership and health reporting.

## 7. Release decision

**No-go** for public/general just-works release.

**Conditional go** for continued maintainer dogfood and a labeled technical-owner preview of summary-plus-verbatim.

Release gate:

- documented consumer install/upgrade and visible version;
- one selected host completes a real supported source from a fresh consumer project through documented natural language;
- no source inspection, envelope editing, or undocumented config repair;
- pending cannot be mistaken for complete;
- completion names Markdown, signals, archive, and reconcile;
- duplicate re-drop and interrupted handoff recover in UAT;
- doctor separates blockers/advisories;
- README, help, skills, defaults, and status agree;
- green tests and at least one post-remediation external UAT.

## 8. Confidence and unresolved questions

Confidence is high on installation, onboarding, CLI, docs, and tested recovery; medium-high on daily workflow because the primary interface is agent-mediated and lacks fresh UAT.

Unresolved questions:

- Which host is first?
- Should init accept a session-workflow choice or should the host skill confirm config changes?
- What status/exit represents healthy pending work?
- Should advisories make `doctor` nonzero?
- What repairs artifact/signal orphans after primary ledger failure?
- What is the distribution and upgrade guarantee for 0.1.0?
- Can host skills be generated from one contract?
- Did schema embedding actually eliminate UAT friction?
- Are the three low-confidence dates correct?
- Is the immediate identity agent-operated ingestion for one technical owner, or broader platform-neutral readiness?
