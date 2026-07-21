# Just Works Continuity: Semantic Integrity Guardrails Implementation Plan

**Goal:** Prevent future meeting artifacts from inventing speaker qualifiers, overstating causal certainty, converting rejected proposals into actions, resolving ambiguous identities too confidently, or losing transcript-supported time context.

**Milestone placement:** This is a bounded quality gate inside Just Works Continuity Track 3, Fresh Claude Code Meeting Proof and Recovery. It does not create a competing milestone, adopt the HTV or Spelman corpus, implement Stakeholder Briefing, or broaden the supported host/provider/output-mode surface.

**Architecture:** Split integrity controls by what the engine can actually prove. The engine deterministically indexes normalized transcript speaker labels and timestamps, binds that index into provider requests, and rejects provider labels or evidence locators that are absent from the transcript. A single versioned semantic-guidance source governs model judgment for time context, causal certainty, proposal/decision/action disposition, and identity ambiguity. Synthetic fixtures exercise deterministic failures in `pytest`; a redacted session-provider acceptance case evaluates semantic judgment without committing a private transcript. Existing client artifacts remain untouched until the owner separately authorizes corpus mutation and the planned regeneration contract is implemented.

**Evidence:** Dogfood captures `cap_20260720T161601Z_c3b4b417` and `cap_20260720T162508Z_5966b520` record the reviewed HTV case. The private source and generated artifact are evidence for this plan but are not repository fixtures.

## Success Criteria

- A provider cannot add `(Contractor)` or another qualifier to a raw speaker label that does not occur in the normalized transcript.
- Every communication-signal evidence speaker must match a normalized transcript speaker label.
- A non-null communication-signal timestamp must match a normalized transcript turn timestamp.
- Every person-directed meeting signal has a grounded evidence speaker; an ungrounded `stakeholder_name` never becomes durable raw identity provenance.
- Session-provider requests expose the exact allowed speaker labels, timestamps, and semantic-guidance version to the extraction agent.
- The guidance version survives request cleanup in the response binding, run summary, artifact provenance, and ledger snapshot.
- The maintained extraction guidance explicitly preserves time-of-day context, epistemic certainty, proposal disposition, action acceptance, and identity ambiguity.
- A redacted acceptance transcript reproduces the five dogfood patterns and has explicit expected outcomes.
- `validate-response` catches deterministic grounding failures before markdown, signals, ledger, archive, reconcile, or cache cleanup.
- Phase 2 records the existing typed provider-validation failure when a response bypasses preflight and fails grounding.
- The full suite remains green and a fresh Claude Code session-provider acceptance run satisfies every semantic assertion.

## Non-Goals And Boundaries

- Do not copy, redact in place, fingerprint-adopt, or otherwise add the HTV transcript or artifact to this repository.
- Do not mutate the existing HTV artifact, signals, ledger, processed source, or iQ Context state from this plan.
- Do not claim deterministic validation can prove causality, agreement, nickname identity, or AM/PM interpretation from arbitrary natural language.
- Do not add a second model/judge call to the normal ingest path. Extraction cost and latency are already dogfood concerns.
- Do not implement broad identity registries, colleague/client tiers, relationship profiling, global aliases, or Stakeholder Briefing.
- Do not implement `regenerate`, `repair-title`, alternate output modes, or general artifact mutability here. Post-ingest semantic correction remains approval-gated as described in Task 6.
- Preserve backward readability for provider requests already minted without the new grounding metadata. Compute their grounding index from the persisted normalized transcript at validation time.

## Integrity Model

### Deterministic blocking checks

These checks use exact source facts and fail with the existing `invalid_provider_output` / `ProviderValidationError` path:

1. `attendees[].raw_labels[]` must be drawn from the transcript speaker-label set. When the set is empty, attendee raw-label arrays must be empty.
2. Every meeting-provider `communication_signals[].evidence.speaker` is required and must be drawn from the same set. This is the transcript utterer of the evidence, not necessarily its audience or directed-to party. When no speaker can be grounded, the provider must omit the signal rather than substitute its display-oriented `stakeholder_name`.
3. `communication_signals[].evidence.timestamp`, when present, must be drawn from the normalized transcript timestamp set.
4. Persisted grounding metadata must equal a fresh index of the persisted normalized transcript; request metadata cannot override transcript truth.

Whitespace normalization may collapse repeated whitespace, but it must not remove, add, or rewrite parenthetical qualifiers. Matching is case-sensitive after whitespace normalization because capitalization and qualifiers are source provenance.

### Provider semantic responsibilities

These rules guide extraction and are verified through acceptance evaluation rather than brittle runtime heuristics:

1. Preserve nearby time context. Do not add AM/PM unless it is explicit or unambiguously established by phrases such as “last run of the night.”
2. Separate observations, hypotheses, and confirmed causes. Do not use “caused by,” “traced to,” or equivalent causal language when root cause remains open.
3. Record a proposal as a decision only when the transcript shows acceptance. Record an action only when an owner accepts it or a direction is acknowledged.
4. Never carry a rejected or infeasible proposal into open actions.
5. Do not merge people from nickname similarity alone. Conflicting or incomplete alias evidence stays unresolved and receives low confidence.
6. Keep the TL;DR consistent with the detailed topics, decisions, risks, actions, and open questions.

## Task 1: Freeze The Semantic Integrity Contract

**Files:**

- Modify: `docs/artifact-contract.md`
- Modify: `docs/provider-handoff-contract.md`
- Modify: `docs/session-provider-inbox-agent-workflow.md`
- Modify: `DECISIONS.md`

- [ ] Add a `Provider Semantic Integrity Contract` section to `docs/artifact-contract.md` defining the two integrity classes above: deterministic blocking checks and provider semantic responsibilities.
- [ ] State that attendee raw labels and signal evidence speakers are source labels, not affiliation or relationship classifications.
- [ ] State that provider-generated display names and role context may summarize grounded evidence but cannot alter raw labels or establish an alias/affiliation absent from the transcript.
- [ ] Define stable validation issue text for each deterministic failure:
  - `response.attendees[N].raw_labels[M] must copy one normalized transcript speaker label verbatim.`
  - `response.communication_signals[N].evidence.speaker must copy one normalized transcript speaker label verbatim.`
  - `response.communication_signals[N].evidence.speaker is required for a person-directed meeting signal.`
  - `response.communication_signals[N].evidence.timestamp must copy one normalized transcript timestamp verbatim.`
  - `provider request transcript_grounding does not match normalized_transcript.`
- [ ] Amend the handoff contract so new requests carry `transcript_grounding` and `semantic_guidance_version`, while old request schema 1.0 files remain readable through deterministic recomputation.
- [ ] Freeze the request-bound `semantic_guidance_version` echo in the response envelope before implementation. Accepted provenance values are the current version (`"1.0"` initially), `"legacy"` for a pre-field persisted handoff, and `"none"` for the non-semantic mock provider.
- [ ] Freeze durable placement of `semantic_guidance_version` in artifact front matter, run summaries, and ledger artifact/provider provenance. These fields survive successful handoff cleanup and must use the effective bound value, never whichever guidance version happens to be current at read time.
- [ ] Document that `validate-response` is the no-side-effect grounding gate and phase 2 repeats the same validation under the project lock.
- [ ] Record the decision in `DECISIONS.md`: exact source facts fail closed; semantic judgment is prompt-contract plus acceptance evidence; no automatic second-model review is added.
- [ ] Record the privacy boundary: dogfood findings may generate synthetic fixtures, but private corpus source text requires separate fingerprinted adoption approval.

**Contract checkpoint:** Review and approve this task before implementation changes. Later tasks must use the frozen field names, matching rules, compatibility behavior, and error text.

## Task 2: Build A Canonical Transcript Grounding Index

**Files:**

- Modify: `src/meeting_ingest/transcript.py`
- Modify: `src/meeting_ingest/extract.py`
- Modify: `src/meeting_ingest/providers/mock.py`
- Test: `tests/test_extract.py`
- Test: create `tests/test_transcript.py`

**Interface:**

```python
@dataclass(frozen=True)
class TranscriptGrounding:
    speaker_labels: tuple[str, ...]
    timestamps: tuple[str, ...]


def index_normalized_transcript(text: str) -> TranscriptGrounding: ...
```

- [ ] Add one canonical normalized-turn parser supporting the renderer’s `**Speaker** (timestamp): text`, `**Speaker**: text`, and conservative plain-text `Speaker: text` forms.
- [ ] Reuse `TranscriptTurn`; do not create a second incompatible speaker parser.
- [ ] Preserve first-seen order while deduplicating labels and timestamps.
- [ ] Normalize repeated whitespace only. Preserve exact capitalization, comma order, punctuation, and parenthetical qualifiers.
- [ ] Avoid treating URL schemes, clock-only prefixes, Markdown headings, and generic prose containing a colon as speakers.
- [ ] Add extraction tests covering:
  - `Opeyemi, Baba` remains distinct from `Opeyemi, Baba (Contractor)`;
  - two real contractor labels plus one unqualified client-side label;
  - merged same-speaker VTT turns;
  - DOCX hour-long timestamps;
  - plain-text speaker lines;
  - transcripts with no confidently parseable speakers;
  - stable first-seen ordering and deduplication.
- [ ] Tie timestamp tests to the actual grounding index: compacted VTT, DOCX hour-long, and retained merged-turn timestamps pass; a plausible timestamp dropped by same-speaker merging is absent and later fails grounding.
- [ ] Refactor mock attendee inference to consume the canonical parser so tests and production do not disagree on what constitutes a speaker.
- [ ] Preserve parenthetical qualifiers in mock raw labels. The current mock regex strips them and would fail the new direct-provider grounding gate.
- [ ] Audit mock-dependent expectations in `tests/test_pipeline_ingest.py`, `tests/test_signals.py`, and `tests/test_session_inbox.py`; the parser change has a broader blast radius than the focused transcript tests.
- [ ] Expose the computed grounding index on `SourceExtraction` or compute it once from `normalized_text` in `_prepare_ingest`; do not repeatedly parse the transcript at unrelated layers.

**Focused verification:**

```bash
uv run pytest tests/test_transcript.py tests/test_extract.py tests/test_provider_render.py -q
```

## Task 3: Bind Grounding And Guidance Into Provider Requests

**Files:**

- Create: `src/meeting_ingest/extraction_guidance.py`
- Modify: `src/meeting_ingest/provider.py`
- Modify: `src/meeting_ingest/pipeline.py`
- Modify: `src/meeting_ingest/provider_handoff.py`
- Modify: `src/meeting_ingest/provider_contract.py`
- Modify: `src/meeting_ingest/providers/anthropic.py`
- Modify: `src/meeting_ingest/render.py`
- Modify: `src/meeting_ingest/ledger.py`
- Test: `tests/test_pipeline_ingest.py`
- Test: `tests/test_anthropic_provider.py`
- Test: `tests/test_provider_render.py`
- Test: `tests/test_ledger.py`
- Test: `tests/fixtures/expected_markdown/summary_plus_verbatim_basic.md`

**New request fields:**

```json
{
  "semantic_guidance_version": "1.0",
  "transcript_grounding": {
    "speaker_labels": ["Graham, Ken (Contractor)", "Opeyemi, Baba"],
    "timestamps": ["00:39", "00:51"]
  }
}
```

- [ ] Define `SEMANTIC_GUIDANCE_VERSION = "1.0"` and the six semantic rules in one Python module.
- [ ] Extend `ProviderRequest` with immutable `transcript_grounding` and `semantic_guidance_version` fields, and populate them for direct providers in `_ingest_locked`.
- [ ] New session-provider requests must persist the guidance version and grounding index next to `normalized_transcript`.
- [ ] Add both fields to the request’s generated response contract metadata. New response envelopes must echo `semantic_guidance_version` under a request-bound `const`; legacy request/response pairs may omit it only when the persisted request predates the field.
- [ ] When speaker labels or timestamps exist, constrain response-contract JSON Schema values:
  - attendee `raw_labels.items.enum` uses exact speaker labels;
  - signal `evidence.speaker` is required and is one exact speaker label;
  - signal `evidence.timestamp` is `null` or one exact transcript timestamp.
- [ ] When the speaker set is empty, require attendee `raw_labels` and `communication_signals` to be empty rather than allowing invented attribution. When the timestamp set is empty, require signal evidence timestamps to be null.
- [ ] `_validate_request` must recompute grounding from `normalized_transcript` and reject mismatched persisted metadata.
- [ ] For legacy requests without the new fields, compute grounding from `normalized_transcript`, use guidance version `legacy`, and continue through validation. Do not silently rewrite the request.
- [ ] Include the versioned semantic rules in the session request so the extraction agent does not depend on remembering a host-local prompt revision.
- [ ] Make the Anthropic API adapter consume the same semantic guidance and transcript grounding; do not maintain a divergent hand-written rule list.
- [ ] Treat the embedded JSON Schema enums as authoring guidance only. The engine does not execute that schema; `validate_provider_grounding` in Task 4 is the enforcement layer for both session and direct providers.
- [ ] Propagate the effective guidance version through the response binding, run summary, rendered artifact front matter, and ledger artifact/provider provenance so deleting a completed handoff does not erase which rules shaped the output.
- [ ] Add tests asserting request-bound enums, empty-index behavior, tamper detection, legacy-request compatibility, response-version binding, durable provenance, and Anthropic prompt inclusion.
- [ ] Document the expected parity boundary: direct providers use the in-process grounding index and current guidance version; session providers additionally verify persisted request grounding and the echoed version.

**Focused verification:**

```bash
uv run pytest tests/test_pipeline_ingest.py tests/test_session_inbox.py tests/test_anthropic_provider.py -q
```

## Task 4: Enforce Grounding Before Side Effects

**Files:**

- Modify: `src/meeting_ingest/schema.py`
- Modify: `src/meeting_ingest/pipeline.py`
- Modify: `src/meeting_ingest/provider_handoff.py`
- Test: `tests/test_provider_render.py`
- Test: `tests/test_pipeline_ingest.py`
- Test: `tests/test_session_inbox.py`

**Interface:**

```python
def validate_provider_grounding(
    response: ProviderResponse,
    grounding: TranscriptGrounding,
) -> None: ...
```

- [ ] Keep structural `validate_provider_response` separate from source-aware `validate_provider_grounding` so callers cannot accidentally pass an arbitrary transcript into shape validation.
- [ ] Aggregate all grounding problems into one `ProviderValidationError`, matching existing multi-issue behavior.
- [ ] Include the allowed transcript labels/timestamps in structured error details or an adjacent correction hint so the extraction agent can repair verbatim values without inspecting unrelated runtime state.
- [ ] Run both validators in:
  - direct provider ingest before `_finish_ingest`;
  - `validate-response` using the persisted request transcript;
  - session phase 2 after request/response identity binding and before `_finish_ingest`.
- [ ] Ensure validation precedes signal writes, markdown writes, ledger success snapshots, archive, reconcile, and provider-cache cleanup.
- [ ] Preserve existing failure recording when phase 2 is invoked without successful preflight: `ingest_failed`, provider-validation phase, source remains actionable, request/response retained for correction.
- [ ] Test the expected retry UX: overwrite only the invalid provider response, rerun `validate-response`, then complete phase 2 without reminting the request.
- [ ] Add tests with a synthetic transcript containing two qualified contractor labels and one unqualified label. A response that adds `(Contractor)` to the unqualified label must fail in attendees and communication signals.
- [ ] Add tests for invented evidence timestamps, multiple aggregated grounding issues, no-side-effect preflight, phase-2 failure retention, and a fully grounded success.
- [ ] Add explicit timestamp tests for compacted VTT, hour-long DOCX, and same-speaker merged turns.
- [ ] Remove the `signal.evidence.speaker or signal.stakeholder_name` raw-identity fallback for meeting-provider signals. Signal enrichment copies only a required, validated evidence speaker into `stakeholder_name_raw`; display-oriented `stakeholder_name` is never raw provenance.
- [ ] Add regression tests for both the grounded-speaker path and the rejected null-speaker path so a fabricated qualifier cannot enter signal identity or downstream derivation.

**Focused verification:**

```bash
uv run pytest tests/test_provider_render.py tests/test_pipeline_ingest.py tests/test_session_inbox.py tests/test_signals.py -q
```

## Task 5: Align Every Extraction Surface And Add Semantic Acceptance Evaluation

**Files:**

- Modify: `docs/session-provider-subagent-prompt.md`
- Modify: `docs/claude-agents/meeting-ingest-session-provider.md`
- Modify: `docs/claude-skills/meeting-ingest/SKILL.md`
- Modify: `docs/codex-skills/meeting-ingest/SKILL.md`
- Modify: installed `~/.claude/agents/meeting-ingest-session-provider.md`
- Modify: installed `~/.claude/skills/meeting-ingest/SKILL.md`
- Modify: installed `~/.codex/skills/meeting-ingest/SKILL.md`
- Create: `tests/fixtures/semantic-integrity/session-provider-eval.vtt`
- Create: `tests/fixtures/semantic-integrity/expected-review.json`
- Create: `docs/testing/semantic-integrity-acceptance.md`

- [ ] Update all maintained and installed provider instructions to read and obey `semantic_guidance_version`, versioned rules, and `transcript_grounding` from the request.
- [ ] State plainly that `raw_labels` are exact copies, not normalized display names or inferred affiliations.
- [ ] Add the six semantic responsibilities verbatim or reference the request-carried list without weakening it.
- [ ] Keep durable Codex skill source and installed copy byte-for-byte synchronized.
- [ ] Keep durable Claude agent/skill sources and installed copies synchronized.
- [ ] Add explicit `cmp -s` or SHA-256 verification commands to the acceptance document for each durable/installed pair; installed home-directory copies are not covered by `pytest`.
- [ ] Create a wholly synthetic VTT using invented people and systems. It must contain these five patterns without copying private wording:
  1. two attendees have `(Contractor)` in source labels and one does not;
  2. an unlabeled `10:06` time is explicitly established as the last nightly run, with a nearby later-night retry;
  3. an observed failure coexists with an explicitly unconfirmed root cause;
  4. one participant proposes a redesign and the putative owners reject it as infeasible;
  5. a nickname could refer to an attendee, but later dialogue suggests a separate absent person.
- [ ] `expected-review.json` must contain machine-readable assertions, not a golden prose summary:
  - unqualified attendee remains unqualified;
  - time is PM/night or left without an invented meridiem, never AM;
  - TL;DR says root cause is unconfirmed;
  - rejected redesign is absent from open actions and may appear as rejected context;
  - nickname identity remains unresolved/low-confidence;
  - TL;DR and detailed sections do not contradict one another;
  - all raw labels and signal locators pass deterministic validation.
- [ ] Document a fresh-project Claude Code acceptance run using the approved immutable build once Track 1 exists. Until then, label development runs as non-release evidence.
- [ ] Record host version, model, build identity, guidance version, quality, elapsed time, extraction tokens, interventions, output paths, signal count, and the assertion results.
- [ ] Require a human semantic review and one independent blind review for the milestone proof; neither review mutates artifacts.
- [ ] State the verification split explicitly: `pytest` proves deterministic grounding and lifecycle behavior; the session-provider run plus human/blind review evaluates the semantic assertions without adding a second model call to normal ingest.

**Acceptance command outline:**

```bash
meeting-ingest init --root "$TEMP_PROJECT"
meeting-ingest provider-request "$SOURCE" --provider session --quality balanced --meeting-date YYYY-MM-DD --json
meeting-ingest validate-response "$RESPONSE" --source "$SOURCE" --json
meeting-ingest ingest "$SOURCE" --provider session --provider-response "$RESPONSE" --json
meeting-ingest doctor --root "$TEMP_PROJECT" --json
```

The final testing document must use explicit safe temporary paths and the actual CLI shapes available when implemented.

## Task 6: Define Correction And Recovery Boundaries

**Files:**

- Modify: `docs/artifact-contract.md`
- Modify: `docs/product-status.md`
- Modify: `CURRENT-QUESTIONS.md`

- [ ] Document the pre-ingest correction loop: deterministic validation failure retains the request/response, reports every issue, and permits rewriting only the provider response before retrying validation and phase 2.
- [ ] State that failed grounding never writes or partially replaces durable output.
- [ ] State that already-ingested semantic correction requires the contracted but unimplemented regeneration path because markdown, signal JSONL, ledger current state, and downstream derivations must move together.
- [ ] Add an explicit current question for the owner-approved generated-Markdown mutability and semantic-regeneration policy.
- [ ] Keep existing HTV and Spelman artifacts read-only. Their reviewed defects remain dogfood evidence until a fingerprinted adoption/correction plan receives separate approval.
- [ ] Reference the already-frozen Regeneration Contract in `docs/artifact-contract.md`; do not create a second semantic-regeneration design.
- [ ] Add a follow-on implementation slice for the existing `regenerate --provider session` contract after the owner approves generated-Markdown mutability and client-corpus correction. Its acceptance must cover the already-contracted atomic artifact/signal replacement, fingerprints, append-only `artifact_regenerated`, and downstream supersession behavior.
- [ ] Do not recommend manual markdown or signal edits as an interim repair mechanism.

## Task 7: Verification, Dogfood Proof, And Product-Truth Update

**Files:**

- Modify after implementation evidence exists: `docs/product-status.md`
- Modify after implementation evidence exists: `docs/implementation-plan.md`
- Modify after implementation evidence exists: `README.md`
- Modify after implementation evidence exists: `docs/codex-skills/meeting-ingest/SKILL.md`

- [ ] Run focused suites after every task and the full suite at the end:

```bash
uv run pytest -q
```

- [ ] Run formatting/static checks already configured by the repository; do not introduce a new tool solely for this slice.
- [ ] Run `git diff --check` and inspect the diff for unrelated dirty-worktree changes before staging.
- [ ] Run the redacted Claude Code session-provider acceptance case from a fresh temporary consumer project.
- [ ] Confirm deterministic failures are actionable and side-effect-free.
- [ ] Confirm a valid response completes markdown, signals, ledger, archive, reconcile, and doctor cleanly.
- [ ] Record the semantic assertion results and dogfood metrics in a dated session note.
- [ ] Update product truth only with demonstrated claims. Do not claim general semantic correctness or corpus correction.
- [ ] Generate the maintained ready-to-paste Claude Code review prompt at the review-before-commit checkpoint, then incorporate or disposition findings before commit.

## Required Test Matrix

| Case | Expected result |
|---|---|
| Exact transcript label | Accepted |
| Added parenthetical affiliation | Blocking provider-validation error |
| Case-changed or punctuation-changed raw label | Blocking provider-validation error |
| Evidence speaker absent from transcript | Blocking provider-validation error |
| Evidence timestamp absent from transcript | Blocking provider-validation error |
| Compacted/hour-long retained timestamp | Accepted exactly as present in normalized transcript |
| Timestamp removed by same-speaker merge | Blocking provider-validation error |
| Null signal speaker on a person-directed meeting signal | Blocking provider-validation error; no stakeholder-name fallback |
| Null signal timestamp | Accepted when structurally valid |
| Transcript with no parseable speakers | Attendee raw labels and communication signals empty |
| New request grounding metadata | Matches recomputed transcript index |
| Tampered request grounding metadata | Blocking provider-validation error |
| Legacy request without grounding metadata | Recomputed and validated without request rewrite |
| Rejected proposal in synthetic acceptance transcript | Not emitted as an open action |
| Unconfirmed cause in synthetic acceptance transcript | TL;DR preserves uncertainty |
| Night-context time in synthetic acceptance transcript | PM/night or unqualified, never AM |
| Ambiguous nickname in synthetic acceptance transcript | Unresolved or low-confidence |
| Invalid preflight | No durable side effects; handoff retained |
| Invalid phase 2 | Failure snapshot only; no ready artifacts; handoff retained |
| Valid phase 2 | Artifact, signals, archive, reconcile, and clean health |

## Completion Gate

This slice is complete only when:

1. The frozen contract distinguishes deterministic enforcement from semantic evaluation.
2. Every provider path uses the same grounding index and semantic-guidance version.
3. The known fabricated-affiliation pattern is impossible to finalize.
4. The redacted acceptance case passes every semantic assertion in the reference host.
5. No private corpus content was committed or mutated.
6. Full regression tests pass.
7. Product-status language accurately limits the claim to guarded fresh-ingest output.
8. Independent review findings are resolved or explicitly deferred with rationale.

## Suggested Commit Sequence

1. `docs: freeze provider semantic integrity contract`
2. `feat: index transcript speakers and evidence timestamps`
3. `feat: bind provider responses to transcript grounding`
4. `docs: align session extraction guidance`
5. `test: add semantic integrity acceptance case`
6. `docs: record semantic correction boundary and proof`

Commits must exclude unrelated pre-existing working-tree changes and volatile `.iq-context` runtime files.
