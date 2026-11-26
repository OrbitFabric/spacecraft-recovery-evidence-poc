# SAFE Is Not Ready | G0 → G1 source-baseline transition

**Status:** D0.2, 2026-11-26; G0 source-feasibility closeout recorded after PR #5 merge. **G1 technical contract and results pending joint review**.  
**Scope:** provenance and interpretation of the PoC's successive source baselines. This document records the source progression *after* G0 closure; it does not approve an Evidence Bundle, approve RC-01..05, or authorize spacecraft recovery.

## 1. Why there are two baselines

G0 is an auditable **feasibility/source reconciliation**, documenting the changes that made the thermal SAFE/clearance experiment natively executable in the host simulator. G1 is the **subsequent, locally executed PoC experiment** involving A/B/C, the synthetic OrbitFabric Mission Model, contract-to-evidence binding and the continuous-run C+ extension.

These baselines are chronological and complementary. G1 does not retroactively change what the earlier G0 source audit proved, nor does the G0 draft's historical “not yet run” statement describe the subsequent G1 results.

## 2. Version ledger

| Component | G0 audit/document basis | G1 local experiment basis | What changed / how to read it |
|---|---|---|---|
| openOBSW | **v0.19**, `c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c` | **v0.20**, `a4c56715cbf57e34d7812b71a4d5f32cf9285b18` | The [v0.20 release](https://github.com/lipofefeyt/openobsw/releases/tag/v0.20) is a documentation release: **no change to flight code, wire protocol v4 or SRDB content** versus v0.19. It adds generated reference material and validation/CI, not a new flight-thermal recovery claim. |
| openSVF | `034945e8841eda3e4a35e07624a06aec5c6db26a`, pinned alongside v0.19 | **v1.3.0**, `9bf3f3a29696f695a6406080ad4436cb4a5154fc` | [v1.3.0](https://github.com/lipofefeyt/opensvf/releases/tag/v1.3.0) pins openOBSW v0.20 and contains the existing thermal input/parsed HK/event path plus subsequent stderr/exit handling (#208), finite-duration fault expiry (#207), and OBT alignment L3 tests (#209). A PoC run does not automatically qualify every feature under every fault or time condition. |
| OrbitFabric Core | Not part of the v0.19 / `034945e` G0 source-audit evidence | **1.3.0**, `d0206f11d31922581a05b96ee76d05bf7b0d6870` | A synthetic nine-YAML Mission Model was linted with **0 errors / 0 warnings** and exported to a Core Integration Input Set. The Core entity index was associated with native parsed TM through **PoC-local** bindings; it is not a released adapter capability or a Core recovery engine. |
| Story-local evaluator | Not implemented/qualified by G0 | Frozen experimental **v0.4** | Independent bounded thermal assessment of admitted observations, separate from openSVF's native campaign PASS/FAIL and separate from any spacecraft authorization. |
| PoC C+ | Not in G0 | Executed locally, 2026-11-26 | One continuous host simulator; original first-window incomplete retention → `INDETERMINATE` → request for a **new** observation window → later-window `ADMISSIBLE`, without repairing historical evidence. |

**Source pins and run claim:** The G1 result derives from the user-workstation replay, run ID `g1-cplus-a78b4f92c357`, one simulator PID `22296`, first 5–10 s, second 10–15 s. Its full original capture and assessments remain on the workstation, not in this draft repository package. Five output checksums were verified locally. See [G1 engineering handoff](../experiments/g1-engineering-handoff-20261126.md) and [`experiments/g1/README.md`](../../experiments/g1/README.md) once the G1 candidate is proposed for review.

## 3. What G0 established and what it did not

The G0 source audit and Gonçalo's [17 November comment](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1#issuecomment-6940902275) establish the host-simulator's ability to exercise a thermal fault, trigger S12/S5/SAFE, clear the simulated thermal input through the equipment model and observe housekeeping while remaining SAFE. The [21 November correction](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1#issuecomment-7068637637) makes clear that **all openOBSW v0.19 PRs #124–#130 except #127 touched `src/`**; the thermal sensor fields themselves are still consumed only by the **host simulator**. STM32H7 Renode FDIR evidence exercises a **different parameter**, not the thermal closed-loop scenario, and is not hardware qualification.

The full corrected list is already recorded in draft [PR #5](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5), `docs/gates/g0-source-baseline-20261120.md`, section 4. The six residuals in its section 5 are carried into G1 rather than used as G0 exit blockers, consistent with [Gonçalo's PR #5 comment](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5#issuecomment-7068638035).

**G0 disposition:** Following Gonçalo's conditional closeout response, PR #5 was merged as `5702a0a6499b2d3a1dbcb52255f59d6df772aabb` and issue #1 closed on 2026-11-26. The six residuals remain G1 inputs. This formalizes *G0 source feasibility only*, not Gonçalo's acceptance of the later G1 implementation or evaluator.

## 4. Exactly what G1 adds and what remains provisional

**Locally demonstrated:**

- A: recovered thermal value 650 raw, sufficient retained post-fault HK1 and HK3, bounded `ADMISSIBLE`.
- B: persistent 1300 raw, sufficient HK, bounded `NOT_ADMISSIBLE`.
- C: **same underlying A capture**, deliberately omit original HK1 packet indices `[54, 60, 66]`, bounded `INDETERMINATE` (not a separate flight or RF-loss run).
- Core's declared `>1250` fault, telemetry identities, event IDs and SAFE mode are resolved in a real exported Mission Model and correlated with parsed TM; a separately lint-valid 1200-raw contract fails the PoC correlation check.
- C+: a **new** continuous host-SIL process with two successive 5-second windows: deliberately incomplete first retained view (2/5 HK1) → new observation request → fresh later 5/5 HK1 and 5/5 HK3, re-assessed with the **unchanged** v0.4 evaluator. The first verdict stays `INDETERMINATE`.

**Not claimed:** G1 evidence/RC policy was jointly approved; openSVF provides producer-owned original raw-wire custody; semantic checks are generic OrbitFabric adapter features; thermal input was qualified on hardware/Renode; RC-03 global non-recurrence or RC-04 other-subsystem health was demonstrated; an `ADMISSIBLE` verdict permits SAFE→NOMINAL or resumption of spacecraft operations. RC-05 is bounded by the actual capture/provenance checks; file SHA-256 equality does not authenticate independent producer custody.

**Important semantic limit:** Core declares `fault >1250 raw`, while the frozen v0.4 assessor requires `temperature <1250 raw` to establish clearance. Equality is deliberately not treated as cleared. Core does not own the experiment-specific 5-second/5-sample policy.

## 5. Residuals, attribution and proposed disposition

| Item | G0 disposition proposal | G1 treatment |
|---|---|---|
| Source / flight-code scope disclosure | Corrected in PR #5 §4 | Preserve baseline history; no claim of thermal flight target qualification |
| Listener ordering and captures | G1 input | Use parsed-TM listener; document callback semantics and incomplete coverage |
| Producer original raw-TM custody | G1 input, not a G0 blocker | Explicitly **not provided** by current PoC; no raw-wire authenticity claim |
| Sim exit visibility / timed fault expiry | Residuals at the **old** G0 openSVF pin | Addressed in v1.3.0 upstream; no general PoC failure-mode certification inferred |
| OBT/time semantics | G1 input | Distinguish OBT vs simulator tick time, S1 time-setting exception, reset/coverage limits |
| Assessment acceptance / full RC-01..05 | Outside G0 | G1 local *candidate*, requires joint review; RC-03 partial, RC-04 absent, RC-05 bounded |

**Next decision:** Independently review the G1/C+ draft PR and open G1 issues #2–#4, keeping the experimental verdicts bounded and the upstream boundaries explicit. G0 closure is complete; G1 acceptance remains open.

## 6. Primary references

- Joint PoC: https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc
- G0 issue: https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1
- Draft PR #5: https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/pull/5
- G1 issues: [#2 bundle](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/2), [#3 observability](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/3), [#4 criteria](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/4)
- openOBSW release notes: [v0.19](https://github.com/lipofefeyt/openobsw/releases/tag/v0.19), [v0.20](https://github.com/lipofefeyt/openobsw/releases/tag/v0.20)
- openSVF [v1.3.0 release notes](https://github.com/lipofefeyt/opensvf/releases/tag/v1.3.0)
- OrbitFabric [v1.3.0 release notes](https://github.com/OrbitFabric/orbitfabric/releases/tag/v1.3.0)

**Review note:** This is a source-baseline ledger for the G1 review branch. It describes executed local results without implying Gonçalo has examined or accepted them.
