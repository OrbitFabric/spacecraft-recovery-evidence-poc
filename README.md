# SAFE Is Not Ready

### What evidence do we actually need before allowing spacecraft mission operations to resume?

A joint engineering proof of concept exploring the boundary between **spacecraft behavior**, **verification evidence**, and **mission-level assessment**.

This is an open, collaborative investigation involving [OrbitFabric](https://github.com/OrbitFabric), [openOBSW](https://github.com/lipofefeyt/openobsw), and [openSVF](https://github.com/lipofefeyt/opensvf). The engineering question comes first; the technologies are here to help us answer it.

> **Status (2026-11-20):** openOBSW **v0.19** and openSVF **034945e** now implement and upstream-test the thermal fault/clearance path in host SIL. The G0 baseline is reconciled for joint review and **G1 evidence-contract work can proceed**. The PoC has **not** yet produced an independent A/B/C assessment or a qualified Evidence Bundle. See the [G0 review note](docs/gates/g0-source-baseline-20261120.md) and [G1 field inventory](docs/design/evidence-field-inventory.md).

## The question

A spacecraft enters SAFE after an anomaly. Later, the triggering condition appears to have cleared.

**Is that sufficient to justify resuming operations?**

We want to distinguish four questions:

1. **Behavior:** What actually happened in the onboard software?
2. **Observation:** What did the verification system capture?
3. **Integrity:** Is that evidence complete, correctly interpreted, and temporally trustworthy?
4. **Assessment:** What conclusion, if any, is justified against explicit mission-level recovery criteria?

A passing test is not automatically sufficient evidence, and a return to SAFE is not itself a return-to-operations authorization.

## Three experiments, one engineering argument

We propose beginning with one credible anomaly and controlled variations of *behavior* and *evidence availability*:

| Case | Underlying behavior | Available evidence | Target assessment |
| --- | --- | --- | --- |
| **A · Recovery demonstrated** | Fault cleared; recovery conditions remain stable | Sufficient and valid | **ADMISSIBLE** |
| **B · Recovery not demonstrated** | Fault persists or recurs | Sufficient and valid | **NOT ADMISSIBLE** |
| **C · Evidence gap** | Same recovered behavior as A | Critical observation or continuity is missing | **INDETERMINATE** |

These are **proposed assessment categories**, not existing product verdicts or pre-established test results.

**A versus C is the decisive comparison:** identical underlying recovery behavior can justify different conclusions when the quality of available evidence changes.

Malformed or unverifiable evidence must be **rejected at the input-validation boundary**. It is not a fourth operational verdict.

## Complementary responsibilities

| System | Role in the investigation |
| --- | --- |
| **openOBSW** | Actual onboard-software behavior in a controlled host-simulator execution: monitoring, events, mode management, and fault response |
| **openSVF** | Simulation equipment, fault application and clearance, execution campaigns, telemetry acquisition, and native verification reports |
| **OrbitFabric** | Mission-facing identities and intent, an explicitly authored recovery-assessment contract, evidence correlation, and interpretation of what the observations justify |

The precise interface between these roles is **to be jointly designed**, not imposed on either upstream project. This PoC does not assume that all proposed recovery semantics or evidence exporters already exist in OrbitFabric or openSVF.

## G0: initial findings and current qualified baseline

The [original concept and experimental-design drafts](docs/proposals/README.md) recorded a genuine source-audit blocker: openOBSW had no simulator-driven S12-monitorable temperature that could clear while SAFE, and several observation/time semantics were not yet aligned.

Since that review, upstream changes have materially advanced the executable baseline:

- **openOBSW v0.19** ([release](https://github.com/lipofefeyt/openobsw/releases/tag/v0.19), commit `c9fdc5d`) adds the **v4 thermal sensor frame**, simulator mode-entry events, TM OBT timestamps, temperature/S12 event encoding corrections, and STM32H7 S12-to-SAFE coupling. The STM32H7 coupling has Renode evidence, **not hardware qualification**.
- **openSVF** ([PR #198](https://github.com/lipofefeyt/opensvf/pull/198), commit `034945e`) pins v0.19, provides the F1 OBC thermal input model with fault injection and explicit clearance, decodes HK set 1 by SRDB, and includes source-backed upstream **A-like and B-like L3 integration tests**. Upstream openSVF CI passed at that commit.
- **Scope changed:** across the v0.19 PR train, **#124–#126 and #128–#130 touched `src/`; only #127 did not**. The thermal input is **consumed only in the host simulator**, while FreeRTOS S12/SAFE coupling was demonstrated under Renode with a different parameter and not on hardware. See the [per-PR scope reconciliation](docs/gates/g0-source-baseline-20261120.md#4-scope-change-disclosure).
- **Residual caveat:** openOBSW's v0.19 release CI had 10 passed jobs and one ZynqMP bare-metal job failure at **toolchain installation**. This is not an all-green qualification, but it does not block host-SIL G1 design.
- **Critical boundary:** the executed upstream tests are **not** OrbitFabric recovery verdicts, continuous TM evidence custody, or a PoC outcome C. Keeping SAFE after the fault clears is behavior under observation, not an autonomous return to operations.

See [G0 source and CI reconciliation](docs/gates/g0-source-baseline-20261120.md) for pinned sources, PRs, scope changes and pending gate disposition. The [Evidence Field Inventory v0.1 proposal](docs/design/evidence-field-inventory.md) identifies what can actually be captured, what requires qualification and what is still unavailable.

## Proposed gate plan

| Gate | Purpose | Exit evidence |
| --- | --- | --- |
| **G0 · Feasibility** | Confirm source behavior, blockers, and native execution boundaries | Traceable audit; upstream enablers identified |
| **G1 · Evidence contract** | Agree on actual fields, provenance, temporal model, validation, and recovery criteria | Reviewed minimal bundle and assessment contract |
| **G2 · Native instrumentation** | Qualify simulator enablers and capture producer-owned observations | Repeatable execution and evidence export |
| **G3 · Experiments** | Execute A, B, and C and evaluate them independently | Reproducible case-by-case assessments |
| **G4 · Independent review** | Challenge claims, omissions, malformed input, and reproduction steps | Reviewed negative tests and evidence |
| **G5 · Engineering Story** | Explain the question, investigation, surprises, limits, and results | Mutually reviewed public narrative |

Gate completion is evidence-based. An identified blocker can be a valid G0 finding; it is **not** proof that the later experiments work.

## Current working threads

The original G0 questions are preserved as historical context. These issues now track the source-backed baseline and the open G1 contract questions:

1. [G0 · Source audit and upstream blockers](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1)
2. [G1 · Minimal Evidence Bundle v0.1](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/2)
3. [G1 · TM-listener observability and HK decoding](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/3)
4. [G1 · Recovery criteria and A/B/C contrast](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/4)

The [initial concept note and experimental design proposal](docs/proposals/README.md) are **historical discussion drafts**, not approved results. The index provides exact PDF fingerprints and upload status. Please review the issues against current source revisions before treating a design assumption as an implementation requirement.

## Working rules

- **Joint design and mutual review.** Decisions affecting the shared boundary are made in the open, with both sides able to challenge them.
- **Evidence before claims.** Distinguish demonstrated source behavior, tested runtime behavior, interpretations, and unverified hypotheses.
- **Preserve provenance.** Keep source revisions, campaign reports, raw/native observations where available, fault schedules, and transformation records traceable.
- **No silent scope expansion.** Upstream modifications stay in their respective projects and follow their maintainers' review processes.
- **No automatic resumption.** The assessment is a bounded experimental conclusion, not an operational flight-authority command.
- **No private project dependencies.** This public PoC is independent of internal planning repositories and employer materials.

The preferred editorial venue for the eventual Engineering Story is [OrbitFabric Reference Mission](https://github.com/OrbitFabric/orbitfabric-reference-mission), with reciprocal attribution and the freedom to present or reference the results from openOBSW/openSVF channels. Publication content will be jointly reviewed.

## Related projects

- [OrbitFabric](https://github.com/OrbitFabric/orbitfabric)
- [OrbitFabric Reference Mission](https://github.com/OrbitFabric/orbitfabric-reference-mission)
- [OrbitFabric × openOBSW/openSVF adapter](https://github.com/OrbitFabric/orbitfabric-openobsw-opensvf-adapter)
- [openOBSW](https://github.com/lipofefeyt/openobsw)
- [openSVF](https://github.com/lipofefeyt/opensvf)

## Collaboration and licensing

This repository is being established as a **shared PoC workspace**. The initial concept note and experimental design proposal are discussion drafts; their agreed revisions and technical decisions will be recorded here.

This repository adopts the **[Apache License, Version 2.0](LICENSE)** for project-owned material. This is aligned with [OrbitFabric](https://github.com/OrbitFabric/orbitfabric) and [openSVF](https://github.com/lipofefeyt/opensvf) and supports collaborative, reusable PoC code with explicit licensing terms.

The historical discussion drafts in [`docs/proposals/`](docs/proposals/README.md) remain unmodified and retain their attribution and provenance; this license does not transfer third-party copyright or override any separately stated rights. Third-party code must keep its applicable license and notices. Decisions on contribution boundaries and upstreaming remain subject to joint review.

Use issues and PRs for design questions, upstream dependency tracking and evidence-contract proposals. A license choice does **not** by itself approve an implementation, establish an Evidence Bundle contract or authorize a recovery conclusion.
