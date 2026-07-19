# Stakeholder Playbook Design

## Status

Accepted durable design baseline. The Stakeholder Briefing V1 artifact contract is frozen; the Guidance V1.1 derivation provider contract remains pending.

This document defines the product and technical design for Stakeholder Briefing V1 and Playbook Guidance V1.1. It is the design baseline for later amendments to `docs/artifact-contract.md`, `docs/implementation-plan.md`, `docs/product-status.md`, and the implementation.

Where this document conflicts with the current artifact contract or roadmap, the existing contract remains authoritative until the conflict is reviewed and deliberately amended.

## Purpose

Meeting Ingest already produces source-grounded communication signals from meetings. The stakeholder playbook turns those signals into durable, useful communication memory without turning source extraction into personality profiling or turning Meeting Ingest into an autonomous messaging system.

The playbook should help answer:

> What should I remember before communicating with this person, why do we believe it, and how current is that belief?

The design must support current meeting-derived signals and provide a clean path for later communication sources such as email bodies, Teams threads, text threads, screenshots, social posts, and social profiles.

## Product Outcomes

The product should prioritize these outcomes:

1. **Interaction preparation**: surface current asks, commitments, priorities, concerns, preferences, recent changes, and cautions before a meeting or message.
2. **Commitment integrity**: preserve what was promised, by whom, to whom, when it was observed, and whether resolution evidence exists.
3. **Evidence-grounded communication cues**: provide practical guidance only when it is supported by qualified observations and scoped to the context where it applies.
4. **Continuity across sources and time**: maintain a coherent view as evidence accumulates across meetings and later communication sources.
5. **Auditability and correction**: let every fact, pattern, and cue be traced to evidence and let identity or derivation mistakes be corrected without rewriting canonical source observations.
6. **Change awareness**: show strengthening, weakening, contested, stale, superseded, or unresolved information instead of flattening a stakeholder into a static profile.

The primary product surface is a concise pre-interaction briefing. The stored profile is the substrate for that briefing, not the end of the user experience.

## Product Increments

### Stakeholder Briefing V1

Stakeholder Briefing V1 is deterministic and local. It provides:

- reviewed stakeholder identity and evidence coverage
- tracked asks and commitments with lifecycle uncertainty stated honestly
- current priorities, concerns, risks, and decision rationales
- explicit communication preferences
- observed communication behaviors
- interaction responses when present
- recency, source counts, and freshness
- unresolved identities and low-confidence observations
- mechanical contradiction candidates where the structured data supports them
- human-readable Markdown and machine-readable JSON
- full deterministic rebuilds
- status and doctor visibility
- correction controls for identity, bad signals, tracked-item resolution, and unwanted derived entries

This milestone provides useful communication memory without requiring a model during derivation.

### Playbook Guidance V1.1

Playbook Guidance V1.1 adds provider-assisted judgment over deterministically qualified observations:

- semantic clustering of related observations
- contextual pattern scope
- confirmed contradictions and tensions
- communication cues and caveats
- positive-response pattern analysis
- emerging, established, contested, stale, and retired pattern states
- explicit human review controls for inferred guidance

Provider-assisted guidance must remain derived, evidence-linked, reviewable, and removable through rebuild. It must not mint new source facts or overwrite contradictory evidence.

## Non-Goals

The first playbook releases do not include:

- autonomous outreach or message sending
- automatic persuasion strategies
- psychological, personality, diagnostic, intelligence, motive, vulnerability, or protected-trait inference
- sentiment-only stakeholder conclusions
- relationship scores
- cross-project or global stakeholder profiles
- automatic fuzzy identity merges
- screenshot OCR or image-region evidence in Briefing V1
- social-profile analysis in Briefing V1
- embeddings, vector storage, a hosted backend, or multi-user synchronization
- a dashboard or web application
- copying complete transcripts or concentrated profile bodies into iQ Context

Drafting agents may consume a briefing when explicitly invoked, but drafting remains outside the playbook derivation boundary.

## Design Principles

1. **Sources remain canonical.** Source artifacts and validated observations are the durable evidence base.
2. **Profiles are disposable materializations.** Every profile can be rebuilt from sources, signals, identity state, rules, and review overlays.
3. **Observation is separate from interpretation.** Source extraction records what happened; derivation determines patterns and guidance.
4. **Behavioral language outranks trait language.** Prefer “requested source lineage in three technical reviews” over “is skeptical.”
5. **Uncertainty remains visible.** Missing resolution evidence, identity ambiguity, weak inference, conflicting evidence, and stale guidance must not be hidden.
6. **Contradiction is preserved.** New evidence may contest or supersede older evidence, but it does not silently erase it.
7. **Guidance requires stronger evidence than observation.** One weak interaction cannot become durable communication advice.
8. **Context matters.** A preference observed in a technical review may not apply to an executive status update.
9. **Derived work does not redefine ingest success.** Playbook failure must not fail an otherwise successful source ingest.
10. **Local-first is sufficient for V1.** Filesystem artifacts, JSON, JSONL, TOML, and deterministic rebuilds remain the default architecture.

## Conceptual Model

### Source Artifact

A canonical acquired communication artifact, including:

- meeting transcript
- email body
- chat or message thread
- document or memo
- screenshot
- social post
- social profile capture

A source has content identity, source kind, occurrence timing, acquisition timing, processing timing, privacy classification, participant metadata, and extraction provenance.

### Evidence Reference

An addressable location within a source:

- transcript timestamp
- message ID
- line range
- document page or paragraph
- screenshot bounding region
- URL and captured element

Evidence references include only the minimum excerpt or paraphrase needed to understand the observation. The source remains the full record.

### Observation

An immutable, validated, source-grounded record of an ask, priority, commitment, concern, rationale, preference, behavior, or interaction response.

Observations do not contain durable communication guidance. They preserve raw identity labels and evidence even when identity resolution is uncertain.

### Pattern

A rebuildable interpretation over multiple qualified observations. A pattern contains:

- stakeholder identity
- category
- behavioral statement
- applicable context
- supporting observation references
- contradicting observation references
- distinct source-event count
- first and last observed times
- confidence and confidence rationale
- lifecycle state
- review state

Patterns are never source facts.

### Guidance

A practical, scoped suggestion derived from one or more qualified patterns. Guidance contains:

- actionable cue
- basis pattern and observation references
- applicable context
- caveat or “do not apply when” condition
- confidence
- freshness
- derivation provenance
- human review state

### Stakeholder Identity

A stable project-local person ID, reviewed display name, reviewed aliases, and optional reviewed source-specific identifiers.

Identity resolution is current-state interpretation. Canonical observations preserve the raw names and labels found in their sources.

### Profile

A materialized current view of a stakeholder’s qualified observations, tracked items, patterns, guidance, contradictions, freshness, and evidence coverage.

### Derivation Run

An append-only record of one playbook rebuild. It records inputs, fingerprints, affected stakeholders, rules and schema versions, provider provenance when applicable, outputs, warnings, and status.

### Review Overlay

Human decisions applied after derivation without mutating source observations. Review overlays can suppress bad signals, reject or tombstone derived entries, resolve tracked asks or commitments, and later accept or edit guidance.

## Observation Taxonomy

The current five source observation types remain:

- `explicit_ask`
- `stakeholder_priority`
- `decision_rationale`
- `commitment`
- `risk_or_concern`

The playbook foundation adds three narrow observation types.

### `communication_preference`

Use only for a stated preference about receiving or giving information, including:

- format
- level of detail
- sequencing
- channel
- timing
- supporting evidence
- interaction structure

Example:

> “Please send the one-page summary before the review so I can read it first.”

A single observed behavior does not become a preference unless the stakeholder states or clearly requests the preference.

### `communication_behavior`

Use for an observable interaction behavior without converting it into a person-level trait.

Examples:

- requested source lineage before approving a recommendation
- redirected a broad discussion toward the immediate decision
- asked for a concrete example after an abstract explanation
- requested a shorter status update

Repeated behaviors may support a derived preference or pattern. The source observation describes only what happened in that event.

### `interaction_response`

Use for an observable response linked to a specific preceding communication approach.

An interaction response must identify:

- the antecedent communication approach
- the observed response
- their source and evidence references
- their timestamps when available
- link confidence
- causal confidence

Abbreviated illustrative shape. The artifact contract defines the complete required `source` and `timing` fields for each source kind; this example focuses on the standard signal fields and typed interaction extension:

```json
{
  "schema_version": "1.1",
  "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731",
  "ingest_run_id": "ingest-20260710-20260710T180000Z-a1b2",
  "effective_at": "2026-07-10",
  "recorded_at": "2026-07-10T18:00:00Z",
  "source": {
    "source_id": "src-a1b2c3d4e5f6",
    "source_kind": "chat_thread",
    "evidence_locator_scheme": "message_id"
  },
  "signal_type": "interaction_response",
  "stakeholder_id": "person-kushali-g",
  "stakeholder_name": "Kushali G",
  "stakeholder_name_raw": "Kushali G",
  "summary": "The stakeholder explicitly approved an update that led with a recommendation and then supporting evidence.",
  "evidence": {
    "kind": "quote",
    "text": "This is exactly what I needed. Use this format going forward.",
    "speaker": "Kushali G",
    "timestamp": "2026-07-10T14:07:00-04:00"
  },
  "inference_level": "explicit",
  "confidence": "high",
  "topics": ["status-update"],
  "project_refs": [],
  "recurrence": "unknown",
  "status": "active",
  "interaction": {
    "antecedent": {
      "source_id": "src-a1b2c3d4e5f6",
      "evidence_locator": "msg-14",
      "approach_tags": ["recommendation_first", "supporting_detail"],
      "summary": "The update led with a recommendation and then supporting evidence."
    },
    "response": {
      "source_id": "src-a1b2c3d4e5f6",
      "evidence_locator": "msg-15",
      "response_kind": "explicit_approval",
      "valence": "positive",
      "summary": "The stakeholder explicitly approved the recommendation."
    },
    "antecedent_at": "2026-07-10T14:03:00-04:00",
    "response_at": "2026-07-10T14:07:00-04:00",
    "link_confidence": "high",
    "causal_confidence": "unknown"
  }
}
```

`interaction_response` remains a standard schema 1.1 signal record. It keeps the common `summary`, `evidence`, identity, inference, and confidence fields and adds a typed `interaction` extension. The common evidence object describes the primary response evidence. The nested locators bind the antecedent and response to addressable positions in the source.

Recommended response kinds:

- `explicit_approval`
- `adoption_or_action`
- `requested_continuation`
- `accepted_with_revision`
- `requested_clarification`
- `explicit_rejection`
- `abandoned_or_reversed`
- `polite_acknowledgment`
- `emoji_reaction`
- `response_timing`
- `unclear`

Allowed valence values are:

- `positive`
- `negative`
- `neutral`
- `mixed`
- `unclear`

`accepted_with_revision` normally maps to `mixed`. `requested_clarification` normally maps to `neutral` or `unclear` unless the source contains separate positive or negative evidence.

Evidence rules:

- Explicit approval is a valid source observation but does not automatically establish a context-general pattern.
- Adoption or action is strong observable evidence when linked to the proposal, but the record should not claim causation without explicit support.
- A request to continue, repeat, expand, or reuse an approach is strong evidence of a preference.
- Timing may strengthen linkage but never establishes positive response by itself.
- Emoji, thanks, politeness, and sentiment are corroborating evidence only.
- No response is not evidence of positive or negative preference.
- Records should say “followed by” unless causality is explicit.
- `causal_confidence` defaults to `unknown` and does not inherit link confidence.

Meeting transcripts are expected to produce relatively few interaction-response observations. Email and thread ingestion will provide more complete antecedent-and-response sequences.

`approach_tags` must use a controlled vocabulary with a free-text escape for unclassified approaches. The vocabulary is a Guidance V1.1 contract input because positive-response aggregation depends on comparable approach categories.

### Derived `communication_style`

`communication_style` is not a source observation type. It may be used as a derived pattern category only when qualified observations support a scoped behavioral statement.

Allowed:

> In technical design reviews, repeatedly requests source lineage before approval.

Not allowed:

> Has a distrustful communication style.

## Generalized Source Provenance

Playbook work requires communication-neutral source provenance before non-meeting ingest begins.

Signal schema 1.1 should add nested `source` and `timing` objects while retaining current meeting fields through the 1.x compatibility window.

Illustrative shape:

```json
{
  "schema_version": "1.1",
  "signal_id": "sig-a1b2c3d4e5f6-91aa2c80b731",
  "meeting_id": "mtg-20260612-71e6b28b",
  "effective_at": "2026-06-12",
  "recorded_at": "2026-07-03T12:00:00Z",
  "stakeholder_id": "person-kushali-g",
  "stakeholder_name": "Kushali G",
  "stakeholder_name_raw": "G, Kushali",
  "source": {
    "source_id": "src-a1b2c3d4e5f6",
    "source_kind": "meeting_transcript",
    "source_sha256": "a1b2c3d4e5f6...",
    "meeting_id": "mtg-20260612-71e6b28b",
    "artifact_path": "2026-06-12-kushali-adbook.md",
    "channel": "teams",
    "evidence_locator_scheme": "timestamp"
  },
  "timing": {
    "occurred": {
      "value": "2026-06-12",
      "precision": "date",
      "timezone": null,
      "source": "transcript_header",
      "confidence": "high"
    },
    "acquired": {
      "value": "2026-07-03T11:45:00-04:00",
      "precision": "datetime",
      "timezone": "America/Detroit",
      "source": "filesystem_mtime",
      "confidence": "low"
    },
    "recorded": {
      "value": "2026-07-03T12:00:00Z",
      "precision": "datetime",
      "timezone": "UTC",
      "source": "system_clock",
      "confidence": "high"
    }
  }
}
```

Time semantics:

- `occurred`: when the meeting or communication happened
- `acquired`: when the source was downloaded, copied, captured, or placed into the workflow
- `recorded`: when Meeting Ingest processed and persisted the observation

Occurrence precision must support:

- `datetime`
- `date`
- `range`
- `unknown`

Threads may include a start and end value. File modification time normally describes acquisition, not occurrence, for downloaded Teams transcripts. If it is the only available fallback for occurrence, it must remain low confidence and be reported as such.

Compatibility rules:

- Existing `meeting_id`, `ingest_run_id`, `effective_at`, and `recorded_at` remain readable.
- Schema 1.1 meeting signals may mirror those fields while also emitting `source` and `timing`.
- `meeting_id` is optional for non-meeting sources.
- Readers normalize schema 1.0 records into the generalized internal model.
- Schema 1.1 requires `stakeholder_name_raw` for every person-directed observation; it preserves the source/provider label used for current registry resolution.
- Schema 1.0 readers treat `stakeholder_name` as the best available raw label and record that the value may already be provider-normalized.
- `stakeholder_id` in a stored signal is an extraction-time hint only. Derivation must not use it as an identity shortcut; it resolves the raw label through the current registry.
- Providers do not set recurrence. Schema 1.1 extraction writes `recurrence: "unknown"`; derivation computes recurrence across observations.
- Source-kind-specific privacy and provider gates apply independently.

Allowed schema 1.1 source kinds:

- `meeting_transcript`
- `email`
- `chat_thread`
- `text_thread`
- `document`
- `screenshot`
- `social_post`
- `social_profile`

`source_kind` describes the communication artifact. It is deliberately distinct from the existing source-ledger `source_type`, which describes a file format such as `docx`, `vtt`, or `txt`.

Unknown source kinds are rejected. Schema 1.1 must freeze required metadata for `meeting_transcript`; email and document requirements are frozen with the Phase 4 communication contract, and richer-source requirements are frozen before each Phase 5 source is implemented. Signals for non-meeting sources should use `_signals/<source_id>.jsonl`; meeting signal paths remain backward compatible with `_signals/<meeting_id>.jsonl`.

## Signal Identity

The current date-and-ordinal signal ID shape can collide across multiple sources on the same date and is unstable as a global playbook reference.

New signals should use a deterministic source-and-observation identity:

```text
sig-<source-hash-prefix>-<observation-hash-prefix>
```

The observation identity hash should include stable normalized inputs such as:

- signal type
- raw actor identity
- evidence locator
- normalized evidence identity only when no stable locator exists

The canonical observation reference is the pair `(source_id, signal_id)`. Existing signal IDs remain valid and do not require immediate migration.

Locator-based identity is preferred when the source provides stable message IDs, timestamps, line ranges, or region locators. It survives provider paraphrase changes better than evidence-text identity. When a source has no stable locator, the fallback evidence normalization and collision behavior must be explicit.

Two observations that produce the same identity inputs within one source are exact-duplicate candidates. The engine should collapse them only when their normalized structured content is identical. Otherwise it must add a deterministic collision suffix and emit a validation warning.

The exact hash input, truncation length, normalization rules, and collision suffix must be frozen and covered by deterministic fixtures before implementation.

### Signal Regeneration

Refreshing signals for an already-ingested source may supersede earlier observations. Regeneration must not pretend that provider wording is stable.

Rules:

- Locator-based observation IDs remain stable when signal type, raw actor, and source locator remain stable.
- Regenerated observations that cannot retain an old identity explicitly supersede prior observation references for that source.
- Rebuild reports overrides whose referenced observations no longer exist.
- `doctor` reports re-emergent observations that match a suppressed signal by source, signal type, raw actor, and locator but use a new signal ID.
- Suppression is never silently discarded because evidence wording changed.
- The derivation ledger records the before-and-after signal-set fingerprints used for the rebuild.

Phase 0 fixtures must cover provider paraphrase drift, locator changes, duplicate observations, superseded signals, and suppression across regeneration.

## Identity Registry And Resolution

### Registry

Stakeholder identity uses a small, reviewed, project-local registry. The registry is human-owned and must not be silently modified by extraction or derivation.

Proposed location:

```text
_playbook-state/stakeholders.toml
```

Illustrative shape:

```toml
[[people]]
person_id = "person-kushali-g"
display_name = "Kushali G"
aliases = ["Kushali", "G, Kushali", "Kushali G"]
status = "reviewed"
```

Later schema versions may add reviewed source-specific identifiers. Cross-project or global identity remains deferred.

### Resolution Order

1. Exact reviewed external identifier, when available.
2. One unique exact match across reviewed aliases and normalized display names.
3. Candidate match surfaced for review.
4. Unresolved identity.

Fuzzy similarity must never auto-merge people.

### Canonical Behavior

- Stable person IDs are immutable.
- Display-name and alias changes do not change the person ID.
- Observations retain raw stakeholder names and source labels.
- Provider-proposed person IDs are advisory.
- New observations may include a reviewed ID when an exact registry match is available.
- Derivation always resolves through the current registry, even when an older signal contains an ID.
- For schema 1.1, resolution uses `stakeholder_name_raw`; for schema 1.0 it uses `stakeholder_name` as the best available legacy raw label.
- Stored `stakeholder_id` values are never authoritative derivation inputs, including existing `person-*` slugs and future registry hints.
- A normalized alias or display name that appears under multiple people is ambiguous and resolves to no person until repaired.
- `doctor` reports alias collisions.
- Corrections and merges use registry aliases or redirects plus a full rebuild, not signal rewrites.
- Group-directed observations use `audience_id` and `audience_name`, or remain unresolved; they do not mint fake people.

### Identity Candidates

Derivation should write unresolved names, counts, source labels, and candidate slugs to:

```text
_derived/generations/<derivation-run-id>/identity-candidates.json
```

The tool may suggest registry entries but must not write reviewed identity mappings automatically.

## Local Storage Model

Filesystem storage remains sufficient for V1.

Proposed structure:

```text
_playbook-state/
  stakeholders.toml
  derivation-ledger.jsonl
  overrides.jsonl

_derived/
  playbook-index.json
  generations/
    <derivation-run-id>/
      identity-candidates.json
      stakeholders/
        <person_id>/
          profile.json
          briefing.md
```

### `profile.json`

Canonical machine-readable materialized profile for one stakeholder within one immutable derivation generation.

### `briefing.md`

Deterministic human- and agent-readable rendering of the profile. It should use stable headings, explicit empty sections, stable entry IDs, compact evidence references, and no information absent from the JSON profile.

### `playbook-index.json`

Atomic current-generation pointer and manifest containing:

- schema version
- latest successful derivation run
- corpus input fingerprint
- identity registry fingerprint
- review-overlay fingerprint
- rules and threshold version
- profile paths
- affected stakeholder states
- stale or current state
- unresolved identity count

Readers resolve all current profile and briefing paths through the index. They must not infer current state by choosing the newest generation directory.

### `derivation-ledger.jsonl`

Append-only run history containing:

- derivation run ID
- trigger and requested scope
- input fingerprints
- rules, schema, and renderer versions
- provider and model provenance when used
- affected stakeholders
- output paths
- warnings and errors
- status
- recorded time

The derivation ledger is authoritative for playbook derivation history. The source ledger remains authoritative for source ingestion. The ledger is durable reviewed workflow state and therefore lives under `_playbook-state/`, not `_derived/`.

The source ledger may record that a source made derived work pending and may reference a derivation run. It must not receive one corpus-wide derived snapshot per source during every rebuild.

### `overrides.jsonl`

Append-only human decisions that survive rebuild without mutating source observations. Current override state is computed by folding valid events in order, matching the project’s existing ledger conventions and preserving reject, restore, resolve, and later review history.

### Cleanup And Backup Safety

All paths in this section are relative to the project meetings root.

`_derived/` contains rebuildable materializations and may be deleted safely when no derivation is running. Committed generation directories may be retained for audit or pruned under an explicit retention policy when they are not current in the index and are not required to recover the current generation. `_playbook-state/` contains human-reviewed identity, resolution, suppression, and derivation history and must never be deleted by cache or derived-output cleanup tooling.

Project-local meeting storage is ignored by default, so source control is not a backup for `_playbook-state/`. User documentation must recommend including `_playbook-state/` in an approved local or encrypted project backup. `status` and `doctor` report whether the durable state directory, registry, and override ledger exist, but they cannot reconstruct lost human decisions.

## Stakeholder Profile Contract

Illustrative top-level shape:

```json
{
  "schema_version": "1.0",
  "stakeholder": {
    "person_id": "person-kushali-g",
    "display_name": "Kushali G",
    "aliases": ["Kushali", "G, Kushali"],
    "identity_status": "reviewed"
  },
  "generated_at": "2026-07-10T18:00:00Z",
  "input_fingerprint": "...",
  "coverage": {
    "source_count": 7,
    "source_kinds": {"meeting_transcript": 6, "email": 1},
    "first_observed_at": "2026-01-15",
    "last_observed_at": "2026-07-09"
  },
  "tracked_asks": [],
  "tracked_commitments_by_stakeholder": [],
  "tracked_commitments_to_stakeholder": [],
  "priorities": [],
  "concerns_and_risks": [],
  "decision_rationales": [],
  "communication_preferences": [],
  "communication_behaviors": [],
  "interaction_responses": [],
  "patterns": [],
  "guidance": [],
  "recent_changes": [],
  "contradictions": [],
  "unresolved_observations": [],
  "stale_items": []
}
```

The artifact contract must define each entry schema. At minimum, every derived entry needs:

- stable entry ID
- category and statement
- scope
- confidence and confidence rationale
- supporting observation references
- contradicting observation references when applicable
- distinct source-event count
- first and last observed times
- lifecycle state
- review state
- freshness state
- derivation provenance

### Briefing Markdown Shape

Recommended stable sections:

1. Stakeholder identity and evidence coverage
2. Tracked asks
3. Commitments by the stakeholder
4. Commitments to the stakeholder
5. Current priorities
6. Concerns and risks
7. Decision rationale history
8. Explicit communication preferences
9. Observed communication behaviors
10. Interaction responses
11. Communication cues
12. Emerging and established patterns
13. Recent changes
14. Contradictions and cautions
15. Unresolved or low-confidence observations
16. Evidence index

Briefing V1 renders guidance and provider-derived sections with stable headings and an explicit `Not available in Briefing V1` marker. It does not omit the sections. This preserves stable agent parsing and the project’s explicit-empty-section convention across profile versions.

## Ask And Commitment Lifecycle

Absence of closure evidence does not establish that an ask or commitment remains open.

Allowed lifecycle states:

- `unknown`
- `explicitly_outstanding`
- `resolved`
- `withdrawn`
- `superseded`

Only explicit lifecycle evidence or a reviewed override may assign a state other than `unknown`.

Briefings should say:

> Committed on June 12; no evidence of resolution since.

They should not say:

> Open since June 12.

Each tracked item should show:

- observed date
- age
- last lifecycle evidence date
- lifecycle state
- supporting evidence
- resolution source or override when applicable
- stale or verify-before-citing state

Provider-assisted matching may propose lifecycle links between differently worded observations, but uncertain links require review.

## Qualification And Promotion Rules

### Observation To Pattern

A provider-derived pattern normally requires:

- at least two compatible observations
- from at least two distinct source events
- with sufficient confidence
- no unresolved fresher contradiction that invalidates the pattern

One explicit, high-confidence communication preference may qualify as a current preference without being presented as a recurrent pattern.

Weak-inference observations may appear in an unconfirmed section but cannot independently qualify a pattern or guidance.

### Pattern To Guidance

Guidance requires:

- at least one qualified pattern or explicit preference
- supporting evidence references
- scoped applicability
- confidence rationale
- freshness status
- caveat or non-applicability condition
- no unaddressed fresher contradiction

Context-general guidance requires evidence across more than one context. Otherwise the scope must remain narrow.

### Pattern Lifecycle

Candidate lifecycle values:

- `emerging`
- `established`
- `contested`
- `stale`
- `retired`

The artifact contract defines versioned default thresholds and freshness bands. Project config may override permitted values. Every derivation-ledger record stores the effective ruleset version and fingerprint; thresholds must never be undocumented implementation constants.

## Deterministic And Provider-Assisted Boundaries

### Deterministic Work

- schema validation
- identity resolution through reviewed identifiers and aliases
- evidence-reference validation
- exact duplicate detection
- grouping by resolved stakeholder, exact signal type, and explicit tags
- counts, distinct-event counts, first and last observed times
- recency and freshness calculations
- threshold enforcement
- explicit lifecycle and supersession links
- mechanical contradiction candidates based on structured mutually exclusive values
- review-overlay application
- input fingerprinting
- profile materialization and rendering

### Provider-Assisted Work

- semantic equivalence between differently worded observations
- semantic cluster proposals
- contradiction confirmation or discovery
- contextual scope inference
- cross-context applicability judgments
- positive-response pattern synthesis
- communication guidance phrasing

A same-type or same-topic collision is not automatically a contradiction.

Provider judgment may only group, scope, confirm, or phrase deterministically qualified inputs. It may not:

- mint new source facts
- raise source confidence
- remove contradicting evidence
- resurrect observations that failed qualification
- assign reviewed identity
- create guidance without valid evidence references

Provider responses must use a structured request/response contract and pass engine validation before profiles are materialized.

### Evidence Validation Scope

For current meeting signals, deterministic validation can verify evidence shape, required text, timestamp format, and membership in the declared locator scheme. Existing transcript timestamps are not always machine-resolvable addresses, so Briefing V1 must not claim that every meeting excerpt was found again in the source.

Existence validation is required only when the source provides addressable locators such as message IDs, line ranges, document anchors, or image regions. Provider-derived entries must always cite valid input observation references even when the observation’s source excerpt can receive only structural validation.

## Full Rebuild Model

Full deterministic rebuild is authoritative in V1.

Inputs include:

- all eligible validated signal files
- source-exclusion state
- identity registry
- qualification rules and thresholds
- review overlays
- provider-derived candidates when requested
- schema and renderer versions

Benefits:

- deterministic golden tests
- global recurrence and freshness calculations
- retroactive identity correction
- reliable source deletion or exclusion
- no mutation drift from incremental prose patches
- straightforward stale-state detection

Targeted stakeholder refresh is deferred. Full rebuild is the only authoritative update mode in Briefing V1; the current corpus does not justify the additional equivalence and concurrency surface.

## Review And Correction Controls

### Required For Briefing V1

- `reject`: suppress a derived entry while preserving an audit record
- `resolve`: set reviewed lifecycle state for an ask or commitment
- `suppress_signal`: exclude a bad observation from derivation without editing its source JSONL
- identity correction through the registry

### Required For Guidance V1.1

- `accept`: mark guidance as reviewed
- `reject`: suppress the same evidence-backed guidance candidate
- `tombstone`: suppress a concept lineage until explicitly restored

Editing reviewed presentation text may follow after V1.1.

Derived entry identity depends on entry kind:

- A tracked ask or commitment is anchored to its originating observation: stakeholder ID, entry kind, source ID, and signal ID. Later supporting or resolution evidence does not change its entry ID.
- A deterministic single-observation fact uses the same originating-observation rule.
- A deterministic multi-observation rollup anchors to its earliest qualifying observation, using normalized occurrence time and then sorted source/signal reference as the tie-breaker. Later supporting or contradicting observations do not change its entry ID. If the anchor is suppressed, superseded, or disqualified, the rollup remints and orphaned review state is reported with a nearest-successor hint rather than transferred silently.
- A pattern or guidance candidate uses stakeholder ID, entry kind, normalized scope, and the sorted qualifying supporting observation references that formed the candidate.
- Contradicting observation references never participate in lineage identity. New contradiction evidence changes state, confidence, and presentation without erasing the review target.
- Provider wording never participates in lineage identity.

Supporting-set growth may legitimately remint a pattern or guidance candidate. Rebuild and `doctor` must report orphaned review events and provide a nearest-successor hint based on the same stakeholder, entry kind, compatible scope, and overlapping supporting references. The tool must not silently transfer a review decision when the basis changed.

Signal suppression targets the canonical `(source_id, signal_id)` pair. Resolve events target the stable originating-observation lineage for the tracked item.

Review overlays are append-only JSONL events. Rebuild computes current review state by folding valid events and reports malformed, orphaned, or superseded events without deleting history.

## Derivation Workflow

### Briefing V1

1. Discover validated signal files.
2. Normalize schema 1.0 and 1.1 records into the generalized internal model.
3. Apply source and signal exclusions.
4. Resolve stakeholder identities using the reviewed registry.
5. Surface ambiguous and unresolved identities.
6. Validate evidence references and observation identity.
7. Group exact factual observations by stakeholder and structured attributes.
8. Calculate counts, recency, freshness, lifecycle evidence, and qualification state.
9. Apply reviewed lifecycle and rejection overlays.
10. Materialize profile JSON.
11. Render briefing Markdown.
12. Publish profiles, append the derivation-ledger commit record, and rewrite the index in the defined commit order.

### Guidance V1.1

1. Complete deterministic qualification.
2. Create a small derivation request containing qualified observations, structured evidence references, candidate clusters, and candidate contradiction pairs.
3. Obtain structured provider judgment through the configured provider path.
4. Validate that every proposed pattern and guidance item cites eligible inputs.
5. Enforce confidence ceilings, scope requirements, contradiction visibility, and prohibited-inference rules.
6. Apply review overlays.
7. Materialize updated profile JSON and Markdown.
8. Record provider and ruleset provenance in the derivation ledger.

Provider requests should contain the minimum evidence necessary for synthesis rather than complete raw transcripts whenever possible.

### Locking, Two-Phase Synthesis, And Commit Order

Playbook writes use the same project lock discipline as ingest.

Deterministic rebuild is expected to be short and holds the project lock while it:

1. reads the eligible signal, registry, ruleset, and review-overlay fingerprints
2. derives the complete output set
3. writes and verifies a new immutable generation directory without changing the current index
4. appends the successful derivation-ledger record, which is the commit point
5. atomically rewrites `playbook-index.json` to point to the committed generation

Generation outputs written before the ledger commit are uncommitted and must not become current through the index. If the ledger append succeeds but the index rewrite fails, the derivation is committed; `doctor` detects the mismatch, and an explicit repair command can rebuild the index from the ledger and committed generation outputs. A crash before ledger commit leaves an uncommitted generation that `doctor` may report and cleanup may remove; it never replaces the current profiles.

Provider-assisted synthesis uses a two-phase handoff:

1. Phase 1 acquires the project lock, computes the exact input fingerprint, persists a derivation request under `_cache/derivation-requests/`, records the expected response identity, and releases the lock.
2. Provider judgment runs without the project lock.
3. Phase 2 reacquires the lock, verifies the persisted request and response, recomputes the full input fingerprint, and publishes only if the fingerprint still matches.
4. Changed signals, registry state, rules, or review overlays produce a typed recoverable `stale_inputs` result. Phase 2 must not publish guidance against the stale request.

The derivation provider contract must define request and response cleanup, retry, failure, and doctor semantics before Guidance V1.1. Long-running provider work must never hold the project lock.

## CLI And Agent Surfaces

Candidate CLI surface:

```text
meeting-ingest playbook update [--provider none|anthropic|session] [--quality fast|balanced|deep] [--json]
meeting-ingest playbook show <person-id-or-alias> [--format markdown|json]
meeting-ingest playbook brief <person-id-or-alias> [--format markdown|json]
meeting-ingest playbook reject <entry-id> --reason ... [--json]
meeting-ingest playbook resolve <entry-id> --state explicitly_outstanding|resolved|withdrawn|superseded --note ... [--json]
meeting-ingest playbook suppress-signal <source-id> <signal-id> --reason ... [--json]
```

Mutating commands use `--json` for the standard machine-readable run summary. Read commands use `--format markdown|json` for their payload and do not add a second `--json` flag with ambiguous meaning.

Reject and suppress-signal operations require a reason. Resolve requires a lifecycle state and note. Every review event records actor and timestamp. Guidance acceptance needs no reason; later edit and tombstone commands must preserve the same audit metadata.

The artifact contract must freeze exact command names, JSON summaries, output payloads, and errors before implementation.

Recommended cadence:

- Source ingest marks playbook inputs as changed or pending.
- Briefing rebuild is explicit in V1.
- `status` and `doctor` report stale derivation state.
- Agent wrappers may offer to run a deterministic rebuild after ingest.
- Provider-assisted session derivation uses a separate two-phase handoff and must not block primary ingest completion.

The primary read surface should be concise enough to inject into an agent context or scan before a meeting without loading the full evidence corpus.

### Exit Codes

Playbook commands reuse the existing error categories:

- provider failures use exit `5`
- provider-response validation failures use exit `6`
- profile or renderer writes use exit `7`
- derivation-ledger writes use exit `8`
- lock conflicts and `stale_inputs` use exit `10`
- invalid CLI or config uses exit `2`
- otherwise unrecoverable derivation failures use exit `1`

Exit `11` should be reserved and removed from active playbook semantics when the artifact contract is amended. Source ingest no longer runs blocking playbook derivation; an explicitly invoked playbook update is the primary command and reports its real failure category.

Exit `10` summaries must distinguish typed error codes: a lock conflict is retryable after the competing operation completes, while `stale_inputs` requires abandoning the old phase-1 derivation request and starting a fresh phase 1.

## Status And Doctor Behavior

`status --json` should eventually report:

- number of stakeholder profiles
- latest successful derivation run
- current input fingerprint
- derived fingerprint
- current or stale state
- unresolved identity count
- rejected or suppressed entry count
- provider-assisted guidance availability
- failed or pending derivation state

`doctor --json` should check:

- malformed identity registry
- ambiguous aliases
- missing durable playbook-state files when profiles or prior derivation references exist
- missing or malformed signal inputs
- duplicate or invalid observation IDs
- malformed evidence references and, for addressable locator schemes, dangling source locators
- malformed derivation ledger lines
- index and latest-ledger mismatch
- uncommitted or partially written generation directories
- missing profile JSON or Markdown
- profile schema mismatch
- stale input fingerprint
- orphaned review overlays
- suppressed observations that re-emerged under regenerated signal IDs
- provider-derived entries with invalid evidence references
- guidance with structurally invalid review state, scope, caveat, confidence, or citations

Doctor can enforce structural prohibited-inference safeguards but cannot reliably detect every prohibited semantic claim without provider judgment. Semantic trust review remains part of Guidance V1.1 review and adversarial fixtures.

Doctor remains diagnostic by default. Repair commands should be explicit and separately contracted.

## Privacy, Trust, And Safety

### Evidence And Inference

- Every profile fact, pattern, and cue must cite source observations.
- Explicit statements, observable behaviors, and inferred patterns remain visibly distinct.
- Contradictory evidence lowers confidence or changes lifecycle state; it is not silently omitted.
- Absence of evidence is not evidence of a preference, resolution, or response.
- Public self-presentation is not equivalent to private working behavior.

### Prohibited Inferences

The system must not infer or store:

- protected traits
- diagnoses or mental-health claims
- intelligence or competence ratings
- personality types
- hidden motives
- emotional vulnerabilities
- manipulation opportunities
- relationship scores

Guidance should be phrased as communication accommodation:

> Include the mitigation plan because this stakeholder has repeatedly requested risk controls in technical reviews.

It must not be phrased as exploitation:

> Use their fear of failure to secure approval.

### Privacy Boundaries

- Profiles remain under project-local, ignored storage by default.
- Remote meeting-provider permission does not authorize remote email, screenshot, or social processing.
- Source-kind-specific privacy gates must be explicit.
- Deterministic Briefing V1 derivation uses no provider and needs no provider privacy gate.
- Guidance synthesis requires its own explicit, default-false gates: `privacy.allow_remote_playbook_synthesis` for API-backed providers and `privacy.allow_session_playbook_synthesis` for subscription/session-backed providers.
- Meeting extraction permissions do not imply playbook-synthesis permission. A cross-source derivation request is a more concentrated disclosure than any one source.
- Provider-assisted derivation must also exclude any source kind whose evidence is not authorized for the selected provider path.
- Provider requests should minimize excerpts and omit irrelevant source content.
- Profiles should link to evidence rather than reproduce large sensitive excerpts.
- Source deletion or exclusion must remove its influence after rebuild.
- iQ Context integration must not copy complete profile bodies or sensitive evidence by default.

Concentrated stakeholder profiles and briefings may be more sensitive than any one source signal. Access, source-control, sharing, agent-context injection, and capture policies must reflect that concentration risk.

## Testing Strategy

### Contract And Schema Tests

- schema 1.0 compatibility normalization
- schema 1.1 source and timing validation
- source-kind-specific required fields
- raw-label identity resolution and schema 1.0 fallback
- deterministic signal identity
- regeneration, supersession, and within-source collision behavior
- identity-registry parsing and alias collision detection
- observation and evidence validation

### Golden Fixtures

- profile JSON
- briefing Markdown
- empty sections
- unresolved identity
- alias correction and rebuild
- one-source versus two-source qualification
- explicit preference
- repeated communication behavior
- positive interaction response
- weak tone or timing evidence rejected from guidance
- tracked commitment with unknown lifecycle
- reviewed resolution override
- contested and stale pattern

### Determinism And Rebuild Tests

- repeated builds are byte-stable with a frozen clock
- registry edits retroactively merge or split profiles correctly
- excluded source removes all derived influence
- orphaned overrides remain visible
- lineage successor hints appear when pattern evidence changes
- derived failure leaves source ingest state unchanged
- ledger-commit/index-rewrite failure recovers through doctor
- concurrent signal changes produce `stale_inputs` during provider phase 2

### Provider Boundary Tests

- provider cannot cite nonexistent observations
- provider cannot cite suppressed or unqualified observations
- provider cannot raise observation confidence
- provider cannot omit contradicting evidence supplied by validation rules
- guidance without scope or caveat fails validation
- provider failure preserves deterministic briefing output
- session-provider derivation verifies persisted request identity
- synthesis is denied unless its dedicated privacy gate is enabled

### Adversarial Trust Tests

- one terse message does not become a personality claim
- emoji or thanks does not become a positive-response pattern
- rapid response does not become a preference
- unresolved speaker evidence does not attach to a reviewed stakeholder
- social-profile claims do not become private communication preferences
- stale priorities do not render as current without warning

## Implementation Phases

### Phase 0: Contract And Fixtures

- amend the signal and artifact contracts
- freeze schema 1.1 provenance, timing, and signal identity
- freeze identity registry and candidate artifacts
- freeze profile, derivation ledger, index, and review-overlay schemas
- freeze qualification and prohibited-inference rules
- freeze locking, two-phase synthesis, and derivation commit ordering
- reserve playbook-synthesis privacy gates in config
- freeze the Guidance V1.1 approach-tag vocabulary
- supersede the current source-ledger derived-work and in-ingest cadence contracts explicitly
- add manually annotated stakeholder scenarios

Acceptance:

- representative existing signals can be normalized without migration
- weak inference, ambiguity, contradiction, staleness, and lifecycle uncertainty have explicit expected outputs
- contract review finds no conflict about which store is authoritative for source and derived state

### Phase 1: Provenance And Identity Foundation

- implement schema 1.1 tolerant readers and writers
- implement generalized source and timing model
- implement deterministic signal identity for new records
- implement identity registry reader and derivation-time resolver
- produce identity candidates and doctor findings

Acceptance:

- two reviewed aliases resolve to one profile identity
- ambiguous aliases remain unresolved
- old signals remain consumable
- occurrence, acquisition, and processing time remain distinct

### Phase 2: Stakeholder Briefing V1

- implement full deterministic rebuild
- materialize profile JSON and briefing Markdown
- implement derivation ledger and index
- implement explicit update, show, and brief surfaces
- implement stale-state status and doctor checks
- implement reject, resolve, suppress-signal, and identity correction paths

Acceptance:

- every entry cites valid observations
- full rebuild is deterministic
- identity correction requires no signal rewrite
- unknown lifecycle is never presented as open
- new eligible signals make the current index stale
- playbook failure never changes primary ingest success

### Phase 3: Playbook Guidance V1.1

- implement structured derivation provider request and response
- implement semantic clustering, scoped patterns, and contradiction confirmation
- implement positive-response pattern analysis
- implement communication guidance and caveats
- implement accept, reject, and tombstone review controls

Acceptance:

- one weak observation cannot become guidance
- provider output cannot invent or upgrade facts
- every cue has scope, evidence, confidence rationale, and non-applicability guidance
- contradictory evidence remains visible
- failed synthesis leaves deterministic briefing artifacts usable

### Phase 4: Plain-Text Communication Pilot

- add email-body or pasted-message ingest
- preserve sender, recipients, subject, thread boundaries, sent time, acquisition provenance, and privacy class
- produce generalized observations
- rebuild profiles across meeting and email evidence

Acceptance:

- meeting and email evidence remain distinguishable
- both source kinds may support one qualified pattern
- email provider permission is independent from meeting provider permission
- non-meeting outputs do not enter the meeting artifact namespace

### Phase 5: Richer Communication Sources

Implement only after the evidence and review contracts are trusted:

- Teams and text thread exports
- screenshot OCR and region-addressable evidence
- text-message screenshots
- social posts
- social profiles

Each source kind requires its own provenance, privacy, attribution, uncertainty, and evidence-location contract.

Phase 5 must also define communication-event identity so two representations of one event, such as a forwarded email and a screenshot of that email, do not count as two independent events for promotion thresholds.

## Required Contract Supersessions

This design deliberately changes two existing authorities and must not be merged into the roadmap as an additive clarification.

### Source-Ledger Derived Semantics

The current artifact contract places `derived_updated` events and mutable `derived.playbook_update_status` state in the source ledger. That model is superseded because playbook profiles depend on a corpus, identity registry, ruleset, and review overlays rather than one source.

The contract amendment should:

- deprecate `derived_updated` as a source-ledger event
- move successful, failed, and stale playbook derivation history to `_playbook-state/derivation-ledger.jsonl`
- replace new source records’ mutable playbook status with an ingest-time `derived.playbook_input_status` hint using `not_applicable` or `pending`
- treat existing `derived.playbook_update_status` fields as compatibility data only
- remove or deprecate the mirrored `derived.playbook_update_status` field in ingest JSON run summaries and replace it with the same ingest-time input-status semantics
- compute current/stale playbook state from source and signal fingerprints against the derivation ledger and index
- reserve exit `11` rather than use it for blocking derived work

### Update Cadence

The current decision that playbook updates should happen during ingest when possible is superseded for Briefing V1.

The contract amendment should state:

- primary ingest marks playbook inputs pending and completes normally
- deterministic playbook rebuild is an explicit command
- `status` and `doctor` report staleness
- agent wrappers may offer or invoke the explicit rebuild after primary ingest, but the engine does not make it part of ingest completion
- provider-assisted guidance always uses a separate two-phase derivation workflow

### Provider And Skill Contracts

Adding `communication_preference`, `communication_behavior`, and `interaction_response` requires a coordinated amendment to:

- signal schema validation
- provider response payloads
- session-provider request and response contracts
- extraction prompts
- repo-maintained Codex and Claude skill sources
- installed skill copies when user-facing behavior changes

## Roadmap Integration

The current roadmap should be revised after this design is reviewed:

- Layer 1: add effective-date reliability as a prerequisite for trustworthy freshness and response sequencing
- Layer 5A: generalized provenance and identity foundation
- Layer 5B: Stakeholder Briefing V1
- Layer 5C: Playbook Guidance V1.1
- Layer 7A: plain-text communication ingestion
- Layer 7B: image-based communication ingestion
- Layer 7C: public and social-source policy and ingestion

Layer 2 output-mode work remains independently shippable. This design does not require weakening or bypassing the source ingest, archive, ledger, reconcile, provider, or privacy contracts.

## Decisions To Freeze Before Implementation

- observation taxonomy and evidence requirements
- interaction-response schema and causal uncertainty rules
- source provenance and three distinct time semantics
- deterministic signal identity
- identity registry format and derivation-time authority
- profile JSON and briefing Markdown contracts
- derivation ledger and current manifest contracts
- review-overlay history model and stable lineage keys
- durable-state cleanup and backup rules
- locking, commit ordering, and stale-input behavior
- playbook-synthesis privacy gates
- ask and commitment lifecycle language
- qualification, freshness, and prohibited-inference rules
- controlled interaction approach tags
- deterministic and provider-assisted boundary
- Briefing V1 and Guidance V1.1 milestone split
- CLI commands and JSON summaries

## Safe To Defer

- cross-project identity
- group profiles
- cross-representation communication-event identity
- automatic semantic lifecycle closure
- automatic candidate identity promotion
- edited guidance text
- screenshot and OCR contracts
- social-source details
- response-time baselines
- embeddings or SQLite search indexes
- hosted backend
- dashboard or web UI
- fine-grained numeric confidence scoring

## Remaining Contract Parameters

Review resolved the architectural open questions:

- review state is append-only JSONL
- the schema 1.1 source-kind vocabulary is fixed, with source-specific metadata added by phase
- contract defaults may be overridden by project config and are fingerprinted in derivation history
- unavailable Guidance V1.1 sections remain present with an explicit marker
- session synthesis mirrors the persisted-request two-phase provider pattern
- reject and suppress require reasons; resolve requires state and note; all review events record actor and time
- targeted updates are deferred
- source-ledger playbook state becomes an ingest-time input hint; derivation state moves to the playbook ledger

The artifact and provider contracts still need exact values for:

1. source ID, observation ID, and derived-lineage hash inputs, truncation lengths, normalization, and collision suffixes, including the schema 1.0 mapping from `meeting_id` plus source-ledger identity to generalized `source_id`
2. default qualification thresholds and category-specific freshness bands
3. the controlled Guidance V1.1 `approach_tags` vocabulary and free-text escape shape
4. the complete schema 1.1 evidence-locator union and which source kinds support existence validation
5. the derivation request and response payload schemas, cache filenames, cleanup, retry, and failure details
6. the exact profile entry schemas and derivation-ledger record schema
7. review-event actor identity representation and restore semantics
8. temporary/staging paths and recovery behavior for partially published profile sets
9. playbook command JSON summaries and the compatibility treatment of exit `11`
10. required email/document source metadata before Phase 4

## Recommended Next Step

Run a focused follow-up review of the resolved findings. After the design is accepted:

1. amend `DECISIONS.md` for source-ledger authority and explicit rebuild cadence
2. amend the Rolling Stakeholder Playbook, Proposed Communication Signal Schema, and future communication sections of `docs/design-proposal.md` so they no longer compete with this design
3. amend `docs/artifact-contract.md`
4. add the Guidance V1.1 derivation contract to `docs/provider-handoff-contract.md` or a dedicated provider contract
5. amend `docs/implementation-plan.md`
6. amend `docs/product-status.md`
7. update extraction prompts and repo-maintained Codex and Claude skills when the new signal taxonomy becomes user-facing
8. add annotated contract fixtures
9. begin Phase 1 implementation only after the new contracts are frozen
