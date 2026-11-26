#!/usr/bin/env python3
"""G1 minimal read-only correlation: OrbitFabric Core entities -> parsed openSVF TM.

Uses the original A/B/C family and the *existing* qualified v0.4 report.
It neither assesses recovery nor implements a general-purpose evidence platform.
All inputs remain read-only. Only the requested Markdown report is written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REQUIRED = {
    ("telemetry", "obc.temperature_raw"),
    ("telemetry", "obc.mode"),
    ("events", "obc.thermal_hard_limit"),
    ("events", "obc.safe_entry"),
    ("faults", "obc.thermal_high_fault"),
    ("modes", "SAFE"),
}
EXPECTED = {"A": "ADMISSIBLE", "B": "NOT_ADMISSIBLE", "C": "INDETERMINATE"}


def need(ok: bool, why: str) -> None:
    if not ok:
        raise ValueError(why)


def load(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(data, dict), f"expected JSON object: {path}")
    return data


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def packet_kind(p: dict) -> tuple[str | None, int | None]:
    svc, sub = p["service"], p["subservice"]
    data = bytes.fromhex(p["app_data_hex"])
    if (svc, sub) == (3, 25) and data:
        if data[0] == 1:
            need(len(data) >= 3, "truncated HK1")
            return "HK1", int.from_bytes(data[1:3], "big", signed=True)
        if data[0] == 3:
            need(len(data) >= 2, "truncated HK3")
            return "HK3", data[1]
    if svc == 5:
        need(len(data) >= 2, "truncated S5 event")
        return "S5", int.from_bytes(data[:2], "big")
    return None, None


def from_packets(record: dict) -> dict:
    observations = record["observations"]
    need(isinstance(observations, list), "observations must be a list")
    events, temps, modes = [], [], []
    for p in observations:
        kind, value = packet_kind(p)
        if kind == "S5" and p["phase"] == "fault_activation":
            if value in (0x0051, 0x0002):
                events.append((p["index"], value))
        elif p["phase"] == "post_fault_observation":
            if kind == "HK1":
                temps.append((p["index"], value))
            elif kind == "HK3":
                modes.append((p["index"], value))
    return {"events": events, "temps": temps, "modes": modes}


def csv_indices(items: list[tuple[int, int]]) -> str:
    return ", ".join(str(index) for index, _ in items) or "none"


def run(core: Path, artifacts: Path, output: Path) -> None:
    manifest = load(core / "integration_input_manifest.json")
    need(manifest.get("kind") == "orbitfabric.integration_input_set", "not a Core Input Set")
    need(manifest.get("load_result") == "loaded" and manifest.get("lint_result") == "passed",
         "Core Input Set was not cleanly loaded/linted")
    surfaces = {item["role"]: item for item in manifest["surfaces"]}
    for role in ("entity_index", "mission_snapshot", "relationship_manifest", "lint_report"):
        row = surfaces[role]
        need(row["status"] == "available", f"Core surface unavailable: {role}")
        path = core / row["path"]
        need(path.is_file() and digest(path) == row["sha256"],
             f"Core exported surface digest mismatch: {role}")

    index = load(core / surfaces["entity_index"]["path"])
    snapshot = load(core / surfaces["mission_snapshot"]["path"])
    actual = {(e["domain"], e["id"]) for e in index["entities"]}
    need(REQUIRED.issubset(actual), f"missing Core EntityRefs: {sorted(REQUIRED - actual)}")
    need(snapshot.get("result") == "loaded", "Core snapshot not loaded")
    need(index["mission"]["id"] == snapshot["mission"]["id"] ==
         manifest["mission"]["id"] == "safe_thermal_evidence_demo", "Core mission mismatch")

    model = snapshot["model"]
    temp = next(t for t in model["telemetry"] if t["id"] == "obc.temperature_raw")
    mode = next(t for t in model["telemetry"] if t["id"] == "obc.mode")
    fault = next(f for f in model["faults"] if f["id"] == "obc.thermal_high_fault")
    need(temp["type"] == "int16" and temp["unit"] == "raw_count" and
         temp["source"] == "obc" and temp["limits"]["critical_high"] == 1250,
         "temperature binding/type/unit/threshold mismatch")
    need(mode["type"] == "enum" and "SAFE" in mode["enum"], "mode entity mismatch")
    need(fault["condition"]["telemetry"] == "obc.temperature_raw" and
         fault["condition"]["operator"] == ">" and
         fault["condition"]["value"] == 1250 and
         fault["recovery"]["mode_transition"] == "SAFE", "thermal fault binding mismatch")
    need({"obc.thermal_hard_limit", "obc.safe_entry"}.issubset(
         {e["id"] for e in model["events"]}), "event binding mismatch")

    verdict_path = artifacts / "g1-offline-verdicts-v0_4.json"
    verdicts = load(verdict_path)
    sidecar = artifacts / "g1-offline-verdicts-v0_4.sha256"
    if sidecar.exists():
        need(sidecar.read_text().split()[0].lower() == digest(verdict_path),
             "v0.4 report checksum mismatch")
    policy = verdicts["policy"]
    need(policy["version"] == "experimental-v0.4" and policy["hard_limit_raw"] == 1250,
         "experimental v0.4 policy mismatch")
    need(policy["required_5s_hk_samples"] == 5, "unexpected coverage policy")
    cases = {}
    for case in "ABC":
        path = artifacts / f"g1-thermal-{case.lower()}.json"
        native = load(path)
        assessment = verdicts["cases"][case]
        need(assessment["admission"] == "ACCEPTED" and
             assessment["verdict"] == EXPECTED[case], f"not the admitted G1 {case} baseline")
        need(assessment["input_sha256"] == digest(path),
             f"G1 {case} file differs from evaluated file")
        need(assessment["packet_count"] == len(native["observations"]),
             f"G1 {case} packet count mismatch")
        extracted = from_packets(native)
        observed = assessment["observed"]
        need([v for _, v in extracted["temps"]] == observed["post_hk1_raw"],
             f"G1 {case} native HK1 differs from v0.4 assessment")
        need([v for _, v in extracted["modes"]] == observed["post_hk3_modes"],
             f"G1 {case} native HK3 differs from v0.4 assessment")
        need(sum(v == 0x0051 for _, v in extracted["events"]) ==
             observed["hard_limit_event_count"] and
             sum(v == 0x0002 for _, v in extracted["events"]) ==
             observed["safe_entry_event_count"], f"G1 {case} event count mismatch")
        cases[case] = {"record": native, "extracted": extracted, "assessment": assessment}

    a, c = cases["A"]["record"], cases["C"]["record"]
    omissions = c["derivation"]["omitted_original_indices"]
    need(c["source"]["sha256"] == digest(artifacts / "g1-thermal-a.json"),
         "C is not bound to the exact A artifact")
    need(c["observations"] == [p for p in a["observations"] if p["index"] not in set(omissions)],
         "C is not an exact omission-only A projection")
    omitted = [p for p in a["observations"] if p["index"] in set(omissions)]
    need(len(omitted) == 3 and all(p["phase"] == "post_fault_observation" and
         packet_kind(p)[0] == "HK1" for p in omitted), "C omission set is not 3 post-fault HK1")

    lines = [
        "# G1: Core Mission Contract -> Native Observation Trace",
        "",
        "**Status:** local read-only correlation; not spacecraft recovery authorization.",
        "",
        f"- Core mission: `{snapshot['mission']['id']}`; OrbitFabric `{manifest['orbitfabric_version']}`; Input Set SHA-256 `{manifest['input_set_sha256']}`",
        "- Source: original A/B/C parsed-TM family; v0.4 qualified assessment report; **not** P1C fresh A/B.",
        f"- Policy: 5 s window, {policy['required_5s_hk_samples']} HK samples, hard limit {policy['hard_limit_raw']} raw.",
        "",
        "## Explicit PoC-local bindings (not released adapter mappings)",
        "",
        "| Core entity | Native openSVF parsed-TM observation |",
        "|---|---|",
        "| `telemetry:obc.temperature_raw` | PUS TM(3,25), HK set 1, signed BE int16 from application bytes 1..2 |",
        "| `telemetry:obc.mode` + `modes:SAFE` | PUS TM(3,25), HK set 3, mode byte 1 = SAFE (native PoC mapping) |",
        "| `events:obc.thermal_hard_limit` | PUS TM(5,4), event 0x0051; float32 auxiliary validated by v0.4 |",
        "| `events:obc.safe_entry` | PUS TM(5,4), event 0x0002; corroborates HK3 |",
        "| `faults:obc.thermal_high_fault` | Declared threshold >1250 raw and intended SAFE response; **not** executed by Core |",
        "",
        "## Original experiments, existing v0.4 verdicts",
        "",
        "| Case | Post-fault HK1 raw (packet indices) | Post-fault HK3 mode (indices) | Fault phase S5 indices | v0.4 assessment |",
        "|---|---|---|---|---|",
    ]
    for case in "ABC":
        dat = cases[case]
        x = dat["extracted"]
        hk1_vals = ",".join(str(v) for _, v in x["temps"])
        hk3_vals = ",".join(str(v) for _, v in x["modes"])
        lines.append(f"| {case} | {hk1_vals} (`{csv_indices(x['temps'])}`) | "
                     f"{hk3_vals} (`{csv_indices(x['modes'])}`) | "
                     f"`{csv_indices(x['events'])}` | `{dat['assessment']['verdict']}` |")
    def state(case: str, predicate: str) -> str:
        return cases[case]["assessment"]["criteria"][predicate]["state"]

    lines.extend([
        "",
        f"**A -> C exact omission:** original A packet indices `{', '.join(map(str, omissions))}` (all post-fault HK1).",
        "C retains the same underlying A source, not a separately executed spacecraft run.",
        "",
        "## Proposed RC mapping: explicit coverage limits",
        "",
        "| Original RC | Evidence / v0.4 predicate | A | B | C |",
        "|---|---|---|---|---|",
        "| RC-01 SAFE state | HK3 + SAFE-entry corroboration; v0.4 `safe_entry` / `safe_mode_observation` | " +
            " | ".join(f"{state(c, 'safe_entry')} / {state(c, 'safe_mode_observation')}" for c in "ABC") + " |",
        "| RC-02 thermal clearance | post-fault HK1; v0.4 `thermal_clearance` | " +
            " | ".join(state(c, "thermal_clearance") for c in "ABC") + " |",
        "| RC-03 no recurrence | 5 s HK1 coverage contributes, but no independently agreed RC-03 predicate | PARTIAL | PARTIAL | INSUFFICIENT |",
        "| RC-04 relevant subsystem health | Other-subsystem health not observed in the present contract | NOT DEMONSTRATED | NOT DEMONSTRATED | NOT DEMONSTRATED |",
        "| RC-05 adequacy of evidence | v0.4 `capture_coverage` only; no raw-wire/producer-authentication claim | " +
            " | ".join(state(c, "capture_coverage") for c in "ABC") + " |",
        "",
        "**Boundary:** `ADMISSIBLE` is the frozen v0.4 *thermal-experiment* verdict, not completion of RC-01..05",
        "and never an instruction to transition SAFE -> NOMINAL. Threshold equality is conservative in v0.4:",
        "Core fault declares `>1250`, whereas clearance requires `<1250`.",
        "The Core-to-native table is manually curated and checked for presence/type/threshold, not an adapter projection.",
        "",
    ])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print("G1 CORE-NATIVE CORRELATION: PASS")
    print(f"Core mission: {snapshot['mission']['id']} | hard limit raw: {temp['limits']['critical_high']}")
    for case in "ABC":
        x = cases[case]
        print(f"{case}: {x['assessment']['verdict']} | HK1={len(x['extracted']['temps'])} | "
              f"HK3={len(x['extracted']['modes'])} | TM={len(x['record']['observations'])}")
    print(f"C omitted original A HK1 indices: {omissions}")
    print(f"Report: {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        run(args.core_dir, args.artifacts, args.output)
    except (ValueError, KeyError, OSError, TypeError, StopIteration) as error:
        parser.exit(2, f"G1 CORE-NATIVE CORRELATION: BLOCKED | {error}\n")


if __name__ == "__main__":
    main()
