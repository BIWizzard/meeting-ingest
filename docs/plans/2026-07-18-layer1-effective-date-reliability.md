# Layer 1 Effective-Date Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make meeting occurrence dates trustworthy: deterministic occurrence candidate selection before ID minting, an explicit `--meeting-date` override, prominent file-mtime fallback warnings, a controlled `repair-date` command, and doctor surfacing of low-confidence dates.

**Architecture:** Candidate selection lives in `extract.py` (where all date inference already lives) and feeds `pipeline._prepare_ingest` before `meeting_id`/`ingest_run_id` minting. `repair-date` is a new locked pipeline command modeled on the frozen `repair-title` contract: it renames artifacts, rewrites mutable front-matter date fields and signal `effective_at` values, and appends a `date_repaired` ledger snapshot. `meeting_id` and `signal_id` date segments are immutable minting provenance and never change.

**Tech Stack:** Python 3.12+, stdlib only, `uv run pytest`, frozen dataclasses, typed `MeetingIngestError` taxonomy.

## Global Constraints

- Run tests with `uv run pytest` from the repo root.
- No AI attribution anywhere: commits, code comments, docs. Conventional commit format (`feat:`, `docs:`, `test:`).
- Never hand-edit `.iq-context` state or `_local/project-context/meetings/` ledger/artifacts by hand — live-data repair goes through the engine only.
- All new errors are typed `MeetingIngestError` subclasses or instances with a stable `code`; exit codes reuse the existing constants in `src/meeting_ingest/errors.py`.
- All new dataclasses are `@dataclass(frozen=True)` matching existing style.
- `meeting_id`, `ingest_run_id`, `signal_id`, `source_sha256`, processed archive paths, and transcript content are immutable — no task may change them for an existing ingest.
- Date strings in contracts are always `YYYY-MM-DD` and must be real calendar dates.
- Existing tests (133 passing as of commit `b6c1e9d`) must keep passing after every task.

---

### Task 1: Freeze the occurrence-selection, `--meeting-date`, and `repair-date` contract in docs

**Files:**
- Modify: `docs/artifact-contract.md` (insert a new section immediately after the "Title Repair Contract" section, which ends near line 1003; also add `date_repaired` to the ledger event enumeration near line 1080)
- Modify: `DECISIONS.md` (append a decision entry; match the file's existing heading/entry style — read it first)

**Interfaces:**
- Consumes: existing "Title Repair Contract" section as the structural model.
- Produces: the frozen contract that Tasks 2–6 implement verbatim. Later tasks must not deviate from the field names, warning codes, CLI shapes, and ledger fields written here.

- [ ] **Step 1: Read the surrounding contract sections**

Read `docs/artifact-contract.md` lines 900–1100 and `DECISIONS.md` in full so the new section matches established voice, fence style, and any anchor conventions.

- [ ] **Step 2: Insert the new contract section**

Insert after the Title Repair Contract section (after the `title_repaired` minimum-fields JSON block and before "## Regeneration Contract"):

```markdown
## Meeting Occurrence And Date Repair Contract

### Occurrence Candidate Selection

Effective-date inference is candidate-based and deterministic. Before minting
`meeting_id`, `ingest_run_id`, or a provider request, the engine gathers every
available occurrence candidate and selects by fixed precedence:

1. operator override via `--meeting-date` — confidence `manual`, source `override`
2. transcript content export stamp or human date header — confidence `high`, source `content`
3. filename date — confidence `high`, source `filename`
4. file modification time — confidence `low`, source `file_mtime`

Rules:

- Selection is precedence-ordered, never content-weighted. The first available
  candidate wins.
- Contextual date evidence (weekday names, relative-date phrases, nearby
  absolute-date references inside dialogue) is explicitly out of scope for v1
  candidate selection and must not influence the chosen date.
- When two or more non-`file_mtime` candidates disagree, the engine still
  selects by precedence and appends a run-summary warning listing every
  non-`file_mtime` candidate as `source=value` pairs.
- An operator override always wins, including over conflicting high-confidence
  evidence; the conflict warning still fires so the operator sees the
  disagreement.
- Whenever the selected source is `file_mtime`, `ingest` and `provider-request`
  must append a prominent run-summary warning stating that the date may be a
  download/acquisition time rather than the meeting occurrence, and naming both
  escape hatches: `--meeting-date` before ingest, `repair-date` after.

### Manual Meeting-Date Override

CLI shape:

```text
meeting-ingest ingest <source> --meeting-date YYYY-MM-DD [...]
meeting-ingest provider-request <source> --meeting-date YYYY-MM-DD [...]
```

Rules:

- `--meeting-date` accepts only a real calendar date in `YYYY-MM-DD` form.
  Anything else fails with config error code `invalid_meeting_date` and the
  usage/config exit code before any extraction or minting happens.
- The override participates in candidate selection as the highest-precedence
  candidate; the chosen effective date records confidence `manual` and source
  `override` in artifacts, provider requests, and run summaries.
- Batch commands (`ingest-inbox`, `session-inbox`) do not accept
  `--meeting-date` in v1: one date across many sources is an error amplifier,
  not an escape hatch. Per-source overrides go through single-source `ingest`
  or `provider-request`.
- For session-provider work the override applies at phase 1: the persisted
  provider request carries the overridden `effective_date`,
  `date_confidence`, and `date_source`, and phase 2 adopts them through the
  normal persisted-request rebinding rules.

### Date Repair Contract

Controlled date repair uses this CLI shape:

```text
meeting-ingest repair-date <meeting-id-or-source-sha> --date YYYY-MM-DD [--root <path>] [--json]
```

Rules:

- `<meeting-id-or-source-sha>` is an exact `meeting_id` or an exact full
  `source_sha256`. Prefix matching is not supported in v1.
- `repair-date` updates mutable occurrence metadata only: artifact filename
  date prefixes (file renames), artifact front-matter `date`,
  `date_confidence`, and `date_source` fields, and signal-record
  `effective_at` values.
- Repaired metadata records confidence `manual` and source `repair`.
- It must not change `meeting_id`, `ingest_run_id` values on existing records,
  `signal_id` values, signal counts, `source_sha256`, the processed archive
  path, original source identity, or transcript content. The date segments
  embedded in `meeting_id` and `signal_id` are minting provenance, not current
  occurrence, and are documented as such.
- The signal JSONL file path is keyed by `meeting_id` and therefore does not
  move; its records are rewritten in place with only `effective_at` changed.
- Artifact renames replace the leading `YYYY-MM-DD` filename prefix and keep
  the existing slug. Filename collisions use the same numeric suffix rule as
  initial ingest and must be reported in warnings.
- The repair applies to all ready markdown mode artifacts for the selected
  source.
- The command appends a complete `date_repaired` ledger snapshot containing
  every known mode artifact entry with repaired path metadata, only after all
  file renames and rewrites have succeeded.
- A `date_repaired` snapshot carries current primary-artifact state: duplicate
  detection, no-op summaries, and doctor current-state checks must treat it
  exactly like `ingest_completed` when it is the latest record for a source.
- The command returns `status: "success"` and exit `0` when at least one date
  field or artifact path changed.
- If the requested date already matches current state, the command returns
  `status: "no_op"` and exit `0` without appending a ledger record.
- If the target cannot be resolved from the ledger, the command fails with
  error code `repair_target_not_found`. If an expected artifact or signal file
  is missing or cannot be moved, it fails with `repair_artifact_missing` (or
  the underlying write error) without appending `date_repaired`; partial
  states are surfaced by `doctor` as missing-path issues rather than silently
  normalized.

Minimum `date_repaired` ledger fields:

```json
{
  "schema_version": "1.0",
  "event": "date_repaired",
  "source_sha256": "63d2e8690b7ba09d51e80cc1d3be40fa530c5479b15e33bd2535e0881bccaf55",
  "meeting_id": "mtg-20260703-63d2e869",
  "ingest_run_id": null,
  "artifacts": {
    "summary-plus-verbatim": {
      "status": "ready",
      "path": "2026-07-10-nitesh-follow-up-interview-debrief.md",
      "schema_version": "1.0",
      "title": "Nitesh Follow-Up Interview Debrief",
      "slug": "nitesh-follow-up-interview-debrief"
    }
  },
  "repair": {
    "previous_date": "2026-07-03",
    "previous_date_confidence": "low",
    "previous_date_source": "file_mtime",
    "date": "2026-07-10",
    "changed_modes": ["summary-plus-verbatim"]
  },
  "recorded_at": "2026-07-18T12:00:00Z"
}
```

### Low-Confidence Date Doctor Check

- `doctor` reports advisory issue code `low_confidence_meeting_date` for every
  current ready artifact whose front matter records `date_source: file_mtime`.
- The check is read-only and never mutates project files.
- A successful `repair-date` clears the condition because the repaired front
  matter records `date_source: repair`.
```

- [ ] **Step 3: Add `date_repaired` to the ledger event enumeration**

In the ledger event list (near line 1080, where `title_repaired` is enumerated), add `date_repaired` alongside it, matching list formatting.

- [ ] **Step 4: Append the decision entry to `DECISIONS.md`**

Match the file's existing entry format (read it first). Content to record, dated 2026-07-18:

- Occurrence selection is precedence-based (override > content > filename > file mtime); contextual dialogue evidence deferred from v1.
- `--meeting-date` exists on single-source commands only; batch commands excluded deliberately.
- `meeting_id` and `signal_id` date segments are immutable minting provenance; `repair-date` rewrites only mutable occurrence metadata (artifact filename prefix, front-matter date fields, signal `effective_at`).
- Signal files are rewritten in place because downstream briefing layers sequence on `effective_at`; leaving stale values would poison Layer 5+.

- [ ] **Step 5: Verify doc consistency**

Run: `uv run pytest` (must stay green — docs only, expect 133 passed).
Check fences balance: ` grep -c '^```' docs/artifact-contract.md ` must return an even number.

- [ ] **Step 6: Commit**

```bash
git add docs/artifact-contract.md DECISIONS.md
git commit -m "docs: freeze occurrence selection, meeting-date override, and repair-date contract"
```

---

### Task 2: Occurrence candidate selection in `extract.py` with sanitized Teams VTT fixtures

**Files:**
- Create: `tests/fixtures/teams-vtt/Daily Stand Up - Post-MVP (41).vtt`
- Create: `tests/fixtures/teams-vtt/Daily Stand Up - Post-MVP (42).vtt`
- Modify: `src/meeting_ingest/extract.py`
- Test: `tests/test_extract.py`

**Interfaces:**
- Consumes: existing `EffectiveDate`, `_date_from_content`, `_DATE_PATTERNS`, `_valid_date` in `extract.py`.
- Produces (used by Tasks 3, 4):
  - `OccurrenceCandidate(value: str, confidence: str, source: str)` frozen dataclass
  - `OccurrenceSelection(chosen: EffectiveDate, candidates: tuple[OccurrenceCandidate, ...], conflict: bool)` frozen dataclass
  - `select_occurrence(path: Path, content: str = "", *, override: str | None = None) -> OccurrenceSelection`
  - `extract_source(path: Path, *, meeting_date: str | None = None) -> SourceExtraction`
  - `SourceExtraction` gains field `date_selection: OccurrenceSelection | None = None` (populated by `extract_source`)
  - `infer_effective_date(path, content)` keeps its exact current signature/behavior as a thin wrapper.

- [ ] **Step 1: Create the sanitized fixtures**

These mirror the observed July 10/13 failure shape: a Teams VTT download whose filename and content carry no date, so only file mtime is available. Both files use the same structure; sanitized content, GUID cue IDs, `<v>` voice tags.

`tests/fixtures/teams-vtt/Daily Stand Up - Post-MVP (41).vtt` (represents the 2026-07-10 standup):

```text
WEBVTT

7f3a2c9e-4b1d-4e8a-9c5f-1a2b3c4d5e6f/1-0
00:00:03.120 --> 00:00:06.480
<v Graham, Ken (Contractor)>Morning everyone, quick status before we start.</v>

7f3a2c9e-4b1d-4e8a-9c5f-1a2b3c4d5e6f/2-0
00:00:07.000 --> 00:00:11.240
<v Wilson, John>Validation runs finished overnight, no new mismatches.</v>

7f3a2c9e-4b1d-4e8a-9c5f-1a2b3c4d5e6f/3-0
00:00:12.000 --> 00:00:15.900
<v Graham, Ken (Contractor)>Good. I will pick up the orchestration ticket next.</v>
```

`tests/fixtures/teams-vtt/Daily Stand Up - Post-MVP (42).vtt` (represents the 2026-07-13 standup):

```text
WEBVTT

9d8c7b6a-5e4f-4a3b-8c2d-0f1e2d3c4b5a/1-0
00:00:02.560 --> 00:00:05.980
<v Wilson, John>Quick one today, the sandbox refresh is still running.</v>

9d8c7b6a-5e4f-4a3b-8c2d-0f1e2d3c4b5a/2-0
00:00:06.400 --> 00:00:10.120
<v Graham, Ken (Contractor)>Understood, I will verify the revenue baseline after lunch.</v>
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/test_extract.py`:

```python
FIXTURES = Path(__file__).parent / "fixtures" / "teams-vtt"


def _copy_fixture(tmp_path: Path, name: str, *, mtime: int) -> Path:
    source = tmp_path / name
    source.write_text((FIXTURES / name).read_text(encoding="utf-8"), encoding="utf-8")
    os.utime(source, (mtime, mtime))
    return source


def test_select_occurrence_falls_back_to_file_mtime_for_dateless_teams_vtt(tmp_path: Path) -> None:
    # 2026-07-16 00:00:00 UTC download time for a meeting held 2026-07-10.
    source = _copy_fixture(tmp_path, "Daily Stand Up - Post-MVP (41).vtt", mtime=1784160000)

    selection = select_occurrence(source, source.read_text(encoding="utf-8"))

    assert selection.chosen.value == "2026-07-16"
    assert selection.chosen.confidence == "low"
    assert selection.chosen.source == "file_mtime"
    assert selection.conflict is False
    assert [c.source for c in selection.candidates] == ["file_mtime"]


def test_select_occurrence_override_wins_and_is_manual(tmp_path: Path) -> None:
    source = _copy_fixture(tmp_path, "Daily Stand Up - Post-MVP (42).vtt", mtime=1784160000)

    selection = select_occurrence(source, source.read_text(encoding="utf-8"), override="2026-07-13")

    assert selection.chosen.value == "2026-07-13"
    assert selection.chosen.confidence == "manual"
    assert selection.chosen.source == "override"


def test_select_occurrence_flags_conflicting_trusted_candidates(tmp_path: Path) -> None:
    source = tmp_path / "2026-07-02-standup.txt"
    source.write_text("Team Standup-20260701_090000-Meeting Transcript\n", encoding="utf-8")

    selection = select_occurrence(source, source.read_text(encoding="utf-8"))

    assert selection.chosen.value == "2026-07-01"
    assert selection.chosen.source == "content"
    assert selection.conflict is True


def test_extract_source_threads_meeting_date_override(tmp_path: Path) -> None:
    source = _copy_fixture(tmp_path, "Daily Stand Up - Post-MVP (41).vtt", mtime=1784160000)

    result = extract_source(source, meeting_date="2026-07-10")

    assert result.effective_date.value == "2026-07-10"
    assert result.effective_date.confidence == "manual"
    assert result.effective_date.source == "override"
    assert result.date_selection is not None
    assert result.date_selection.conflict is False
```

Add `select_occurrence` to the imports from `meeting_ingest.extract`.

- [ ] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/test_extract.py -v`
Expected: the four new tests FAIL (ImportError on `select_occurrence` first).

- [ ] **Step 4: Implement candidate selection**

In `src/meeting_ingest/extract.py`, add after the `EffectiveDate` dataclass:

```python
@dataclass(frozen=True)
class OccurrenceCandidate:
    value: str
    confidence: str
    source: str


@dataclass(frozen=True)
class OccurrenceSelection:
    chosen: EffectiveDate
    candidates: tuple[OccurrenceCandidate, ...]
    conflict: bool
```

Add `date_selection: OccurrenceSelection | None = None` as the last field of `SourceExtraction`.

Replace the body of `infer_effective_date` and add `select_occurrence`:

```python
def select_occurrence(path: Path, content: str = "", *, override: str | None = None) -> OccurrenceSelection:
    candidates: list[OccurrenceCandidate] = []
    if override is not None:
        candidates.append(OccurrenceCandidate(value=override, confidence="manual", source="override"))

    content_date = _date_from_content(content)
    if content_date is not None:
        candidates.append(OccurrenceCandidate(value=content_date, confidence="high", source="content"))

    for pattern in _DATE_PATTERNS:
        match = pattern.search(path.name)
        if match:
            date_value = _valid_date(match.group("year"), match.group("month"), match.group("day"))
            if date_value is not None:
                candidates.append(OccurrenceCandidate(value=date_value, confidence="high", source="filename"))
                break

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
    candidates.append(OccurrenceCandidate(value=modified.strftime("%Y-%m-%d"), confidence="low", source="file_mtime"))

    chosen_candidate = candidates[0]
    trusted_values = {candidate.value for candidate in candidates if candidate.source != "file_mtime"}
    return OccurrenceSelection(
        chosen=EffectiveDate(
            value=chosen_candidate.value,
            confidence=chosen_candidate.confidence,
            source=chosen_candidate.source,
        ),
        candidates=tuple(candidates),
        conflict=len(trusted_values) > 1,
    )


def infer_effective_date(path: Path, content: str = "") -> EffectiveDate:
    return select_occurrence(path, content).chosen
```

The mtime candidate is always appended last, so `candidates` always ends with the fallback, precedence selection is simply `candidates[0]`, and the fixture test's `[c.source for c in selection.candidates] == ["file_mtime"]` holds when no other evidence exists. The filename loop `break`s on the first matching pattern so at most one filename candidate is recorded.

Update `extract_source` to accept and thread the override:

```python
def extract_source(path: Path, *, meeting_date: str | None = None) -> SourceExtraction:
```

and replace the return statement's `effective_date=infer_effective_date(path, raw_text)` with:

```python
    selection = select_occurrence(path, raw_text, override=meeting_date)
    return SourceExtraction(
        path=path,
        source_format=source_format,
        raw_text=raw_text,
        normalized_text=normalized,
        effective_date=selection.chosen,
        duration=_duration_from_content(raw_text),
        date_selection=selection,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_extract.py -v`
Expected: all tests PASS, including the pre-existing mtime-fallback and invalid-filename-date tests (they exercise `infer_effective_date`, which now delegates).

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest`
Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add tests/fixtures/teams-vtt src/meeting_ingest/extract.py tests/test_extract.py
git commit -m "feat: add deterministic occurrence candidate selection with sanitized Teams VTT fixtures"
```

---

### Task 3: Thread `--meeting-date` through pipeline and CLI; warn on file-mtime fallback and evidence conflicts

**Files:**
- Modify: `src/meeting_ingest/pipeline.py` (`ingest`, `provider_request`, `_ingest_locked`, `_provider_request_locked`, `_prepare_ingest`, `_finish_ingest`; new helpers `_validate_meeting_date`, `_date_warnings`)
- Modify: `src/meeting_ingest/cli.py` (add `--meeting-date` to `ingest` and `provider-request` parsers and pass through)
- Test: `tests/test_pipeline_ingest.py`, `tests/test_cli_scaffold.py`

**Interfaces:**
- Consumes: `extract_source(path, meeting_date=...)`, `SourceExtraction.date_selection` from Task 2.
- Produces (used by Task 4's contract text and Task 6's operational step):
  - `pipeline.ingest(..., meeting_date: str | None = None)`
  - `pipeline.provider_request(..., meeting_date: str | None = None)`
  - `pipeline._validate_meeting_date(value: str) -> str` raising `ConfigError(code="invalid_meeting_date")`
  - `pipeline._date_warnings(extraction) -> list[str]` producing the two warning strings below (exact text is contract-adjacent; keep stable):
    - mtime: `f"effective date {value} was inferred from file modification time and may be a download date rather than the meeting occurrence; re-run with --meeting-date YYYY-MM-DD or fix later with repair-date"`
    - conflict: `f"conflicting meeting date evidence ({listing}); selected {source}={value}"` where `listing` joins non-`file_mtime` candidates as `f"{c.source}={c.value}"` with `", "`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_pipeline_ingest.py`, find the existing mock-provider ingest test helpers (project init + inbox source setup) and reuse them. Add:

```python
def test_ingest_warns_when_effective_date_comes_from_file_mtime(tmp_path: Path) -> None:
    paths = _init_project(tmp_path)  # use this file's existing project-setup helper name
    source = paths.inbox / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text(
        (Path(__file__).parent / "fixtures" / "teams-vtt" / "Daily Stand Up - Post-MVP (41).vtt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))

    summary = pipeline.ingest(source, start=tmp_path, provider="mock")

    assert summary.status == "success"
    assert any("file modification time" in warning for warning in summary.warnings)
    assert summary.meeting_id is not None and summary.meeting_id.startswith("mtg-20260716-")


def test_ingest_meeting_date_override_mints_ids_from_override(tmp_path: Path) -> None:
    paths = _init_project(tmp_path)
    source = paths.inbox / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text(
        (Path(__file__).parent / "fixtures" / "teams-vtt" / "Daily Stand Up - Post-MVP (41).vtt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))

    summary = pipeline.ingest(source, start=tmp_path, provider="mock", meeting_date="2026-07-10")

    assert summary.status == "success"
    assert summary.meeting_id is not None and summary.meeting_id.startswith("mtg-20260710-")
    assert not any("file modification time" in warning for warning in summary.warnings)
    artifact_path = tmp_path / "_local/project-context/meetings" / summary.artifacts[0]["path"]
    front_matter = artifact_path.read_text(encoding="utf-8")
    assert "date: 2026-07-10" in front_matter
    assert "date_confidence: manual" in front_matter
    assert "date_source: override" in front_matter


def test_ingest_rejects_invalid_meeting_date(tmp_path: Path) -> None:
    paths = _init_project(tmp_path)
    source = paths.inbox / "meeting.txt"
    source.write_text("Ken: Hello\n", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        pipeline.ingest(source, start=tmp_path, provider="mock", meeting_date="2026-13-40")

    assert excinfo.value.code == "invalid_meeting_date"


def test_provider_request_warns_when_effective_date_comes_from_file_mtime(tmp_path: Path) -> None:
    paths = _init_project_with_session_provider(tmp_path)  # reuse/extend this file's session-enabled setup
    source = paths.inbox / "Daily Stand Up - Post-MVP (42).vtt"
    source.write_text(
        (Path(__file__).parent / "fixtures" / "teams-vtt" / "Daily Stand Up - Post-MVP (42).vtt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))

    summary = pipeline.provider_request(source, start=tmp_path)

    assert summary.status == "success"
    assert any("file modification time" in warning for warning in summary.warnings)
```

Adapt the two setup-helper names to whatever `tests/test_pipeline_ingest.py` actually defines (read the file first); if no session-enabled helper exists, write the config with `allow_session_provider = true` the same way existing session tests in `tests/test_session_inbox.py` do. Import `ConfigError` from `meeting_ingest.errors` and `os` as needed.

In `tests/test_cli_scaffold.py`, add:

```python
def test_cli_parses_meeting_date_for_ingest_and_provider_request() -> None:
    parser = build_parser()
    ingest_args = parser.parse_args(["ingest", "meeting.vtt", "--meeting-date", "2026-07-10"])
    assert ingest_args.meeting_date == "2026-07-10"
    request_args = parser.parse_args(["provider-request", "meeting.vtt", "--meeting-date", "2026-07-13"])
    assert request_args.meeting_date == "2026-07-13"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_pipeline_ingest.py tests/test_cli_scaffold.py -v`
Expected: new tests FAIL (`TypeError: ingest() got an unexpected keyword argument 'meeting_date'`, missing attr `meeting_date`).

- [ ] **Step 3: Implement pipeline threading and warnings**

In `src/meeting_ingest/pipeline.py`:

Add near `_validate_ingest_options`:

```python
_MEETING_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _validate_meeting_date(value: str) -> str:
    if _MEETING_DATE.match(value):
        try:
            datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            pass
        else:
            return value
    raise ConfigError(
        f"--meeting-date must be a real calendar date in YYYY-MM-DD form, got: {value}",
        code="invalid_meeting_date",
    )


def _date_warnings(extraction) -> list[str]:
    warnings: list[str] = []
    effective = extraction.effective_date
    if effective.source == "file_mtime":
        warnings.append(
            f"effective date {effective.value} was inferred from file modification time and may be a "
            "download date rather than the meeting occurrence; re-run with --meeting-date YYYY-MM-DD "
            "or fix later with repair-date"
        )
    selection = getattr(extraction, "date_selection", None)
    if selection is not None and selection.conflict:
        listing = ", ".join(
            f"{candidate.source}={candidate.value}"
            for candidate in selection.candidates
            if candidate.source != "file_mtime"
        )
        warnings.append(
            f"conflicting meeting date evidence ({listing}); selected {effective.source}={effective.value}"
        )
    return warnings
```

(`datetime` is already imported in pipeline.py via clock usage — verify; add `from datetime import datetime` if absent.)

Thread the parameter:

- `ingest(...)`: add `meeting_date: str | None = None` keyword; pass `meeting_date=meeting_date` to `_ingest_locked`. (Session phase 2 via `--provider-response` does not take the override — the persisted request already carries the date; raise `ConfigError("--meeting-date is not valid with --provider-response; the persisted request already fixes the date.", code="invalid_meeting_date_phase")` if both are supplied.)
- `_ingest_locked(...)`: add `meeting_date: str | None` parameter, pass to `_prepare_ingest`.
- `provider_request(...)` and `_provider_request_locked(...)`: same threading.
- `_prepare_ingest(source, *, paths, clock, meeting_date: str | None = None)`: validate first (`if meeting_date is not None: meeting_date = _validate_meeting_date(meeting_date)`), then `extraction = extract_source(source, meeting_date=meeting_date)`.

Surface the warnings:

- In `_finish_ingest`, after the collision warning block, add `warnings.extend(_date_warnings(extraction))`.
- In `_provider_request_locked`, add `warnings=_date_warnings(prepared.extraction),` to the returned `RunSummary`.

In `src/meeting_ingest/cli.py`:

- Add to both the `ingest` and `provider-request` parsers: `.add_argument("--meeting-date", dest="meeting_date", help="Known meeting occurrence date (YYYY-MM-DD); overrides inferred dates.")`
- Pass `meeting_date=args.meeting_date` in the corresponding `pipeline.ingest(...)` and `pipeline.provider_request(...)` calls in `run()`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_pipeline_ingest.py tests/test_cli_scaffold.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest`
Expected: all pass. If any existing session-inbox or provider-render test asserts exact `warnings == []` for mtime-dated temp sources, update those fixtures to carry a dated filename (e.g. prefix `2026-07-03-`) rather than weakening assertions.

- [ ] **Step 6: Commit**

```bash
git add src/meeting_ingest/pipeline.py src/meeting_ingest/cli.py tests/test_pipeline_ingest.py tests/test_cli_scaffold.py
git commit -m "feat: add --meeting-date override and prominent low-confidence date warnings"
```

---

### Task 4: Implement `repair-date`

**Files:**
- Modify: `src/meeting_ingest/pipeline.py` (new `repair_date`, `_repair_date_locked`, `_rewrite_front_matter_date`, `_repaired_artifact_path`, `_rewrite_signal_effective_at`)
- Modify: `src/meeting_ingest/cli.py` (new `repair-date` subcommand)
- Test: `tests/test_repair_date.py` (new file)

**Interfaces:**
- Consumes: `_validate_meeting_date` (Task 3), `read_records`/`append_snapshot`/`LedgerSnapshot` from `ledger.py`, `ProjectLock`/`lock_path`, `load_project`.
- Produces: `pipeline.repair_date(selector: str, *, date: str, start: Path | None = None, clock: Clock | None = None) -> RunSummary`; ledger event `date_repaired` exactly as frozen in Task 1.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_repair_date.py`:

```python
from pathlib import Path
import json
import os

import pytest

from meeting_ingest import pipeline
from meeting_ingest.errors import MeetingIngestError
from meeting_ingest.ledger import read_records


FIXTURES = Path(__file__).parent / "fixtures" / "teams-vtt"
MEETINGS_RELATIVE = Path("_local/project-context/meetings")


def _ingest_mtime_dated_standup(tmp_path: Path) -> tuple[Path, str]:
    pipeline.initialize(tmp_path)
    meetings_root = tmp_path / MEETINGS_RELATIVE
    source = meetings_root / "_inbox" / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text((FIXTURES / "Daily Stand Up - Post-MVP (41).vtt").read_text(encoding="utf-8"), encoding="utf-8")
    os.utime(source, (1784160000, 1784160000))  # 2026-07-16, download date
    summary = pipeline.ingest(source, start=tmp_path, provider="mock")
    assert summary.status == "success"
    return meetings_root, summary.meeting_id


def test_repair_date_renames_artifact_rewrites_metadata_and_appends_ledger(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)

    summary = pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    assert summary.status == "success"
    assert summary.exit_code == 0
    assert summary.meeting_id == meeting_id  # meeting_id unchanged, still embeds 20260716

    records = read_records(meetings_root / "_ledger.jsonl")
    repaired = [r for r in records if r["event"] == "date_repaired"]
    assert len(repaired) == 1
    record = repaired[0]
    assert record["meeting_id"] == meeting_id
    assert record["ingest_run_id"] is None
    assert record["repair"]["previous_date"] == "2026-07-16"
    assert record["repair"]["previous_date_source"] == "file_mtime"
    assert record["repair"]["date"] == "2026-07-10"

    (mode_entry,) = record["artifacts"].values()
    new_path = meetings_root / mode_entry["path"]
    assert mode_entry["path"].startswith("2026-07-10-")
    assert new_path.exists()
    content = new_path.read_text(encoding="utf-8")
    assert "date: 2026-07-10" in content
    assert "date_confidence: manual" in content
    assert "date_source: repair" in content
    assert f"meeting_id: {meeting_id}" in content  # unchanged

    old_paths = list(meetings_root.glob("2026-07-16-*.md"))
    assert old_paths == []

    signal_path = meetings_root / "_signals" / f"{meeting_id}.jsonl"
    signal_lines = [json.loads(line) for line in signal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert signal_lines, "mock provider must emit at least one signal for this test"
    assert all(line["effective_at"] == "2026-07-10" for line in signal_lines)
    assert all(line["meeting_id"] == meeting_id for line in signal_lines)


def test_repair_date_accepts_source_sha_selector(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    records = read_records(meetings_root / "_ledger.jsonl")
    source_sha = records[-1]["source_sha256"]

    summary = pipeline.repair_date(source_sha, date="2026-07-10", start=tmp_path)

    assert summary.status == "success"
    assert summary.meeting_id == meeting_id


def test_repair_date_is_a_no_op_when_date_already_matches(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)
    before = (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8")

    summary = pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    assert summary.status == "no_op"
    assert summary.exit_code == 0
    assert (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8") == before


def test_repair_date_fails_for_unknown_selector(tmp_path: Path) -> None:
    _ingest_mtime_dated_standup(tmp_path)

    with pytest.raises(MeetingIngestError) as excinfo:
        pipeline.repair_date("mtg-20990101-deadbeef", date="2026-07-10", start=tmp_path)

    assert excinfo.value.code == "repair_target_not_found"


def test_repair_date_fails_without_ledger_append_when_artifact_missing(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    for artifact in meetings_root.glob("2026-07-16-*.md"):
        artifact.unlink()
    before = (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8")

    with pytest.raises(MeetingIngestError) as excinfo:
        pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)

    assert excinfo.value.code == "repair_artifact_missing"
    assert (meetings_root / "_ledger.jsonl").read_text(encoding="utf-8") == before
```

If the mock provider emits zero communication signals, adjust `_ingest_mtime_dated_standup` to assert the signal file exists (it is always written, possibly empty) and drop the non-empty assertion — check `src/meeting_ingest/providers/mock.py` first and keep the strongest assertion that holds.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_repair_date.py -v`
Expected: FAIL with `AttributeError: module 'meeting_ingest.pipeline' has no attribute 'repair_date'`.

- [ ] **Step 3: Implement `repair_date` in `pipeline.py`**

```python
def repair_date(
    selector: str,
    *,
    date: str,
    start: Path | None = None,
    clock: Clock | None = None,
) -> RunSummary:
    new_date = _validate_meeting_date(date)
    _, paths = load_project(start or Path.cwd())
    with ProjectLock(lock_path(paths.cache), clock=clock):
        return _repair_date_locked(selector, new_date=new_date, paths=paths, clock=clock)


def _repair_date_locked(selector: str, *, new_date: str, paths: ProjectPaths, clock: Clock | None) -> RunSummary:
    target: dict[str, Any] | None = None
    for record in read_records(paths.ledger):
        if selector in (record.get("meeting_id"), record.get("source_sha256")) and _record_has_primary_artifacts(record):
            target = record
    if target is None:
        raise MeetingIngestError(
            phase="repair",
            code="repair_target_not_found",
            message=f"No ready ingest found for selector: {selector}",
            exit_code=EXIT_USAGE_OR_CONFIG,
            recoverable=True,
            details={"selector": selector},
        )

    meeting_id = str(target["meeting_id"])
    artifacts = {mode: dict(entry) for mode, entry in target.get("artifacts", {}).items() if isinstance(entry, dict)}
    for mode, entry in artifacts.items():
        artifact_path = paths.meetings_root / str(entry.get("path", ""))
        if not entry.get("path") or not artifact_path.exists():
            raise MeetingIngestError(
                phase="repair",
                code="repair_artifact_missing",
                message=f"Artifact for mode {mode!r} is missing: {entry.get('path')}",
                exit_code=EXIT_ARTIFACT_WRITE,
                recoverable=False,
                details={"mode": mode, "path": entry.get("path")},
            )

    first_entry = next(iter(artifacts.values()))
    previous = _front_matter_date_fields(paths.meetings_root / str(first_entry["path"]))
    paths_already_repaired = all(
        Path(str(entry["path"])).name.startswith(f"{new_date}-") for entry in artifacts.values()
    )
    if previous.get("date") == new_date and paths_already_repaired:
        return RunSummary(
            status="no_op",
            exit_code=0,
            source_sha256=str(target["source_sha256"]),
            meeting_id=meeting_id,
            details={"command": "repair-date", "date": new_date, "reason": "date_already_current"},
        )

    warnings: list[str] = []
    changed_modes: list[str] = []
    for mode, entry in artifacts.items():
        old_path = paths.meetings_root / str(entry["path"])
        slug = str(entry.get("slug") or re.sub(r"^\d{4}-\d{2}-\d{2}-", "", old_path.stem))
        destination = _repaired_artifact_path(paths, new_date, slug, current=old_path)
        content = _rewrite_front_matter_date(
            old_path.read_text(encoding="utf-8"), date=new_date, confidence="manual", source="repair"
        )
        destination.path.write_text(content, encoding="utf-8")
        if destination.path != old_path:
            old_path.unlink()
        if destination.collision:
            warnings.append(f"artifact filename collision; wrote {destination.path.relative_to(paths.meetings_root)}")
        entry["path"] = str(destination.path.relative_to(paths.meetings_root))
        changed_modes.append(mode)

    signals_state = dict(target.get("signals", {})) if isinstance(target.get("signals"), dict) else {}
    if signals_state.get("path"):
        _rewrite_signal_effective_at(paths.meetings_root / str(signals_state["path"]), new_date=new_date)

    append_snapshot(
        paths.ledger,
        LedgerSnapshot(
            event="date_repaired",
            source_sha256=str(target["source_sha256"]),
            meeting_id=meeting_id,
            ingest_run_id=None,
            source=dict(target.get("source", {})),
            artifacts=artifacts,
            signals=signals_state,
            reconcile=dict(target.get("reconcile", {})),
            derived=dict(target.get("derived", {"playbook_update_status": "not_applicable"})),
        ),
        clock=clock,
    )
    return RunSummary(
        status="success",
        exit_code=0,
        source_sha256=str(target["source_sha256"]),
        meeting_id=meeting_id,
        artifacts=[
            {"kind": "markdown", "mode": mode, "status": "ready", "path": str(entry["path"])}
            for mode, entry in artifacts.items()
        ],
        warnings=warnings,
        details={
            "command": "repair-date",
            "repair": {
                "previous_date": previous.get("date"),
                "previous_date_confidence": previous.get("date_confidence"),
                "previous_date_source": previous.get("date_source"),
                "date": new_date,
                "changed_modes": changed_modes,
            },
        },
    )
```

The ledger `repair` block must also land in the snapshot, and `LedgerSnapshot` has no `repair` field. Add an optional field to `LedgerSnapshot` in `src/meeting_ingest/ledger.py`:

```python
    repair: dict[str, Any] | None = None
```

and in `to_dict`, after `"reconcile": self.reconcile,` add:

```python
        **({"repair": self.repair} if self.repair is not None else {}),
```

Then pass to the snapshot in `_repair_date_locked`:

```python
            repair={
                "previous_date": previous.get("date"),
                "previous_date_confidence": previous.get("date_confidence"),
                "previous_date_source": previous.get("date_source"),
                "date": new_date,
                "changed_modes": changed_modes,
            },
```

(The `title_repaired` contract also uses a `repair` block, so this field serves both when title repair is implemented later.)

Helpers:

```python
def _front_matter_date_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return fields
    for line in lines[1:]:
        if line.strip() == "---":
            break
        for key in ("date", "date_confidence", "date_source"):
            prefix = f"{key}: "
            if line.startswith(prefix):
                fields[key] = line[len(prefix):].strip()
    return fields


def _rewrite_front_matter_date(content: str, *, date: str, confidence: str, source: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    replacements = {"date": date, "date_confidence": confidence, "date_source": source}
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            break
        for key, value in replacements.items():
            if lines[index].startswith(f"{key}: "):
                lines[index] = f"{key}: {value}"
    return "\n".join(lines) + ("\n" if content.endswith("\n") else "")


def _repaired_artifact_path(paths: ProjectPaths, new_date: str, slug: str, *, current: Path) -> _ArtifactPath:
    base = f"{new_date}-{slug}"
    candidate = paths.meetings_root / f"{base}.md"
    collision = False
    counter = 2
    while candidate.exists() and candidate != current:
        collision = True
        candidate = paths.meetings_root / f"{base}-{counter}.md"
        counter += 1
    return _ArtifactPath(path=candidate, collision=collision)


def _rewrite_signal_effective_at(path: Path, *, new_date: str) -> None:
    if not path.exists():
        return
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        record["effective_at"] = new_date
        lines.append(json.dumps(record, sort_keys=True))
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
```

Imports needed in pipeline.py (verify which already exist): `json`, `EXIT_USAGE_OR_CONFIG`, `EXIT_ARTIFACT_WRITE`, `MeetingIngestError` from `meeting_ingest.errors`, `read_records` from `meeting_ingest.ledger`, `Any` from `typing`.

**Critical current-state fix:** after a repair, the `date_repaired` snapshot is the latest ledger record for the source, so it must count as carrying current primary-artifact state. In `src/meeting_ingest/pipeline.py:1089`, extend the event set in `_record_has_primary_artifacts`:

```python
    if record.get("event") not in {"primary_artifacts_ready", "ingest_completed", "reconcile_repaired", "date_repaired"}:
        return False
```

Without this, a second `repair-date` resolves the pre-repair record (whose artifact path no longer exists) and fails instead of no-opping, and re-ingesting an already-repaired source would not be detected as a duplicate. The no-op test and the duplicate test below cover both regressions. Add this duplicate test to `tests/test_repair_date.py`:

```python
def test_reingest_after_repair_is_still_a_no_op(tmp_path: Path) -> None:
    meetings_root, meeting_id = _ingest_mtime_dated_standup(tmp_path)
    pipeline.repair_date(meeting_id, date="2026-07-10", start=tmp_path)
    processed = next((meetings_root / "_processed").iterdir())

    summary = pipeline.ingest(processed, start=tmp_path, provider="mock")

    assert summary.status == "no_op"
```

In `src/meeting_ingest/cli.py`, add to `build_parser()`:

```python
    repair_date_parser = subparsers.add_parser("repair-date")
    repair_date_parser.add_argument("selector", help="meeting_id or full source_sha256 of the ingest to repair.")
    repair_date_parser.add_argument("--date", required=True, help="Correct meeting occurrence date (YYYY-MM-DD).")
    repair_date_parser.add_argument("--root", default=".", help="Path used for project discovery.")
    repair_date_parser.add_argument("--json", action="store_true", help="Emit a machine-readable run summary.")
```

and to `run()` before the final `raise AssertionError`:

```python
    if args.command == "repair-date":
        return pipeline.repair_date(args.selector, date=args.date, start=Path(args.root))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_repair_date.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest`
Expected: all pass (ledger `to_dict` change is additive; existing ledger tests asserting exact dict shapes must still pass because `repair` is omitted when `None` — if a test asserts exact key sets, confirm it still holds).

- [ ] **Step 6: Commit**

```bash
git add src/meeting_ingest/pipeline.py src/meeting_ingest/cli.py src/meeting_ingest/ledger.py tests/test_repair_date.py
git commit -m "feat: add repair-date command with date_repaired ledger snapshots"
```

---

### Task 5: Doctor check for low-confidence meeting dates

**Files:**
- Modify: `src/meeting_ingest/doctor.py` (new `_low_confidence_date_issues`, wired into `find_issues`)
- Test: `tests/test_doctor_status.py`

**Interfaces:**
- Consumes: `_current_records`, `_has_primary_artifacts`, `DoctorIssue` in `doctor.py`; front-matter format written by `render.py`.
- Produces: doctor issue code `low_confidence_meeting_date` with the artifact's relative path.

- [ ] **Step 1: Write the failing tests**

In `tests/test_doctor_status.py` (reuse this file's existing project/ingest setup helpers — read it first; the ingest-a-source pattern from Task 4's `_ingest_mtime_dated_standup` works here too):

```python
def test_doctor_reports_low_confidence_meeting_date_and_clears_after_repair(tmp_path: Path) -> None:
    pipeline.initialize(tmp_path)
    meetings_root = tmp_path / "_local/project-context/meetings"
    source = meetings_root / "_inbox" / "Daily Stand Up - Post-MVP (41).vtt"
    source.write_text(
        (Path(__file__).parent / "fixtures" / "teams-vtt" / "Daily Stand Up - Post-MVP (41).vtt").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    os.utime(source, (1784160000, 1784160000))
    summary = pipeline.ingest(source, start=tmp_path, provider="mock")

    doctor_summary = pipeline.doctor(tmp_path)
    issue_codes = [issue["code"] for issue in doctor_summary.to_dict()["issues"]]
    assert "low_confidence_meeting_date" in issue_codes

    pipeline.repair_date(summary.meeting_id, date="2026-07-10", start=tmp_path)

    doctor_summary = pipeline.doctor(tmp_path)
    issue_codes = [issue["code"] for issue in doctor_summary.to_dict()["issues"]]
    assert "low_confidence_meeting_date" not in issue_codes
```

Adapt the `doctor` summary access to the actual `doctor --json` shape documented in this test file (read how existing tests extract issues — it may be `details["issues"]`).

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_doctor_status.py -v`
Expected: new test FAILS on the first `assert "low_confidence_meeting_date" in issue_codes`.

- [ ] **Step 3: Implement the check**

In `src/meeting_ingest/doctor.py`, add:

```python
def _low_confidence_date_issues(paths: ProjectPaths, records: list[dict[str, object]]) -> list[DoctorIssue]:
    issues: list[DoctorIssue] = []
    for record in _current_records(records):
        if not _has_primary_artifacts(record):
            continue
        artifacts = record.get("artifacts", {})
        if not isinstance(artifacts, dict):
            continue
        for artifact in artifacts.values():
            if not isinstance(artifact, dict) or not artifact.get("path"):
                continue
            artifact_path = paths.meetings_root / str(artifact["path"])
            if not artifact_path.exists():
                continue
            if _front_matter_value(artifact_path, "date_source") == "file_mtime":
                issues.append(
                    DoctorIssue(
                        code="low_confidence_meeting_date",
                        message="Artifact meeting date came from file modification time and may be a download date; verify and fix with repair-date.",
                        path=str(artifact["path"]),
                    )
                )
    return issues


def _front_matter_value(path: Path, key: str) -> str | None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    if not lines or lines[0].strip() != "---":
        return None
    prefix = f"{key}: "
    for line in lines[1:]:
        if line.strip() == "---":
            return None
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None
```

Wire into `find_issues` after the `_current_records` loop (it already has `records` in scope):

```python
    issues.extend(_low_confidence_date_issues(paths, records))
```

Also extend the event set in doctor's `_has_primary_artifacts` (`src/meeting_ingest/doctor.py:183`) to include `"date_repaired"`, mirroring the pipeline fix from Task 4 — otherwise every current-state doctor check (missing artifact/signal/processed-source, incomplete reconcile, and this new check) silently skips any source whose latest ledger record is a repair:

```python
    if record.get("event") not in {"primary_artifacts_ready", "ingest_completed", "reconcile_repaired", "date_repaired"}:
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_doctor_status.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add src/meeting_ingest/doctor.py tests/test_doctor_status.py
git commit -m "feat: surface low-confidence meeting dates in doctor"
```

---

### Task 6: Status-doc reconciliation and live-corpus repair

**Files:**
- Modify: `docs/product-status.md` (move the five effective-date "Remaining" items under Layer 1 to Done; update the "Known limitation" block under Source Extraction)
- Modify: `docs/implementation-plan.md` (same reconciliation in the Layer 1 section; move the two decided items out of "Needs design decision": repair-date contract → decided/frozen, contextual date evidence → explicitly deferred)
- Modify: `README.md` (only if it enumerates CLI commands/flags — read it first; add `--meeting-date` and `repair-date` where commands are documented)

**Interfaces:**
- Consumes: everything shipped in Tasks 1–5.
- Produces: docs that match reality, plus the live `_local/project-context/meetings` corpus repaired through the engine.

- [ ] **Step 1: Reconcile the docs**

In `docs/product-status.md`: under "Source Extraction → Known limitation" replace the three bullets with the new state (candidate selection implemented, `--meeting-date` and `repair-date` implemented, file-mtime fallback now warns). Under "Layer 1 → Remaining", move these to Done: occurrence reliability for downloaded transcripts, occurrence/acquisition distinction in the engine-facing contract, manual override + controlled repair path, mtime warning. Leave title-inference-quality and provider-title-confidence items in Remaining. Make the equivalent edits in `docs/implementation-plan.md` Layer 1 (Remaining → Done for the five date items; "Needs design decision" loses the repair-date-contract bullet and the contextual-evidence bullet becomes "deferred: contextual date evidence — frozen out of v1 candidate selection").

- [ ] **Step 2: Verify and commit**

Run: `uv run pytest` (green), then:

```bash
git add docs/product-status.md docs/implementation-plan.md README.md
git commit -m "docs: reconcile product status after effective-date reliability landed"
```

- [ ] **Step 3: Surface the affected live artifacts**

Run from the repo root:

```bash
uv run meeting-ingest doctor --root . --json
```

Expected: three `low_confidence_meeting_date` issues, for
`2026-07-03-nitesh-follow-up-interview-debrief.md`,
`2026-07-03-wide-orbit-orchestration-and-uat-readiness-working-session.md`, and
`2026-07-07-fable-5-agent-workflow-and-model-routing-review.md`.

- [ ] **Step 4: Repair with operator-confirmed dates — BLOCKED ON USER INPUT**

The true occurrence dates are operator knowledge (the July 10/13 capture refers to observed standups; the three flagged artifacts carry download-time dates). Ask the user for the correct date of each flagged meeting, then repair each one through the engine, e.g.:

```bash
uv run meeting-ingest repair-date mtg-20260703-63d2e869 --date <confirmed-date> --json
```

Do not guess dates. If the user also has the July 10/13 standup VTTs still to ingest, ingest them with `--meeting-date 2026-07-10` / `--meeting-date 2026-07-13`.

- [ ] **Step 5: Verify the live corpus is clean**

Run: `uv run meeting-ingest doctor --root . --json`
Expected: no `low_confidence_meeting_date` issues (for every artifact the user provided a date for).

---

## Verification (whole plan)

- `uv run pytest` green (133 pre-existing + new tests).
- `uv run meeting-ingest ingest <dateless vtt> --provider mock --json` on a scratch project shows the mtime warning and `date_source: file_mtime`.
- Same ingest with `--meeting-date` shows no warning, `date_source: override`, and a `mtg-<override-date>-...` meeting ID.
- `repair-date` round-trip: artifact renamed, front matter and signal `effective_at` rewritten, `date_repaired` appended, `meeting_id`/`signal_id` untouched, second run is a `no_op`.
- `doctor` flags and then clears `low_confidence_meeting_date`.
