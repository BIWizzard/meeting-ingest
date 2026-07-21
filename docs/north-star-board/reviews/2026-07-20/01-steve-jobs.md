# Steve Jobs Seat

## 1. Verdict

Meeting Ingest has a clear soul, but it is not yet a coherent product experience.

Its essence is strong: give it a raw meeting transcript and receive useful, durable project knowledge while validation, provenance, deduplication, archive, and recovery disappear. That promise is visible in `README.md:3-21`, `README.md:48-55`, and `docs/personal-workflow-scope.md:39-56`.

The engine increasingly fulfills the trustworthy half of the promise. The experience does not fulfill the simple half. The primary workflow still exposes provider selection, privacy gates, request and response envelopes, validation, phase-two completion, status diagnosis, and a separate iQ Context capture.

Interpretation: development moved into a sophisticated stakeholder briefing system before the core act—ingest this meeting—was proven effortless for a fresh intended user. That is a loss of focus, not a lack of engineering quality.

The smallest correct next milestone is a **One Meeting Just Works** proof: one supported host, one obvious invocation, one real transcript, one useful artifact, safe retry and recovery, and no requirement that the user understand the handoff protocol.

## 2. Evidence

- The original proposition is one sentence: raw `.docx`, `.txt`, and `.vtt` meeting artifacts become durable structured project knowledge (`README.md:3-21`).
- The intended user is a technical owner already working in an agentic harness. Normal use was supposed to happen inside that harness without returning to a terminal or understanding orchestration (`docs/personal-workflow-scope.md:22-56`; `DECISIONS.md:103-115`).
- The core is substantial: initialization, all three advertised extractors, IDs, locking, typed errors, validated provider output, summary-plus-verbatim rendering, signals, ledger, archive, reconcile, duplicate/no-op recovery, session handoffs, and date repair (`docs/product-status.md:93-220`).
- A real artifact has a scannable title, summary, attendees, topics, decisions, actions, asks, risks, evidence, signals, questions, provenance, and transcript (`_local/project-context/meetings/2026-07-03-wide-orbit-orchestration-and-uat-readiness-working-session.md:1-132`). No issue was found with the usefulness or inspectability of that structure.
- Six real meetings across `.docx`, `.vtt`, and `.txt` completed the full artifact/signal/archive/ledger path (`00-source-brief.md`, Real-World Dogfooding Evidence).
- External UAT proved failure atomicity and safe retry, but also required source inspection and four invalid phase-two attempts. The response contract was improved afterward, but no post-fix external UAT proves closure (`.iq-context/workstreams/default/captures.jsonl`, capture `cap_20260718T220148Z_a28fa2b4`).
- The session workflow remains multi-stage and contradicts the intended experience of simply asking the active agent to ingest a meeting (`docs/personal-workflow-scope.md:41-53`; `docs/session-provider-inbox-agent-workflow.md`).
- Initialized projects default to `mock` and disable session extraction, while the real personal workflow requires `session` plus its privacy gate (`src/meeting_ingest/config.py:41-83`; `_local/project-context/meetings/meeting-ingest.toml:1-21`).
- CLI help exposes many commands without explaining the primary journey (`src/meeting_ingest/cli.py:17-125`).
- Product truth is split inside `docs/product-status.md`: the opening says Layer 5 code has not shipped, later sections say most of it is implemented, the next slice repeats completed work, and validation still cites 133 tests instead of 231 (`docs/product-status.md:26-37`, `docs/product-status.md:315-366`, `docs/product-status.md:433-464`).

Work classification:

- **Complete:** deterministic ingest engine, one combined mode, supported extractors, done semantics, provider validation, session handoffs, date repair, generalized signals, identity foundation, and most deterministic briefing mechanics.
- **Active:** uncommitted cleanup/corruption recovery and North Star governance.
- **Planned:** contradiction candidates, Guidance V1.1, corpus adoption, broader sources, deeper iQ integration, and production host adapters.
- **Absorbed:** sub-agent operation into the session handoff protocol; iQ integration into instructions and post-ingest capture.
- **Deferred:** alternate modes, title repair, regeneration, stale-handoff cleanup, extra providers, migration, and non-meeting sources.
- **Superseded:** legacy Claude skill architecture, source-ledger playbook authority, and CodeRabbit review automation.
- **Abandoned or cancelled:** no product capability is explicitly cancelled; only retired review process is recorded.

## 3. What is working

- The best output is excellent. It is a project operating artifact, not merely a summary.
- The strong done process is real and engine-owned (`DECISIONS.md:29-40`, `DECISIONS.md:223-227`).
- Retry and duplicate behavior protect trust through content-hash identity, success-class no-op, and incomplete archive/reconcile repair (`DECISIONS.md:42-44`, `DECISIONS.md:205-235`).
- The three-format boundary is coherent and appropriately narrow. No focus issue was found there.
- Providers remain replaceable and cannot bypass validation or completion semantics (`DECISIONS.md:46-64`).
- Privacy gates and provider provenance are appropriate. No issue was found with explicit consent.
- The 231-test suite is broad and fast. No correctness defect was found in the examined deterministic core.
- Stakeholder guidance design appropriately requires evidence, uncertainty, review, and non-manipulative boundaries (`DECISIONS.md:133-141`, `DECISIONS.md:181-203`).

## 4. Gaps and risks

- The primary workflow is not obvious. `ingest`, `ingest-inbox`, `session-inbox`, `provider-request`, `validate-response`, and phase-two `ingest` expose mechanism rather than outcome.
- The default first run can succeed with `mock` without demonstrating real product value.
- Complexity moved into documentation instead of disappearing; the response-envelope protocol precedes a clean first-real-meeting journey (`README.md:170-236`).
- The product has two identities: broad platform-agnostic tool and narrow technical agent-operated engine. Only the latter is demonstrated.
- Product development outran proof. Playbook machinery is extensive, while live state has no current playbook, no reviewed people, and zero profiles.
- The roadmap no longer functions as a decision instrument because it describes completed work as next work.
- Claims exceed implementation for output modes. The immediate answer is to narrow the claim, not automatically add scope.
- Three of six dogfood artifacts retain low-confidence mtime dates. Warning and repair are good, but chronology remains unresolved.
- `doctor` makes advisory dates and absent optional playbook state look like a broken project.
- Distribution is an internal operational arrangement, not a release experience.
- No post-remediation proof shows a fresh user completing the intended workflow without expert intervention.

## 5. Recommendations in priority order

1. Define the product in one sentence: **Meeting Ingest turns a meeting transcript into a trustworthy project record—summary, decisions, actions, evidence, and archive—in one request.**
2. Establish One Meeting Just Works before roadmap expansion. Select one canonical host and make the multi-step engine disappear behind one request.
3. Make first run honest and useful. Provide one short path from installation and consent to a real session-backed meeting; do not let mock masquerade as the demonstration.
4. Run fresh-consumer UAT after the response-contract fix across real supported formats, including interruption, invalid response, duplicate, and archive/reconcile recovery.
5. Make completion unmistakable: foreground title, effective date/confidence, artifact, decisions/actions, archive/reconcile, and one next action.
6. Reconcile README, status, roadmap, CLI language, package positioning, questions, and iQ state after owner approval.
7. Separate blocking health failures, recoverable incomplete work, and advisories.
8. After the core gate, choose either output integrity or demonstrated Stakeholder Briefing based on observed demand; do not advance both.

## 6. What to stop, defer, or simplify

- Stop Playbook Guidance V1.1 until deterministic briefing has live reviewed use.
- Defer additional sources, OCR, social inputs, migration, global identity, extra providers, deeper iQ integration, and more hosts.
- Allow already-started integrity-critical Layer 5 cleanup to finish review, but do not use it as a bridge to more Layer 5 scope.
- Defer extra modes until the default path is proven; narrow the public claim now.
- Make one command or agent request own normal session ingestion. Keep handoff commands as expert/recovery surfaces.
- Lead with the useful record, not platform, provider, schema, derivation, or host-neutral language.
- Do not call implemented mechanics a product capability until the outcome is demonstrated.

## 7. Release decision

Do not release Meeting Ingest as a general self-serve product and do not claim that it just works.

Approve it as an internal alpha or maintainer-grade technical preview. The engine, artifact quality, done semantics, and recovery foundations are credible. Wrapper experience, onboarding, current-state coherence, and fresh-user proof are not.

Release gate:

- one canonical host and invocation;
- fresh documented initialization;
- one real supported meeting without source inspection, envelope hand-editing, or raw phase orchestration by the user;
- useful artifact and signals;
- completed ledger/archive/reconcile;
- safe duplicate no-op;
- clear interruption and invalid-response recovery;
- explicit, repairable date confidence;
- blocker/advisory health distinction;
- post-fix UAT across supported formats;
- one truthful definition across README, CLI, roadmap, status, package, and active state.

## 8. Confidence and unresolved questions

Confidence is high in the product judgment and medium-high in the release judgment. Architecture, deterministic behavior, artifact quality, and dogfooding are well evidenced; wrapper experience lacks post-fix independent proof.

Unresolved questions:

- Which host is the first canonical experience?
- Is the release for only the maintainer, technical collaborators, or external self-serve users?
- Should init or the host skill guide session-provider consent and configuration?
- Should unresolved low-confidence chronology block healthy status?
- Is the cleanup slice observed-risk closure or defensive depth?
- After the core gate, should usage drive output modes or Stakeholder Briefing first?
- Recommended definition of no expert intervention: a first-time technical user follows one path and never reads source code or edits protocol JSON.

## Post-Board Owner Extension: Version Certainty

This section was added after the independent seat completed its report. It records owner evidence that sharpens, but does not retroactively alter, the original judgment.

The maintainer is both lead developer and the only true power user. Even with deeper machinery knowledge than any intended user should need, the maintainer cannot answer before a meeting whether a consumer project will run the latest approved Meeting Ingest logic or needs an update.

That is a Jobs-level product failure because the product has not made its own identity disappear. The user should never have to wonder which Meeting Ingest will show up tomorrow.

Current evidence:

- the global frozen tool reports only package version `0.1.0` through `uv tool list`;
- `meeting-ingest --version` does not exist;
- package version remains `0.1.0` across many implementation commits;
- the uv installation receipt records the local source directory but not a git revision or build identity;
- post-commit and post-merge hooks reinstall the tool when `main` moves in this one clone, but do not fetch remote changes and do not prove freshness from a consumer repository;
- consumer projects have no built-in command to report installed revision, release channel, source revision, skill revision, or whether an update is available;
- at review time, direct hash verification confirmed all 33 installed Python source files matched committed `main` at `3bc917de8c6072239848ed190c4c45889d6cf227`, and installed Codex/Claude skills matched their repository copies—but this required expert filesystem and git inspection unavailable in the product.

The required experience is simple:

> Before processing a meeting, the host and user can see exactly which approved Meeting Ingest build and workflow contract will run, whether it is current for the selected channel, and the one safe action required to update it.

Version certainty belongs in Just Works Ingest. It is not release ceremony. It is part of trust.

Required product outcomes:

1. `meeting-ingest --version` reports semantic version, build/revision identity, and release channel.
2. A read-only preflight reports engine version, installed skill/contract version, configuration schema, consumer project root, provider posture, and whether the components are compatible.
3. Consumer documentation defines one update command and whether it tracks a pinned release, approved `main`, or another channel.
4. Consumer projects can detect stale or incompatible engine/skill combinations without reaching into the source repository.
5. Meeting artifacts and run summaries record enough engine/contract provenance to determine afterward which logic processed the meeting.
6. Automatic refresh is never the only freshness guarantee; it is observable, verifiable, and fails loudly enough to preserve trust.
