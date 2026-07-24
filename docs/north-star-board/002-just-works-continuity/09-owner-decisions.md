# Owner Decisions

Decision date: 2026-07-20

## Approved

- Product definition:

  > Meeting Ingest turns each meeting into a trustworthy project record and keeps accumulated meeting history usable and explainable through one approved agent workflow.

- Next milestone: **Just Works Continuity**.
- Reference host: **Claude Code**.
- Initial audience: **the maintainer as the sole reference user in a maintainer-only private alpha**.
- Read-only HTV and Spelman corpus reckoning.
- Corpus adoption will be decided later from the reckoning and a future fingerprinted adoption plan.
- Complete-state removal of the six redundant local records because they provide no unique product evidence or fixture value.

## Completed Under This Approval

- The read-only corpus reckoning is recorded in `08-corpus-reckoning.md`.
- The six copied records are excluded from product evidence.
- Their six Markdown artifacts, twelve ledger snapshots, six signals, six processed sources, and six done sources were removed together while preserving the local project configuration and empty runtime directory structure.

## Approved Runtime Policies

### Approved immutable build authority and consumer policy

This decides what “the approved Meeting Ingest logic” concretely means in Claude Code and consumer projects.

The practical choice is between:

- an exact immutable build identity, such as a tagged/package build tied to a commit or digest; or
- a moving channel such as `main` or `stable`, where the selected build can change.

Approved decision:

- Consumer projects record one exact approved immutable build identity tied to a reviewed commit and packaged build.
- A named stable channel may announce a newer approved build, but it does not silently change the build a consumer runs.
- Preflight reports the running build, approved build, whether they match, and whether an update is available.
- Updating and approving the replacement build are explicit actions.

### Editable development-build policy

HTV currently has an executable that imports code directly from the Meeting Ingest working tree. That means uncommitted development changes can become the logic used for client work merely through virtual-environment activation.

The decision is whether to:

- block editable/development builds for client work; or
- permit them only through an explicit override that clearly marks the run and outputs as development-generated.

Approved decision:

- The approved Claude Code client workflow blocks editable/development builds by default.
- An explicit maintainer override is permitted for intentional testing.
- Readiness output and generated provenance must make development execution unmistakable.
- Development-generated output must not be confused with an approved client-build result.

## Other Later Decisions

- Whether safe next-meeting ingest may proceed as `Ready with history warnings` while historical continuity remains incomplete.
- Which corpus classes should be adopted, regenerated, mapped, preserved as legacy, or ignored.
- Minimum historical and identity coverage required for Stakeholder Briefing proof.
- Generated Markdown mutability policy.
- Low-confidence historical date acceptance policy.
- Whether bounded Layer 5B carryover closes before Just Works Continuity implementation begins.
