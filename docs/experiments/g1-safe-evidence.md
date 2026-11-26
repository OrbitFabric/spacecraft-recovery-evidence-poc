# SAFE Is Not Ready — G1 engineering-story evidence and review boundary

**Status:** joint-discussion candidate / not yet an agreed G1 closeout.  
**Source:** local, pinned openOBSW v0.20 + openSVF v1.3.0 host-SIL / OrbitFabric Core 1.3.0.

## Why this experiment is worth reviewing

Entering SAFE and clearing a thermal anomaly are not the same as *demonstrating* a recovery condition. A and C follow the same underlying observed behavior but differ in available HK1. The frozen experiment accepts A (`ADMISSIBLE`), rejects B as thermally unsafe (`NOT_ADMISSIBLE`) and leaves C undecidable (`INDETERMINATE`). These are **bounded thermal** assessments, not operational authority to resume mission activities.

The OrbitFabric contribution is specific: declared mission identities, units, threshold and mode semantics form a Core-validated source for the observation binding. A separate local consumer refuses to correlate a self-consistent **but drifted** Core limit (1200) to evidence qualified at 1250. This proves semantic-contract consistency, not synthesis of the five-sample rule or automated export of an openSVF verification scenario.

The native executable contribution is also specific: openSVF stimulates the thermal model and retains native parsed TM from running openOBSW in a controlled host-SIL scenario. The evaluator is a separate, frozen story-local consumer and remains independent of runtime expectations and the derived C labels.

## C+: proposed extension to the same engineering question

A **new single-process run**, distinct from historical A/B/C, deliberately omits only three retained first-window HK1 samples. The first assessment remains `INDETERMINATE`. It emits a structured request for a **fresh** five-second interval of thermal HK1, corroborated by HK3 SAFE. The host simulator stays alive, the fault remains cleared, and a second observation window is acquired. The second assessment reuses original fault-entry evidence and **only second-window HK**; it must not backfill the earlier window.

The new observation request is derived from the first evaluator's UNKNOWN criteria and references `telemetry:obc.temperature_raw` from Core. Its five-sample coverage rule is **experimental v0.4 policy, not owned by OrbitFabric**. No onboard command or automated SAFE exit occurs.

C+ is a constrained host-SIL demonstration of the *need for further observations*, not an actual ground-pass scheduling product. A later healthy interval cannot establish that an earlier unobserved interval contained no recurrence. RC-03 is only partially demonstrated; RC-04 is not demonstrated; RC-05 is bounded to existing capture checks. Those limits must remain in the publication narrative.

## Reproducible review inputs

See [`experiments/g1/README.md`](../../experiments/g1/README.md) for precise pins, original fixtures, validator, live C+ runner, offline unit tests and the local replay command. No upstream dependency is vendored. The local C+ output **passed on the user workstation on 2026-11-26**, with the independent review still pending. Full live-run JSON outputs remain on that workstation and are not represented as attached producer-authenticated evidence in this repository bundle.

## Questions for Gonçalo / joint G1 review

1. Is the distinction between producer parsed TM, PoC-derived evidence projections and independent assessment unambiguous?
2. Do the two windows preserve simulator continuity and original packet/time identity sufficiently for the bounded claim, without overstating the capture's provenance?
3. Are HK1/HK3 + S5 0x0051/0x0002 correctly interpreted in the pinned openSVF/openOBSW revisions?
4. Is the per-window assessment framing honest about RC-03/RC-04 and about the inability to reconstruct historical gaps?
5. Which pieces, if any, merit later upstream abstraction, and which should remain PoC-local?

**This is a PoC-local experimental review candidate.** G0 source documentation was merged via PR #5; G1 interface and assessment conclusions remain subject to joint review. No upstream source changes or operational SAFE-exit authority are claimed.
