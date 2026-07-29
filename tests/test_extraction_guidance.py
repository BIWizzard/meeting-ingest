import re
from pathlib import Path

from meeting_ingest.extraction_guidance import (
    PUBLISHED_SEMANTIC_GUIDANCE_RULES,
    SEMANTIC_GUIDANCE_RULES,
    SEMANTIC_GUIDANCE_VERSION,
)

REPO_ROOT = Path(__file__).parents[1]

INSTRUCTION_SURFACES = (
    "docs/claude-agents/meeting-ingest-session-provider.md",
    "docs/session-provider-subagent-prompt.md",
    "docs/claude-skills/meeting-ingest/SKILL.md",
    "docs/codex-skills/meeting-ingest/SKILL.md",
    "docs/artifact-contract.md",
)

_NUMBERED_LINE = re.compile(r"^(\d+)\. (.*)$")


def _numbered_lines(text: str) -> dict[int, list[str]]:
    lines: dict[int, list[str]] = {}
    for line in text.splitlines():
        match = _NUMBERED_LINE.match(line)
        if match:
            lines.setdefault(int(match.group(1)), []).append(match.group(2))
    return lines


def test_published_semantic_guidance_1_0_rules_are_frozen() -> None:
    assert PUBLISHED_SEMANTIC_GUIDANCE_RULES["1.0"] == (
        'Preserve nearby time context. Do not add AM/PM unless it is explicit or unambiguously established by phrases such as "last run of the night."',
        'Separate observations, hypotheses, and confirmed causes. Do not use "caused by," "traced to," or equivalent causal language when root cause remains open.',
        "Record a proposal as a decision only when the transcript shows acceptance. Record an action only when an owner accepts it or a direction is acknowledged.",
        "Never carry a rejected or infeasible proposal into open actions.",
        "Do not merge people from nickname similarity alone. Conflicting or incomplete alias evidence stays unresolved and receives low confidence.",
        "Keep the TL;DR consistent with the detailed topics, decisions, risks, actions, and open questions.",
    )


def test_published_semantic_guidance_1_1_rules_are_frozen() -> None:
    assert PUBLISHED_SEMANTIC_GUIDANCE_RULES["1.1"] == (
        'Preserve nearby time context. Do not add AM/PM unless it is explicit or unambiguously established by phrases such as "last run of the night."',
        'Separate observations, hypotheses, and confirmed causes. Do not use "caused by," "traced to," or equivalent causal language when root cause remains open.',
        "Record a proposal as a decision only when the transcript shows acceptance. Record an action only when an owner accepts it or a direction is acknowledged.",
        "Never carry a rejected, infeasible, or parked proposal into open actions or commitments; stating its disposition inline does not make it eligible. Wherever such a proposal's substance appears in any other field — topic summary, decision, risk or dependency, open question, or stakeholder ask — say in that same text that it was rejected, infeasible, or parked. A disposition recorded only in a separate status field does not satisfy this.",
        "Do not merge people from nickname similarity alone. Conflicting or incomplete alias evidence stays unresolved and receives low confidence. This applies to every signal whose stakeholder name, summary, or evidence text carries the ambiguous alias, including a signal whose content is itself a report that the alias is ambiguous: confidence records how well the identity is resolved, not how plainly the ambiguity was stated. Inference level is unaffected — an ambiguity stated outright in the transcript is still explicit.",
        "Keep secondary framing fields — role context, risk and dependency impact, and similar narrative summaries — within what the transcript establishes. Do not widen a scope or deadline to cover items it did not cover, do not generalize a single occurrence into a standing condition or dependency, and do not turn a stated constraint into a broader blocker.",
        "Keep the TL;DR consistent with the detailed topics, decisions, risks, actions, and open questions.",
    )


def test_current_semantic_guidance_version_is_published() -> None:
    assert SEMANTIC_GUIDANCE_VERSION in PUBLISHED_SEMANTIC_GUIDANCE_RULES
    assert (
        PUBLISHED_SEMANTIC_GUIDANCE_RULES[SEMANTIC_GUIDANCE_VERSION]
        == SEMANTIC_GUIDANCE_RULES
    )


def test_instruction_surfaces_carry_the_current_rules_verbatim() -> None:
    mismatched: list[str] = []
    for surface in INSTRUCTION_SURFACES:
        lines = _numbered_lines((REPO_ROOT / surface).read_text(encoding="utf-8"))
        for number, rule in enumerate(SEMANTIC_GUIDANCE_RULES, 1):
            if rule not in lines.get(number, []):
                mismatched.append(f"{surface}: rule {number}")

    assert mismatched == []
