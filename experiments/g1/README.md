# G1 — SAFE Is Not Ready: mission contract, native evidence, C+

**Status (2026-11-26):** executed and locally verified candidate; **independent G1 review and publication remain pending**.  
**Scope:** bounded thermal observation experiment, not spacecraft operational recovery authorization.  
**Owners:** proposed joint OrbitFabric / openOBSW / openSVF engineering discussion; upstream acceptance remains open.

This directory holds a small, source-backed demonstration of a real engineering distinction: the spacecraft can clear an anomaly while the **retained evidence** remains insufficient to justify the bounded assessment. An explicit observation request can then trigger a **new observation window**, without backfilling history or commanding SAFE exit.

## What the repository candidate contains

- `mission/`: nine-file, synthetic OBC OrbitFabric Mission Model. Validated with **Core 1.3.0**, source revision `d0206f11d31922581a05b96ee76d05bf7b0d6870` on the test workstation. Core owns the entity identities and declared `>1250` fault condition; it does **not** execute FDIR or define the five-sample policy.
- `g1_core_native_trace.py`: read-only validation of the real Core Integration Input Set against the original A/B/C native parsed-TM captures and their frozen v0.4 reports. Rejects threshold/semantic mismatch; no recovery verdict computation.
- `g1_offline_evaluator_v0_4.py`: **frozen** story-local admitted-observation evaluator, not part of either upstream project. A/B/C policy: 5-second window, 5 HK1 and HK3, threshold 1250 raw. The subprocess decision receives admitted observations and declared window, not C-derived metadata or scenario name.
- `g1_cplus.py`: one **continuous** pinned host-SIL process; first incomplete retained window -> `INDETERMINATE` -> observation request -> fresh full window -> new bounded assessment. Retains the complete producer-observed parsed-TM stream and produces two explicitly derived assessment views.
- `test_g1_cplus.py`: offline unit/admission tests; any synthetic second window is **not** evidence of executing C+ host-SIL.
- `fixtures/`: immutable original A/B/C parsed-TM captures, sidecar checksums, and existing qualified v0.4 verdicts, for reproducibility. No simulation binary or external project source is vendored.

## Precisely what the stories claim

| Story | Observation | Outcome |
|---|---|---|
| A | 5 complete nominal-temperature HK1 and 5 HK3 SAFE samples | Bounded thermal `ADMISSIBLE` |
| B | 5 high-temperature HK1, 5 HK3 SAFE samples | Bounded thermal `NOT_ADMISSIBLE` |
| C | Exactly A minus three retained HK1 reports | Bounded thermal `INDETERMINATE` |
| C+ | **Separate** continuous host-SIL run: C-like incomplete first window, then fresh second window | First `INDETERMINATE`, second `ADMISSIBLE` **observed in the local host-SIL replay** (not independently reviewed) |

C is an **offline projection** of A; not an RF loss event or a separate spacecraft run. C+ is a new, distinct host-SIL experiment, **not** an extension of the original A/C recorded run. Neither changes the original experiments. In C+, the unmodified host simulator must remain alive during both windows. The first verdict stays permanently indeterminate.

An `ADMISSIBLE` result means the **five-second thermal subset** only. RC-03 (no recurrence) is partial, RC-04 (other-subsystem health) unproven, RC-05 partial. No SAFE -> NOMINAL authorization is claimed.

## Trusted/pinned interfaces

| Dependency | Pinned basis |
|---|---|
| openOBSW | `a4c56715cbf57e34d7812b71a4d5f32cf9285b18` (v0.20) |
| openSVF | `9bf3f3a29696f695a6406080ad4436cb4a5154fc` (v1.3.0) |
| `obsw_sim` local binary | SHA-256 `4672bdc9473d6097b6a7dfba4085992b4013b6e99b84f4f1e97c628ef662ba7b` |
| OrbitFabric Core | 1.3.0, Git `d0206f11d31922581a05b96ee76d05bf7b0d6870` (local tested) |
| Evaluator | frozen experimental v0.4 as included |

The `ThermalHarness` imported by C+ is a **pinned upstream test fixture** in `openSVF/tests/system/test_obsw_alignment.py`; this is intentional PoC-local reuse, not a released public Python API or production adapter integration. The live run requires an existing workspace containing the exact source checkouts and built `bin/obsw_sim`. The actual 2026-11-26 user-workstation replay produced one PID and two contiguous windows (5–10 s, 10–15 s). Its full JSON output remains local on that workstation; it is **not included** in this source-only review package. This package never modifies them.

## Reproduction on the established G1 workstation (WSL)

Assumes an existing G1 host-SIL workspace with pinned `GF/.venv`, `GF/upstream/{opensvf,openobsw}`, a built `obsw_sim`, and a validated Core Integration Input Set. Clone this PoC repository to a local working directory; this review branch does not vendor upstream dependencies:

```bash
# Supply your own existing host-SIL workspace and this repository checkout
GF='/path/to/your/spacecraft-recovery-evidence-g1'
REPO='/path/to/your/spacecraft-recovery-evidence-poc'
CAND="$REPO/experiments/g1"
CORE="$GF/vertical-slice/G1_THERMAL_MISSION_MODEL_CANDIDATE_2026-11-26/generated/integration_input"

# 1. No host-SIL required: existing evaluator and negative tests
"$GF/.venv/bin/python" "$CAND/g1_offline_evaluator_v0_4.py" --self-test
"$GF/.venv/bin/python" "$CAND/test_g1_cplus.py"

# 2. Compare the validated real Core export with frozen A/B/C evidence
"$GF/.venv/bin/python" "$CAND/g1_core_native_trace.py" \
  --core-dir "$CORE" --artifacts "$CAND/fixtures" \
  --output "$GF/review/G1_CORE_NATIVE_TRACE_CHECK.md"

# 3. Execute C+ in one real host-SIL process, new distinct run directory
"$GF/.venv/bin/python" "$CAND/g1_cplus.py" \
  --gf "$GF" --core-dir "$CORE" \
  --evaluator "$CAND/g1_offline_evaluator_v0_4.py" \
  --out "$GF/cplus-runs/first-candidate"

# 4. Verify produced checksums
(cd "$GF/cplus-runs/first-candidate" && sha256sum -c g1-cplus.sha256)
```

If `first-candidate` already contains files, specify a new output directory. The script refuses to overwrite previous evidence. The first two commands are offline gates; **the live C+ replay on 2026-11-26 passed locally**; the reproducibility commands remain necessary for independent review.

## Expected live C+ conditions

- Exactly one host simulator process ID, one initialize and one teardown, no reset, no SAFE exit.
- Fault S5 0x0051 and SAFE-entry S5 0x0002, authoritative HK3 SAFE, 1300 raw at fault then 650 after fault clearance.
- First window [5,10] s: original 5/5 HK1, retained only 2/5; HK3 5/5 -> `INDETERMINATE` and a request for **new** 5-second HK1/HK3 observation.
- Second window [10,15] s: **fresh** 5/5 HK1 and HK3 from same process -> expected `ADMISSIBLE` if native observations and admitted evidence support it.
- `g1-cplus-full-capture.json` retains both original windows and packet identities. The two view files declare their selection/omission provenance. An explicit request is produced **before** the second window is acquired.
- Summary `G1_CPLUS_REPORT.md`; all local outputs covered by `g1-cplus.sha256`. These hashes attest file equality, **not** independent producer authenticity.

Any mismatch is **NOT QUALIFIED**, not an invitation to fake, reconstruct or manually adjust observations. Capture link health and the pinned simulator state for triage.

## Boundary / source truth

- Core: mission entity identities and declared threshold.
- PoC binding: HK1/HK3/S5 source mapping (not a released adapter).
- openSVF: native stimulus, simulator timeline and parsed-TM capture.
- openOBSW: executed onboard response.
- Frozen evaluator: **separate story-local** bounded verdict policy.
- PoC C+: missing-observation request and two-window orchestration **only**.

The C+ observation request is **not a telecommand**, autonomous planner, recovery controller, or a full recovery-intent projection of OrbitFabric. Original C unknown history stays unknown; the later assessment pertains only to the later interval.

## Integration/review status

- G0 source-feasibility reconciliation was merged in **PR #5** (`5702a0a`) and issue #1 closed, with residuals explicitly carried into G1. This G1 code/contract and its results remain independent-review candidates, not jointly accepted.
- Artifacts here come from a local experimental baseline, not a shared producer-approved Evidence Bundle schema.
- This review branch publishes source, frozen A/B/C fixtures, local replay transcript and reproduction instructions. The full C+ JSON capture and its checksum sidecars remain on the execution workstation; **not** contained in the repository. Independent recreation and review are pending.
