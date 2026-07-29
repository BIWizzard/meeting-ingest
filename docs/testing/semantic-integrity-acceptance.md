# Semantic Integrity Acceptance Run

This document defines the acceptance run that evaluates provider semantic judgment for the semantic-integrity guardrails slice. It is the manual half of a deliberately split verification model.

## Verification Split

`pytest` proves deterministic grounding and lifecycle behavior. Every check that compares provider output against exact transcript facts — verbatim speaker labels, retained turn timestamps, required evidence speakers, tampered request grounding, preflight side-effect freedom, phase-2 failure retention — is a repository test and runs on every commit.

The session-provider acceptance run plus human and independent blind review evaluates the semantic assertions: time context, epistemic certainty, proposal and action disposition, identity ambiguity, and TL;DR consistency. These cannot be proven from arbitrary natural language, so they are a versioned prompt contract measured by acceptance evidence.

No second model or judge call is added to normal ingest. Acceptance evaluation carries that weight instead.

Installed home-directory workflow copies are outside `pytest` entirely. Their verification is described under [Workflow Copy Verification](#workflow-copy-verification).

## Fixture

| Item | Path |
|---|---|
| Acceptance transcript | `tests/fixtures/semantic-integrity/session-provider-eval.vtt` |
| Expected assertions | `tests/fixtures/semantic-integrity/expected-review.json` |

Both files are wholly synthetic: invented people, invented systems, invented incident. They reproduce five observed defect patterns without carrying any private corpus source text.

The transcript contains:

1. two speaker labels with a `(Contractor)` qualifier and one without;
2. an unlabeled `10:06` run explicitly established as the last run of the night, with a nearby manual retry before midnight;
3. an observed merge abort whose root cause is explicitly unconfirmed, alongside a stated guess;
4. a proposed loader split that the putative owners reject as infeasible and park;
5. the nickname `Ro`, which could plausibly mean the attendee `Villanueva, Rosa` but which later dialogue points at a separate absent person.

`expected-review.json` carries the machine-readable assertions. It is not a golden prose summary: a correct run may word its output freely as long as every assertion holds. Assertion IDs `DG*` are deterministic and blocking; `S*` are semantic, and each names the `semantic_guidance_version` `1.1` rule it enforces. The `DG` prefix is deliberate: bare `D1`/`D2` are the local decision IDs the response payload itself uses, and a recorded result table must not blur the two.

## Release Evidence Versus Development Evidence

A release-evidence run uses the approved immutable build in a freshly pinned consumer project, with `readiness` reporting `ready` or `ready_with_history_warnings`. Only such a run is milestone proof.

Any run that needs `--development-override`, uses an editable checkout, or reports `development_override` is development evidence and must be labeled non-release in the record. Codex runs are development/non-release evidence regardless of verdict; Claude Code is the reference host.

## Prepare A Temporary Consumer Project

Use an explicit temporary root and remove it when the run is recorded. The project holds transcript-bearing runtime files under `_cache/` and must not be created inside this repository or inside a client project.

```bash
ACCEPTANCE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/meeting-ingest-acceptance.XXXXXX")"
MEETING_INGEST="$HOME/.local/bin/meeting-ingest"   # approved frozen executable
RECEIPT_PATH="<release-store>/releases/<build-id>/receipt.json"
REPO="$PWD"                                        # this repository
```

Install the receipt-verified workflow artifacts into the acceptance root before pinning. `runtime pin` verifies the project-level copies at `<root>/.claude/`, and those same copies shadow the user-level install for a Claude Code session started in that directory — so they are both the pin's evidence and the instructions that actually shape the run:

```bash
"$REPO/scripts/install-approved-skill.py" \
  --receipt "$RECEIPT_PATH" \
  --template "$REPO/docs/claude-skills/meeting-ingest/SKILL.md" \
  --executable "$MEETING_INGEST" \
  --skill-destination "$ACCEPTANCE_ROOT/.claude/skills/meeting-ingest/SKILL.md" \
  --agent "$REPO/docs/claude-agents/meeting-ingest-session-provider.md" \
  --agent-destination "$ACCEPTANCE_ROOT/.claude/agents/meeting-ingest-session-provider.md" \
  --json
```

Pin the acceptance project to the approved receipt. `runtime pin` is a bootstrap mutation outside project readiness, so it runs before `init`:

```bash
"$MEETING_INGEST" runtime pin --receipt "$RECEIPT_PATH" --root "$ACCEPTANCE_ROOT" --json
```

The pin is written to `$ACCEPTANCE_ROOT/_local/project-context/meetings/meeting-ingest-runtime.toml`. Now initialize the project:

```bash
"$MEETING_INGEST" init --root "$ACCEPTANCE_ROOT" --json
```

`init` writes `$ACCEPTANCE_ROOT/_local/project-context/meetings/meeting-ingest.toml` with `default_provider = "mock"` and both privacy gates closed. Enable the session provider before continuing:

```bash
CONFIG="$ACCEPTANCE_ROOT/_local/project-context/meetings/meeting-ingest.toml"
python3 - "$CONFIG" <<'PY'
import pathlib, sys
path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace('default_provider = "mock"', 'default_provider = "session"')
text = text.replace("allow_session_provider = false", "allow_session_provider = true")
path.write_text(text, encoding="utf-8")
PY
```

Confirm readiness:

```bash
"$MEETING_INGEST" readiness --host claude-code --root "$ACCEPTANCE_ROOT" --json
```

Record `verdict`, `running_build`, and `runtime_provenance.runtime_mode`. Stop if `verdict` is `blocked` (exit `12`).

Copy the acceptance transcript into the inbox:

```bash
SOURCE="$ACCEPTANCE_ROOT/_local/project-context/meetings/_inbox/session-provider-eval.vtt"
cp "$REPO/tests/fixtures/semantic-integrity/session-provider-eval.vtt" "$SOURCE"
```

## Run The Acceptance Case

`provider-request` and `ingest` discover the project from the current working directory, so run them from inside the acceptance root. `validate-response`, `doctor`, and `status` take `--root`.

Phase 1. The fixture carries no in-file date, so it infers `date_confidence: low` from the file mtime. The workflow forbids letting an unconfirmed low-confidence date mint the final artifact, so pass `--meeting-date` explicitly. The fixture is synthetic and any fixed date works; keep the same date across runs so artifact identity stays comparable.

```bash
cd "$ACCEPTANCE_ROOT"
"$MEETING_INGEST" provider-request "$SOURCE" \
  --provider session \
  --quality balanced \
  --meeting-date 2026-07-26 \
  --json
```

Read `provider_request.path` and `provider_response.path` from the summary. Both are relative to the meetings root.

```bash
MEETINGS_ROOT="$ACCEPTANCE_ROOT/_local/project-context/meetings"
REQUEST="$MEETINGS_ROOT/<provider_request.path>"
RESPONSE="$MEETINGS_ROOT/<provider_response.path>"
```

Extraction. Invoke the `meeting-ingest-session-provider` agent with the request and expected response paths, exactly as the `meeting-ingest` skill does for ordinary inbox work. Do not hand-author the response and do not correct it mid-run: the whole point of the case is what the bound guidance version produces unaided. Record any intervention that does occur.

Before evaluating semantics, confirm the request actually bound the contract under test:

```bash
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["semantic_guidance_version"]); print(json.dumps(d["transcript_grounding"], indent=2))' "$REQUEST"
```

Expect `1.1` and the grounding index recorded in `expected-review.json` under `transcript_grounding`.

Preflight. This is the no-side-effect grounding gate and satisfies assertion `DG6`:

```bash
"$MEETING_INGEST" validate-response "$RESPONSE" --source "$SOURCE" --root "$ACCEPTANCE_ROOT" --json
```

Proceed only on exit `0` with `status: "success"`, `provider_response.status: "valid"`, and a non-blocked `runtime_readiness.verdict`. A provider-validation failure (exit `6`) returns every issue in `errors[0].details.issues`; record it as a `DG*` assertion failure, since the deterministic tier caught what it exists to catch.

Snapshot the response before phase 2. This step is mandatory, not housekeeping: successful phase 2 deletes the request/response pair, and every assertion in `expected-review.json` is rooted at the response payload, which the rendered Markdown and signal JSONL do not expose.

```bash
EVAL_RESPONSE="$ACCEPTANCE_ROOT/eval-response.json"
cp "$RESPONSE" "$EVAL_RESPONSE"
```

Phase 2:

```bash
"$MEETING_INGEST" ingest "$SOURCE" \
  --provider session \
  --provider-response "$RESPONSE" \
  --json
```

Health check:

```bash
"$MEETING_INGEST" doctor --root "$ACCEPTANCE_ROOT" --json
"$MEETING_INGEST" status --root "$ACCEPTANCE_ROOT" --json
```

Expect a clean `doctor` and no lingering `session_handoff_*` issues: successful phase 2 deletes the request/response pair.

## Evaluate The Assertions

Evaluate every assertion in `expected-review.json` against the preserved response payload — the `response` key of `$EVAL_RESPONSE` — using the selector, operator, null, and severity vocabulary declared in that file's `evaluation` block. That payload is the declared root, and the selectors resolve against nothing else. The rendered Markdown and signal JSONL are inputs to the human review below, not to the assertions.

- Every `blocking` assertion must pass. One blocking failure fails the acceptance run.
- An `advisory` failure is a recorded quality finding that the human reviewer dispositions in the record.
- `DG2`–`DG5` are enforced by the engine, so they should pass by construction once `DG6` passes. Evaluate them anyway: a `DG*` assertion that fails while `validate-response` succeeded is an enforcement gap, not a provider defect, and is the more serious of the two findings.
- `DG1` is the exception, and its result must not be read as an engine guarantee. `validate_provider_grounding` only checks that each supplied raw label belongs to the grounding set; it never requires every transcript speaker to appear as an attendee. `DG1`'s set equality is a completeness expectation this fixture adds, so a `DG1` failure is an ordinary extraction defect, not an enforcement gap.

Record each assertion as `pass`, `fail`, or `not_applicable`, with the offending value quoted for every failure.

## Record

Record the following in a dated session note alongside the assertion results. This is the run's provenance; without it the result is not reproducible evidence.

| Field | Source |
|---|---|
| Host and host version | the Claude Code session running the case |
| Model | `provider.model_id` in the response envelope, plus the pinned agent model |
| Build identity | `running_build` and `runtime_provenance` from `readiness --json` |
| Runtime mode and verdict | `runtime_provenance.runtime_mode` and `verdict` from `readiness --json` |
| Semantic guidance version | `semantic_guidance_version` in the request, echoed in the response, stamped in artifact front matter |
| Quality | `quality` in the request; `model_alias` in the response |
| Elapsed time | wall clock from request creation to phase-2 completion |
| Extraction tokens | token usage reported by the host for the extraction agent |
| Interventions | every correction, retry, or manual edit, or `none` |
| Output paths | markdown artifact path and signal JSONL path from the phase-2 summary |
| Signal count | `count` on the signals artifact in the phase-2 summary |
| Assertion results | per-ID `pass`/`fail`/`not_applicable` from the section above |

State plainly whether the run is release evidence or development/non-release evidence.

## Review

Two reviews are required for milestone proof, and neither review mutates artifacts. A defect found in review is recorded as a finding against this run; correcting it means a fresh run, not an edit to the generated markdown or signal JSONL.

1. **Human semantic review.** The owner reads the generated artifact against the transcript and judges the five patterns directly, not only through the assertion regexes. The assertions are a floor: output can satisfy every pattern and still misread the meeting.
2. **Independent blind review.** A second reviewer who has not seen `expected-review.json` and did not run the case reads the transcript and the generated artifact, then reports what the artifact overstates, understates, or invents. Blind means blind: showing the expected assertions first destroys the evidence value of the second opinion.

Reconcile the two reviews in the record. Unresolved disagreement is a finding, not a tie to be broken silently.

## Workflow Copy Verification

The instruction surfaces that shaped the run are part of the evidence. Verify them with the mechanism that matches how each pair is maintained.

**Claude pairs are receipt-managed.** `docs/claude-skills/meeting-ingest/SKILL.md` and `docs/claude-agents/meeting-ingest-session-provider.md` reach `~/.claude/` and any consumer project-level `.claude/` copy only through the release flow: source edit, new approved receipt, receipt-verified install to every destination, repin. The installed skill is rendered, not copied — the installer substitutes the `{{MEETING_INGEST_APPROVED_EXECUTABLE}}` marker — so a byte comparison against the source is meaningless. The receipt is the verification:

```bash
"$MEETING_INGEST" readiness --host claude-code --root "$ACCEPTANCE_ROOT" --json
"$MEETING_INGEST" runtime inspect --root "$ACCEPTANCE_ROOT" --json
```

`readiness` must not report `workflow_hash_mismatch`. `runtime inspect --json` reports `workflow.skill_path`, `workflow.skill_sha256`, `workflow.agent_path`, `workflow.agent_sha256`, and `workflow.match` for the user-level `~/.claude/` copies. `pin.comparisons` checks those hashes against the `installed_claude_skill_sha256` and `claude_agent_sha256` values the pin recorded from the project-level copies, and `receipt.comparisons` checks the pin's values against the approved receipt. A clean chain therefore proves receipt, project-level copy, and user-level copy are all the same instructions. Record the four workflow values and the `match` flags on both comparison sets.

Never hand-edit an installed Claude copy to make a hash match. A direct edit fails readiness with `workflow_hash_mismatch` by design; that is the mechanism working, and re-running the installer is the only fix.

**The Codex pair is not receipt-managed.** `docs/codex-skills/meeting-ingest/SKILL.md` and `~/.codex/skills/meeting-ingest/SKILL.md` are kept byte-for-byte identical, so an explicit comparison is the check:

```bash
cmp -s "$REPO/docs/codex-skills/meeting-ingest/SKILL.md" "$HOME/.codex/skills/meeting-ingest/SKILL.md" \
  && echo "codex skill in sync" || echo "codex skill DRIFT"
shasum -a 256 \
  "$REPO/docs/codex-skills/meeting-ingest/SKILL.md" \
  "$HOME/.codex/skills/meeting-ingest/SKILL.md"
```

Both digests must match. This comparison applies to the Codex pair only.

## Clean Up

The acceptance root holds transcript-bearing runtime files, the preserved `$EVAL_RESPONSE` snapshot, and a generated artifact. Finish evaluating and recording the assertions first — removing the root destroys the only remaining copy of the response payload. Then:

```bash
rm -rf "$ACCEPTANCE_ROOT"
```

Do not commit the acceptance root, the generated artifact, or the handoff files. The fixture, the assertions, and the dated record are the durable outputs.
