#!/usr/bin/env python3
"""Evaluate a semantic-integrity provider response against its acceptance spec."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Any


VALUE_OPERATORS = {
    "set_equals",
    "each_in",
    "each_matches",
    "none_match",
    "any_matches",
    "each_matching_also_matches",
}
OPERATORS = VALUE_OPERATORS | {"record_conditional", "cross_implies", "cli_exit_code"}
JSON_TYPES = {"string", "number", "boolean", "null", "object", "array"}
MISSING = object()


class SpecError(ValueError):
    """Raised when the expected-review contract is malformed."""


def quoted(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def descendant_leaves(value: Any) -> list[Any]:
    if isinstance(value, dict):
        leaves: list[Any] = []
        for child in value.values():
            leaves.extend(descendant_leaves(child))
        return leaves
    if isinstance(value, list):
        leaves = []
        for child in value:
            leaves.extend(descendant_leaves(child))
        return leaves
    return [value]


def select(payload: Any, selector: str) -> list[Any]:
    if not isinstance(selector, str):
        raise SpecError(f"selector must be a string, got {quoted(selector)}")
    if selector == "$":
        return [payload]
    if selector == "$..*":
        return descendant_leaves(payload)
    if not selector.startswith("$"):
        raise SpecError(f"invalid selector {quoted(selector)}")

    values = [payload]
    position = 1
    while position < len(selector):
        if selector.startswith("[*]", position):
            values = [item for value in values if isinstance(value, list) for item in value]
            position += 3
            continue
        if selector[position] != ".":
            raise SpecError(f"invalid selector {quoted(selector)}")
        end = position + 1
        while end < len(selector) and selector[end] != "." and not selector.startswith("[*]", end):
            end += 1
        field = selector[position + 1 : end]
        if not field or "[" in field or "]" in field:
            raise SpecError(f"invalid selector {quoted(selector)}")
        values = [value[field] for value in values if isinstance(value, dict) and field in value]
        position = end
    return values


def selected_values(payload: Any, assertion: dict[str, Any]) -> list[Any]:
    selectors = assertion.get("selector", MISSING)
    if selectors is MISSING:
        raise SpecError("assertion is missing selector")
    if isinstance(selectors, str):
        selectors = [selectors]
    elif not isinstance(selectors, list) or not all(isinstance(item, str) for item in selectors):
        raise SpecError("selector must be a string or an array of strings")
    values = [value for selector in selectors for value in select(payload, selector)]
    if "value_type" in assertion:
        type_name = assertion["value_type"]
        predicates = {
            "string": lambda value: isinstance(value, str),
            "number": lambda value: isinstance(value, (int, float)) and not isinstance(value, bool),
            "boolean": lambda value: isinstance(value, bool),
            "null": lambda value: value is None,
            "object": lambda value: isinstance(value, dict),
            "array": lambda value: isinstance(value, list),
        }
        if type_name not in JSON_TYPES:
            raise SpecError(f"unknown value_type {quoted(type_name)}")
        values = [value for value in values if predicates[type_name](value)]
    return values


def regex_flags(value: Any) -> int:
    if value is None or value == "":
        return 0
    if value == "i":
        return re.IGNORECASE
    raise SpecError(f"unsupported regex_flags {quoted(value)}")


def patterns(assertion: dict[str, Any], key: str = "patterns") -> list[str]:
    values = assertion.get(key)
    if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
        raise SpecError(f"{key} must be a non-empty array of strings")
    try:
        for value in values:
            re.compile(value, regex_flags(assertion.get("regex_flags")))
    except re.error as error:
        raise SpecError(f"invalid regular expression in {key}: {error}") from error
    return values


def first_match(value: Any, candidates: list[str], flags: int) -> str | None:
    if not isinstance(value, str):
        return None
    return next((pattern for pattern in candidates if re.search(pattern, value, flags)), None)


def validate_selection_spec(assertion: dict[str, Any]) -> None:
    selectors = assertion.get("selector", MISSING)
    if selectors is MISSING:
        raise SpecError("assertion is missing selector")
    if isinstance(selectors, str):
        selectors = [selectors]
    elif not isinstance(selectors, list) or not all(isinstance(item, str) for item in selectors):
        raise SpecError("selector must be a string or an array of strings")
    for selector in selectors:
        select({}, selector)
    if "value_type" in assertion and assertion["value_type"] not in JSON_TYPES:
        raise SpecError(f"unknown value_type {quoted(assertion['value_type'])}")
    if "allow_null" in assertion and not isinstance(assertion["allow_null"], bool):
        raise SpecError("allow_null must be a boolean")


def validate_value_spec(assertion: dict[str, Any]) -> None:
    operator = assertion.get("operator")
    if operator not in VALUE_OPERATORS:
        raise SpecError(f"unknown value operator {quoted(operator)}")
    validate_selection_spec(assertion)
    regex_flags(assertion.get("regex_flags"))
    if operator == "set_equals":
        if not isinstance(assertion.get("expected"), list):
            raise SpecError("set_equals expected must be an array")
    elif operator == "each_in":
        if not isinstance(assertion.get("allowed"), list):
            raise SpecError("each_in allowed must be an array")
    elif operator in {"each_matches", "none_match", "any_matches"}:
        patterns(assertion)
    else:
        patterns(assertion, "when_patterns")
        patterns(assertion, "require_patterns")


def validate_record_spec(assertion: dict[str, Any]) -> None:
    validate_selection_spec(assertion)
    regex_flags(assertion.get("regex_flags"))
    when = assertion.get("when")
    requirements = assertion.get("require")
    if not isinstance(when, dict) or not isinstance(requirements, list) or not requirements:
        raise SpecError("record_conditional requires when and a non-empty require array")
    if ("field" in when) == ("fields" in when):
        raise SpecError("record_conditional when must use exactly one of field or fields")
    fields = when.get("fields", [when.get("field")])
    if not isinstance(fields, list) or not fields or not all(isinstance(field, str) for field in fields):
        raise SpecError("record_conditional when requires non-empty string field names")
    patterns({"patterns": when.get("patterns"), "regex_flags": assertion.get("regex_flags")})
    for clause in requirements:
        if not isinstance(clause, dict) or not isinstance(clause.get("field"), str):
            raise SpecError("record_conditional require clause must name a field")
        has_one_of = "one_of" in clause
        has_patterns = "patterns" in clause
        if has_one_of == has_patterns:
            raise SpecError("record_conditional require clause must use exactly one of one_of or patterns")
        if has_one_of and not isinstance(clause["one_of"], list):
            raise SpecError("record_conditional one_of must be an array")
        if has_patterns:
            patterns({"patterns": clause["patterns"], "regex_flags": assertion.get("regex_flags")})


def validate_cli_spec(assertion: dict[str, Any]) -> None:
    command = assertion.get("command")
    expected_exit_code = assertion.get("expected_exit_code")
    expected_fields = assertion.get("expected_fields", {})
    if (
        not isinstance(command, str)
        or not command
        or not isinstance(expected_exit_code, int)
        or isinstance(expected_exit_code, bool)
        or not isinstance(expected_fields, dict)
        or not all(isinstance(field, str) for field in expected_fields)
    ):
        raise SpecError("cli_exit_code requires command, integer expected_exit_code, and expected_fields object")
    try:
        if not shlex.split(command):
            raise SpecError("cli_exit_code command must not be empty")
    except ValueError as error:
        raise SpecError(f"invalid cli_exit_code command: {error}") from error


def unique(values: list[Any]) -> list[Any]:
    result: list[Any] = []
    for value in values:
        if not any(json_equal(value, present) for present in result):
            result.append(value)
    return result


def json_equal(left: Any, right: Any) -> bool:
    """Compare JSON values without treating booleans as numbers."""
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and left.keys() == right.keys()
            and all(json_equal(left[key], right[key]) for key in left)
        )
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(json_equal(left_item, right_item) for left_item, right_item in zip(left, right))
        )
    return left == right


def evaluate_value_operator(assertion: dict[str, Any], payload: Any) -> tuple[bool, list[str]]:
    operator = assertion["operator"]
    values = selected_values(payload, assertion)
    allow_null = assertion.get("allow_null", False)

    if operator == "set_equals":
        expected = assertion.get("expected")
        if not isinstance(expected, list):
            raise SpecError("set_equals expected must be an array")
        selected_set = unique(values)
        expected_set = unique(expected)
        missing = [value for value in expected_set if not any(json_equal(value, item) for item in selected_set)]
        extra = [value for value in selected_set if not any(json_equal(value, item) for item in expected_set)]
        if not missing and not extra:
            return True, []
        return False, [
            f"selected {quoted(selected_set)} did not equal expected {quoted(expected_set)}; "
            f"missing {quoted(missing)}, unexpected {quoted(extra)}"
        ]

    if operator == "each_in":
        allowed = assertion.get("allowed")
        if not isinstance(allowed, list):
            raise SpecError("each_in allowed must be an array")
        failures = []
        for value in values:
            if value is None and allow_null:
                continue
            if value is None or not any(json_equal(value, item) for item in allowed):
                failures.append(f"value {quoted(value)} is not in allowed {quoted(allowed)}")
        return not failures, failures

    if operator in {"each_matches", "none_match", "any_matches"}:
        candidates = patterns(assertion)
        flags = regex_flags(assertion.get("regex_flags"))
        if operator == "each_matches":
            failures = []
            for value in values:
                if value is None and allow_null:
                    continue
                hit = first_match(value, candidates, flags)
                if value is None or hit is None:
                    failures.append(f"value {quoted(value)} missed patterns {quoted(candidates)}")
            return not failures, failures
        non_null = [value for value in values if value is not None]
        hits = [(value, first_match(value, candidates, flags)) for value in non_null]
        if operator == "none_match":
            failures = [
                f"value {quoted(value)} hit pattern {quoted(hit)}" for value, hit in hits if hit is not None
            ]
            return not failures, failures
        for value, hit in hits:
            if hit is not None:
                return True, []
        return False, [f"selected values {quoted(non_null)} missed patterns {quoted(candidates)}"]

    if operator == "each_matching_also_matches":
        when_candidates = patterns(assertion, "when_patterns")
        require_candidates = patterns(assertion, "require_patterns")
        flags = regex_flags(assertion.get("regex_flags"))
        failures = []
        for value in values:
            if value is None:
                continue
            when_hit = first_match(value, when_candidates, flags)
            if when_hit is not None and first_match(value, require_candidates, flags) is None:
                failures.append(
                    f"value {quoted(value)} hit when pattern {quoted(when_hit)} but missed required patterns "
                    f"{quoted(require_candidates)}"
                )
        return not failures, failures

    raise SpecError(f"unknown value operator {quoted(operator)}")


def dotted(record: Any, field: str) -> Any:
    value = record
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return MISSING
        value = value[part]
    return value


def record_label(record: dict[str, Any]) -> str:
    return f"record id {quoted(record['id'])}" if "id" in record else f"record {quoted(record)}"


def evaluate_record_conditional(assertion: dict[str, Any], payload: Any) -> tuple[bool, list[str]]:
    records = selected_values(payload, assertion)
    when = assertion.get("when")
    requirements = assertion.get("require")
    if not isinstance(when, dict) or not isinstance(requirements, list) or not requirements:
        raise SpecError("record_conditional requires when and a non-empty require array")
    if "field" in when and "fields" in when:
        raise SpecError("record_conditional when must use field or fields, not both")
    fields = when.get("fields", [when.get("field")])
    if not isinstance(fields, list) or not fields or not all(isinstance(field, str) for field in fields):
        raise SpecError("record_conditional when requires field or fields")
    when_spec = {"patterns": when.get("patterns"), "regex_flags": assertion.get("regex_flags")}
    when_patterns = patterns(when_spec)
    flags = regex_flags(assertion.get("regex_flags"))
    failures = []
    for record in records:
        if not isinstance(record, dict):
            raise SpecError(f"record_conditional selector yielded non-record {quoted(record)}")
        active = any(
            first_match(dotted(record, field), when_patterns, flags) is not None for field in fields
        )
        if not active:
            continue
        for clause in requirements:
            if not isinstance(clause, dict) or not isinstance(clause.get("field"), str):
                raise SpecError("record_conditional require clause must name a field")
            has_one_of = "one_of" in clause
            has_patterns = "patterns" in clause
            if has_one_of == has_patterns:
                raise SpecError("record_conditional require clause must use exactly one of one_of or patterns")
            value = dotted(record, clause["field"])
            label = record_label(record)
            if has_one_of:
                allowed = clause["one_of"]
                if not isinstance(allowed, list):
                    raise SpecError("record_conditional one_of must be an array")
                if value is MISSING or not any(json_equal(value, item) for item in allowed):
                    shown = "<missing>" if value is MISSING else quoted(value)
                    failures.append(
                        f"{label}: field {quoted(clause['field'])} value {shown} is not in one_of {quoted(allowed)}"
                    )
            else:
                clause_spec = {"patterns": clause["patterns"], "regex_flags": assertion.get("regex_flags")}
                required_patterns = patterns(clause_spec)
                hit = None if value is MISSING else first_match(value, required_patterns, flags)
                if value is MISSING or value is None or hit is None:
                    shown = "<missing>" if value is MISSING else quoted(value)
                    failures.append(
                        f"{label}: field {quoted(clause['field'])} value {shown} missed patterns "
                        f"{quoted(required_patterns)}"
                    )
    return not failures, failures


def evaluate_cross_implies(assertion: dict[str, Any], payload: Any) -> tuple[bool, list[str]]:
    when = assertion.get("when")
    then = assertion.get("then")
    if not isinstance(when, dict) or not isinstance(then, dict):
        raise SpecError("cross_implies requires when and then clauses")
    for name, clause in (("when", when), ("then", then)):
        if clause.get("operator") not in VALUE_OPERATORS:
            raise SpecError(f"cross_implies {name} clause requires a value operator")
    when_holds, _ = evaluate_value_operator(when, payload)
    if not when_holds:
        return True, []
    passed, details = evaluate_value_operator(then, payload)
    return passed, [f"then clause failed: {detail}" for detail in details]


def validate_dg6(
    assertion: dict[str, Any], response_path: Path, source_path: Path, meeting_ingest: str
) -> tuple[bool, list[str]]:
    command = assertion.get("command")
    expected_exit_code = assertion.get("expected_exit_code")
    expected_fields = assertion.get("expected_fields", {})
    if not isinstance(command, str) or not isinstance(expected_exit_code, int) or not isinstance(expected_fields, dict):
        raise SpecError("cli_exit_code requires command, integer expected_exit_code, and expected_fields object")
    command_parts = shlex.split(command)
    try:
        executable = shlex.split(meeting_ingest)
    except ValueError as error:
        raise SpecError(f"invalid --meeting-ingest command: {error}") from error
    if not executable:
        raise SpecError("--meeting-ingest must not be empty")
    if command_parts[0] == "meeting-ingest":
        command_parts = executable + command_parts[1:]
    command_parts = [
        part.replace("RESPONSE", str(response_path)).replace("SOURCE", str(source_path))
        for part in command_parts
    ]
    try:
        completed = subprocess.run(command_parts, capture_output=True, text=True, check=False)
    except OSError as error:
        return False, [f"command {quoted(command_parts)} could not run: {quoted(str(error))}"]
    failures = []
    if completed.returncode != expected_exit_code:
        failures.append(
            f"command {quoted(command_parts)} exited with {quoted(completed.returncode)}; expected "
            f"{quoted(expected_exit_code)}; stderr {quoted(completed.stderr)}"
        )
    try:
        stdout = json.loads(completed.stdout)
    except json.JSONDecodeError:
        failures.append(f"command stdout {quoted(completed.stdout)} is not valid JSON")
        return False, failures
    for field, expected in expected_fields.items():
        if not isinstance(field, str):
            raise SpecError("cli_exit_code expected_fields keys must be strings")
        actual = dotted(stdout, field)
        if actual is MISSING or actual != expected:
            shown = "<missing>" if actual is MISSING else quoted(actual)
            failures.append(
                f"stdout field {quoted(field)} value {shown} did not equal expected {quoted(expected)}"
            )
    return not failures, failures


def evaluate_assertion(
    assertion: dict[str, Any],
    payload: Any,
    validation: tuple[Path, Path, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(assertion, dict):
        raise SpecError(f"assertion must be an object, got {quoted(assertion)}")
    assertion_id = assertion.get("id")
    severity = assertion.get("severity")
    operator = assertion.get("operator")
    if not isinstance(assertion_id, str) or not assertion_id:
        raise SpecError("assertion requires a non-empty string id")
    if severity not in {"blocking", "advisory"}:
        raise SpecError(f"assertion {assertion_id} has invalid severity {quoted(severity)}")
    if operator not in OPERATORS:
        raise SpecError(f"assertion {assertion_id} has unknown operator {quoted(operator)}")

    if operator in VALUE_OPERATORS:
        validate_value_spec(assertion)
    elif operator == "record_conditional":
        validate_record_spec(assertion)
    elif operator == "cross_implies":
        when = assertion.get("when")
        then = assertion.get("then")
        if not isinstance(when, dict) or not isinstance(then, dict):
            raise SpecError("cross_implies requires when and then clauses")
        validate_value_spec(when)
        validate_value_spec(then)
    else:
        validate_cli_spec(assertion)

    if operator == "cli_exit_code":
        if validation is None:
            return {
                "id": assertion_id,
                "severity": severity,
                "result": "not_applicable",
                "details": [
                    "Satisfied by the standard acceptance procedure preflight before phase 2; phase 2 deletes "
                    "the live response file. Provide --validate-response and --validate-source to re-run it "
                    "against archived copies."
                ],
            }
        passed, details = validate_dg6(assertion, *validation)
    elif operator == "record_conditional":
        passed, details = evaluate_record_conditional(assertion, payload)
    elif operator == "cross_implies":
        passed, details = evaluate_cross_implies(assertion, payload)
    else:
        passed, details = evaluate_value_operator(assertion, payload)
    return {
        "id": assertion_id,
        "severity": severity,
        "result": "pass" if passed else "fail",
        "details": details,
    }


def evaluate_document(
    expected: Any, payload: Any, validation: tuple[Path, Path, str] | None = None
) -> list[dict[str, Any]]:
    if not isinstance(expected, dict):
        raise SpecError("expected file top level must be an object")
    evaluation = expected.get("evaluation")
    assertions = expected.get("assertions")
    if not isinstance(evaluation, dict) or not isinstance(evaluation.get("operators"), dict):
        raise SpecError("expected file requires an evaluation block with operators")
    declared = set(evaluation["operators"])
    if declared != OPERATORS:
        raise SpecError(
            f"evaluation operators {quoted(sorted(declared))} do not match supported contract "
            f"{quoted(sorted(OPERATORS))}"
        )
    if not isinstance(assertions, list):
        raise SpecError("expected file requires an assertions array")
    return [evaluate_assertion(assertion, payload, validation) for assertion in assertions]


def load_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise SpecError(f"cannot read JSON file {path}: {error}") from error


def build_record(expected_path: Path, response_path: Path, results: list[dict[str, Any]]) -> dict[str, Any]:
    tally = {
        "pass": sum(result["result"] == "pass" for result in results),
        "fail": sum(result["result"] == "fail" for result in results),
        "not_applicable": sum(result["result"] == "not_applicable" for result in results),
    }
    blocking_failures = sum(
        result["result"] == "fail" and result["severity"] == "blocking" for result in results
    )
    return {
        "expected": str(expected_path),
        "response": str(response_path),
        "evaluated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "results": results,
        "tally": tally,
        "blocking_failures": blocking_failures,
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("response", type=Path, metavar="EVAL_RESPONSE.json")
    result.add_argument(
        "--expected",
        type=Path,
        default=Path(__file__).with_name("expected-review.json"),
    )
    result.add_argument(
        "--root-key",
        default="response",
        help='payload key to evaluate (default: "response"); use "$" to evaluate the document root',
    )
    result.add_argument("--json", type=Path, dest="json_path")
    result.add_argument("--validate-response", type=Path)
    result.add_argument("--validate-source", type=Path)
    result.add_argument("--meeting-ingest", default="meeting-ingest")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if (args.validate_response is None) != (args.validate_source is None):
        print("error: --validate-response and --validate-source must be provided together", file=sys.stderr)
        return 2
    try:
        expected = load_json(args.expected)
        document = load_json(args.response)
        if args.root_key == "$":
            payload = document
        elif isinstance(document, dict) and args.root_key in document:
            payload = document[args.root_key]
        else:
            raise SpecError(f"response document is missing root key {quoted(args.root_key)}")
        validation = None
        if args.validate_response is not None:
            validation = (args.validate_response, args.validate_source, args.meeting_ingest)
        results = evaluate_document(expected, payload, validation)
        record = build_record(args.expected, args.response, results)
        if args.json_path is not None:
            try:
                args.json_path.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
            except OSError as error:
                raise SpecError(f"cannot write JSON file {args.json_path}: {error}") from error
    except SpecError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for result in results:
        print(f"{result['id']} {result['severity']} {result['result']}")
        for detail in result["details"]:
            print(f"  {detail}")
    tally = record["tally"]
    fail_suffix = ""
    if tally["fail"]:
        advisory = tally["fail"] - record["blocking_failures"]
        labels = []
        if record["blocking_failures"]:
            labels.append(f"{record['blocking_failures']} blocking")
        if advisory:
            labels.append(f"{advisory} advisory")
        fail_suffix = f" ({', '.join(labels)})"
    print(
        f"{tally['pass']} pass / {tally['fail']} fail{fail_suffix} / "
        f"{tally['not_applicable']} not_applicable"
    )
    return 1 if record["blocking_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
