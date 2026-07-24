# Apple Marketing And Branding Seat

## 1. Verdict

Meeting Ingest has a credible product core and a distinctive promise: it does not merely summarize a transcript; it completes a trustworthy workflow that produces durable, inspectable project records. The artifacts demonstrate that promise better than the packaging does.

The product is not ready for a public just-works claim or general beta. Its strongest experience is a maintainer-operated system assembled from CLI, host skills, repository instructions, local config, and agent judgment. That is a valid private alpha, but public first impression implies broader readiness and portability than onboarding, distribution, and host integration demonstrate.

The immediate marketing task is truth alignment: one user, one job, one flagship workflow, one supported environment, and one demonstrable outcome.

## 2. Evidence

### Product definition and audience

- README leads with the broad, architectural phrase platform-agnostic and the abstract structured-project-knowledge outcome (`README.md:3-5`).
- The more accurate internal definition is a project-local engine for technical owners in agent workflows, not general self-service (`docs/product-status.md:9-24`).
- The compelling intended interaction is simple: ask the agent to process the inbox (`docs/session-provider-inbox-agent-workflow.md:3-11`).
- The differentiator is the strong done process—artifact, signals, provenance, ledger, archive, and reconcile—not summarization alone (`DECISIONS.md:29-40`).

Interpretation: the internal definition is coherent; the public definition is too broad and abstract. The best promise already exists but does not lead.

### First impression and language

- The name is literal, understandable, and consistent with scope. Renaming is not justified.
- README clearly explains why transcripts contain reusable value (`README.md:7-21`).
- Executable material begins under Development nearly 100 lines in and uses module invocation, while the actual console command is `meeting-ingest` (`README.md:97-132`; `pyproject.toml:16-17`).
- CLI help lists commands without product description, examples, defaults, or next action (`src/meeting_ingest/cli.py:17-125`).

Interpretation: a new user meets implementation before experience.

### Claims and demonstrability

- `.txt`, `.vtt`, and `.docx` support is consistently claimed and demonstrated. No issue was found with this claim.
- Output-mode direction is easy to read as capability, while only summary-plus-verbatim works (`README.md:36-46`; `docs/product-status.md:125-143`).
- Host-neutral architecture is defensible, but a platform-agnostic experience is not demonstrated; production host adapters remain unfinished (`docs/product-status.md:271-292`).
- Fresh init uses `mock` and disables session use; real personal value requires manual configuration and consent (`src/meeting_ingest/config.py:41-83`; `AGENTS.md:74-89`).
- Plain CLI cannot complete a session-backed meeting by itself.
- README exposes the response envelope and phase-two process before a simple user path (`README.md:141-236`).
- Stakeholder Briefing is broad in code but absent from live current state, and Product Status contradicts itself about its implementation (`docs/product-status.md:26-36`, `docs/product-status.md:315-366`).

Interpretation: qualifications exist, but are distributed so a reader can form a wrong impression without reading a false sentence.

### Packaging and launch posture

- Package metadata is adequate for internal tooling: 0.1.0, Python 3.11+, no runtime dependencies, console entry (`pyproject.toml:5-17`).
- It lacks project URLs, license declaration, contact/support metadata, classifiers, and release-channel information.
- No public install, upgrade policy, changelog, release notes, or compatibility matrix is evidenced.
- External use currently depends on a frozen local `uv tool` install from `main` (`AGENTS.md:136-146`).

Interpretation: credible internal-tool packaging, not launch packaging.

### Demonstrated artifact value

Real artifacts show provenance, model/host, source hash, date confidence, stable headings, useful summary, decisions, actions, risks, evidence, signals, questions, and explicit transcript boundary. No material marketing issue was found with core artifact presentation. It is the strongest product proof.

## 3. What is working

1. **Name:** clear and appropriately utilitarian; no rename needed.
2. **Differentiation:** strong done process materially exceeds paste-a-transcript-into-chat behavior.
3. **Natural-language experience:** process the inbox is simple and memorable.
4. **Output:** generated records are demonstrably useful and inspectable.
5. **Visible trust:** hashes, provenance, confidence, IDs, and transcript support auditability.
6. **Privacy:** explicit opt-in gates are clear. No issue was found with the gate language.
7. **Internal audience:** current status correctly narrows the product to technical agent operators.

## 4. Gaps and risks

1. Public proposition overstates breadth and understates the user.
2. Flagship experience is not the first-run experience.
3. No single truthful quick start exists for a real meeting.
4. Current behavior, direction, and future scope are mixed.
5. Default behavior proves mechanics, not useful value.
6. Command surface exposes internal orchestration and lacks one canonical user path.
7. Launch packaging is incomplete.
8. Dogfooding is real but not independent enough; post-fix closure is unproven.
9. Stakeholder Briefing risks diluting the core story before it has live proof.
10. Truth drift is a brand risk that makes the product look less controlled than its engineering deserves.

## 5. Recommendations in priority order

1. Adopt one present-tense definition:

   > Meeting Ingest turns transcript files into trustworthy meeting records—summary, decisions, actions, evidence, and source history—for technical project owners working with coding agents.

   Use host-neutral engine as supporting language; defer platform-agnostic as a headline.

2. Choose and prove one flagship workflow from fresh install through safe recovery in one host. Record time, interventions, exposed commands, and outputs.
3. Rebuild README around one sentence, audience, before/after artifact, current inputs/mode, first real meeting, release posture, and limitations. Move envelope and architecture detail into reference docs.
4. Label everything available now, experimental/internal, or planned.
5. Make the natural-language skill the experience and CLI the trust/recovery layer.
6. Pick one canonical phrase and command for normal inbox processing; lower-level handoff commands are integration APIs.
7. Define what 0.1.0 means: audience, host, install, compatibility, privacy, and support boundary.
8. Maintain a sanitized artifact example with source type, outcome, provenance, idempotency, and completion proof.
9. Reconcile public/internal truth as one bounded pass after owner approval.
10. Defer brand expansion; effortless proof is the best branding asset.

## 6. What to stop, defer, or simplify

- Stop leading with architecture terms such as platform-agnostic, provider-backed, schema, handoff, and derivation.
- Stop mixing roadmap and current capability without status labels.
- Stop presenting every CLI seam as a peer workflow.
- Defer mode claims until implemented and demonstrated.
- Defer marketing Stakeholder Briefing until reviewed identities, a current generation, useful briefings, and a repeatable consumption story exist.
- Defer Guidance V1.1, broader sources, additional providers, public/social input, and brand expansion until the flagship workflow passes.
- Simplify to one technical owner, one host, three formats, one mode, and one process-my-inbox experience.
- Simplify installation to one method and recovery to visible states/actions.
- Do not rename the product.

## 7. Release decision

Continue as an internal/private alpha. Do not declare public beta or claim that Meeting Ingest just works.

Credible current claims:

- supports `.txt`, `.vtt`, and `.docx`;
- produces summary-plus-verbatim Markdown and signals;
- records provenance and content-hash identity;
- archives and reconciles completed sources;
- has real maintainer dogfooding;
- is intended for technical owners using supported agent workflows.

Unsupported claims:

- general self-service;
- platform-agnostic user experience;
- selectable modes;
- effortless install/onboarding;
- productized support across all named hosts;
- proven Stakeholder Briefing;
- one-request completion without expert intervention.

Minimum launch gate: a recorded post-fix fresh-consumer run in one named host, from install to useful output, without source inspection, envelope debugging, or maintainer intervention, plus safe recovery and documentation that reproduces it.

## 8. Confidence and unresolved questions

Confidence is high in positioning, first impression, packaging, and launch findings; medium in ultimate audience breadth because no external demand evidence exists.

Unresolved questions:

1. Which host is the first supported experience?
2. Is 0.1.0 internal, private alpha, or a public compatibility promise?
3. What is the canonical consumer install method?
4. Has any non-maintainer completed the post-fix workflow without implementation inspection?
5. Is the headline experience the natural-language agent interaction or the host-neutral engine? Evidence favors the former as experience and latter as reliability layer.
6. What live proof is required before marketing Stakeholder Briefing?
7. Should advisory doctor findings be success-class health?
8. Are stale-handoff cleanup and slug quality release blockers for the chosen alpha?
9. Is the repository intended for external discovery now? If yes, license/support/release metadata become immediate.
