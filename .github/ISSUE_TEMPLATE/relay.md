---
name: Relay
about: Cross-project request from another repo or agent — dogfood finding, pipeline bug, extraction-quality report, or feature ask
title: "Relay: <short ask>"
labels: relay
---

## Ask

One sentence: the capability or change requested. Name the kind — dogfood
finding, pipeline bug, extraction-quality report, or feature ask.

## Target

Pick one. This project ships to consumers as receipt-managed frozen builds, so
a request is only actionable once it says what it is aimed at.

- **Shipped build** — a defect observed on an installed consumer build. Name
  the build id and the receipt sha256. Run
  `meeting-ingest runtime inspect --json` on the consumer and copy `build.build_id`
  and `receipt.sha256`; that is the one command that prints both.
  `readiness --json` reports the build id only, as `running_build`. A pinned
  consumer may be behind HEAD, so a defect report without the build identity is
  untriageable, and evidence from a development checkout is not release
  evidence.
- **Source repo** — a feature ask, a contract question, or anything else aimed
  at HEAD rather than a specific released build.

## Concrete driver

Why the need is real now — the observed situation, not a hypothetical. Name the
consumer and the event that surfaced the gap.

## Workaround ruled out

What was tried, or why no workaround exists. If a rule forbids the workaround
(e.g. the hand-edit rule), cite it — that citation is what makes this relay the
intended escape path rather than a preference.

## Suggested scope (take or leave)

The smallest shape that satisfies the ask. Name what stays out of scope.

## First intended use

What happens on receipt — concrete enough that an implementer can verify the
finished work against it.

## Source

Requesting project/agent and date. Link capture ids or session references if
they exist.

<!--
Relay issues are intake, not state. The receiving project triages them into its
own tracking (capture, next action, or board reading) and cross-links the issue
number; the issue closes when the work ships or the ask is declined with a
stated reason.
-->
