# Read-Only HTV And Spelman Corpus Reckoning

Review date: 2026-07-20

Authorization: owner-approved read-only corpus reckoning. No consumer file was written, moved, repaired, adopted, regenerated, or deleted.

Privacy boundary: this report records aggregate structure, hashes, schema markers, and health classifications only. It does not reproduce transcript content, meeting titles, participant names, decisions, or client business details.

## Verdict

The accumulated consumer history is valuable and recoverable, but it is not one uniform current-contract corpus.

HTV contains a cleanly distinguishable current generation and legacy generation at the ledger source-identity level. Every legacy ledger source still has a byte-matching processed-source copy, which makes later controlled adoption plausible. However, legacy artifacts and signals do not carry enough current linkage metadata to authorize automatic adoption today.

Spelman contains one source-backed legacy bundle with internally matching source copies and a known date-quality problem. It is suitable historical quality evidence and a future repair/adoption candidate, not current-contract proof.

## Method

The reckoning used only read-only operations:

- filesystem counts by representation type;
- JSON structural and schema inspection;
- current frozen-engine `status --json` and `doctor --json` where configuration permitted;
- SHA-256 comparison among ledger identities, processed sources, and done sources;
- current artifact front-matter and transcript-marker counts;
- current versus legacy meeting/source identity comparisons;
- current ledger event and path-state aggregation.

The installed frozen engine used for status/doctor matched committed HEAD `3bc917de8c6072239848ed190c4c45889d6cf227` by the review's earlier 33-file hash comparison. This provenance was established externally because the current product cannot report it itself.

## HTV Physical Inventory

| Representation | Physical count | Current-contract observation |
| --- | ---: | --- |
| Top-level Markdown objects | 190 | 37 carry current artifact schema and transcript markers; 40 carry `meeting_id` |
| Ledger lines | 173 | 92 schema 1.0 records; 81 legacy three-field records |
| Unique ledger source hashes | 119 | 38 current-generation; 81 legacy; zero overlap |
| Signal files | 118 | 37 current-linked; 81 legacy-invalid under the current contract |
| Processed sources | 118 | 37 match current sources; 81 match legacy sources; zero orphans |
| Done files | 138 physical / 134 unique hashes | 37 match current sources; 78 match legacy sources; 19 hashes have no ledger identity |
| Direct inbox files | 0 | No waiting source input |
| Cached handoffs | 2 requests / 3 responses | Two stale handoffs and one stale response are reported |

Physical objects are not meeting counts. Multiple representations, retries, repairs, and unlinked legacy outputs prevent a one-file-equals-one-meeting interpretation.

## HTV Ledger Classification

### Current-generation sources: 38

- 37 source identities have `primary_artifacts_ready` and `ingest_completed` history.
- One source identity is quarantined and has no primary artifact bundle.
- Five of the 37 completed source histories also contain earlier failed events, demonstrating successful retry rather than five additional meetings.
- Two source histories contain `reconcile_repaired` events.
- The ledger contains 37 historical primary-artifact path references; 34 paths still exist at the recorded location and three no longer do. Current `doctor` reports one active missing-artifact issue, so two absent historical paths appear to have later state that avoids an active missing-artifact diagnosis.

Provisional classification:

- **current-linked:** 37 source identities;
- **current-quarantined:** one source identity;
- **current repair attention:** at least one of the 37 current-linked identities because of the active missing-artifact finding.

This report does not call all 37 fully current-valid until the planned scanner evaluates each logical bundle against latest-state and integrity rules.

### Legacy sources: 81

Each legacy ledger record contains only `ingest_run_id`, `meeting_id`, and `source_sha256`. All 81 hashes are unique, none overlaps a current-generation ledger source, and every one has a byte-matching processed-source copy.

The legacy ledger does not record artifact paths, signal paths, event state, archive/reconcile state, schema provenance, provider provenance, or exact engine build. Consequently these sources are:

- **legacy source-backed:** 81;
- **potentially adoptable after deterministic linkage:** 81;
- **automatically adoptable today:** zero proven.

## HTV Artifact And Signal Classification

### Current-shaped representations

- 37 Markdown objects carry current artifact schema and transcript markers.
- 37 distinct artifact source hashes match the 37 current primary source identities.
- 37 signal-file identities match current meeting identities.

### Legacy-shaped representations

- 153 Markdown objects do not carry a current source-hash contract sufficient for deterministic source linkage.
- 81 signal files fail current validation and do not expose current meeting linkage in the same way as the 37 current files.
- The 153 Markdown objects must not be treated as 153 meetings. They may include multiple representations or historical output shapes.

Provisional classification:

- **current-linked artifact/signal candidates:** 37 bundles, subject to the active missing-artifact issue;
- **legacy-unlinked Markdown objects:** 153;
- **legacy-invalid signal files:** 81;
- **automatic artifact/signal adoption:** not proven.

## HTV Archive And Reconcile Classification

- All 118 processed-source files match a known ledger source: 37 current and 81 legacy. There are no processed-source orphans.
- Done state contains 134 unique content hashes: 37 current matches, 78 legacy matches, and 19 hashes absent from the ledger.
- Three legacy ledger sources have no matching done-file hash.
- Four of the 138 physical done files duplicate content already present in done state.

The 19 ledger-absent done hashes require classification as possible historical inputs, duplicate variants, failed/pre-ledger runs, or intentionally ignored files. They must not be imported or deleted automatically.

## HTV Health Classification

Current frozen-engine health reports 179 findings:

- 81 invalid legacy ledger records;
- 81 invalid legacy signal files;
- 12 low-confidence meeting dates;
- two stale session handoffs;
- one stale provider response;
- one missing artifact;
- one missing playbook state.

Operational interpretation:

- **next-meeting readiness blockers or residue:** stale handoffs/response require product-owned resolution before a clean readiness claim;
- **current repair attention:** one missing artifact;
- **historical adoption work:** 81 legacy ledgers and 81 legacy signals;
- **quality review:** 12 low-confidence dates;
- **optional, not corruption:** missing playbook state;
- **identity/Briefing gate:** 31 identity candidates and zero reviewed people.

The current aggregate issue count is therefore not a useful release verdict without severity and consequence categories.

## Spelman Classification

Physical state:

- two top-level Markdown objects;
- one legacy ledger record;
- one signal file;
- one processed source;
- one done source;
- no active handoffs.

The ledger, processed source, and done source share the same source hash. Neither Markdown object carries current artifact, meeting, source-hash, or transcript-boundary markers. The corpus lacks current project configuration, so current status/doctor cannot inspect it normally.

The known historical date error makes this bundle unsuitable for silent adoption.

Provisional classification:

- **legacy source-backed bundle:** one;
- **legacy unlinked Markdown objects:** two;
- **date repair/review required:** one bundle;
- **automatic adoption:** not authorized or proven.

## Deterministic Classification Summary

| Class | HTV | Spelman | Present treatment |
| --- | ---: | ---: | --- |
| Current-linked source candidates | 37 | 0 | Eligible for latest-state integrity scan |
| Current quarantined sources | 1 | 0 | Preserve and report |
| Legacy source-backed identities | 81 | 1 | Preserve; candidate for later linkage/adoption analysis |
| Processed-source orphans | 0 | 0 | No issue found |
| Ledger-absent done hashes | 19 | 0 | Investigate; do not import/delete automatically |
| Legacy/unlinked Markdown objects | 153 | 2 | Do not count as meetings or adopt automatically |
| Legacy-invalid signal files | 81 | At least one legacy-shaped file | Exclude from current derivation pending qualification |
| Active missing-artifact findings | 1 | Not assessable through current doctor | Repair plan required |
| Low-confidence/known-wrong dates | 12 advisories | 1 known wrong date | Review before freshness-sensitive derivation |
| Stale handoff findings | 2 plus one stale response | 0 | Resolve before readiness proof |

## What This Reckoning Proves

- The historical corpus is real sustained-use evidence.
- Current and legacy ledger source generations are separable without content inspection.
- Preserved processed sources provide strong foundations for controlled reconstruction.
- Raw Markdown count cannot be used as meeting count or current-contract proof.
- Current Stakeholder Briefing cannot truthfully claim representative historical coverage.
- A dry-run adoption scanner can begin from source identity and processed-source evidence, but must solve artifact/signal linkage and ambiguity explicitly.

## What This Reckoning Does Not Prove

- Which of the 153 HTV legacy Markdown objects corresponds to each of the 81 legacy sources.
- Whether legacy summaries should be preserved, mapped, regenerated, superseded, or ignored.
- Whether the 19 ledger-absent done hashes represent unique meetings or redundant variants.
- Which low-confidence dates are acceptable.
- Which identity candidates should be reviewed or merged.
- That any consumer mutation is safe.

## Recommended Adoption-Planning Input

The future scanner should produce one logical-bundle record per candidate source with:

- source hash and source-preservation state;
- current or legacy ledger identity;
- candidate artifact and signal links with confidence and reasons;
- date evidence and confidence;
- duplicate/orphan/conflict status;
- proposed class: current-valid, legacy-valid, adoptable, repairable, conflicting, ignored, duplicate, or orphaned;
- derivation/Briefing eligibility;
- proposed action and reversibility;
- deterministic report fingerprint.

Any write-capable adoption step must require separate approval against that fingerprint and preserve original bytes and legacy provenance.

## Decision

The authorized read-only reckoning is complete. **No adoption decision is made by this report.** Corpus mutation remains deferred until the owner reviews a deterministic adoption plan and approves specific classes separately.
