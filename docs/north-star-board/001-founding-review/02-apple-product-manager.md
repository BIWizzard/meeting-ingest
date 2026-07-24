# Apple Product Manager Seat

## 1. Verdict

Meeting Ingest has demonstrated a valuable and unusually disciplined ingestion engine, but it has not demonstrated the intended product experience.

A defensible current definition is:

> Meeting Ingest turns `.txt`, `.vtt`, and `.docx` transcripts into inspectable meeting records, signals, provenance, archives, and ledger state for a technical owner working through an agentic coding harness.

That is narrower than the public platform-agnostic positioning and the intended experience of simply asking an agent to process the inbox (`README.md:3-21`; `docs/session-provider-inbox-agent-workflow.md:5-11`).

The central finding is a sequencing error. The roadmap advanced deeply into Stakeholder Briefing before proving that a fresh intended user can complete the primary workflow without understanding provider envelopes, response schemas, cache handoffs, or recovery internals. Layer 5 value remains plausible rather than demonstrated: live state has no reviewed people or current playbook, and no post-remediation external UAT is recorded.

The right posture is internal dogfood alpha. The next milestone should be a bounded **Just Works Ingest** proof on one selected host.

## 2. Evidence

### Product, user, and job

The scope is personal-workflow first, host-neutral, frequent-use fast, trustworthy, configurable without heaviness, and easy to initialize (`docs/personal-workflow-scope.md:3-20`). Normal use should happen inside an active harness (`docs/personal-workflow-scope.md:39-56`).

Interpretation: the primary job is not running a transcript CLI. It is turning a meeting into durable, trustworthy knowledge without interrupting the user's existing work.

### Demonstrated value

Six real artifacts across all supported formats contain summaries, decisions, actions, risks, evidence, provenance, transcripts, signals, archives, and ledger records. Both Codex and Claude Code hosts appear in their provenance.

The pipeline writes signals and Markdown, records primary readiness, archives/reconciles, records completion, and returns paths and date evidence (`src/meeting_ingest/pipeline.py:777-946`). Tests cover failure boundaries, retry, repair, duplicates, handoffs, and provider validation (`tests/test_pipeline_ingest.py:379-580`, `tests/test_pipeline_ingest.py:722-877`).

No issue was found with the usefulness or inspectability of sampled generated artifacts.

### Experience not yet demonstrated

Plain CLI stops at `pending_provider_response`; an active agent must read a request, produce the envelope, validate it, and invoke phase two (`docs/session-provider-inbox-agent-workflow.md:36-179`). The first external UAT required four failed attempts and source inspection. The response contract was improved afterward, but no independent post-fix proof exists.

### Work accounting

| Classification | Assessment |
| --- | --- |
| Complete | Initialization, three extractors, deterministic identity, summary-plus-verbatim, signals, ledger, archive/reconcile, duplicate repair, date repair, providers, handoff validation, status/doctor, and broad tests. |
| Active | Uncommitted Layer 5B cleanup/corruption recovery and this review. |
| Planned | Contradiction candidates, Guidance V1.1, corpus adoption, broader sources, deeper iQ integration, production host adapters, and remote-provider posture. |
| Absorbed | Sub-agent operation into session handoffs; iQ integration into instructions and capture protocol. |
| Deferred | Global identity, targeted rebuilds, extra providers, migration, stale-handoff cleanup, title repair, regeneration, and non-meeting sources. |
| Superseded | Legacy skill architecture, source-ledger playbook authority, and CodeRabbit workflow. |
| Abandoned or cancelled | No explicit product cancellation. |

### Roadmap and truth drift

The original milestones correctly built foundations through the session provider (`docs/implementation-plan.md:492-617`). Later roadmap layers put V1 polish, modes, host productization, and provider hardening before Stakeholder Briefing (`docs/implementation-plan.md:647-664`).

Current status contradicts itself: it first says Layer 5 code has not shipped, later lists 5A/5B as implemented, recommends already-completed work, and cites 133 tests rather than 231 (`docs/product-status.md:26-37`, `docs/product-status.md:315-366`, `docs/product-status.md:433-464`).

README direction presents multiple modes, but the pipeline always renders summary-plus-verbatim (`README.md:36-46`; `src/meeting_ingest/pipeline.py:819-840`).

### Distribution and onboarding

Packaging mechanics are clean: Python 3.11+, no runtime dependencies, console entry point (`pyproject.toml:5-17`). The release channel, support promise, first-run configuration, and canonical workflow are not productized. Default init selects `mock`, while the intended personal workflow requires `session` and explicit consent (`src/meeting_ingest/config.py:42-83`).

## 3. What is working

- The product solves a real problem and produces reusable work products.
- Strong done semantics are engine-owned (`DECISIONS.md:29-40`; `src/meeting_ingest/pipeline.py:777-946`).
- Content-hash idempotency and recovery behavior are demonstrated by tests and UAT.
- All three supported formats appear in real dogfood.
- Provider boundaries converge on one completion path.
- The response-contract remediation directly addresses the external UAT failure (`README.md:185-226`).
- Artifacts are human-readable, agent-readable, stable, and inspectable.
- The foundation is strong enough for a focused product-proof milestone without architectural reinvention.

## 4. Gaps and risks

1. No post-remediation proof shows the intended workflow working for a fresh user without source inspection.
2. Layer 5 breadth outran the job-to-be-done proof.
3. Public, internal, package, and operational definitions do not form one release promise.
4. Initialization defaults conflict with the intended personal workflow.
5. Output-mode labels can disagree with resulting behavior.
6. Three of six dogfood dates remain low-confidence; `doctor` turns advisory uncertainty into failing posture.
7. Stale-handoff recovery still exposes manual filesystem ceremony.
8. Stakeholder Briefing is technically present but not demonstrated as user value.
9. Current-state documents represent different moments and are unreliable for planning.
10. Version `0.1.0` has no defined audience boundary.

## 5. Recommendations in priority order

1. Adopt a single **Just Works Ingest** milestone.

   Exit gates:

   - fresh-project initialization and first real meeting through one reference host;
   - at least three trials by an operator other than the primary author;
   - all three formats across at least six real or safely shareable sources;
   - no source inspection, hand-authored envelopes, or undocumented deletion;
   - every success produces Markdown, signals, archive, completed reconcile, and iQ capture where protocol requires it;
   - low-confidence dates require confirmation or explicit acceptance;
   - duplicate, interruption, invalid response, and stale-handoff recovery succeed without hand-editing durable artifacts;
   - post-trial `status` is healthy and `doctor` separates blockers from advisories.

2. Choose and state the supported 0.1 audience and reference host. Recommended: maintainer and similarly technical owners using one named agent host.
3. Reconcile product truth before changing the roadmap. Separate committed/released, uncommitted, demonstrated, test-only, planned, and deferred.
4. Narrow claims: one current output mode, no general self-service claim, and Stakeholder Briefing implemented but unproven.
5. Make one coherent first-run experience with clear consent, one command style, and next actions.
6. Close bounded trust gaps: doctor severity, stale-handoff cleanup, unresolved local dates, and slug behavior.
7. After the core proof, either implement explicit modes and regeneration or remove them from the supported interface.
8. Then prove Stakeholder Briefing in a real pre-interaction task before Guidance V1.1.
9. Reconvene at milestone exit.

## 6. What to stop, defer, or simplify

Stop:

- treating technical Layer 5 completion as shipped stakeholder value;
- extending the roadmap from stale status text;
- presenting aspirational modes as current;
- implying broad host support before one host passes the suite.

Defer:

- Guidance V1.1, extra providers, broader sources, richer iQ integration, migration, global identity, and semantic interpretation;
- mode expansion until the reference path passes, unless the interface is first narrowed.

Simplify:

- immediate roadmap to **Just Works Ingest**, **Explicit Output Integrity**, and **Proven Stakeholder Briefing**;
- one canonical user surface, with lower-level handoff commands treated as integration/recovery APIs;
- blocker/advisory health separation;
- summary-plus-verbatim as the sole supported default until alternatives work.

## 7. Release decision

No general release and no just-works claim. Continue as a bounded **0.1 internal alpha**.

A defensible claim is:

> Meeting Ingest reliably produces structured, inspectable meeting artifacts through an expert-operated agent workflow, with strong provenance, idempotency, and recovery mechanics.

General self-service, effortless first run, production support across all named hosts, alternate modes, demonstrated Stakeholder Briefing, and no-expert-intervention claims are unsupported.

The uncommitted cleanup slice may finish its existing review as bounded reliability work, but must not reopen Layer 5 expansion without owner approval.

## 8. Confidence and unresolved questions

Confidence is high on the verdict and sequencing; medium on exact trial thresholds.

Human judgment is required on:

1. first supported host;
2. intended 0.1 audience;
3. date warning completion policy;
4. whether alternate modes remain near-term commitments;
5. whether the cleanup slice is accepted as bounded completion;
6. minimum proof for Stakeholder Briefing;
7. whether stale-handoff cleanup and slug quality are core-gate items;
8. whether init or the host wrapper owns session setup.
