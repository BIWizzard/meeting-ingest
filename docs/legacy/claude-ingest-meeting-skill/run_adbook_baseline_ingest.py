#!/usr/bin/env python3
"""
Ingest script: Meeting to review the Adbook Baseline (2026-06-15)
"""
import sys, os
sys.path.insert(0, "/Users/kmgdev/.claude/skills/ingest-meeting")

from ingest_meeting import extract, pipeline

# ── Monkeypatch detect_type before calling pipeline ──────────────────────────
extract.detect_type = lambda text, title: "adbook-baseline-review"

PATH = "/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/_local/project-context/meetings/_inbox/Meeting to review the Adbook Baseline.docx"
PROJECT_ROOT = "/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics"
INGEST_RUN_ID = "ingest-20260615-b4e201"
HOME = "/Users/kmgdev"

# ── Composed markdown (GENERIC BASE section set) ──────────────────────────────
MD = """# AdBook Baseline Review
**Date:** 2026-06-15
**Duration:** ~1h 4m
**Type:** adbook-baseline-review

---

## Participants & Roles

| Name | Role |
|------|------|
| Graham, Ken (Contractor) | Data Engineering Lead — presented baseline walkthrough |
| G, Kushali | Data Engineer — AdBook silver/gold owner, live screen share |
| Jayavelu, Dilip | Client Lead — primary questioner, set deadlines |
| Olaleye, Mark | Client — participated in advertiser/agency naming investigation |
| Francois Harden, Jean (Contractor) / Jean Francois Hardan | Engineering Lead — asked for pipeline diagram, dropped at ~52m |

---

## TL;DR

The AdBook historical baseline (Decentrix write-forward data, Jan 1 2016–Jun 3 2026) has been loaded into bronze and merged into fact_revenue in a shadow table. The daily BLOB snapshot pipeline (Jun 4 2026 onward) runs bronze→silver→gold. The two data streams cannot yet be compared directly because the write-forward history has 10 columns while the live silver/gold summary layer has 13 (3 extra digital-specific columns, e.g. copy_type). Kushali is adding the 3 columns to history today; a reconciled baseline view targeting Wednesday Jun 17 at 11:30am. A second issue surfaced: AdBook BLOB flat files are missing advertiser/agency GUID (customer code), causing name mismatches between AdBook and Wide Orbit. Kushali has reached out to Decentrix (Alex) and John Branco; Dilip asked to be copied on the email and approved Kushali or John Branco adding the field to the 9th scheduled report.

---

## Key Discussion

### 1. Historical baseline scope and pipeline architecture

Ken confirmed historical Decentrix write-forward data (2016–Jun 3 2026) is in bronze and merged into fact_revenue (shadow). Daily BLOB snapshots start Jun 4 2026, flowing bronze→silver→(detail→summary)→fact_revenue (gold). Dilip was hearing about "fact_revenue_summary" for the first time; Ken explained it is a month-to-date roll-up layer that sits between per-drop detail and the final gold fact — required because the daily snapshot grain is per-drop projected revenue while the Decentrix history is air-date / actual-spend based.

Kushali clarified: the write-forward table is split into two — one for Wide Orbit, one for digital (AdBook). The 3 extra columns are digital-specific and do not affect Wide Orbit.

Ken noted the team refreshes the last two years (2025 and 2026) from Decentrix each day, though no restatements are expected for 2025.

### 2. Grain mismatch between history and daily snapshots — the "seam" problem

History ends at Jun 4, daily starts at Jun 5 (or Jun 4, depending on alignment). The two streams cannot be directly compared because: history does not project revenue forward to future drop dates; daily snapshots do. Kushali must add 3 columns to the historical Excel sheets and reload bronze before the summary layer can produce an apples-to-apples comparison at the seam. She committed to having bronze loaded by end of day Jun 15 (today). Silver, code changes, and shadow table push will follow, making Wednesday Jun 17 the realistic baseline comparison date.

Dilip's question: can gold be compared to the write-forward bronze table for Jun 4? Answer: not yet — different grain. Once Kushali's column addition is in, the comparison becomes valid.

### 3. Wednesday follow-up baseline meeting

Dilip confirmed: Wednesday Jun 17, 11:30am–12:00pm (same slot). Goal: view the reconciled Jun 4 (or Jun 5) daily delta stats alongside the write-forward stats as the first validated baseline.

### 4. Advertiser/agency name mismatch — missing GUID in AdBook flat files

Kushali surfaced an issue discovered Friday Jun 13: AdBook BLOB flat files (9 scheduled reports) do not include the advertiser/agency GUID (customer code). As a result, the advertiser name in our data (e.g. "Dan Newlin PA") does not match the canonical Wide Orbit / Decentrix reporting name (e.g. the full attorney name with INC). The 9 files carry truncated/abbreviated names; Decentrix appears to use the outbound Wide Orbit data to perform the name matching internally before delivering reporting output, but that mapping logic is opaque to the team.

Dilip's framing: Decentrix is "gluing" the INC-version (Wide Orbit) order with the non-INC (AdBook) order somewhere internally. The team needs to understand how, and add the customer code GUID to the flat files so HTV IQ can perform the same join.

Mark and Kushali investigated live: for agency-type orders, AdBook uses the agency name as the "client name" field rather than the advertiser name; Decentrix then resolves this to the Wide Orbit advertiser. This explains the ~30 non-matching records Kushali identified.

**Fix path agreed:** Kushali will ask John Branco (and copy Dilip) whether the team can self-serve the customer code addition to the 9th scheduled BLOB report, or if Branco must handle it. Alex (Decentrix) has also been contacted. Dilip: if Branco says self-service is OK, proceed; if not, notify him to do it.

### 5. Pipeline diagram / documentation ask

Jean Francois asked for a flow diagram documenting the full AdBook pipeline. Ken acknowledged the gap and committed to bringing a proper explainer to the next session. No diagram exists today.

---

## Decisions & Direction Changes

- **Wednesday Jun 17, 11:30am** is the target for the first reconciled baseline comparison (history + daily delta aligned at the seam).
- **Kushali will add 3 columns (+3) to the Decentrix write-forward history** rather than dropping 3 from summary, to achieve grain alignment. Target: bronze loaded by EOD Jun 15.
- **Last-2-years refresh cadence confirmed:** the write-forward pipeline refreshes 2025 and 2026 each day.
- **GUID/customer code fix path:** Kushali emails Branco (copy Dilip), asking if team can self-serve adding customer code to the 9th scheduled AdBook report; Dilip decides based on reply.
- **Updates on advertiser/agency GUID issue** to be provided at daily standup until resolved.

---

## Action Items / Asks

| Owner | Item | Due |
|-------|------|-----|
| Kushali | Add 3 columns to Decentrix write-forward historical Excel sheets; reload bronze | EOD Jun 15 |
| Kushali | Push silver + code changes + shadow table after bronze is ready | Jun 16 (Tue) |
| Ken | Prepare reconciled baseline comparison view (gold vs. write-forward at the seam) | By Jun 17 AM |
| Kushali | Email Alex (Decentrix) re: customer code in flat files; CC Dilip | ASAP |
| Kushali | Email John Branco re: self-service adding customer code to 9th scheduled report; CC Dilip | ASAP |
| Kushali | Investigate ~30 non-matching advertiser/agency records; confirm agency-order naming hypothesis | TBD |
| Ken | Create pipeline flow diagram / explainer for next session | Next meeting |
| Dilip | Reschedule follow-up baseline call to Wed Jun 17 11:30am | Jun 15 |

---

## Open Questions / Blockers

- How is Decentrix internally resolving abbreviated AdBook advertiser names to canonical Wide Orbit names? (Awaiting Alex reply; Branco also contacted.)
- Is the customer code GUID available in any current AdBook API or BLOB file? (Currently null in 9th report agency pull.)
- Does the +3 column history reload change the fact_revenue grain enough to fully close the seam, or are other adjustments needed?

---

## North Star Signals

- History-to-bronze-to-fact_revenue reconciliation is passing to the penny per month — the historical load chain is validated.
- Daily BLOB snapshot chain (bronze→silver→detail→summary→fact_revenue) is operating correctly; numbers line up as expected.
- The seam problem is understood and has a concrete fix in flight (today).
- The advertiser/agency GUID gap is a known gap now surfaced early; fix is in motion.

---

## Cross-References

- Decentrix write-forward baseline: [[project_adbook_june_baseline_built]]
- AdBook BLOB file GUID gap: [[project_adbook_factrevenue_two_table_design]] (advertiser/agency GUID noted as open)
- John Branco contact: [[reference_john_branco]]
- AdBook silver ownership: [[project_adbook_silver_ownership_and_path]]
"""

# ── Observations (typed facets + signals) ─────────────────────────────────────
OBS = [
    # Typed facets — decisions
    {
        "signal_id": "adbook-baseline-2026-06-15-d001",
        "speaker": "Jayavelu, Dilip",
        "person_id": None,
        "kind": "project-specific",
        "text": "DECISION: Wednesday Jun 17 11:30am–12:00pm set as follow-up baseline review meeting.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-d002",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "DECISION: Add 3 columns to Decentrix write-forward historical data (+3 to history, not -3 from summary) to align grain between history and daily snapshot layers. Target: bronze loaded EOD Jun 15.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-d003",
        "speaker": "Jayavelu, Dilip",
        "person_id": None,
        "kind": "project-specific",
        "text": "DECISION: Kushali emails John Branco (CC Dilip) to ask whether team can self-serve adding customer code GUID to the 9th scheduled AdBook BLOB report. If Branco says self-service OK, team proceeds; otherwise Branco handles it.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-d004",
        "speaker": "Jayavelu, Dilip",
        "person_id": None,
        "kind": "project-specific",
        "text": "DECISION: Advertiser/agency GUID customer code issue to be reported at daily standup until resolved.",
        "meeting_id_ref": None
    },
    # Typed facets — action items
    {
        "signal_id": "adbook-baseline-2026-06-15-a001",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: Add 3 digital-specific columns to Decentrix write-forward historical Excel sheets and reload bronze. EOD Jun 15.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-a002",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: After bronze is ready, push changes through silver and shadow table. Target Jun 16.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-a003",
        "speaker": "Graham, Ken (Contractor)",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: Prepare reconciled baseline comparison (gold vs. write-forward at the seam) for Wednesday Jun 17 meeting.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-a004",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: Email Alex (Decentrix) re: how they resolve abbreviated AdBook names to canonical Wide Orbit names; CC Dilip. (Email already sent Friday Jun 13; awaiting reply.)",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-a005",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: Email John Branco asking if team can self-serve adding customer code to 9th scheduled AdBook BLOB report; CC Dilip.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-a006",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: Investigate ~30 non-matching advertiser/agency records; verify agency-order naming hypothesis (agency name used as client name in AdBook for agency-type orders).",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-a007",
        "speaker": "Graham, Ken (Contractor)",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: Create pipeline flow diagram / explainer for AdBook data pipeline for next session (tagged by Jean Francois).",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-a008",
        "speaker": "Jayavelu, Dilip",
        "person_id": None,
        "kind": "project-specific",
        "text": "ACTION: Dilip to reschedule follow-up baseline call to Wednesday Jun 17 11:30am.",
        "meeting_id_ref": None
    },
    # Typed facets — topics
    {
        "signal_id": "adbook-baseline-2026-06-15-t001",
        "speaker": "Graham, Ken (Contractor)",
        "person_id": None,
        "kind": "project-specific",
        "text": "TOPIC: AdBook historical baseline — Decentrix write-forward data (Jan 1 2016–Jun 3 2026) loaded into bronze, merged into fact_revenue shadow table. Validated to the penny per month.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-t002",
        "speaker": "Graham, Ken (Contractor)",
        "person_id": None,
        "kind": "project-specific",
        "text": "TOPIC: AdBook pipeline architecture — bronze→silver→(detail→summary)→fact_revenue (gold). fact_revenue_summary is month-to-date roll-up created by Kushali; first disclosed to Dilip in this meeting.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-t003",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "TOPIC: Grain mismatch / seam between history and daily snapshots — write-forward has 10 columns, live summary has 13 (3 extra digital-specific: e.g. copy_type). Kushali adding +3 to history to enable direct comparison at the Jun 4/5 seam.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-t004",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "project-specific",
        "text": "TOPIC: AdBook BLOB flat files missing GUID/customer code for advertiser and agency — causes name mismatches (e.g. 'Dan Newlin PA' vs. full attorney name). ~30 records affected. Fix = add customer code field to 9th scheduled report.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-t005",
        "speaker": "Olaleye, Mark",
        "person_id": None,
        "kind": "project-specific",
        "text": "TOPIC: Agency-order naming hypothesis — for agency-type orders, AdBook uses agency name as 'client name' field; Decentrix resolves to Wide Orbit advertiser for reporting. Kushali to verify against ~30 non-matching records.",
        "meeting_id_ref": None
    },
    # Signals — stable preferences / project-specific
    {
        "signal_id": "adbook-baseline-2026-06-15-s001",
        "speaker": "Francois Harden, Jean (Contractor)",
        "person_id": None,
        "kind": "stable-preference",
        "text": "JF/Jean Francois: Always wants a pipeline flow diagram for any new data pipeline before or alongside the demo. Tagged Ken explicitly.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-s002",
        "speaker": "Jayavelu, Dilip",
        "person_id": None,
        "kind": "stable-preference",
        "text": "Dilip prefers to pick a specific example date for baseline comparison rather than an abstract discussion. He proposed 'you pick day one' and set Wednesday as the concrete checkpoint.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-s003",
        "speaker": "Jayavelu, Dilip",
        "person_id": None,
        "kind": "stable-preference",
        "text": "Dilip wants ongoing issues (e.g. customer code GUID) surfaced at daily standup, not just in ad-hoc meetings.",
        "meeting_id_ref": None
    },
    # Time-bound
    {
        "signal_id": "adbook-baseline-2026-06-15-tb001",
        "speaker": "G, Kushali",
        "person_id": None,
        "kind": "time-bound",
        "text": "Kushali committed to having write-forward history reloaded into bronze (with +3 columns) by EOD Jun 15, 2026.",
        "meeting_id_ref": None
    },
    {
        "signal_id": "adbook-baseline-2026-06-15-tb002",
        "speaker": "Jayavelu, Dilip",
        "person_id": None,
        "kind": "time-bound",
        "text": "Baseline comparison target: Wednesday Jun 17, 2026, 11:30am–12:00pm follow-up meeting.",
        "meeting_id_ref": None
    },
]


def llm_extract(clean_text, meeting_type):
    return {"markdown": MD, "observations": OBS}


if __name__ == "__main__":
    res = pipeline.ingest_transcript(
        PATH,
        PROJECT_ROOT,
        llm_extract,
        ingest_run_id=INGEST_RUN_ID,
        home=HOME
    )
    print(res)
