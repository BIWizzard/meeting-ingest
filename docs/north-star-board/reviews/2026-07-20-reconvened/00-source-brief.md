# Reconvened North Star Review Board Source Brief

Review date: 2026-07-20

Review: reconvened after material owner correction

Repository: `meeting-ingest`

Mode: read-only product-governance review. No implementation, corpus mutation, migration, repair, deletion, roadmap replacement, commit, external-system change, or iQ Context mutation is authorized for independent reviewers.

## Why The Board Was Reconvened

The founding board reviewed the Meeting Ingest repository, its six local meeting artifacts, one recorded external UAT, implementation, tests, documents, and active state. It unanimously judged the engine credible and the low-ceremony experience unproven.

After the board closed, the owner supplied material context that changes the evidence base:

1. The maintainer is the only true power user and also the lead developer.
2. Sustained real use exists in the HTV IQ Data Analytics consumer project for Hearst, not primarily in the Meeting Ingest repository.
3. Spelman contains additional historical output and a known legacy date-inference failure.
4. The six local meeting artifacts are redundant samples drawn from consumer-project work and must not be counted as independent dogfood proof.
5. The power user's accumulated history has not been reconciled into current contracts, health, migration/adoption policy, identity review, or Stakeholder Briefing proof.
6. Even the lead developer cannot determine through the product interface which engine and workflow logic a consumer repository will run before a meeting or whether it needs an update.
7. HTV currently exposes two valid-looking Meeting Ingest executables that can run different code while both identify as version `0.1.0`.

The board is reconvened before milestone planning to determine whether this history and version-certainty evidence changes the verdict, product definition, sequencing, or release gates.

## Exact Review Question

Given that Meeting Ingest has one lead-developer power user, a large real HTV history, a smaller Spelman history, unresolved legacy/current contract divergence, redundant local samples, and no user-visible build certainty, what must the product prove next so that it serves both the next meeting and the accumulated history reliably without requiring the user to understand or audit the machinery?

The board must revisit:

1. What is the real product vision when sustained history, not a single ingest, is considered?
2. Is the target job only processing the next transcript, or maintaining trustworthy meeting continuity over time?
3. What has actually been implemented versus accumulated in consumer projects?
4. What works reliably in sustained power-user use?
5. Where do consumer corpus, implementation, documentation, active state, installed code, and product claims disagree?
6. What should be complete, active, adopted, repaired, deferred, superseded, or retired?
7. Does Just Works Ingest remain the correct next milestone, and if so must it include corpus reckoning and version certainty?
8. What historical-corpus proof is required before Stakeholder Briefing or broader expansion?
9. What must be true before the owner can walk into a meeting knowing which approved logic will run?

## Decision Standard

Use the founding board standard plus these additions:

- The product can identify the exact approved engine and workflow contract that will run.
- A consumer can determine whether it is current for its chosen release channel without inspecting source or installation internals.
- The product distinguishes current-valid, legacy, adoptable, repairable, conflicting, and ignored history.
- Historical adoption is dry-run first and never mutates client corpora without separate approval.
- The product provides useful continuity across accumulated meetings, not only correct processing of the next file.
- Evidence is counted once at its authoritative consumer source; redundant local copies do not inflate dogfood claims.
- Client-sensitive content is not copied into governance artifacts.

## Product Vision And User

The original vision remains to turn `.txt`, `.vtt`, and `.docx` meeting artifacts into durable, structured project knowledge with strong done semantics (`README.md:3-21`). The product is personal-workflow first, host-neutral, trustworthy, and intended to operate through an active agent without forcing the user into raw terminal orchestration (`docs/personal-workflow-scope.md:3-56`).

The owner correction reveals that continuity over time is not a secondary idea. The power user has accumulated a large project history and expects the product to know what has already been processed, which logic produced it, what remains usable, and how that history can support future work.

Proposed job-to-be-done for review:

> Turn each meeting into a trustworthy project record and keep the accumulated meeting history usable, current, and explainable—without requiring the technical owner to audit engine versions, handoff protocols, or legacy storage before the next meeting.

## Founding Board Verdict

The five independent seats unanimously concluded:

- the engine and artifact value are credible;
- the normal agent-operated experience is not independently proven;
- current posture is internal/private alpha;
- one reference host and a Just Works Ingest gate should precede expansion;
- broader Guidance, source, provider, host, migration, identity, and iQ expansion should freeze;
- current public/internal truth must be reconciled.

The founding reports are preserved at `docs/north-star-board/reviews/2026-07-20/`. The reconvened seats must make fresh judgments and must not read one another's new reports.

## Authoritative Dogfood Evidence

### HTV IQ Data Analytics

Consumer root: `/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics`

Meetings root: `/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/_local/project-context/meetings`

This is the primary sustained power-user corpus. `docs/current-output-evaluation.md:5-13` already identified it as the primary reference because it contained sustained real use.

Read-only filesystem inventory on 2026-07-20:

- 190 top-level meeting Markdown files;
- 173 physical source-ledger lines;
- 118 signal JSONL files;
- 118 processed-source files;
- 138 `_inbox/_done` files;
- zero direct inbox files;
- two cached provider requests and three cached provider responses.

Artifact contract markers:

- 40 Markdown files contain a `meeting_id` field;
- 37 contain the current transcript boundary marker;
- 37 declare artifact schema 1.0.

Current engine `status --json`:

- 38 recognized sources;
- 92 valid ledger records;
- signal contract invalid with 81 legacy signal issues;
- two stale handoffs;
- 31 identity candidates, zero reviewed people;
- no current Stakeholder Briefing generation.

Current engine `doctor --json`:

- 179 issues total;
- 81 invalid legacy ledger records;
- 81 invalid legacy signal records;
- 12 low-confidence meeting dates;
- two stale session handoffs;
- one stale provider response;
- one missing artifact;
- one missing playbook state issue.

The project is configured for session extraction with the remote provider disabled. No client transcript content was copied into this brief.

### Spelman

Consumer root: `/Users/kmgdev/dev_projects/spelman`

Meetings root: `/Users/kmgdev/dev_projects/spelman/_local/project-context/meetings`

Read-only inventory:

- two top-level meeting Markdown files;
- one ledger line;
- one signal file;
- one processed source;
- one `_inbox/_done` file;
- no active handoff files.

The current engine returns `config_not_found`; the corpus is historical and not initialized as a current consumer.

The Spelman meeting is important quality evidence: its actual date appeared in file content, but the legacy inference path minted the wrong date (`docs/sessions/2026-07-03-design-reviews.md:48`).

## Redundant Local Corpus Exclusion

The Meeting Ingest repository contains an ignored local runtime corpus with six Markdown artifacts, twelve ledger snapshots, six signals, six processed copies, and six `_done` sources.

The owner states these were plucked from HTV/Spelman work and should be removed and not referenced as independent samples. Hash inspection confirms four of the six source hashes appear in the HTV ledger; the other two do not match current HTV/Spelman ledger hashes and may reflect legacy or copied variants. Their exact basenames do not match consumer artifact basenames.

Board treatment:

- exclude all six from dogfood counts and product-proof claims;
- treat the authoritative consumer corpora as the evidence source;
- preserve the founding board's historical reports but mark their six-meeting evidence assumption superseded;
- do not delete individual local files because they form one ledger/artifact/signal/archive/done state;
- decide whether to remove the entire ignored local runtime set after this review, using a complete-state cleanup rather than piecemeal deletion.

## Current Implementation And Test Evidence

The core implementation evidence from the founding brief remains valid:

- init, config/path discovery, hashing, IDs, locking, typed errors, JSON summaries;
- deterministic `.txt`, `.vtt`, and `.docx` extraction;
- provider validation and mock/Anthropic/session boundaries;
- summary-plus-verbatim rendering and signal JSONL;
- append-only ledger, archive, reconcile, duplicate/no-op repair;
- effective-date override, warning, and repair;
- session handoff binding, embedded response schema, preflight validation, resume-safe scanning;
- Layer 5A generalized provenance/identity and most deterministic Layer 5B mechanics;
- 231 passing repository tests on 2026-07-20.

These tests prove deterministic contracts and failure behavior. They do not prove current consumer-version certainty, legacy adoption, or historical continuity.

## Distribution And Version-Certainty Evidence

### Global frozen tool

- normal command resolution in Meeting Ingest, HTV, and Spelman points to `/Users/kmgdev/.local/bin/meeting-ingest`;
- this is a frozen uv tool installation;
- `uv tool list` reports `meeting-ingest v0.1.0`;
- `meeting-ingest --version` is not implemented;
- the install receipt records the Meeting Ingest source directory but no git revision/build identity;
- the package version in `pyproject.toml` remains `0.1.0` across many implementation commits.

Repository-local git hooks reinstall the global tool after commits and merges on `main` in this clone (`scripts/git-hooks/refresh-global-tool.sh`). They do not fetch remote changes, prove that `main` is current, run from consumer repositories, or expose freshness through the product.

At review time, expert hash comparison verified all 33 installed Python files matched committed `main` at `3bc917de8c6072239848ed190c4c45889d6cf227`. Installed Codex and Claude skills also matched repository copies. This required filesystem, git, and hashing knowledge and is not a product capability.

### HTV repository-local tool

HTV also contains `/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/.venv/bin/meeting-ingest`.

That installation is editable and points directly to `/Users/kmgdev/dev_projects/meeting-ingest/src`. It therefore runs the current working tree, including uncommitted code, when invoked explicitly or when the HTV virtual environment is activated.

The global frozen command runs committed `main`; the HTV editable command runs the dirty working tree. Both identify as `0.1.0`, and neither reports a revision.

Consequences:

- command selection can change behavior based on PATH or activation state;
- the lead developer cannot use the product itself to know which logic will process tomorrow's meeting;
- a consumer run summary/artifact does not record an engine revision sufficient to reconstruct that choice;
- automatic refresh can succeed or fail outside the consumer's view;
- engine and installed skill compatibility is not checked by consumer preflight.

## Current Workflow Reality

The active-agent session path remains multi-stage internally. The skill hides some of it, but the user must trust that the host selected the intended executable, compatible skill, current provider contract, and correct configuration.

The product can currently report project status but not distribution status. It cannot answer:

- Which executable will run?
- Is it frozen or editable?
- Which commit/build does it contain?
- Is it current for the selected channel?
- Does the installed skill match the engine contract?
- Was the prior meeting processed with the same logic?
- Is an update required before client work?

## Work Classification

### Complete

- Core deterministic ingest engine and strong done-process mechanics.
- Current provider-response contract remediation and validation.
- Effective-date warning/override/repair foundation.
- Layer 5A and most Layer 5B deterministic mechanics.
- Sustained power-user use exists in HTV, although much of it is legacy-contract history.

### Active

- Uncommitted Layer 5B cleanup/corruption-recovery carryover.
- North Star board reconvening.
- Owner-directed correction of evidence hierarchy.

### Planned or proposed

- One-host Just Works experience.
- Read-only corpus scan/adoption report.
- Version/build/preflight/update certainty.
- Output modes/repair integrity and demonstrated Stakeholder Briefing.

### Absorbed

- Historical Hearst/Spelman migration questions are now part of product validation, not merely late roadmap housekeeping.
- Distribution mechanics exist through global uv tooling and hooks, but not yet as a user-verifiable product outcome.

### Deferred

- In-place corpus mutation/backfill until a reviewed dry-run report.
- Guidance V1.1, broader sources/providers/hosts, global identity, public launch, deeper iQ integration.

### Superseded

- Six local copies as independent dogfood evidence.
- Package version `0.1.0` alone as meaningful build identity.
- Automatic reinstall hooks as sufficient freshness proof.

### Retire or remove, pending review disposition

- The complete ignored six-meeting local runtime corpus, if no unique evidence depends on it.
- Editable consumer installs as an undocumented normal operating mode.

## Truth And Trust Drift

- Founding review counted six local copies as dogfood; authoritative evidence is the HTV/Spelman consumer history.
- HTV has 173 physical ledger lines but only 92 current-valid records.
- HTV has 118 signal files but 81 current-contract-invalid legacy signal files.
- HTV has 190 top-level Markdown files but only 37 current schema/transcript-marker artifacts.
- Current product status does not account for this accumulated real-use divergence.
- Layer 6 corpus adoption was deferred, but the power user's core continuity depends on resolving its stance.
- Global and editable executables can run different code under one static version.
- Installed engine/skill state currently matches committed sources only by expert out-of-band verification.
- Run summaries and artifacts do not provide enough engine-build provenance for tomorrow-meeting certainty.

## Known Trust Gaps To Rejudge

- Pending provider work can appear success-class.
- `doctor` mixes corruption, legacy incompatibility, optional playbook absence, and advisory dates.
- Three config keys are exposed but unused.
- Known write/ledger boundaries can leave orphans.
- Stale locks and handoffs require filesystem expertise.
- Provider scalar/front-matter hardening is incomplete.
- Historical adoption rules are designed but not implemented or exercised.
- Version, update, channel, and engine-skill compatibility are not product-visible.
- The only power user's deep history has not produced a current briefing or reviewed identity registry.

## Privacy And Review Boundaries

- Review filesystem structure, metadata, status, counts, contracts, and representative artifact shape only.
- Do not quote client transcript content, names, decisions, or business details in reports.
- Do not write to HTV or Spelman.
- Do not run ingest, repair, reconcile, cleanup, playbook update, or migration commands in consumer projects.
- Do not delete the redundant local corpus during the independent review.
- Do not update iQ Context from a review seat.

## Questions For The Reconvened Board

1. Does the original one-meeting vision need to become an accumulated-continuity vision?
2. Is corpus reckoning part of Just Works or a separate prerequisite/milestone?
3. Should the product first prove fresh external use, historical power-user continuity, or both in one gate?
4. What is the correct release/update channel for the only current power user?
5. Should consumer projects pin approved immutable builds rather than track `main`?
6. What version/build provenance belongs in CLI output, run summaries, artifacts, and ledgers?
7. Should editable installs be prohibited, labeled development-only, or made unmistakable?
8. What qualifies legacy HTV/Spelman evidence for current Stakeholder Briefing?
9. Should the redundant six-meeting local runtime corpus be removed completely?
10. What must the owner see before tomorrow's meeting to trust the selected engine and history?

## Repository Status At Reconvening

Branch: `main`, committed HEAD `3bc917d`, aligned with `origin/main` at the review start.

The worktree remains dirty with pre-existing uncommitted Layer 5B implementation/tests/contracts, iQ Context state, the founding North Star review package, owner addendum, and this reconvened package. No independent seat may modify it.

## Required Independent Report Structure

Each seat must return findings only, with file/line references where practical and without client-sensitive content:

1. Verdict
2. What the new evidence changes
3. Evidence
4. What is working
5. Gaps and risks
6. Recommendations in priority order
7. What to stop, defer, retire, or simplify
8. Release decision
9. Confidence and unresolved questions

Each seat must state explicitly whether it keeps, revises, or replaces the founding verdict and milestone recommendation.
