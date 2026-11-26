# SAFE Is Not Ready | G1 engineering evidence and handoff dossier

**Version:** D0.1, 2026-11-26  
**Status:** local technical execution PASS; **G0 source feasibility closed; independent G1 review and evidence-contract approval pending**.  
**Publication:** G1 draft-review branch candidate; source and original A/B/C fixtures only. Full C+ runtime JSON remains on the execution workstation.  
**Scope:** joint OrbitFabric × openOBSW/openSVF Proof of Concept; host-SIL, synthetic thermal case.  

## 1. Executive conclusion

The experiment addresses a real mission-assurance boundary: an onboard fault can clear while available ground-facing evidence remains insufficient to justify a conclusion. A, B and C distinguish recovered behavior with sufficient evidence, continuing fault with sufficient evidence, and recovered behavior with a deliberate critical observation gap. C+ extends the same question by generating a new observation obligation and re-assessing a **fresh, later** five-second interval in the **same host-simulator process**. There is no autonomous return to NOMINAL or claim of spacecraft operational recovery authorization.

The local run passed: first-window assessment **INDETERMINATE**, a new-observation request, second-window assessment **ADMISSIBLE**. The second verdict applies only to the later thermal interval. Original C remains INDETERMINATE and the missing historical HK remains missing.

OrbitFabric Core contributes validated mission entities and a declared fault threshold. The PoC-local binding checks Core-to-native semantics and refuses valid but incompatible drift. It does **not** make OrbitFabric an assessment engine or imply that a released adapter already projects this recovery scenario.

## 2. Source and governance anchors

| Component | Source / pinned basis | Boundary |
|---|---|---|
| Joint PoC | [OrbitFabric/spacecraft-recovery-evidence-poc](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc) | Joint decisions, not unilateral G1 approval |
| G0 closed thread | [PoC issue #1](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1) | Closed after PR #5 merge; G1 residuals remain tracked separately |
| G1 Evidence Bundle | [PoC issue #2](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/2) | Producer vs derived, provenance, coverage; no approved universal schema |
| G1 observability | [PoC issue #3](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/3) | Parsed-TM listener; no producer-owned original raw-wire custody |
| G1 assessment criteria | [PoC issue #4](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/4) | A/B/C semantics still subject to independent review |
| G0/G1 source documentation | [Merged PoC PR #5](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5) | Merged `5702a0a`; closes **G0 source feasibility**, not G1 schema or assessment |
| Gonçalo G0 source update | [Issue #1 comment 6940902275](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1#issuecomment-6940902275) | v0.19 enablers and original outstanding limits |
| Gonçalo scope correction | [Issue #1 comment 7068637637](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1#issuecomment-7068637637) | All v0.19 PRs #124–#130 except #127 touched `src/` |
| Gonçalo PR review response | [PR #5 comment 7068638035](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5#issuecomment-7068638035) | Listener behavior, raw TM limitations, G0 closeout precondition |
| openOBSW live G1 | [`a4c56715cbf57e34d7812b71a4d5f32cf9285b18`](https://github.com/lipofefeyt/openobsw/commit/a4c56715cbf57e34d7812b71a4d5f32cf9285b18), v0.20 | Actual onboard source executed by host simulator; not flight-board thermal verification |
| openSVF live G1 | [`9bf3f3a29696f695a6406080ad4436cb4a5154fc`](https://github.com/lipofefeyt/opensvf/commit/9bf3f3a29696f695a6406080ad4436cb4a5154fc), v1.3.0 | Native thermal harness, parsed TM, no raw-wire claim |
| OrbitFabric local Core | [`d0206f11d31922581a05b96ee76d05bf7b0d6870`](https://github.com/OrbitFabric/orbitfabric/commit/d0206f11d31922581a05b96ee76d05bf7b0d6870), package 1.3.0 | Actually installed, linted and exported on user workstation |
| Earlier G0 inspected sources | openOBSW v0.19 `c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c`, openSVF `034945e8841eda3e4a35e07624a06aec5c6db26a` | **Not** the later G1 execution pins; do not conflate |

## 3. Engineering development record

1. **Concept and G0:** isolated the question “SAFE Is Not Ready”; four boundaries behavior / observation / integrity / assessment. Identified simulator thermal-input and telemetry observability dependencies. Gonçalo and upstream contributors advanced v0.19; G0 PR #5 records the corrected scope and caveats and was merged after the stated closure condition was satisfied.
2. **Native scenario:** selected one thermal FDIR experiment, with nominal 650 raw (25°C), fault 1300 raw (90°C), hard limit 1250 raw (85°C). Conversion `temperature_C = raw/10 - 40`. openOBSW enters SAFE, remains SAFE after explicit fault clearance.
3. **A/B/C evidence family:** native parsed-TM capture and scenario-local evaluator v0.4. A and B have 70 parsed TM each; C has 67, derived exactly from A by omission of original post-fault HK1 packet indices `[54, 60, 66]`. Original evidence fixtures and frozen reports are kept unchanged.
4. **Assessment boundary:** per requirement SATISFIED / VIOLATED / UNKNOWN; bounded aggregate ADMISSIBLE / NOT_ADMISSIBLE / INDETERMINATE; malformed or inadmissible input is rejected before classification, not a fourth recovery verdict. Qualifying work included evaluator self-tests and negative/adversarial tests. Original G1 evaluator v0.4 is frozen for C+.
5. **OrbitFabric mission contract:** one OBC, modes NOMINAL/SAFE, one NOMINAL→SAFE transition, two telemetry identities, two named S5 events, one threshold fault; **no** fabricated SAFE→NOMINAL transition or command. Nine mandatory Core YAML files; no generic Core changes. Core 1.3.0 lint: **0 errors, 0 warnings**. Core Integration Input Set: load/lint passed; `entity_index`, `lint_report`, `mission_snapshot`, `model_summary`, `relationship_manifest` available. Input Set digest: `f7de824fca1e18a7dc093f8f73c3b39d9777254828fd06d56bd7426e4ea10c7b`.
6. **Core → native correlation:** one PoC-specific mapping from Core entity IDs to HK1 `TM(3,25)` signed BE int16, HK3 `TM(3,25)` SAFE=1, S5 `TM(5,4)` 0x0051 and 0x0002. Correlation with A/B/C v0.4 outputs: **PASS**; no verdict recomputation or upstream adapter extension.
7. **Semantic drift adversarial test:** mutate isolated Mission Model to 1200 raw. Real Core lint/export both **PASS** (the altered mission is structurally and internally valid), while binding to frozen 1250-based evidence/policy is **BLOCKED** with `temperature binding/type/unit/threshold mismatch`. No original source changed.
8. **C+ feasibility and realization:** reuse `ThermalHarness` from pinned openSVF upstream test fixture; two `run(50)` intervals in **one live host-simulator process** with one initialization and teardown. First retain 2/5 HK1 (only in a declared derived projection), assess INDETERMINATE before further acquisition, issue structured *new* observation request, then acquire 5/5 HK1 and HK3 from later simulation time and reassess with unmodified v0.4.
9. **Live C+ qualified locally, 2026-11-26:** run ID `g1-cplus-a78b4f92c357`, one simulator PID `22296`, first window 5–10 s, second 10–15 s; first INDETERMINATE (HK1=2, HK3=5), second ADMISSIBLE (HK1=5, HK3=5). Five output-file SHA-256 checks verified `OK`. Full generated JSON and checksums remain at the user's local G1 workstation; **not copied into this repository candidate**. No independent reproduction is claimed.
10. **Test suite:** frozen evaluator self-test PASS; six C+ offline tests PASS (baseline identity, modified survivor rejection, non-HK1 omission rejection, earlier-window replay rejection, recurrence rejection, baseline + synthetic second-stage behavior); Core-native trace against actual Core export PASS. The synthetic offline second-window test is not substituted for the live C+ run.

## 4. Concrete observations and bounded conclusions

| Experiment | Post-fault HK1 | Post-fault HK3 | Existing experimental verdict | Grounded meaning |
|---|---|---|---|---|
| A | 5 × 650 raw | 5 × SAFE | `ADMISSIBLE` | thermal subset supported with observed clearance |
| B | 5 × 1300 raw | 5 × SAFE | `NOT_ADMISSIBLE` | supported violation: high temperature persists |
| C | 2 × 650 raw | 5 × SAFE | `INDETERMINATE` | insufficient retained thermal observations despite A-like underlying behavior |
| C+ first, new run | 2 × 650 raw | 5 × SAFE | `INDETERMINATE` | new original fault/run; first retained window is incomplete |
| C+ second, same new run | 5 × 650 raw | 5 × SAFE | `ADMISSIBLE` | **new later window only** supports bounded thermal clearance |

C+ never repairs original A/C record gaps. The two C+ windows share one host simulator and source timeline, but a healthy later window does not prove what happened during an earlier unobserved interval. The first assessment remains intact. No automatic recovery command or release of SAFE protection is attempted.

**Recovery criteria limitations:** RC-01 SAFE is observed via HK3, corroborated by S5. RC-02 thermal clearance is evaluated on HK1. RC-03 stable/no-recurrence is **partial** (five-second thermal subset, no independently agreed global predicate). RC-04 other subsystem health is **not demonstrated**. RC-05 native parsed TM, timing/coverage/link summary and file equality provide **partial** evidence quality; there is no independent raw-wire custody, cryptographically authenticated producer attestation or completeness across unobserved periods. Therefore `ADMISSIBLE` **never** means spacecraft operations may resume.

**Threshold:** Core's fault definition is raw `>1250`; frozen evaluator's clearance requires raw `<1250`. At raw=1250 the condition is not accepted as cleared. This conservative equality behavior is explicitly scoped to the experiment, not automatically derived by Core.

## 5. Reproduction and content

Commit-ready candidate subtree:

- `experiments/g1/mission/` — nine Core YAML mission files.
- `experiments/g1/g1_core_native_trace.py` — read-only contract/evidence validator.
- `experiments/g1/g1_offline_evaluator_v0_4.py` — frozen independent local assessor.
- `experiments/g1/g1_cplus.py` — continuous-process two-window runner and observation request.
- `experiments/g1/test_g1_cplus.py` — six negative/regression tests.
- `experiments/g1/fixtures/` — original A/B/C parsed-TM fixtures and hashes, frozen A/B/C verdicts.
- `experiments/g1/README.md` — pins, expected semantics, reproduction commands.
- `docs/experiments/g1-safe-evidence.md` — story-oriented explanation and questions for joint review.
- `docs/experiments/g1-engineering-handoff-20261126.md` — **this dossier**.

All external source checkouts and simulator binaries remain upstream: no vendor source or executable is added. Re-run the commands in [`experiments/g1/README.md`](../../experiments/g1/README.md) using the stated commits. The released OrbitFabric openOBSW/openSVF adapter is **not** claimed to support generic thermal scenario projection or recovery judgments. Source tests should be reviewed as PoC-scoped reuse of upstream test fixtures, not a stable upstream API.

User-workstation local evidence files (**not committed** to this PR):

```
G1_CPLUS_REPORT.md
 g1-cplus-assessments.json
 g1-cplus-first-retained.json
 g1-cplus-full-capture.json
 g1-cplus-second-fresh.json
 g1-cplus.sha256
```

The SHA-256 check on 2026-11-26 returned `OK` for the first five files. It proves equality to the sidecar checksum, **not authenticated native producer custody**.

## 6. GitHub gate reconciliation (2026-11-26)

- [Gonçalo's 17 November G0 update](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1#issuecomment-6940902275) established the upstream enabling changes and their limitations.
- [Gonçalo's 21 November correction](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1#issuecomment-7068637637) established that all v0.19 PRs #124–#130 except #127 touched `src/`. Section 4 in [PR #5](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5) now lists the changes explicitly.
- [His PR review](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5#issuecomment-7068638035) stated G0 could close after that correction, with six residuals carried into G1.
- PR #5 was merged on 2026-11-26 at `5702a0a6499b2d3a1dbcb52255f59d6df772aabb`; [issue #1](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1) was closed with the residual disposition recorded.
- The historical G0 source basis remains openOBSW v0.19 / openSVF `034945e`; this **subsequent** locally executed G1 work pins openOBSW v0.20 / openSVF v1.3.0. Their evidence claims are not interchangeable.
- Issues [#2](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/2), [#3](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/3) and [#4](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/4) remain open for joint design and independent acceptance. No G1 milestone completion is asserted.

## 7. Proposed reviewer questions for Gonçalo

1. Is the completed G0-to-G1 source-baseline transition described accurately, without extending G0 host-SIL evidence to hardware?
2. Are parsed-TM listener observations and dual derived views an acceptable **PoC-local** minimum, without falsely asserting raw-wire custody?
3. Does the same-process two-window C+ design demonstrate **new evidence for a new interval**, without retroactively repairing an unknown prior interval?
4. Are the SAFE/HK/event and OBT/time claims aligned with openSVF 1.3.0 and openOBSW v0.20, without extrapolating thermal results to Renode/flight hardware?
5. Do we agree on the RC-03/RC-04/RC-05 limitations and on what, if anything, merits a reusable upstream feature later?

## 8. Proposed public-story direction

**Title:** *SAFE Is Not Ready: When a spacecraft recovers before the evidence does*.

The story progresses from a real anomaly/SAFE response to a comparison of actual recovery versus retained evidence, then to contract-governed native observation correlation and deliberate refusal of semantic drift. The optional-but-executed C+ shows a bounded *evidence closure loop*: an indeterminate assessment can request **new** observations and reassess a **later** window. Core's mission semantics, openSVF's capture/stimulus and openOBSW's executed behavior remain distinctly owned. The story is experimental and repeatable, not a new operational authorization product.

**Engineering-story publication and G1 acceptance should remain joint.** This draft PR is a request for Gonçalo's independent technical review, not a G1 closeout or permission to modify upstream software.
