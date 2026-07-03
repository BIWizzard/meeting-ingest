import sys
sys.path.insert(0, '/Users/kmgdev/.claude/skills/ingest-meeting')
from ingest_meeting import pipeline, extract

SLUG = 'kushali-adbook-history-shadow-schema-changes'
extract.detect_type = lambda text, title: SLUG

PATH = '/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics/_local/project-context/meetings/_inbox/Call with G, Kushali (13).docx'
PROJECT_ROOT = '/Users/kmgdev/dev_projects/hearst-client/HTV-IQ-DataAnalytics'
INGEST_RUN_ID = 'ingest-20260616-494d46'
HOME = '/Users/kmgdev'

MD = r"""# Call with G, Kushali — AdBook History Shadow Schema Changes

**Date:** 2026-06-16
**Duration:** ~14 minutes
**Participants:** Ken Graham (Contractor), G, Kushali

---

## Participants & Roles

| Name | Role |
|------|------|
| G, Kushali | AdBook gold/fact owner; driving schema alignment |
| Graham, Ken (Contractor) | Orchestration/pipeline owner; implementing loader changes |

---

## Key Discussion

### Context
Kushali loaded new AdBook history files overnight. The history table structure has changed (new columns added), and the history loader that merges into `fact_revenue_shadow` (AdBook) needs to be updated before the orchestration can run cleanly.

### History Load Flow (confirmed)
- History lives in bronze as the `wf_` (write-forward) AdBook table rebuilt recently.
- The loader merges history directly into **fact_revenue_shadow** — there is no intermediate staging table.
- No silver step for history; it goes bronze → shadow (fact_revenue).

### Column Changes — What to Drop in Shadow
Kushali directed: **drop `third_party` and `gl_account`** from the shadow/fact_revenue load (keep them in bronze). Rationale: those fields are not available in the 9 BLOB CSV files, so they cannot be sourced for ongoing fact_revenue.

### New Columns to Add to History Loader

1. **`copy_type_sk`** — a surrogate key (SK). Reference pattern: Kushali's existing CTE in `fact_revenue_adbook_detail` (gold, `adbook_test` notebook). Build the same copy_type CTE in the history loader and join it.

2. **`national_digital_revenue`** — boolean (stored as string `true`/`false`). For history rows pre-2023, the value is `NA` (field didn't exist yet). Kushali will also add this to the summary table.

### `revenue_type_2` Alignment Decision
- In Kushali's history table: was stored as string `NA`.
- In `fact_revenue_adbook_detail`: stored as integers `1`, `2`, `3`.
- **Decision:** Change history to use `1`, `2`, `3` (numeric string) to match detail. Kushali owns this change. Ken confirmed this is what the data shows (`1`, `2`, `3` only).

### Do Not Touch `fact_revenue` Main Table Yet
Kushali explicitly: "don't touch fact_revenue yet" — the shadow (`fact_revenue_shadow` / EOM shadow) is the target. After shadow is validated, ask Jim whether to add `national_digital_revenue` to the main `fact_revenue`. **Do not mention this to Jim yet** — Kushali wants to avoid churn until shadow is confirmed.

### Testing / Orchestration Plan
- Ken will write gold output to **v2 tables** when running through orchestration.
- Compare v2 output against Kushali's manually-run gold layer to verify parity.
- Ken plans to **turn on bronze + silver hourly orchestration** (not writing to Kushali's live summary/detail tables). Kushali confirmed this is fine as long as v2 tables are the target.

---

## Decisions

1. Drop `third_party` and `gl_account` from shadow/fact_revenue load (keep in bronze).
2. Add `copy_type_sk` to history loader (pattern from Kushali's detail CTE).
3. Add `national_digital_revenue` as string (`true`/`false`/`NA`) to history loader; Kushali also adds to summary.
4. Change `revenue_type_2` in history from `NA` string to `1`/`2`/`3` (Kushali owns).
5. Write to v2 tables during orchestration testing; compare vs. live.
6. Do not inform Jim about `national_digital_revenue` addition until shadow is stable.

---

## Action Items

| Owner | Action |
|-------|--------|
| Ken | Update history loader: drop `third_party` + `gl_account` from shadow merge |
| Ken | Add `copy_type_sk` CTE (reference Kushali's `fact_revenue_adbook_detail`) to history loader |
| Ken | Add `national_digital_revenue` (string true/false/NA) to history loader |
| Ken | Reload history into `fact_revenue_shadow` after changes |
| Ken | Turn on bronze + silver hourly orchestration (writing to v2 tables) |
| Ken | Ask Jim (later) whether to add `national_digital_revenue` to main fact_revenue |
| Kushali | Change `revenue_type_2` in history from `NA` → `1`/`2`/`3` |
| Kushali | Add `national_digital_revenue` to summary table |

---

## Open Questions

- When should `national_digital_revenue` be added to the main `fact_revenue` table? (Gate: Jim alignment, post-shadow validation)
- Does `copy_type_sk` for history need a default/null handling for rows where copy_type data is unavailable?

---

## Cross-References

- [[project_adbook_factrevenue_two_table_design]] — detail vs. summary table split context
- [[project_adbook_silver_ownership_and_path]] — orchestration pipeline ownership
- [[project_adbook_june_baseline_built]] — history/wf_ integration context
- [[project_adbook_silver_simplification_2026_06_10]] — simplification decisions affecting silver
"""

OBS = [
    {
        "signal_id": "obs-001",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "DECISION: Drop third_party and gl_account from shadow/fact_revenue load (keep in bronze). These fields are not available in the 9 BLOB CSV files."
    },
    {
        "signal_id": "obs-002",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "DECISION: Add copy_type_sk to history loader. Build the same copy_type CTE as in fact_revenue_adbook_detail (gold adbook_test notebook). Ken owns implementation."
    },
    {
        "signal_id": "obs-003",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "DECISION: Add national_digital_revenue (string true/false, NA for pre-2023 history) to history loader and summary table. Do not inform Jim until shadow is validated."
    },
    {
        "signal_id": "obs-004",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "DECISION: Change revenue_type_2 in history from NA/string to 1/2/3 (numeric string) to match fact_revenue_adbook_detail. Kushali owns this change."
    },
    {
        "signal_id": "obs-005",
        "speaker": "Graham, Ken (Contractor)",
        "person_id": "ken_graham",
        "kind": "project-specific",
        "text": "DECISION: Testing plan = write gold orchestration output to v2 tables, compare against Kushali's manually-run gold layer for parity validation."
    },
    {
        "signal_id": "obs-006",
        "speaker": "Graham, Ken (Contractor)",
        "person_id": "ken_graham",
        "kind": "project-specific",
        "text": "ACTION: Update history loader — drop third_party + gl_account, add copy_type_sk CTE, add national_digital_revenue. Reload into fact_revenue_shadow."
    },
    {
        "signal_id": "obs-007",
        "speaker": "Graham, Ken (Contractor)",
        "person_id": "ken_graham",
        "kind": "project-specific",
        "text": "ACTION: Turn on bronze + silver hourly orchestration targeting v2 tables (not Kushali's live summary/detail tables)."
    },
    {
        "signal_id": "obs-008",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "ACTION: Kushali to change revenue_type_2 in history from NA to 1/2/3; also add national_digital_revenue to summary table."
    },
    {
        "signal_id": "obs-009",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "TOPIC: History load flow confirmed — bronze wf_ table → loader merges directly into fact_revenue_shadow, no intermediate silver step for history."
    },
    {
        "signal_id": "obs-010",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "ASK: After shadow is validated, ask Jim whether national_digital_revenue should be added to the main fact_revenue table."
    },
    {
        "signal_id": "obs-011",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "TOPIC: national_digital_revenue field appeared around 2023-2024; for rows going back to 2016, value will be NA (no backfill available)."
    },
    {
        "signal_id": "obs-012",
        "speaker": "G, Kushali",
        "person_id": "kushali_g",
        "kind": "project-specific",
        "text": "TOPIC: fact_revenue_shadow (EOM) is the current target; main fact_revenue is hands-off until shadow is stable and Jim is aligned."
    }
]


def llm_extract(clean_text, meeting_type):
    return {"markdown": MD, "observations": OBS}


res = pipeline.ingest_transcript(PATH, PROJECT_ROOT, llm_extract,
                                 ingest_run_id=INGEST_RUN_ID, home=HOME)
print(res)
