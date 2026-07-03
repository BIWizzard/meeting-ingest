"""Ingest script for TRACE3 Daily Stand Up - Post-MVP (27) — 2026-06-15"""
import sys
sys.path.insert(0, '/Users/kmgdev/.claude/skills/ingest-meeting')

from ingest_meeting import pipeline

PATH = '/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/_local/project-context/meetings/_inbox/TRACE3 _ Daily Stand Up - Post-MVP  (27).docx'
PROJECT_ROOT = '/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics'
INGEST_RUN_ID = 'ingest-20260615-b4e201'
HOME = '/Users/kmgdev'

MD = """\
# Daily Stand-Up — 2026-06-15

**Meeting:** TRACE3 Daily Stand Up - Post-MVP (27)
**Date:** June 15, 2026
**Duration:** 17m 58s
**Facilitator:** Lewis Bolton

---

## TL;DR

Sprint 4 day-1 check-in. Data agent certification at ~50% (Josh). AdBook glossary at ~75% (Jake). Finance semantic model baseline 3 due tomorrow (Kushali). WO delta data processing ~100% pending a duplicate-record fix on name-join logic (Jim). AdBook historical + delta ingestion marked **done** by Ken (code complete, daily runs active). RLS gold table building today (JF), delivery target 6/16 confirmed. Dilip closed with a work-life-balance reminder — no expectation of weekend work.

---

## Ken — Updates & Commitments

- AdBook historical + live-snapshot ingestion merged all the way to **fact_revenue shadow table** — final shape working.
- Code marked **done** (97% noted on board, code complete as of standup). Daily deltas running; recurrent-maintenance task covers ongoing cadence.
- Baseline meeting on historical delta characterization held today; first baseline loaded.
- **Orchestration** (unattended runs): working in earnest starting today; target EOD today with fallback to tomorrow morning; Lewis confirmed no blocker.
- Staying in sync with Jim's WO side on duplicate/unmatched records — iterative work ongoing.
- Hetal noted Ken's pipeline runs at **5:45 AM daily**, ingesting bronze split of AdBook and WideOrbit.

---

## Team Updates

**Josh Docken — Data Agent Certification & Framework Design**
- Had conversations with JF this morning; progress made Friday.
- Agent created and "working" — estimated 50%.
- Wants to meet with Dilip (12–1 or 3–4 EST today) to talk through outstanding items.

**Jake Searle — AdBook Glossary / Data Discovery**
- Started entering AdBook data into the glossary; ~75% complete; on track for 6/17.
- Meeting Kushali later today to review definitions.
- Met Tanya (Credit & Collections); she didn't fully understand scope. Follow-up meeting with Tanya tomorrow to clarify and gather more definitions.
- Dilip flagged: Tanya may not be a D1 user; finance may not come in until early next year — lower priority accordingly.

**Kushali G — Finance Semantic Model Validation**
- Validate → find issues → fix → re-baseline cycle ongoing. Two baselines complete.
- Baseline 3 target: tomorrow (6/16). Dilip requested to see it then.
- Kushali to send Dilip baseline 2.

**Jim Haley — WideOrbit Delta Data Processing / Orchestration**
- Delta data processing ~100% but has a **name-join duplicate issue**: joining on name (no GUID from AdBook) returns 2–3 records, doubling/tripling fact rows. Worst case ~8% off.
- Fix options: ROW_NUMBER() or SCD Type-2 variant. JF suggested surrogate keys; Jim confirmed that's the direction but name ambiguity remains.
- Data fix (loading logic) is elsewhere but impacts this task. Jim expects to finish fix today.
- Starting **orchestration** this week.
- Mark asked Jim to mark the delta processing task done once the fix is in.

**Jean Francois Hardan — RLS Enforcement**
- Great session with Josh this morning. Bronze and silver data extracted and looking good.
- Building **gold table today**; Josh will use it for dashboard permissions.
- Dilip confirmed three AD groups to include: all-access, finance (HTVIQ Finance Northeast), and all GSM groups from D365.
- Some confusion around EVPs vs. finance group resolved: EVPs see everything; the PDF finance group is a separate static set.
- Delivery target **6/16** — JF sees no red flags; "we will meet the timeline without a doubt."
- Mark to coordinate RLS review meeting with Lewis for **Wednesday 6/17** so Dilip can review with JF and Josh.

**Hetal Gada — Data Validation / Decentrix Upload**
- Data validation going well; waiting on Jim to finish so she can validate his fact_revenue table.
- Will give Jim updated code from her weekend work for him to incorporate.
- Continuing daily Decentrix uploads; Ken's pipeline ingesting at 5:45 AM.

---

## Client Voice — Mark & Dilip

**Mark Olaleye**
- Confirmed validation of WO current data is Pooja's responsibility; not until 6/17.
- Pushed for ETA clarity on finance semantic model baseline (moved to tomorrow).
- Asked Jim to mark delta processing done once fix is complete.
- Asked Ken to confirm AdBook historical + delta done → confirmed.
- Will coordinate with Lewis to set up RLS review Wednesday 6/17.

**Dilip Jayavelu**
- Available today 12–1 and 3–4 EST for Josh conversation on data agent.
- Flagged Tanya (Credit & Collections) as likely not a D1 user; finance scope may slip to early next year.
- Requested baseline 2 from Kushali; wants baseline 3 by tomorrow.
- Confirmed three AD groups for RLS: all-access + finance (HTVIQ Finance Northeast) + GSM D365 groups.
- Closed the standup with a **work-life-balance message**: acknowledged extended and weekend hours, explicitly stated no expectation of weekend work, framed as resourcing concern not billing. "We are still in D1 only, we have a long way to go."

---

## Internal Leadership — JF & Josh

**Jean Francois Hardan**
- Suggested surrogate keys as a path for Jim's name-ambiguity issue.
- Clarified EVP scope (Mike Hayes group) vs. finance group for RLS.
- Confirmed RLS gold table delivery today; no red flags for 6/16.
- Plans to call Dilip after standup to finalize RLS groups.

**Josh Docken**
- Data agent at 50%; wants Dilip + JF alignment call today.
- Confirmed finance dashboard role permissions already set for Mike Hayes group and others (they can see everything).

---

## Decisions & Direction Changes

- **AdBook historical + delta processing: marked DONE.** Recurrent-maintenance task covers ongoing daily cadence from here.
- **Finance semantic model baseline 3 due tomorrow (6/16);** Kushali to send Dilip baseline 2 today.
- **WO delta data processing:** Jim will mark done once duplicate-name fix is complete (today).
- **Tanya (Credit & Collections) de-prioritized** for D1; finance scope likely early next year.
- **RLS delivery confirmed for 6/16.** Gold table building today. Three groups confirmed: all-access, finance HTVIQ Northeast, GSM D365.
- **RLS review meeting: Wednesday 6/17** — Lewis + Mark to coordinate.
- **Work-life balance directive from Dilip:** no expectation of weekend work; team to adjust accordingly.

---

## Action Items / Asks

| Owner | Action | Due |
|---|---|---|
| Josh Docken | Meet with Dilip (12–1 or 3–4 EST today) on data agent | Today 6/15 |
| Jake Searle | Meet Kushali today re glossary definitions | Today 6/15 |
| Jake Searle | Meet Tanya tomorrow to clarify scope + gather definitions | 6/16 |
| Kushali G | Send Dilip baseline 2 | Today 6/15 |
| Kushali G | Complete baseline 3 | 6/16 |
| Jim Haley | Fix name-join duplicate logic; mark delta task done | Today 6/15 |
| Jim Haley | Begin WO orchestration | This week |
| Ken Graham | Complete AdBook orchestration (unattended runs) | EOD 6/15 or 6/16 |
| Jean Francois Hardan | Build RLS gold table | Today 6/15 |
| Jean Francois Hardan | Wire up RLS; target delivery | 6/16 |
| Jean Francois Hardan | Call Dilip post-standup to finalize RLS group list | Today 6/15 |
| Hetal Gada | Share updated code with Jim from weekend work | ASAP |
| Mark Olaleye + Lewis Bolton | Schedule RLS review meeting with Dilip, JF, Josh | Wednesday 6/17 |

---

## North Star Signals

- D1 delivery pressure is real but manageable: all active Sprint 4 threads have owners and near-term ETAs.
- Name-join duplication in WO↔AdBook joins is a first-sighted data quality signal — ~8% delta, being resolved with ROW_NUMBER or SK pinning.
- RLS is on a strong trajectory; JF has no red flags for 6/16.
- Dilip's work-life-balance message signals he is watching team sustainability as a long-range concern — D1 is not the finish line.
- Tanya / finance scope confirmation: D1 is limited; finance likely early next year. Reduces glossary urgency for that lane.

---

## Communication Signals (by person)

**Dilip Jayavelu:** Authoritative, direct. Closed with genuine care about team sustainability. Provided concrete AD group list for RLS. Expects Kushali baseline 3 by tomorrow with no pushback taken.

**Mark Olaleye:** Efficient board-hygiene focus — pushed for ETAs, asked for tasks to be marked done, coordinating review meeting. Teams acting up noted.

**Lewis Bolton:** Tight facilitation. Pressed for % completion estimates. Moved briskly through 10+ items in under 18 minutes.

**Jim Haley:** Transparent about near-miss data issue; clear on root cause (name-ambiguity, no GUID from AdBook). Realistic framing ("think of it as the report is good, the data behind it is bad").

**Ken Graham:** Measured; confirmed code done but needed Mark's framing help to understand what "done" means for a recurrent task. Confirmed once framing was clear.

**Jean Francois Hardan:** Confident on RLS; some minor confusion on EVP vs. finance group clarified in real-time with Dilip. Plans follow-up call immediately.

**Josh Docken:** Brief; agent at 50%, wants alignment call with Dilip today.

**Jake Searle:** Proactive; already identified Tanya gap and has a path. Took Dilip's reprioritization of Tanya gracefully.

**Kushali G:** Responsive; agreed to baseline 3 by tomorrow and to send baseline 2 to Dilip today.

**Hetal Gada:** Brief update; validation going well; giving Jim updated code. Noted daily Decentrix upload routine and Ken's 5:45 AM pipeline schedule.

---

## Cross-References

- [[project_adbook_factrevenue_two_table_design]] — fact_revenue shadow table now populated (Ken confirmed merge complete)
- [[project_wo_master_orchestration_state]] — Jim starting WO orchestration this week; Ken starting AdBook orchestration today
- [[project_adbook_june_baseline_built]] — baseline confirmed; delta processing marked done
- [[project_rls_sprint3]] — RLS gold table building today; delivery 6/16; review 6/17
- [[project_dim_sk_business_key_rework]] — name-join duplication issue (Jim) directly related to no-GUID AdBook join problem
- [[project_deliverable1_redefinition]] — D1 scope confirmed active; Dilip explicitly said "we are still in D1 only"
- [[feedback_cross_cutting_group_alignment]] — RLS AD group list confirmed in group standup (all-access + finance + GSM D365)
"""

OBS = [
    {
        "signal_id": "s27-001",
        "speaker": "Ken Graham",
        "person_id": "ken_graham",
        "kind": "project-specific",
        "text": "DECISION: AdBook historical + delta data processing task marked DONE. Code complete, daily runs active; recurrent-maintenance task covers ongoing cadence."
    },
    {
        "signal_id": "s27-002",
        "speaker": "Jim Haley",
        "person_id": "jim_haley",
        "kind": "project-specific",
        "text": "DECISION: WO delta data processing ~100% but has name-join duplicate issue (~8% off). Fix = ROW_NUMBER or SK pinning. Jim will mark done once fix is complete today."
    },
    {
        "signal_id": "s27-003",
        "speaker": "Jean Francois Hardan",
        "person_id": "jf_hardan",
        "kind": "project-specific",
        "text": "DECISION: RLS delivery confirmed for 6/16. Gold table building today. Three confirmed AD groups: all-access, HTVIQ Finance Northeast, GSM D365 groups."
    },
    {
        "signal_id": "s27-004",
        "speaker": "Olaleye, Mark",
        "person_id": "mark_olaleye",
        "kind": "project-specific",
        "text": "DECISION: RLS review meeting scheduled for Wednesday 6/17. Mark + Lewis to coordinate; attendees: Dilip, JF, Josh."
    },
    {
        "signal_id": "s27-005",
        "speaker": "Jayavelu, Dilip",
        "person_id": "dilip_jayavelu",
        "kind": "project-specific",
        "text": "DECISION: Finance semantic model baseline 3 due 6/16 (Kushali). Baseline 2 to be sent to Dilip today."
    },
    {
        "signal_id": "s27-006",
        "speaker": "Jayavelu, Dilip",
        "person_id": "dilip_jayavelu",
        "kind": "project-specific",
        "text": "DECISION: Tanya (Credit & Collections) de-prioritized for D1. Finance scope likely early next year. Lower glossary priority for that lane."
    },
    {
        "signal_id": "s27-007",
        "speaker": "Jayavelu, Dilip",
        "person_id": "dilip_jayavelu",
        "kind": "stable-preference",
        "text": "Dilip explicitly stated no expectation of weekend or extended-hours work. Work-life balance is a resourcing priority not a billing concern. 'We are still in D1 only, we have a long way to go.'"
    },
    {
        "signal_id": "s27-008",
        "speaker": "Ken Graham",
        "person_id": "ken_graham",
        "kind": "project-specific",
        "text": "ACTION: Complete AdBook orchestration (unattended runs). Target EOD 6/15, fallback 6/16 morning."
    },
    {
        "signal_id": "s27-009",
        "speaker": "Jim Haley",
        "person_id": "jim_haley",
        "kind": "project-specific",
        "text": "ACTION: Fix name-join duplicate logic in WO loading; mark delta processing task done. Today 6/15."
    },
    {
        "signal_id": "s27-010",
        "speaker": "Jean Francois Hardan",
        "person_id": "jf_hardan",
        "kind": "project-specific",
        "text": "ACTION: Build RLS gold table today; wire up RLS by 6/16. Call Dilip post-standup to finalize three AD group list."
    },
    {
        "signal_id": "s27-011",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "ACTION: Send Dilip baseline 2 today; complete baseline 3 by 6/16."
    },
    {
        "signal_id": "s27-012",
        "speaker": "Josh Docken",
        "person_id": "josh_docken",
        "kind": "project-specific",
        "text": "ACTION: Meet with Dilip today (12–1 or 3–4 EST) on data agent certification progress and outstanding questions."
    },
    {
        "signal_id": "s27-013",
        "speaker": "Searle, Jake",
        "person_id": "jake_searle",
        "kind": "project-specific",
        "text": "ACTION: Meet Kushali today re glossary definitions; meet Tanya tomorrow to clarify scope and gather more definitions."
    },
    {
        "signal_id": "s27-014",
        "speaker": "Gada, Hetal",
        "person_id": "hetal_gada",
        "kind": "project-specific",
        "text": "ACTION: Share updated code with Jim from weekend work so he can incorporate it into his fact_revenue table."
    },
    {
        "signal_id": "s27-015",
        "speaker": "Jim Haley",
        "person_id": "jim_haley",
        "kind": "project-specific",
        "text": "TOPIC: Name-join duplication in WO-AdBook joins — no GUID from AdBook side means joining on name returns 2–3 records, inflating facts by ~8%. Resolution options: ROW_NUMBER or SCD Type-2. JF noted surrogate keys as path."
    },
    {
        "signal_id": "s27-016",
        "speaker": "Gada, Hetal",
        "person_id": "hetal_gada",
        "kind": "project-specific",
        "text": "TOPIC: Ken's pipeline runs daily at 5:45 AM, ingesting bronze split of AdBook and WideOrbit. Hetal manually uploading Decentrix data daily."
    },
    {
        "signal_id": "s27-017",
        "speaker": "Jayavelu, Dilip",
        "person_id": "dilip_jayavelu",
        "kind": "project-specific",
        "text": "ASK: Dilip to Josh — meet today (12–1 or 3–4 EST) to discuss data agent certification."
    },
    {
        "signal_id": "s27-018",
        "speaker": "Jayavelu, Dilip",
        "person_id": "dilip_jayavelu",
        "kind": "project-specific",
        "text": "ASK: Dilip to JF — finalize RLS group list post-standup call. Three groups: all-access, HTVIQ Finance Northeast, GSM D365."
    },
    {
        "signal_id": "s27-019",
        "speaker": "Jean Francois Hardan",
        "person_id": "jf_hardan",
        "kind": "project-specific",
        "text": "TOPIC: EVP group (Mike Hayes etc.) vs. HTVIQ Finance Northeast group clarification — EVPs see everything (separate finance static set). Josh confirmed finance role permissions already set in dashboard."
    },
    {
        "signal_id": "s27-020",
        "speaker": "Olaleye, Mark",
        "person_id": "mark_olaleye",
        "kind": "audience-fit",
        "text": "Mark noted Teams is acting up (cannot receive messages reliably). Dilip and Jake Searle confirmed same issue. Awareness signal for async comms this day."
    }
]


def llm_extract(clean_text, meeting_type):
    return {"markdown": MD, "observations": OBS}


res = pipeline.ingest_transcript(
    PATH,
    PROJECT_ROOT,
    llm_extract,
    ingest_run_id=INGEST_RUN_ID,
    home=HOME
)
print(res)
