# G1 — Evidence field inventory (source-backed candidate v0.1)

**Status:** PROPOSAL / source inspection only; **not** an approved schema, runtime capture qualification, or Recovery Assessment Contract  
**Date:** 2026-11-20  
**Threads:** [#2 minimum bundle](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/2), [#3 TM observability](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/3), [#4 recovery criteria](https://github.com/OrbitFabric/spacecraft-recovery-evidence-poc/issues/4)  
**Depends on:** [G0 baseline reconciliation](../gates/g0-source-baseline-20261120.md)

## A. Frozen basis, vocabulary, and limits

- **OBSW producer:** [openOBSW v0.19](https://github.com/lipofefeyt/openobsw/tree/c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c), commit `c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c`.
- **Verification/runtime producer:** [openSVF](https://github.com/lipofefeyt/opensvf/tree/034945e8841eda3e4a35e07624a06aec5c6db26a), commit `034945e8841eda3e4a35e07624a06aec5c6db26a`, pinned to openOBSW `v0.19`.
- **PoC assessor:** not implemented. No evidence contract agreed, no exporter qualified and no A/B/C PoC results yet.
- **Producer-owned** means an observation from openSVF/openOBSW. **PoC-captured** means an unchanged or explicitly transformed copy whose custody and provenance are owned by this PoC. **Derived** means calculated, correlated, filtered or assessed after acquisition; it must never be confused with an OBSW-originated fact.
- The `obc_thermal` model is **F1** (constant nominal raw 650), not a predictive spacecraft thermal model.

## B. What the pinned code exposes

| Candidate datum | Native producer / actual source | Available representation now | Time domain / provenance | Proposed status and caveat |
| --- | --- | --- | --- | --- |
| Fault command: injection and explicit clearance | openSVF procedure context + equipment fault engine | Procedure step events can describe actions (`INJECT` / `INFO`), but do **not** automatically constitute a typed, complete fault-state history | Procedure simulation time; simulator action | **Available as execution control**, **structured fault schedule needs qualified capture**. Preserve injected type, raw value, onset, explicit clearance and equipment instance; do not infer that finite `duration_s` has expired |
| Applied thermal raw input | `dhs.obc_thermal.temperature_raw` from F1 model / fault engine | ParameterStore value and v4 frame field `obc_temperature_raw` | Simulator time / equipment | **Available in producer**, but persistent history not guaranteed. Record independently from reported OBSW temperature |
| Thermal input validity | `dhs.obc_thermal.status` / frame `thermal_valid` | Model value and v4 frame | Simulator time / equipment | **Available in producer**. Invalid input leaves S20's last value unchanged; it is not proof of recovery |
| OBSW-reported OBC temperature | openOBSW HK set 1 `TM(3,25)`; openSVF SRDB HK decoder | `dhs.obc.obc_temperature`, raw signed int16 (nominal 650; threshold 1250; fault 1300) | Onboard TM CUC + listener simulation time | **Decoded and upstream L3 tested**, but only latest ParameterStore value retained. Persist *each received HK report* |
| OBSW mode | HK set 3 `TM(3,25)`; openSVF adapter | `dhs.obc.obc_mode`; historical alias `obc_mode`; `LinkHealth.mode_changes` | TM CUC and listener simulation time; mode_changes records **HK-observed changes**, not every HK sample | **Available**. HK set 3 is authoritative for mode; S5 mode-entry event is corroboration rather than an HK replacement |
| OBSW on-board time (OBT) | TM secondary header and HK set 3 `obc_obt` | Parsed `PusTmPacket.timestamp`; HK `dhs.obc.obc_obt` | 32-bit seconds in host/FreeRTOS; no proven UTC epoch mapping | **Available**. Establish reset/rollover and TC(9,128) semantics; distinguish CUC field, HK OBT and simulator time |
| S12 thermal-high event | openOBSW S5, `TM(5,4)` event `0x0051` | Event ID + float32 auxiliary monitored raw count, observable in parsed `PusTmPacket.app_data` | TM header OBT + listener simulation time | **Native packet available**; write a typed decoder and validate event severity, aux length and units (e.g. 1300 raw) |
| SAFE-mode-entry event | openOBSW host sim S5 event `0x0002` | Parsed `TM(5,4)` event | TM OBT + listener sim time | **Native in v0.19**, unlike earlier G0 baseline. Correlate with next HK set 3, do not infer return-to-operations authorization |
| STANDBY and NOMINAL entry events | openOBSW S5 `0x0004` / `0x0005` | Parsed S5 event | TM OBT + listener sim time | **Native**; negative claim (e.g. "no 0x0005") requires documented observation window and coverage |
| Link statistics and mode change summary | openSVF `LinkHealth` | `tm_received`, `tm_parsed`, `tm_dropped`, `tc_*`, `desyncs`, `hk_undecoded`, `mode_changes`, `healthy` | Counters since adapter connection; mode changes use sim time | **Native snapshot**, not proof of complete per-packet chronology; preserve snapshot at well-defined boundaries |
| TC acceptance / rejection | openOBSW S1 telemetry processed by openSVF | `TM(1,1/2/7/8)` parsed and aggregate `LinkHealth` counters | Packet header OBT + listener sim time | **Available**. SAFE gate of `TC(20,1)` unchanged; tests should not use it for thermal clearance |
| Verification campaign verdicts | openSVF `CampaignReport.to_dict()` | Campaign, procedures, verdicts, `duration_s`, `link`, steps, step events | Run duration is wall-clock; step event `t` is simulation time | **Native JSON**. PASS/FAIL/ERROR/INCONCLUSIVE is not the PoC's ADMISSIBLE/NOT_ADMISSIBLE/INDETERMINATE |
| Procedure step event timeline | openSVF `ProcedureContext` and `CampaignReport` | `steps[].events[]`: `t`, `type`, `description`, `details` | Simulation time sampled at logging (rounded in procedure context) | **Native but selective**: events are logged by procedures and do not cover every TM or every HK sample |
| Individual parsed TM packets | openSVF `HilAdapter.add_tm_listener(listener)` called by OBC emulator after successful parse | `listener(PusTmPacket, sim_time)` with APID, sequence, service/subservice, timestamp and `app_data` | Separate packet CUC/OBT and listener sim time | **Candidate primary PoC capture seam**. Callback precedes or is independent of queue draining. Requires executable test for ordering, packet drops, callback behavior, lifecycle and coverage |
| Original raw TM bytes | openOBSW wire output, processed by openSVF before listener | **Not provided by** `PusTmPacket` listener interface as original wire bytes; `app_data` is bytes, but framing/packet reconstruction is not equivalent to preserving received bytes | Wire source and capture stage | **GAP** if immutable raw TM is required. Investigate non-intrusive producer-owned capture or explicitly scope v0.1 to parsed TM without claiming raw-byte custody |
| Parse failures / undecoded HK | openSVF `_parse_tm` + `LinkHealth` | `tm_dropped`, `last_drop_reason`, `hk_undecoded`, `last_hk_problem` | Session counters and messages; not full histories | **Available as summary**. A parse failure does not trigger a listener callback. Need a coverage/continuity rule for missing observations |
| Simulator stderr / subprocess exit | openSVF OBC emulator subprocess | At pinned `034945e`, stderr is read during startup but not continuously afterwards, and subsequent exit may surface first as missing sync. Not a sealed first-class run artifact | Host process state / wall clock | **Baseline-specific G1 gap**; [openSVF #208](https://github.com/lipofefeyt/opensvf/pull/208) subsequently added continuous stderr capture and exit diagnostics in v1.3.0. Verify the new fields and custody at the G1 execution baseline |
| Run/producer identity and revision pins | openSVF config, openOBSW release, Git commits, PoC manifest | Manually pin versions and configuration at present | Static configuration, file digests | **To materialize in PoC**: record commits, version, frame protocol v4, SRDB version, tests, configuration digest and local runtime identity |
| Coverage and observation continuity | Derived from capture records + link counters + declared window | No approved coverage/expected-HK contract yet | Correlated time domains, capture start/stop | **G1 DESIGN REQUIRED**: gaps, startup/end, resets, requested vs observed sampling, parse/desync and event absence |
| Artifact integrity and assessment outputs | PoC custody layer / assessor | Not implemented | Validation before assessment | **G1 DESIGN REQUIRED**: digests, completeness policy, immutable producer evidence, separate derived decisions, invalid-input rejection |

## C. Source anchors (pinned)

These are implementation anchors, **not** proof of a completed PoC acquisition:

1. [`HilAdapter.add_tm_listener` and `_notify_tm`](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/models/dhs/hil_adapter.py#L64-L78): parsed TM callback signature and queue independence.
2. [`OBCEmulatorAdapter._parse_tm`](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/models/dhs/obc_emulator.py#L947-L1115): parse/drop handling; listener invocation; S5 and SRDB HK processing; HK mode/OBT.
3. [`PusTmPacket`](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/pus/tm.py#L46-L75): parsed packet fields including 32-bit timestamp and byte `app_data`.
4. [`LinkHealth`](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/models/dhs/link_health.py#L20-L87): counters, mode timeline, `healthy` definition.
5. [`CampaignReport.to_dict()`](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/campaign/campaign_runner.py#L110-L180) and [`ProcedureContext`](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/campaign/procedure.py): selective campaign step events; link-health attachment.
6. [`obc_thermal` F1 model](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/models/dhs/obc_thermal.py) and [fault-engine implementation](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/src/svf/core/equipment_fault.py): simulator input and explicit clearance.
7. [openSVF L3 A/B-like integration tests](https://github.com/lipofefeyt/opensvf/blob/034945e8841eda3e4a35e07624a06aec5c6db26a/tests/system/test_obsw_alignment.py#L440-L579): source-backed executable thermal path, **not** OrbitFabric assessment.
8. [openOBSW sensor-frame definition](https://github.com/lipofefeyt/openobsw/blob/c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c/sim/sensor_inject.h), [S5 SRDB](https://github.com/lipofefeyt/openobsw/blob/c9fdc5d15c4976820bfe38e1df1804c9d5c39d6c/srdb/data/events.yaml): wire v4, units, event IDs and auxiliary format.

## D. Clock/provenance distinctions to preserve

| Clock / identifier | Where observed | Rules for a first contract |
| --- | --- | --- |
| `sim_time` supplied by listener | openSVF at delivery of parsed TM | Capture explicitly as *acquisition simulation time*. Never silently replace onboard event time with it |
| `PusTmPacket.timestamp` | openOBSW TM secondary-header field | Capture as **onboard OBT seconds**, not validated UTC or subsecond event chronology |
| `dhs.obc.obc_obt` | openOBSW HK set 3 | Corroboration/sampling of onboard clock, not a substitute for timestamp on each TM |
| `LinkHealth.mode_changes[][0]` | openSVF | **Simulation-time HK change observations**, not an exhaustive event or HK timeline |
| TC and fault intervention `t` | Procedure events / equipment model | Simulator command time, which is not proof of when OBSW perceived a physical phenomenon |
| Sequence count / capture order | Parsed TM and local capture counter | Useful continuity input but **not yet qualified** as a loss-proof cross-reset metric |

**Do not infer:** two packets with equal integer OBT seconds are simultaneous or their relative order is known from OBT alone. A continuous-looking HK sequence does not prove missing TM(5,x) cannot exist. Sample provenance and arrival ordering remain separate data.

## E. Proposed minimum candidate: discuss before locking a schema

The *minimal* bundle should expose logical sets, without prescribing filenames or wire formats yet:

1. **Run identity:** software source revisions, simulator configuration and binary identity, protocol version, parameter layout and test definition, producer/tool versions.
2. **Native campaign record:** unmodified openSVF campaign report, with run and per-step outcomes retained as upstream verdicts.
3. **Parsed TM observations:** ordered, timestamped S5, HK sets 1/3 and any relevant S1, preserving the parsed packet's APID/sequence/metadata and `app_data` bytes; clearly label that original raw TM framing is **not** preserved by this listener.
4. **Simulation interventions:** fault schedule and actual applied input/validity, with mechanism and provenance separate from OBSW-observed HK.
5. **Communication evidence:** session link-health snapshot(s), parse/desync/unknown HK conditions, declared capture boundaries and gaps.
6. **Custody/integrity:** source hashes, transformations, capture completeness rules, and strictly separate derived assessments.

The acceptance of any field or omitted field must be made jointly. Only the **validated evidence input** enters per-requirement assessment; malformed or unverifiable bundles are rejected, not assigned a fourth verdict.

## F. First observability spike: proposed acceptance tests (not run)

**To execute only after review of the capture plan:**

- [ ] Run pinned openOBSW `obsw_sim` with pinned openSVF and the native thermal scenario, and record exact commands/configuration/binary digests.
- [ ] Register the listener before the first relevant TM. Verify every successfully parsed packet invokes exactly one callback, in order, even if another consumer drains `get_tm_queue()`.
- [ ] Record a complete **A-like** thermal event/clearance window and check S5 event IDs/float32 aux, signed HK1 raw values, HK3 mode and packet timestamp vs observed HK OBT. Account for the S1 TC(9,128) old-time exception (OBSW-SRS-153).
- [ ] Record a persistent **B-like** window under the same acquisition rules.
- [ ] Introduce controlled packet loss, malformed HK and/or missing capture to test `tm_dropped`, `hk_undecoded`, `desyncs` and capture gap reporting. Distinguish upstream parser drop from deliberate PoC-side redaction.
- [ ] Verify that the raw TM requirement can be satisfied **without private monkey-patching of upstream internals**; otherwise explicitly defer it or propose a reviewed upstream hook.
- [ ] Test reset/OBT discontinuity and same-second event ordering before accepting a clock-correlation rule.
- [ ] Freeze a field inventory with classifications: **native and qualified / native but not yet captured / derived / unavailable**.

**No scenario-level ADMISSIBLE verdict should be generated by this spike.** This is a G1 observability and contract input, not the execution or closure of G3.
