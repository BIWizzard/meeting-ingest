# Apple Developer Seat

## 1. Verdict

**Revise the founding verdict and milestone recommendation.**

The engine remains credible, the normal agent-operated experience remains unproven, and release posture remains internal/private alpha. Meeting Ingest's real job is to produce a trustworthy next-meeting record while keeping history usable, attributable, and recoverable without installation, repository, ledger, or cache inspection.

Revise **Just Works Ingest** into **Just Works Continuity** with inseparable pre-meeting build certainty and read-only historical reckoning. Today the product reduces transcript labor but still makes the owner compensate with PATH awareness, JSON inspection, manual configuration, handoff management, and corpus auditing.

## 2. What The New Evidence Changes

HTV replaces the copied six as authoritative dogfood, strengthening value proof while exposing weak continuity proof (`00-source-brief.md:90-122`). Historical adoption cannot remain an unstarted late layer (`docs/product-status.md:377-386`). Frozen and editable executables that both say `0.1.0` make distribution a user-facing release blocker (`00-source-brief.md:175-204`).

The gate must keep one reference host, add immutable build/update/skill certainty, add read-only HTV/Spelman classification, and prove both a fresh meeting and accumulated continuity.

## 3. Evidence

- Static package version and no CLI build, channel, update, readiness, or corpus-scan surface (`pyproject.toml:5-17`, `src/meeting_ingest/cli.py:17-125`).
- Hooks are local, branch-dependent, non-fetching, and invisible to consumers (`scripts/git-hooks/refresh-global-tool.sh:1-12`).
- Artifacts, run summaries, and ledgers omit immutable engine/workflow identity (`src/meeting_ingest/render.py:11-28`, `src/meeting_ingest/run_summary.py:9-50`, `src/meeting_ingest/ledger.py:14-47`).
- Session inbox can call an all-pending result `success` (`src/meeting_ingest/session_inbox.py:148-180`).
- Plain output omits pending counts, warnings, artifact paths, recovery, and build identity (`src/meeting_ingest/cli.py:225-248`).
- Stale-handoff guidance requires lower-level commands or manual file deletion (`src/meeting_ingest/session_handoffs.py:114-157`).
- `doctor` detects useful conditions but mixes operational consequences (`src/meeting_ingest/doctor.py:54-117`).
- Init safely defaults to mock and disabled session use, after which instructions require manual edits (`src/meeting_ingest/config.py:42-83`, `docs/session-provider-inbox-agent-workflow.md:21-35`).
- README onboarding is development-oriented and lacks a canonical consumer install, update, pin, or verification route (`README.md:97-139`).

## 4. What Is Working

- HTV proves repeated artifact value at scale.
- Engine ownership of extraction, validation, rendering, signals, ledger, archive, and reconcile is correct.
- Request binding and side-effect-free response validation are strong recovery foundations.
- The wrapper resumes existing requests and avoids duplicate reminting.
- Project privacy configuration matches the intended session workflow.
- Hashes, IDs, append-only ledgers, duplicate handling, date override, archive, and reconcile support safe adoption.
- Status and doctor already expose underlying signals that can power a better readiness experience.
- The target interaction—“process the inbox” in the active host—is correct.

## 5. Gaps And Risks

There is no canonical install or update story, no product answer to “Am I ready?”, and no provenance explaining what ran. Pending success and thin human output force the skill to construct the experience from JSON. Initialization does not guide the intended profile. Recovery ownership is inconsistent, including unsafe manual deletion advice. Health does not distinguish next-meeting safety from historical work. The corpus cannot classify legacy/current/repair/conflict state, and static versioning plus duplicated skill instructions increase maintenance risk.

## 6. Recommendations In Priority Order

1. Add one read-only readiness surface reporting executable, frozen/editable mode, immutable build, dirty state, channel freshness, contract compatibility, privacy/config, and blocking versus advisory health as `ready`, `ready_with_history_warnings`, or `not_ready`.
2. Choose one immutable power-user channel and pin it in consumer metadata; fail client readiness for editable mode unless explicitly overridden.
3. Carry engine, build, channel, install kind, provider contract, and skill contract through every trust surface.
4. Make pending state honest and make plain output report completion, paths, remaining work, and one safe next action.
5. Add a side-effect-free corpus scan classifying current-valid, legacy-valid but excluded, adoptable, repairable, conflicting, duplicate, and ignored state.
6. Group diagnosis by next-meeting blocker, active incomplete work, corruption, legacy incompatibility, advisory review, and optional absence.
7. Provide dry-run-first recovery commands for stale handoffs and locks rather than manual deletion.
8. Unify install, init, session consent, verify, update, and first ingest around one reference host.
9. Prove fresh, historical, and recovery paths in the same release gate.
10. Require explicit historical eligibility before Briefing proof.

## 7. What To Stop, Defer, Retire, Or Simplify

Stop static-version-only identity, invisible hooks as update certainty, pending success, manual cache deletion, copied-artifact evidence, and editable client execution. Defer Guidance, added providers/sources/hosts, global identity, deeper iQ integration, public launch, and in-place migration. Retire the HTV editable install as a normal executable and remove the complete six-meeting local state after approval and uniqueness review. Simplify to one readiness result, one channel, one host workflow, thin orchestration skills, and one safe recovery action per condition.

## 8. Release Decision

**No-go beyond internal/private alpha.** Controlled owner use is acceptable only with explicit executable resolution and should not count as solved release experience.

The next gate requires one immutable client executable, product-visible build/channel/install/skill compatibility, blocking preflight, honest pending state, useful human output, deterministic HTV/Spelman classification, separate approval before mutation, one fresh reference-host meeting, recovery proof, and exact provenance on new artifacts.

## 9. Confidence And Unresolved Questions

Confidence is high on the verdict and priority of build/readiness certainty. Open questions include the immutable release mechanism, consumer-pin location, skill/engine contract binding, whether history warnings block fresh ingest, adoption ranking and date review, timing of redundant-corpus removal, and the smallest valid historical Briefing proof.
