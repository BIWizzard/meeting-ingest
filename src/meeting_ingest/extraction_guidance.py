"""Versioned semantic guidance shared by provider extraction paths."""

from __future__ import annotations


SEMANTIC_GUIDANCE_RULES = (
    'Preserve nearby time context. Do not add AM/PM unless it is explicit or unambiguously established by phrases such as "last run of the night."',
    'Separate observations, hypotheses, and confirmed causes. Do not use "caused by," "traced to," or equivalent causal language when root cause remains open.',
    "Record a proposal as a decision only when the transcript shows acceptance. Record an action only when an owner accepts it or a direction is acknowledged.",
    "Never carry a rejected or infeasible proposal into open actions.",
    "Do not merge people from nickname similarity alone. Conflicting or incomplete alias evidence stays unresolved and receives low confidence.",
    "Keep the TL;DR consistent with the detailed topics, decisions, risks, actions, and open questions.",
)
PUBLISHED_SEMANTIC_GUIDANCE_RULES: dict[str, tuple[str, ...]] = {
    "1.0": SEMANTIC_GUIDANCE_RULES,
}
SEMANTIC_GUIDANCE_VERSION = "1.0"
