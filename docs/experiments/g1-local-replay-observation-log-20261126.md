# G1/C+ local host-SIL replay summary (user-provided shell transcript)

**Source:** shell output posted from the user workstation on 2026-11-26. This file is a *transcription* of the displayed command results, **not** the original host-SIL evidence bundle, cryptographically authenticated producer output, or independent reviewer execution.

## Offline checks

```text
Evaluator v0.4 SELFTEST: PASS (A/B/C; blind worker; derived counterfactual; projection fidelity; SEM-01 malformed inputs)
Ran 6 tests in 0.286s
OK
G1 CORE-NATIVE CORRELATION: PASS
A: ADMISSIBLE | HK1=5 | HK3=5 | TM=70
B: NOT_ADMISSIBLE | HK1=5 | HK3=5 | TM=70
C: INDETERMINATE | HK1=2 | HK3=5 | TM=67
C omitted original A HK1 indices: [54, 60, 66]
```

## Continuous C+ host-SIL

```text
[fault-engine:obc_thermal] Injected stuck on 'dhs.obc_thermal.temperature_raw' value=1300.0 duration=0.0s
G1 C+ CONTINUOUS HOST-SIL: PASS
One simulator process PID 22296; windows 5.0-10.0 and 10.0-15.0s
First: INDETERMINATE | HK1=2 | HK3=5
Second: ADMISSIBLE | HK1=5 | HK3=5
```

Run ID from the generated report: `g1-cplus-a78b4f92c357`. Input Set SHA-256: `f7de824fca1e18a7dc093f8f73c3b39d9777254828fd06d56bd7426e4ea10c7b`.

## Sidecar checks

The workstation reported `OK` for `G1_CPLUS_REPORT.md`, `g1-cplus-assessments.json`, `g1-cplus-first-retained.json`, `g1-cplus-full-capture.json`, and `g1-cplus-second-fresh.json` using `sha256sum -c g1-cplus.sha256`. Those files and their checksum sidecars are **not included** in this PR. Independent review must rerun the experiment or separately receive the original outputs; hashes alone do not authenticate the producer.

## Interpretation limits

The first assessment was performed before requesting and acquiring a *new* five-second interval in the same simulated process. Missing earlier HK1 remain missing; the later assessment covers only the later thermal interval. RC-03 partial, RC-04 not demonstrated, RC-05 bounded; there is no permission to exit SAFE.
