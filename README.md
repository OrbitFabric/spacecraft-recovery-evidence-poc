# SAFE Is Not Ready

### What evidence do we actually need before allowing spacecraft mission operations to resume?

A joint engineering proof of concept exploring the boundary between **spacecraft behavior**, **verification evidence**, and **mission-level assessment**.

This is an open, collaborative investigation involving [OrbitFabric](https://github.com/OrbitFabric), [openOBSW](https://github.com/lipofefeyt/openobsw), and [openSVF](https://github.com/lipofefeyt/opensvf). The engineering question comes first; the technologies are here to help us answer it.

> **Status:** G0 source audit has identified a concrete execution blocker and candidate enablers. G1 evidence-contract design is the proposed next step. No recovery outcome has been experimentally qualified by this PoC yet.

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

## G0: what the initial source audit established

The preliminary joint review has identified important limitations in the current host-simulation path:

- No currently S12-monitorable S20 parameter is driven by the simulator's sensor input. The proposed `obc_temperature` path is presently S20-table-driven.
- `TC(20,1)` is rejected in SAFE. Scheduling it through S11 or invoking it through S19 does not bypass the mode-gated dispatcher.
- The host simulator's S12 → S5 → SAFE coupling must **not** be presented as demonstrated flight-target/HIL FDIR equivalence.
- Host-simulator event timestamps, SAFE observability, parameter scaling, and event auxiliary-data decoding require explicit treatment in the evidence contract.
- openSVF's existing campaign report is useful but does not persist complete S5 event or housekeeping histories. The `HilAdapter.add_tm_listener` hook is a candidate for a PoC-owned evidence exporter; the required parameter decoding remains to be verified.

**Candidate upstream enablers (subject to separate issues and review):**

1. **openOBSW, simulation only:** extend the input sensor frame with a thermal value and validity indicator, then feed the monitored S20 parameter without changing flight source code.
2. **openSVF:** add a thermal equipment model that feeds that interface and supports controlled fault application and clearance through existing equipment-fault mechanisms.

The immediate goal is to document these dependencies and qualify the smallest credible execution path, not to bypass the blocker or predetermine results.

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

The initial source-audit review exposed meaningful constraints; these issues are the current shared discussion points:

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
