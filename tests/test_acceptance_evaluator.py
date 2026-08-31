from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).parents[1]
EVALUATOR_PATH = ROOT / "tests/fixtures/semantic-integrity/evaluate.py"
EXPECTED_PATH = ROOT / "tests/fixtures/semantic-integrity/expected-review.json"
TRANSCRIPT_PATH = ROOT / "tests/fixtures/semantic-integrity/session-provider-eval.vtt"

SPEC = importlib.util.spec_from_file_location("semantic_integrity_evaluate", EVALUATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
evaluator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluator)


def assertion(operator: str, **values: object) -> dict[str, object]:
    return {"id": "T1", "severity": "blocking", "operator": operator, **values}


def result(operator: str, payload: object, **values: object) -> dict[str, object]:
    return evaluator.evaluate_assertion(assertion(operator, **values), payload)


@pytest.mark.parametrize(
    ("operator", "payload", "arguments", "passing"),
    [
        ("set_equals", {"v": ["a", "b", "a"]}, {"selector": "$.v[*]", "expected": ["b", "a"]}, True),
        ("set_equals", {"v": ["a", None]}, {"selector": "$.v[*]", "expected": ["a"]}, False),
        ("each_in", {"v": ["a", "b"]}, {"selector": "$.v[*]", "allowed": ["a", "b"]}, True),
        ("each_in", {"v": ["c"]}, {"selector": "$.v[*]", "allowed": ["a", "b"]}, False),
        ("each_matches", {"v": ["alpha", "beta"]}, {"selector": "$.v[*]", "patterns": ["a$"]}, True),
        ("each_matches", {"v": ["alpha", "nope"]}, {"selector": "$.v[*]", "patterns": ["a$"]}, False),
        ("none_match", {"v": ["safe"]}, {"selector": "$.v[*]", "patterns": ["bad"]}, True),
        ("none_match", {"v": ["bad value"]}, {"selector": "$.v[*]", "patterns": ["bad"]}, False),
        ("any_matches", {"v": ["alpha"]}, {"selector": "$.v[*]", "patterns": ["ph"]}, True),
        ("any_matches", {"v": ["alpha"]}, {"selector": "$.v[*]", "patterns": ["zzz"]}, False),
        (
            "each_matching_also_matches",
            {"v": ["loader split parked", "unrelated"]},
            {"selector": "$.v[*]", "when_patterns": ["split"], "require_patterns": ["parked"]},
            True,
        ),
        (
            "each_matching_also_matches",
            {"v": ["loader split adopted"]},
            {"selector": "$.v[*]", "when_patterns": ["split"], "require_patterns": ["parked"]},
            False,
        ),
    ],
)
def test_value_operator_pass_and_fail_paths(
    operator: str, payload: object, arguments: dict[str, object], passing: bool
) -> None:
    evaluated = result(operator, payload, **arguments)
    assert evaluated["result"] == ("pass" if passing else "fail")
    if not passing:
        assert evaluated["details"]


@pytest.mark.parametrize(
    ("operator", "arguments", "expected"),
    [
        ("any_matches", {"patterns": ["x"]}, "fail"),
        ("each_in", {"allowed": ["x"]}, "pass"),
        ("each_matches", {"patterns": ["x"]}, "pass"),
        ("none_match", {"patterns": ["x"]}, "pass"),
        (
            "each_matching_also_matches",
            {"when_patterns": ["x"], "require_patterns": ["y"]},
            "pass",
        ),
        ("set_equals", {"expected": []}, "pass"),
        ("set_equals", {"expected": ["x"]}, "fail"),
    ],
)
def test_empty_selection_semantics(
    operator: str, arguments: dict[str, object], expected: str
) -> None:
    assert result(operator, {}, selector="$.missing[*]", **arguments)["result"] == expected


def test_null_handling_split_and_allow_null() -> None:
    payload = {"v": [None, "ok"]}
    assert result("none_match", payload, selector="$.v[*]", patterns=["bad"])["result"] == "pass"
    assert result("any_matches", payload, selector="$.v[*]", patterns=["ok"])["result"] == "pass"
    assert result("each_in", payload, selector="$.v[*]", allowed=["ok"])["result"] == "fail"
    assert result("each_matches", payload, selector="$.v[*]", patterns=["ok"])["result"] == "fail"
    assert result("each_in", payload, selector="$.v[*]", allowed=["ok"], allow_null=True)["result"] == "pass"
    assert result("each_matches", payload, selector="$.v[*]", patterns=["ok"], allow_null=True)["result"] == "pass"
    assert result(
        "each_matching_also_matches",
        payload,
        selector="$.v[*]",
        when_patterns=["ok"],
        require_patterns=["ok"],
    )["result"] == "pass"


def test_json_equality_distinguishes_booleans_from_numbers() -> None:
    assert result("set_equals", {"v": [True]}, selector="$.v[*]", expected=[1])["result"] == "fail"
    assert result("each_in", {"v": [True]}, selector="$.v[*]", allowed=[1])["result"] == "fail"

    spec = {
        "selector": "$.records[*]",
        "when": {"field": "name", "patterns": ["active"]},
        "require": [{"field": "required", "one_of": [1]}],
    }
    assert result(
        "record_conditional",
        {"records": [{"name": "active", "required": True}]},
        **spec,
    )["result"] == "fail"


def test_array_selector_union_is_evaluated_once() -> None:
    payload = {"first": ["a"], "second": ["b"]}
    evaluated = result(
        "set_equals",
        payload,
        selector=["$.first[*]", "$.second[*]"],
        expected=["a", "b"],
    )
    assert evaluated["result"] == "pass"


def test_value_type_filters_other_json_types() -> None:
    payload = {"values": ["text", 7, None, True]}
    evaluated = result(
        "each_matches",
        payload,
        selector="$.values[*]",
        value_type="string",
        patterns=["^text$"],
    )
    assert evaluated["result"] == "pass"


def test_descendant_selector_yields_leaves_only_and_missing_traversal_is_empty() -> None:
    payload = {"nested": {"items": [1, {"value": None}]}, "flag": True}
    assert evaluator.select(payload, "$..*") == [1, None, True]
    assert evaluator.select(payload, "$.missing.value") == []
    assert evaluator.select(payload, "$.flag[*]") == []


def test_regex_i_flag() -> None:
    assert result(
        "any_matches", {"v": "FRIDAY"}, selector="$.v", patterns=["friday"], regex_flags="i"
    )["result"] == "pass"
    assert result("any_matches", {"v": "FRIDAY"}, selector="$.v", patterns=["friday"])["result"] == "fail"


def test_record_conditional_pass_fail_and_dotted_require() -> None:
    spec = {
        "selector": "$.records[*]",
        "when": {"fields": ["summary", "evidence.text"], "patterns": ["ro"]},
        "require": [
            {"field": "metadata.confidence", "one_of": ["low"]},
            {"field": "owner", "patterns": ["rosa"]},
        ],
        "regex_flags": "i",
    }
    passing = {"records": [{"id": "sig-1", "summary": "RO report", "metadata": {"confidence": "low"}, "owner": "Rosa"}]}
    assert result("record_conditional", passing, **spec)["result"] == "pass"

    failing = copy.deepcopy(passing)
    failing["records"][0]["metadata"] = {}
    evaluated = result("record_conditional", failing, **spec)
    assert evaluated["result"] == "fail"
    assert 'record id "sig-1"' in evaluated["details"][0]
    assert '"metadata.confidence"' in evaluated["details"][0]


def test_record_conditional_missing_null_and_nonactivating_fields() -> None:
    spec = {
        "selector": "$.records[*]",
        "when": {"field": "name", "patterns": ["active"]},
        "require": [{"field": "required", "patterns": ["yes"]}],
    }
    payload = {"records": [{"name": None}, {}, {"name": "active", "required": None}]}
    evaluated = result("record_conditional", payload, **spec)
    assert evaluated["result"] == "fail"
    assert 'value null missed pattern' in evaluated["details"][0]


def test_record_conditional_one_of_explicit_null_and_missing() -> None:
    spec = {
        "selector": "$.records[*]",
        "when": {"field": "name", "patterns": ["active"]},
        "require": [{"field": "required", "one_of": [None]}],
    }
    assert result(
        "record_conditional",
        {"records": [{"name": "active", "required": None}]},
        **spec,
    )["result"] == "pass"
    assert result(
        "record_conditional",
        {"records": [{"name": "active"}]},
        **spec,
    )["result"] == "fail"


def test_record_conditional_and_cross_implies_empty_selections_pass() -> None:
    assert result(
        "record_conditional",
        {},
        selector="$.missing[*]",
        when={"field": "name", "patterns": ["active"]},
        require=[{"field": "owner", "patterns": ["Rosa"]}],
    )["result"] == "pass"
    assert result(
        "cross_implies",
        {},
        when={"selector": "$.missing[*]", "operator": "any_matches", "patterns": ["active"]},
        then={"selector": "$.also_missing[*]", "operator": "any_matches", "patterns": ["Rosa"]},
    )["result"] == "pass"


def test_cross_implies_pass_fail_and_clause_flags() -> None:
    spec = {
        "when": {
            "selector": "$.detail",
            "operator": "any_matches",
            "patterns": ["open"],
            "regex_flags": "i",
        },
        "then": {
            "selector": "$.summary",
            "operator": "none_match",
            "patterns": ["settled"],
            "regex_flags": "i",
        },
    }
    assert result("cross_implies", {"detail": "OPEN", "summary": "uncertain"}, **spec)["result"] == "pass"
    evaluated = result("cross_implies", {"detail": "OPEN", "summary": "SETTLED"}, **spec)
    assert evaluated["result"] == "fail"
    assert evaluated["details"][0].startswith("then clause failed:")
    assert result("cross_implies", {"detail": "closed", "summary": "settled"}, **spec)["result"] == "pass"


def test_cli_exit_code_operator_pass_and_fail(tmp_path: Path) -> None:
    command = tmp_path / "validator.py"
    command.write_text(
        "import json\nprint(json.dumps({'status': 'success', 'provider_response': {'status': 'valid'}}))\n",
        encoding="utf-8",
    )
    spec = assertion(
        "cli_exit_code",
        command="meeting-ingest validate-response RESPONSE --source SOURCE --json",
        expected_exit_code=0,
        expected_fields={"status": "success", "provider_response.status": "valid"},
    )
    validation = (tmp_path / "response.json", tmp_path / "source.vtt", f"{sys.executable} {command}")
    assert evaluator.evaluate_assertion(spec, {}, validation)["result"] == "pass"

    spec["expected_fields"] = {"provider_response.status": "invalid"}
    evaluated = evaluator.evaluate_assertion(spec, {}, validation)
    assert evaluated["result"] == "fail"
    assert 'value "valid"' in evaluated["details"][0]


@pytest.mark.parametrize(
    ("script", "detail"),
    [
        ("import sys\nsys.exit(3)\n", "exited with 3; expected 0"),
        ("print('not json')\n", "is not valid JSON"),
    ],
)
def test_cli_exit_code_process_failures(tmp_path: Path, script: str, detail: str) -> None:
    command = tmp_path / "validator.py"
    command.write_text(script, encoding="utf-8")
    spec = assertion(
        "cli_exit_code",
        command="meeting-ingest validate-response RESPONSE --source SOURCE --json",
        expected_exit_code=0,
        expected_fields={},
    )
    validation = (tmp_path / "response.json", tmp_path / "source.vtt", f"{sys.executable} {command}")
    evaluated = evaluator.evaluate_assertion(spec, {}, validation)
    assert evaluated["result"] == "fail"
    assert any(detail in item for item in evaluated["details"])


def test_cli_exit_code_defaults_to_not_applicable_with_reason() -> None:
    spec = assertion(
        "cli_exit_code",
        command="meeting-ingest validate-response RESPONSE --source SOURCE --json",
        expected_exit_code=0,
        expected_fields={},
    )
    evaluated = evaluator.evaluate_assertion(spec, {})
    assert evaluated["result"] == "not_applicable"
    assert "preflight" in evaluated["details"][0]
    assert "phase 2 deletes" in evaluated["details"][0]


def test_malformed_inactive_assertions_are_spec_errors() -> None:
    malformed_cli = assertion("cli_exit_code", expected_exit_code=0)
    with pytest.raises(evaluator.SpecError, match="cli_exit_code requires"):
        evaluator.evaluate_assertion(malformed_cli, {})

    malformed_cross = assertion(
        "cross_implies",
        when={"selector": "$.state", "operator": "any_matches", "patterns": ["open"]},
        then={"operator": "none_match", "patterns": ["closed"]},
    )
    with pytest.raises(evaluator.SpecError, match="missing selector"):
        evaluator.evaluate_assertion(malformed_cross, {"state": "closed"})

    malformed_record = assertion(
        "record_conditional",
        selector="$.records[*]",
        when={"field": "name", "patterns": ["active"]},
        require=[{"field": "owner", "patterns": []}],
    )
    with pytest.raises(evaluator.SpecError, match="non-empty array"):
        evaluator.evaluate_assertion(malformed_record, {"records": [{"name": "inactive"}]})


def declared_evaluation() -> dict[str, object]:
    return {"operators": {name: name for name in sorted(evaluator.OPERATORS)}}


def write_cli_files(tmp_path: Path, test_assertion: dict[str, object]) -> tuple[Path, Path]:
    expected = tmp_path / "expected.json"
    response = tmp_path / "response.json"
    expected.write_text(
        json.dumps({"evaluation": declared_evaluation(), "assertions": [test_assertion]}),
        encoding="utf-8",
    )
    response.write_text(json.dumps({"response": {"value": "safe"}}), encoding="utf-8")
    return expected, response


def run_cli(response: Path, expected: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVALUATOR_PATH), str(response), "--expected", str(expected), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_exit_codes_zero_one_and_two(tmp_path: Path) -> None:
    passing = assertion("none_match", selector="$.value", patterns=["bad"])
    expected, response = write_cli_files(tmp_path, passing)
    assert run_cli(response, expected).returncode == 0

    advisory = dict(passing, severity="advisory", patterns=["safe"])
    expected, response = write_cli_files(tmp_path, advisory)
    assert run_cli(response, expected).returncode == 0

    blocking = dict(passing, patterns=["safe"])
    expected, response = write_cli_files(tmp_path, blocking)
    completed = run_cli(response, expected)
    assert completed.returncode == 1
    assert "1 fail (1 blocking)" in completed.stdout

    malformed = dict(passing, operator="invented")
    expected, response = write_cli_files(tmp_path, malformed)
    completed = run_cli(response, expected)
    assert completed.returncode == 2
    assert "unknown operator" in completed.stderr

    missing = tmp_path / "missing.json"
    assert run_cli(missing, expected).returncode == 2


def test_cli_missing_default_root_is_spec_error_and_document_root_is_explicit(tmp_path: Path) -> None:
    passing = assertion("none_match", selector="$.value", patterns=["bad"])
    expected, response = write_cli_files(tmp_path, passing)
    response.write_text(json.dumps({"value": "safe"}), encoding="utf-8")
    refused = run_cli(response, expected)
    assert refused.returncode == 2
    assert 'missing root key "response"' in refused.stderr

    record_path = tmp_path / "record.json"
    completed = run_cli(response, expected, "--root-key", "$", "--json", str(record_path))
    assert completed.returncode == 0
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert set(record) == {"expected", "response", "evaluated_at", "results", "tally", "blocking_failures"}
    assert record["tally"] == {"pass": 1, "fail": 0, "not_applicable": 0}


def test_cli_non_object_expected_file_is_spec_error(tmp_path: Path) -> None:
    passing = assertion("none_match", selector="$.value", patterns=["bad"])
    expected, response = write_cli_files(tmp_path, passing)
    expected.write_text("[]", encoding="utf-8")
    completed = run_cli(response, expected)
    assert completed.returncode == 2
    assert "expected file top level must be an object" in completed.stderr


@pytest.mark.parametrize("selector", ["$.a[*", "$.a[0]"])
def test_cli_malformed_selector_is_spec_error(tmp_path: Path, selector: str) -> None:
    malformed = assertion("none_match", selector=selector, patterns=["bad"])
    expected, response = write_cli_files(tmp_path, malformed)
    completed = run_cli(response, expected)
    assert completed.returncode == 2
    assert "invalid selector" in completed.stderr


def known_good_payload() -> dict[str, object]:
    return {
        "attendees": [
            {"display_name": "Rosa Villanueva", "raw_labels": ["Villanueva, Rosa"]},
            {"display_name": "Dara Marchetti", "raw_labels": ["Marchetti, Dara (Contractor)"]},
            {"display_name": "Femi Okonjo", "raw_labels": ["Okonjo, Femi (Contractor)"]},
        ],
        "tl_dr": "The 10:06 final nightly run failed; root cause remains unconfirmed.",
        "topics": [{"summary": "Splitting the loader was rejected and parked until after quarter close."}],
        "decisions": [],
        "action_items": [
            {
                "id": "action-femi",
                "action": "Pull lock waits from the Beacon logs and verify the extract log",
                "owner": "Femi Okonjo",
                "due_timing": "Thursday",
            },
            {
                "id": "action-rosa",
                "action": "Add an alert when the merge timeout wait crosses a threshold",
                "owner": "Rosa Villanueva",
                "due_timing": "Friday",
            },
        ],
        "dependencies_risks": [{"description": "Why the lock persisted and the root cause remain open."}],
        "open_questions": [{"question": "Who is Ro, and who filed the related report?"}],
        "stakeholder_asks": [],
        "communication_signals": [
            {
                "id": "signal-ro",
                "stakeholder_name": "Ro (unresolved)",
                "summary": "Ro reportedly posted a screenshot; attribution is unresolved.",
                "confidence": "low",
                "evidence": {
                    "speaker": "Okonjo, Femi (Contractor)",
                    "timestamp": "02:21",
                    "text": "Ro flagged something like this last week in the channel.",
                },
            },
            {
                "id": "signal-rosa",
                "stakeholder_name": "Rosa Villanueva",
                "summary": "Rosa limited her commitment to alerting by Friday.",
                "confidence": "high",
                "evidence": {
                    "speaker": "Villanueva, Rosa",
                    "timestamp": "02:16",
                    "text": "Alerting change only, no loader logic. I will have it by Friday.",
                },
            },
        ],
    }


def evaluate_real_contract(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    return {item["id"]: item for item in evaluator.evaluate_document(expected, payload)}


def test_real_contract_known_good_payload_and_rule_6_mutations() -> None:
    transcript = TRANSCRIPT_PATH.read_text(encoding="utf-8")
    payload = known_good_payload()
    expected = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    grounding = expected["transcript_grounding"]

    for attendee in payload["attendees"]:
        for label in attendee["raw_labels"]:
            assert label in grounding["speaker_labels"]
            assert f"<v {label}>" in transcript
    for signal in payload["communication_signals"]:
        assert signal["evidence"]["speaker"] in grounding["speaker_labels"]
        assert signal["evidence"]["timestamp"] in grounding["timestamps"]
        assert f"00:{signal['evidence']['timestamp']}" in transcript

    evaluated = evaluate_real_contract(payload)
    assert [item_id for item_id, item in evaluated.items() if item["result"] != "pass"] == ["DG6"]
    assert evaluated["DG6"]["result"] == "not_applicable"

    for action in [
        "Raise the merge timeout and add an alert by Friday",
        "Increase the merge timeout to 30 minutes",
        "Set a longer merge timeout",
        "Ship the alerting change plus loader logic by Friday",
        "Add alerting and change the loader",
    ]:
        widened = copy.deepcopy(payload)
        widened["action_items"][1]["action"] = action
        assert evaluate_real_contract(widened)["S14"]["result"] == "fail", action

    separate_timeout_action = copy.deepcopy(payload)
    separate_timeout_action["action_items"].append(
        {"id": "action-timeout", "action": "Increase the merge timeout to 30 minutes"}
    )
    assert evaluate_real_contract(separate_timeout_action)["S14"]["result"] == "fail"

    wrong_deadline = copy.deepcopy(payload)
    wrong_deadline["action_items"][1]["due_timing"] = "Thursday"
    assert evaluate_real_contract(wrong_deadline)["S15"]["result"] == "fail"

    reassigned = copy.deepcopy(payload)
    reassigned["action_items"][1]["owner"] = "Marchetti, Dara (Contractor)"
    assert evaluate_real_contract(reassigned)["S15"]["result"] == "fail"

    missing_owner = copy.deepcopy(payload)
    del missing_owner["action_items"][1]["owner"]
    assert evaluate_real_contract(missing_owner)["S15"]["result"] == "fail"
