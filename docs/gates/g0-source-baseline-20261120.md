# G0 baseline reconciliation — openOBSW v0.19 / openSVF 034945e

**Date:** 2026-11-20  
**Status:** Review candidate, **not** a unilateral gate closure  
**Related:** [PoC issue #1](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1), [G1 evidence inventory](../design/evidence-field-inventory.md)

## 1. Frozen evidence basis

| Component | Pinned revision | Verification basis |
| --- | --- | --- |
| openOBSW | annotated tag [v0.19](https://github.com/lipofefeyt/openobsw/releases/tag/v0.19), commit [`c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c`](https://github.com/lipofefeyt/openobsw/commit/c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c) | Released 2026-11-16; source and upstream tests |
| openSVF | [`034945e8841eda3e4a35e07624a06aec5c6db26a`](https://github.com/lipofefeyt/opensvf/commit/034945e8841eda3e4a35e07624a06aec5c6db26a) | `main` at the reviewed commit; [PR #198](https://github.com/lipofefeyt/opensvf/pull/198) merged 2026-11-17; `.openobsw-version` pins `v0.19` |
| Shared PoC | [`spacecraft-recovery-evidence-poc`](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc) | No A/B/C campaign evidence or independently qualified recovery assessment produced here yet |

This note consolidates **source and upstream test evidence**. No local build or functional run was performed as part of this documentation update. Earlier PDFs in [`docs/proposals/`](../proposals/README.md) remain unchanged historical discussion drafts.

## 2. Reconciliation of the original blockers

| Initial G0 finding | Status at pinned revisions | Evidence / important boundary |
| --- | --- | --- |
| No simulator-driven thermal S12 parameter; cannot clear a thermal fault while remaining SAFE | **Resolved for host SIL:** type-0x02 sensor wire frame v4 is 50 B, with `int16 obc_temperature_raw` and `thermal_valid`; valid values feed S20 before S12/HK | [openOBSW #130](https://github.com/lipofefeyt/openobsw/pull/130), closes [#122](https://github.com/lipofefeyt/openobsw/issues/122); [openSVF #198](https://github.com/lipofefeyt/opensvf/pull/198) |
| SAFE rejects TC(20,1); S11/S19 cannot bypass the dispatcher | **Unchanged, intentional.** The new simulator-owned thermal input does not depend on a TC in SAFE | openOBSW S11/S19 and host-system tests; no bypass requested |
| Mode-transition S5 events absent in host sim | **Resolved:** mode-entry event IDs `0x0002` SAFE, `0x0004` STANDBY, `0x0005` NOMINAL; `0x0003` removed | [openOBSW #127](https://github.com/lipofefeyt/openobsw/pull/127); [openSVF #195](https://github.com/lipofefeyt/opensvf/pull/195). HK set 3 remains authoritative for observed mode |
| TM secondary-header timestamp always zero | **Resolved on the host sim and supported FreeRTOS contexts:** stamped with OBT seconds | [openOBSW #129](https://github.com/lipofefeyt/openobsw/pull/129). Time correlation, resets, resolution, and parser verification still belong to G1 |
| S12 → S5 → SAFE only demonstrated on host sim | **STM32H7 FreeRTOS coupling implemented**, Renode test identified | [openOBSW #128](https://github.com/lipofefeyt/openobsw/pull/128); [Renode test source](https://github.com/lipofefeyt/openobsw/blob/v0.19/renode/test_s12_safe_stm32h7.py). **Not hardware-validated**. Test uses an S12 monitored parameter for the coupling, not the entire thermal A/B scenario on board |
| Temperature conversion / signedness inconsistent | **Resolved** at source: signed int16 and `degC = 0.1 * raw - 40`; 85 °C = raw 1250 | [openOBSW #124](https://github.com/lipofefeyt/openobsw/pull/124) and [sensor definition](https://github.com/lipofefeyt/openobsw/blob/v0.19/sim/sensor_inject.h) |
| S12 event `0x0051` auxiliary data declared inconsistently | **Resolved:** SRDB declares float32 auxiliary for the monitored value | [openOBSW #125](https://github.com/lipofefeyt/openobsw/pull/125), [event definitions](https://github.com/lipofefeyt/openobsw/blob/v0.19/srdb/data/events.yaml) |
| HK set 1 not decoded into named parameters | **Resolved:** `dhs.obc.obc_temperature` available through SRDB HK layout decoding | [openSVF #196](https://github.com/lipofefeyt/opensvf/pull/196) |
| Campaign JSON misses per-step events | **Resolved for procedure step records**, not an exhaustive TM recorder | [openSVF #197](https://github.com/lipofefeyt/opensvf/pull/197) |

## 3. Upstream execution evidence and what it does NOT establish

[openSVF's pinned L3 integration suite](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/tests/system/test_obsw_alignment.py) executes against a real `obsw_sim` binary:

- **A-like upstream behavior:** nominal 650 raw (25 °C); S12 high limit 1250 raw (85 °C); stuck input 1300 raw (90 °C) triggers S5 `0x0051` with float32 aux 1300 and SAFE-entry `0x0002`. After explicit fault clearance, HK set 1 reports 650 raw during a five-second observation interval; HK set 3 continues to report SAFE and no automatic NOMINAL entry is observed.
- **B-like upstream behavior:** keep the stuck fault active; HK set 1 continues to report 1300 raw with SAFE maintained.
- **Meaning:** the fault/clearance mechanism and observable path exist and are regression-tested upstream. These are **not** PoC Evidence Bundles, independent OrbitFabric recovery assessments, or verified A/B/C mission-level outcomes. The evidence-gap experiment C remains open.
- **Fidelity:** the `obc_thermal` equipment model is F1 (constant nominal temperature + controlled fault), **not a physical thermal dynamics model**.

CI status at pinned commits:

| Repository | Observed CI status | Qualification |
| --- | --- | --- |
| [openSVF `034945e`](https://github.com/lipofefeyt/opensvf/actions/runs/44033363866) | **SUCCESS**, including L3 tests against pinned v0.19 | Upstream integration coverage; no PoC runtime run |
| [openOBSW `c9fdc5d`](https://github.com/lipofefeyt/openobsw/actions/runs/43966820174) | **10 successes / 1 failure** | ZynqMP bare-metal job fails at **Install aarch64-none-elf toolchain**, before a validated build. Not evidence of an application-code defect, and **not** an all-green release qualification |

## 4. Scope-change disclosure

The original proposal described a simulation-only enabler and assumed that flight `src/` code would remain untouched. **That assumption was too narrow for the complete openOBSW v0.19 change train.** Gonçalo corrected the original scope note in [PoC issue #1](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1#issuecomment-7068637637). Per-PR changed-file lists were checked independently:

| openOBSW PR | Flight-source paths touched under `src/` | Nature of change |
| --- | --- | --- |
| [#124](https://github.com/lipofefeyt/openobsw/pull/124) | `src/task/pus.c`, `src/platform/stm32h7/main.c` | Signed S20 temperature typing and related platform handling |
| [#125](https://github.com/lipofefeyt/openobsw/pull/125) | `src/pus/s12.c`, `src/task/pus.c` | S12 event auxiliary-data encoding/alignment |
| [#126](https://github.com/lipofefeyt/openobsw/pull/126) | `src/pus/s5.c`, `src/task/fdir.c` | SRDB-generated SAFE-trigger configuration |
| [#127](https://github.com/lipofefeyt/openobsw/pull/127) | **None** | Host-simulation mode events; no `src/` change |
| [#128](https://github.com/lipofefeyt/openobsw/pull/128) | `src/task/mode.c`, `src/task/pus.c` | S12-to-SAFE coupling and FreeRTOS FSM concurrency control |
| [#129](https://github.com/lipofefeyt/openobsw/pull/129) | `src/task/fdir.c`, `src/task/mode.c`, `src/task/pus.c` | OBT-based TM timestamps in FreeRTOS task contexts |
| [#130](https://github.com/lipofefeyt/openobsw/pull/130) | `src/platform/zynqmp/main.c`; comment/banner-only edits in `src/platform/stm32h7/main.c`, `src/task/tmtc.c` and `src/task/fdir.c` | Reject/ignore incompatible frame length on ZynqMP; other listed flight-source changes are textual |

**Scope distinction:** `src/` changes do **not** imply that the thermal input is consumed by flight targets. At this baseline, **only `sim/main.c` applies `obc_temperature_raw` / `thermal_valid` to the monitored parameter**. The ZynqMP target and STM32H7 superloop do not use the added thermal fields; the STM32H7 FreeRTOS TMTC task accepts only TC frames. The upstream thermal A/B path is **host-SIL only**.

The STM32H7 [Renode S12-to-SAFE test](https://github.com/lipofefeyt/openobsw/blob/v0.19/renode/test_s12_safe_stm32h7.py) exercises the FDIR coupling using **`bdot_gain` (`0x20A0`)**, set while NOMINAL, not the thermal sensor-frame input. Renode evidence is not board-level hardware verification, and no race-specific concurrency test was presented for #128. Each upstream change followed its own review and testing process; neither source changes nor Renode results establish flight-hardware qualification.

## 5. Residuals and proposed gate disposition

**G0 source feasibility:** evidence supports **proceeding with G1**, with upstream host-SIL prerequisites satisfied. **G0 formal closure is pending joint review of this note and issue #1.**

Residuals to carry forward, not bury:

1. [G1 observability issue #3](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/3): qualify the TM listener's actual capture semantics, completeness and ordering; preserve full HK/S5 observations independently from procedure steps.
2. [G1 bundle issue #2](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/2): define native vs derived fields, provenance, OBT/simulation clock correlation, record integrity and completeness.
3. [G1 criteria issue #4](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/4): revise SAFE evidence predicates now that `0x0002` exists; specify unknown/coverage semantics and the A/C evidence contrast.
4. At the **pinned openSVF `034945e` baseline**, the sim stderr reader is not kept active after startup, so a fatal exit can surface only as missed sync; `duration_s` fault expiry also does not advance correctly. Use explicit fault clearance and do not claim full simulator-exit evidence at this pin. These issues were subsequently addressed upstream in [openSVF #208](https://github.com/lipofefeyt/opensvf/pull/208) and [#207](https://github.com/lipofefeyt/opensvf/pull/207), respectively, released in **openSVF v1.3.0** on 2026-11-23. Qualify these changes as part of the proposed G1 baseline, not retroactively as v0.19/`034945e` G0 evidence.
5. Test TM onboard timestamp vs HK OBT and simulator time under resets, TC(9,128), missing packets and incomplete coverage. At the pinned baseline, S1 verification TM of TC(9,128) carries the **pre-update OBT** (OBSW-SRS-153); this is expected, not a capture defect. [openSVF #209](https://github.com/lipofefeyt/opensvf/pull/209) subsequently added upstream L3 time-alignment tests, but no PoC evidence-chain qualification exists yet.
6. Carry the ZynqMP CI toolchain-install failure as a **release qualification caveat** without making it a blocker to this host-SIL G1 design task.

### Proposed G0 acceptance record

- [x] Pin the actual source revisions and release/PR links.
- [x] Reconcile original blocker list with implemented changes and tests.
- [x] Identify upstream CI outcome and hardware-scope limitations.
- [x] Record the out-of-original-scope flight-source changes.
- [ ] Obtain joint review and formal disposition on [issue #1](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/1).

**No GO for an OrbitFabric recovery verdict, C experiment, or engineering-story result is granted by this G0 reconciliation.**
