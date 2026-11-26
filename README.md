# SAFE Is Not Ready

### What evidence do we actually need before allowing spacecraft mission operations to resume?

A joint engineering proof of concept exploring the boundary between **spacecraft behavior**, **verification evidence**, and **mission-level assessment**.

This is an open, collaborative investigation involving [OrbitFabric](https://github.com/OrbitFabric), [openOBSW](https://github.com/lipofefeyt/openobsw), and [openSVF](https://github.com/lipofefeyt/opensvf). The engineering question comes first; the technologies are here to help us answer it.

> **Status (2026-11-26):** G0 source-feasibility reconciliation was merged in [PR #5](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5) and [issue #1](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1) closed, retaining six G1 inputs. A **G1 local experimental review candidate** now provides A/B/C evidence plus a separate, one-process C+ host-SIL replay using openOBSW v0.20, openSVF v1.3.0 and OrbitFabric Core 1.3.0. **G1 evidence-contract approval, independent reproduction and joint acceptance remain pending.** Thermal `ADMISSIBLE` is not spacecraft return-to-operations authorization.

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

The original A/B/C design uses one thermal anomaly with controlled variations of *behavior* and *evidence availability*:

| Case | Underlying behavior | Available evidence | Target assessment |
| --- | --- | --- | --- |
| **A · Recovery demonstrated** | Fault cleared; recovery conditions remain stable | Sufficient and valid | **ADMISSIBLE** |
| **B · Recovery not demonstrated** | Fault persists or recurs | Sufficient and valid | **NOT ADMISSIBLE** |
| **C · Evidence gap** | Same recovered behavior as A | Critical observation or continuity is missing | **INDETERMINATE** |

These are **story-local bounded recovery-assessment categories**, not native openSVF campaign verdicts. Local executions have produced candidate results, documented below and **pending independent G1 review**.

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

See [G0 source and CI reconciliation](docs/gates/g0-source-baseline-20261120.md) for pinned sources, PRs, scope changes and the disposition later closed via PR #5 and issue #1. The [Evidence Field Inventory v0.1 proposal](docs/design/evidence-field-inventory.md) identifies what can actually be captured, what requires qualification and what is still unavailable.

## G1: locally executed experimental candidate (2026-11-26)

The [G1 engineering handoff](docs/experiments/g1-engineering-handoff-20261126.md), [baseline transition](docs/gates/g0-to-g1-baseline-transition-20261126.md), [reproduction guide](experiments/g1/README.md) and [user-workstation replay transcript](docs/experiments/g1-local-replay-observation-log-20261126.md) document a **PoC-local, not-yet-jointly-approved** host-SIL experiment:

| Experiment | Observation boundary | Bounded thermal assessment |
| --- | --- | --- |
| A | Fault cleared; five HK1 at 650 raw, five HK3 SAFE | `ADMISSIBLE` |
| B | Persistent fault; five HK1 at 1300 raw, five HK3 SAFE | `NOT_ADMISSIBLE` |
| C | A's original run, with exactly three post-capture HK1 records deliberately withheld from the assessment view | `INDETERMINATE` |
| C+ | Separate one-process host-SIL run: incomplete 5–10 s window, explicit further-observation request, fresh complete 10–15 s window | `INDETERMINATE` → later-window `ADMISSIBLE` |

The previous **G0** basis was openOBSW v0.19 / openSVF `034945e`. **G1** executes against openOBSW v0.20 (`a4c56715`) / openSVF v1.3.0 (`9bf3f3a`), with a synthetic Core 1.3.0 Mission Model (`d0206f1`) validated and exported through OrbitFabric. A PoC-only binding enforces identities, signed raw-temperature units and the declared 1250-raw threshold; an isolated 1200-raw semantic drift is rejected even though Core lint/export accept the different model.

The observation request and five-second/five-sample policy belong to the **story-local evaluator and C+ runner**, not to Core, the released OrbitFabric adapter or an upstream openSVF API. C+ preserves a single simulator lifecycle and never reconstructs missing historical observations. The new assessment applies **only to the later thermal interval**. RC-03 remains partial, RC-04 is not demonstrated and RC-05 has limited, parsed-TM capture/provenance semantics. No SAFE→NOMINAL command is issued.

The repository includes source code, frozen A/B/C fixtures, offline tests and reproduction steps. The **original full C+ runtime JSON and checksum sidecars remain on the execution workstation** and are **not included** in this draft PR; the linked transcript is a user-provided observation log, not authenticated producer evidence. The G1 results and criteria are **proposed for Gonçalo's independent review**, not accepted gate completion.

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

1. [G0 · Source audit and upstream blockers (closed)](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1)
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
