"""Versioned semantic guidance shared by provider extraction paths."""

from __future__ import annotations


# A published version is immutable. Never edit a frozen tuple below; publish a
# new version instead. Editing one silently redefines rules already bound into
# durable provenance.
_SEMANTIC_GUIDANCE_RULES_1_0 = (
    'Preserve nearby time context. Do not add AM/PM unless it is explicit or unambiguously established by phrases such as "last run of the night."',
    'Separate observations, hypotheses, and confirmed causes. Do not use "caused by," "traced to," or equivalent causal language when root cause remains open.',
    "Record a proposal as a decision only when the transcript shows acceptance. Record an action only when an owner accepts it or a direction is acknowledged.",
    "Never carry a rejected or infeasible proposal into open actions.",
    "Do not merge people from nickname similarity alone. Conflicting or incomplete alias evidence stays unresolved and receives low confidence.",
    "Keep the TL;DR consistent with the detailed topics, decisions, risks, actions, and open questions.",
)
_SEMANTIC_GUIDANCE_RULES_1_1 = (
    'Preserve nearby time context. Do not add AM/PM unless it is explicit or unambiguously established by phrases such as "last run of the night."',
    'Separate observations, hypotheses, and confirmed causes. Do not use "caused by," "traced to," or equivalent causal language when root cause remains open.',
    "Record a proposal as a decision only when the transcript shows acceptance. Record an action only when an owner accepts it or a direction is acknowledged.",
    "Never carry a rejected, infeasible, or parked proposal into open actions or commitments; stating its disposition inline does not make it eligible. Wherever such a proposal's substance appears in any other field — topic summary, decision, risk or dependency, open question, or stakeholder ask — say in that same text that it was rejected, infeasible, or parked. A disposition recorded only in a separate status field does not satisfy this.",
    "Do not merge people from nickname similarity alone. Conflicting or incomplete alias evidence stays unresolved and receives low confidence. This applies to every signal whose stakeholder name, summary, or evidence text carries the ambiguous alias, including a signal whose content is itself a report that the alias is ambiguous: confidence records how well the identity is resolved, not how plainly the ambiguity was stated. Inference level is unaffected — an ambiguity stated outright in the transcript is still explicit.",
    "Keep secondary framing fields — role context, risk and dependency impact, and similar narrative summaries — within what the transcript establishes. Do not widen a scope or deadline to cover items it did not cover, do not generalize a single occurrence into a standing condition or dependency, and do not turn a stated constraint into a broader blocker.",
    "Keep the TL;DR consistent with the detailed topics, decisions, risks, actions, and open questions.",
)
SEMANTIC_GUIDANCE_RULES = _SEMANTIC_GUIDANCE_RULES_1_1
PUBLISHED_SEMANTIC_GUIDANCE_RULES: dict[str, tuple[str, ...]] = {
    "1.0": _SEMANTIC_GUIDANCE_RULES_1_0,
    "1.1": _SEMANTIC_GUIDANCE_RULES_1_1,
}
SEMANTIC_GUIDANCE_VERSION = "1.1"
