#!/usr/bin/env python3
"""G1 C+: one continuous openSVF/openOBSW host-SIL run, two bounded assessments.

PoC-only. No spacecraft SAFE-exit command. No upstream or evaluator changes.
Source TM is producer-observed *parsed* TM; evidence omissions are deliberate
post-capture projections and MUST NOT be called downlink losses.

The first assessment runs before any re-observation. The second uses a NEW
five-second window on the SAME simulator, retaining the original fault-entry
context but never using the first window's HK to fill the second.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import struct
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def as_json(obj: Any) -> bytes:
    return (json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def load_json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    need(isinstance(result, dict), f"JSON object required: {path}")
    return result


def load_evaluator(evaluator_path: Path):
    need(evaluator_path.is_file(), f"missing frozen evaluator: {evaluator_path}")
    spec = importlib.util.spec_from_file_location("g1_eval_frozen_v0_4", evaluator_path)
    need(spec is not None and spec.loader is not None, "cannot import v0.4")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    need(mod.WINDOW_S == 5.0 and mod.MIN_SAMPLES == 5 and
         mod.LIMIT_RAW == 1250 and mod.SAFE_MODE == 1,
         "v0.4 experiment policy unexpectedly changed")
    return mod


ENTITY_REFS = {
    ("telemetry", "obc.temperature_raw"),
    ("telemetry", "obc.mode"),
    ("events", "obc.thermal_hard_limit"),
    ("events", "obc.safe_entry"),
    ("faults", "obc.thermal_high_fault"),
    ("modes", "SAFE"),
}


def admit_core(core_dir: Path, ev) -> dict:
    """Consume actual Core-exported surfaces; reject missing/changed semantics."""
    manifest = load_json(core_dir / "integration_input_manifest.json")
    need(manifest.get("kind") == "orbitfabric.integration_input_set" and
         manifest.get("load_result") == "loaded" and
         manifest.get("lint_result") == "passed", "Core input set not accepted")
    surfaces = {row["role"]: row for row in manifest["surfaces"]}
    for role in ("entity_index", "mission_snapshot", "lint_report", "relationship_manifest"):
        row = surfaces[role]
        need(row["status"] == "available", f"Core export missing {role}")
        path = core_dir / row["path"]
        need(path.is_file() and file_digest(path) == row["sha256"],
             f"Core surface digest mismatch: {role}")
    index = load_json(core_dir / surfaces["entity_index"]["path"])
    snap = load_json(core_dir / surfaces["mission_snapshot"]["path"])
    actual = {(e["domain"], e["id"]) for e in index["entities"]}
    need(ENTITY_REFS <= actual, f"Core EntityRefs absent: {sorted(ENTITY_REFS-actual)}")
    need(snap["result"] == "loaded" and snap["mission"]["id"] ==
         index["mission"]["id"] == manifest["mission"]["id"] ==
         "safe_thermal_evidence_demo", "Core mission identity mismatch")
    model = snap["model"]
    temp = next(t for t in model["telemetry"] if t["id"] == "obc.temperature_raw")
    mode = next(t for t in model["telemetry"] if t["id"] == "obc.mode")
    fault = next(f for f in model["faults"] if f["id"] == "obc.thermal_high_fault")
    need(temp["type"] == "int16" and temp["unit"] == "raw_count" and
         temp["limits"]["critical_high"] == ev.LIMIT_RAW and temp["source"] == "obc",
         "Core/assessor temperature type or threshold drift")
    need(mode["type"] == "enum" and "SAFE" in mode["enum"], "Core SAFE mismatch")
    condition = fault["condition"]
    need(condition["telemetry"] == "obc.temperature_raw" and
         condition["operator"] == ">" and condition["value"] == ev.LIMIT_RAW and
         fault["recovery"]["mode_transition"] == "SAFE", "Core fault semantic drift")
    need({"obc.thermal_hard_limit", "obc.safe_entry"} <=
         {e["id"] for e in model["events"]}, "Core fault/SAFE events absent")
    return {
        "mission": manifest["mission"],
        "core_version": manifest["orbitfabric_version"],
        "core_input_set_sha256": manifest["input_set_sha256"],
        "entity_binding": {
            "telemetry:obc.temperature_raw": "TM(3,25)/HK1 signed BE int16 offset 1",
            "telemetry:obc.mode": "TM(3,25)/HK3 mode byte 1; SAFE=1",
            "events:obc.thermal_hard_limit": "TM(5,4) event 0x0051; float32 BE aux",
            "events:obc.safe_entry": "TM(5,4) event 0x0002",
        },
    }


def packet_is_hk(packet: dict, set_id: int) -> bool:
    return ((packet["service"], packet["subservice"]) == (3, 25)
            and packet["app_data_hex"].startswith(f"{set_id:02x}"))


def event_id(packet: dict) -> int | None:
    if packet["service"] != 5:
        return None
    return int.from_bytes(bytes.fromhex(packet["app_data_hex"])[:2], "big")


def select_view(source: list[dict], selected_indices: set[int],
                suppressed_indices: set[int] | None = None) -> list[dict]:
    """Source-preserving selector. No value or time reconstruction permitted."""
    suppressed_indices = suppressed_indices or set()
    known = {p["index"] for p in source}
    need(selected_indices <= known, "selection refers to unknown source packets")
    need(suppressed_indices <= selected_indices, "omission not in selected packets")
    return [copy.deepcopy(p) for p in source
            if p["index"] in selected_indices - suppressed_indices]


def checked_view(ev, source: list[dict], chosen: list[dict],
                 selected_indices: set[int], omitted: set[int],
                 start: float, end: float) -> None:
    """Validate exact projection and per-window timestamp semantics before assess."""
    need(len(source) > 0 and [p["index"] for p in source] == list(range(len(source))),
         "full source capture is not contiguous")
    ev.check_observations(source)
    expected = select_view(source, selected_indices, omitted)
    need(chosen == expected, "view differs from its declared source projection")
    ev.check_timeline_and_obt(ev.check_observations(chosen), start, end)
    need(abs(end-start-ev.WINDOW_S) < 0.01, "invalid observation window")
    chosen_post = {p["index"] for p in chosen if p["phase"] == "post_fault_observation"}
    need(bool(chosen_post), "selected window empty")
    need(all(start-1e-6 <= p["sim_time_s"] <= end+1e-6
             for p in chosen if p["phase"] == "post_fault_observation"),
         "window contains observations from another time")


def assert_window_hk(observations: list[dict], indices: set[int],
                     expected_raw: int, expected_mode: int, expected_count: int) -> None:
    post = [p for p in observations if p["index"] in indices]
    temps = [struct.unpack_from(">h", bytes.fromhex(p["app_data_hex"]), 1)[0]
             for p in post if packet_is_hk(p, 1)]
    modes = [bytes.fromhex(p["app_data_hex"])[1]
             for p in post if packet_is_hk(p, 3)]
    need(len(temps) == len(modes) == expected_count, "unexpected HK1/HK3 cadence")
    need(set(temps) == {expected_raw} and set(modes) == {expected_mode},
         "native HK contradicts expected thermal/SAFE state")
    need(not any(event_id(p) in (0x0051, 0x0005) for p in post),
         "hard-limit recurrence or nominal transition observed")


def assess_view(ev, source: list[dict], chosen: list[dict],
                selected: set[int], omissions: set[int],
                start: float, end: float, link_health: dict) -> dict:
    checked_view(ev, source, chosen, selected, omissions, start, end)
    ev.check_link_counters(link_health, len(source))
    need(link_health.get("healthy") is True, "producer link not healthy")
    return ev.blind_assessment_subprocess(
        ev.admitted_envelope(chosen, start, end, link_health)
    )


def cplus_request(first_result: dict, core: dict, t: float, ev) -> dict:
    """A PoC-local next-observation request, NOT an autonomous spacecraft TC."""
    criteria = first_result["criteria"]
    need(first_result["verdict"] == "INDETERMINATE" and
         criteria["thermal_clearance"]["state"] == "UNKNOWN" and
         criteria["safe_entry"]["state"] == "SATISFIED" and
         criteria["safe_mode_observation"]["state"] == "SATISFIED" and
         criteria["capture_coverage"]["state"] == "UNKNOWN",
         "first assessment does not justify this narrowly scoped request")
    return {
        "kind": "g1.story_local_observation_request",
        "reason": "insufficient first-window HK1 coverage (not a producer TM-drop claim)",
        "source_verdict": "INDETERMINATE",
        "source_assessment_sha256": digest_bytes(as_json(first_result)),
        "source_core_input_set_sha256": core["core_input_set_sha256"],
        "requested_at_sim_time_s": t,
        "core_entity": "telemetry:obc.temperature_raw",
        "native_observation": "TM(3,25) HK1; verify HK3 SAFE in same new window",
        "policy_owner": "PoC experimental-v0.4; not OrbitFabric Core",
        "fresh_window_s": ev.WINDOW_S,
        "required_hk1": ev.MIN_SAMPLES,
        "required_hk3": ev.MIN_SAMPLES,
        "window_rule": "new independent window; no backfill of earlier absent TM",
        "action_scope": "continue host-SIL observation only; no spacecraft telecommand",
    }


def rev(path: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), "rev-parse", "HEAD"], text=True
    ).strip()


def check_pinned_sil(gf: Path, ev) -> dict:
    svf = gf / "upstream/opensvf"
    obsw = gf / "upstream/openobsw"
    sim = svf / "bin/obsw_sim"
    a, b = rev(svf), rev(obsw)
    need(a == ev.SVF_PIN and b == ev.OBSW_PIN,
         f"unqualified upstream pins: openSVF={a} openOBSW={b}")
    need(file_digest(sim) == ev.SIMULATOR_SHA256,
         "openOBSW simulator binary differs from validated baseline")
    return {"opensvf": a, "openobsw": b, "simulator_sha256": file_digest(sim)}


def run_live(gf: Path, core_dir: Path, evaluator_path: Path, out_dir: Path) -> None:
    """Drive live SIL and assess during one simulator lifecycle."""
    ev = load_evaluator(evaluator_path)
    core = admit_core(core_dir, ev)
    pins = check_pinned_sil(gf, ev)
    need(not out_dir.exists() or not any(out_dir.iterdir()),
         "output directory must be new or empty (avoid overwriting evidence)")

    sys.path.insert(0, str(gf / "upstream/opensvf/tests/system"))
    from test_obsw_alignment import (
        ThermalHarness, _nominal_at_obt, _s1_failures, _events,
        _set1_temperatures, _set3_modes, OBC_TEMPERATURE_PARAM,
        HARD_LIMIT_RAW, FAULT_RAW, TEMPERATURE_SOFT_LIMIT,
        TEMPERATURE_HARD_LIMIT, SAFE_MODE_ENTRY, NOMINAL_ENTRY, SEVERITY_HIGH,
    )
    from svf.models.dhs.obc import MODE_NOMINAL, MODE_SAFE
    from svf.models.dhs.obc_thermal import NOMINAL_RAW
    from svf.pus.services.s12_monitoring import PusService12

    need(HARD_LIMIT_RAW == ev.LIMIT_RAW and int(NOMINAL_RAW) < ev.LIMIT_RAW and
         FAULT_RAW > ev.LIMIT_RAW and MODE_SAFE == ev.SAFE_MODE,
         "openSVF thermal baseline differs from Core/evaluator semantics")

    run_id = "g1-cplus-" + uuid.uuid4().hex[:12]
    started_at = datetime.now(timezone.utc).isoformat()
    h = ThermalHarness()
    observations: list[dict] = []
    phase = {"name": "initialization"}
    interventions: list[dict] = []
    started = False
    try:
        def capture(packet, sim_time):
            observations.append({
                "index": len(observations), "phase": phase["name"],
                "sim_time_s": sim_time, "obt_seconds": packet.timestamp,
                "apid": packet.apid, "sequence_count": packet.sequence_count,
                "service": packet.service, "subservice": packet.subservice,
                "app_data_hex": packet.app_data.hex(),
            })

        h.adapter.add_tm_listener(capture)
        h.adapter.initialise()
        started = True
        process = getattr(h.adapter, "_proc", None)
        need(process is not None, "host simulator process not accessible")
        pid = getattr(process, "pid", None)
        need(isinstance(pid, int) and pid > 0, "host simulator PID unavailable")

        phase["name"] = "nominal_setup"
        _nominal_at_obt(h, 100)
        phase["name"] = "monitor_configuration"
        interventions.append({"action": "configure_s12_high_limit", "sim_time_s": h.t,
                              "threshold_raw": HARD_LIMIT_RAW})
        h.tc(12, 3, PusService12.build_add(
            OBC_TEMPERATURE_PARAM, None, HARD_LIMIT_RAW,
            TEMPERATURE_SOFT_LIMIT, TEMPERATURE_HARD_LIMIT,
            SEVERITY_HIGH, tc_apid=0x010,
        ).app_data)
        h.run(20)
        baseline = h.take()
        need(not _s1_failures(baseline) and
             not _events(baseline, TEMPERATURE_HARD_LIMIT) and
             set(_set1_temperatures(baseline)) == {int(NOMINAL_RAW)} and
             set(_set3_modes(baseline)) == {MODE_NOMINAL},
             "baseline nominal monitoring did not match")

        phase["name"] = "fault_activation"
        interventions.append({"action": "inject_stuck_thermal_fault", "sim_time_s": h.t,
                              "raw": FAULT_RAW})
        h.stick(FAULT_RAW)
        h.run(15)
        fault = h.take()
        events = _events(fault, TEMPERATURE_HARD_LIMIT)
        need(len(events) == 1 and struct.unpack_from(">f", events[0], 2)[0] == FAULT_RAW
             and len(_events(fault, SAFE_MODE_ENTRY)) == 1
             and _set3_modes(fault)[-1] == MODE_SAFE
             and _set1_temperatures(fault)[-1] == int(FAULT_RAW),
             "hard-limit fault entry did not match")

        phase["name"] = "post_fault_observation"
        interventions.append({"action": "clear_thermal_fault", "sim_time_s": h.t})
        h.faults.clear()
        pre_count = len(observations)
        start1 = h.t
        h.run(50)
        post1 = h.take()
        end1 = h.t
        full1 = copy.deepcopy(observations)
        w1 = set(range(pre_count, len(full1)))
        assert_window_hk(full1, w1, int(NOMINAL_RAW), MODE_SAFE, ev.MIN_SAMPLES)
        need(_set3_modes(post1) and set(_set3_modes(post1)) == {MODE_SAFE} and
             not _events(post1, NOMINAL_ENTRY) and
             not _events(post1, TEMPERATURE_HARD_LIMIT), "first window not stable in SAFE")
        link1 = h.adapter.link_health().to_dict()
        need(h.adapter._proc is process and process.poll() is None, "simulator restarted/stopped")

        hk1_indices = [p["index"] for p in full1
                       if p["index"] in w1 and packet_is_hk(p, 1)]
        need(len(hk1_indices) == ev.MIN_SAMPLES, "first window HK1 unexpected")
        omitted = set(hk1_indices[2:])
        need(len(omitted) == 3, "first-window projection should omit precisely three HK1")
        select1 = set(range(len(full1)))
        retained1 = select_view(full1, select1, omitted)
        first = assess_view(ev, full1, retained1, select1, omitted,
                            start1, end1, link1)
        need(first["verdict"] == "INDETERMINATE" and
             first["observed"]["post_hk1_raw"] == [int(NOMINAL_RAW)]*2 and
             len(first["observed"]["post_hk3_modes"]) == ev.MIN_SAMPLES,
             "first assessment not the specified incomplete observation case")
        request = cplus_request(first, core, h.t, ev)

        # First assessment and request have already occurred. Continue the SAME
        # process, fault remains cleared, OBC remains in SAFE.
        need(abs(h.t - end1) < 1e-6, "simulation advanced during assessment")
        need(h.adapter._proc is process and process.poll() is None, "simulator continuity lost")
        start2 = h.t
        h.run(50)
        post2 = h.take()
        end2 = h.t
        full2 = copy.deepcopy(observations)
        w2 = set(range(len(full1), len(full2)))
        need(full2[:len(full1)] == full1, "source prefix altered after reacquisition")
        need(abs(start2 - end1) < 1e-6 and abs(end2-start2-ev.WINDOW_S) < 0.01,
             "re-observation is not the next complete five-second window")
        need(h.adapter._proc is process and process.poll() is None,
             "second window was not the same live simulator process")
        assert_window_hk(full2, w2, int(NOMINAL_RAW), MODE_SAFE, ev.MIN_SAMPLES)
        need(not _events(post2, TEMPERATURE_HARD_LIMIT) and
             not _events(post2, NOMINAL_ENTRY) and h.adapter._mode == MODE_SAFE,
             "second window includes recurrence/SAFE exit")
        link2 = h.adapter.link_health().to_dict()

        # Explicitly omit the original first-window interval from this *new*
        # assessment view; preserve its entire packet history in the full source.
        pre = {p["index"] for p in full2 if p["index"] < pre_count}
        select2 = pre | w2
        view2 = select_view(full2, select2)
        second = assess_view(ev, full2, view2, select2, set(),
                             start2, end2, link2)
        need(second["verdict"] == "ADMISSIBLE" and
             len(second["observed"]["post_hk1_raw"]) == ev.MIN_SAMPLES and
             len(second["observed"]["post_hk3_modes"]) == ev.MIN_SAMPLES,
             "fresh window did not establish bounded thermal clearance")

        need(not any(event_id(p) in (0x0051, 0x0005)
                     for p in full2 if p["index"] in w1 | w2),
             "observed contradictory event across monitored interval")
        need(link1["healthy"] and link2["healthy"], "link reported unhealthy")
        need(h.adapter._proc is process and process.poll() is None,
             "simulator was not continuously alive at final assessment")
    finally:
        if started:
            h.adapter.teardown()

    source = {
        "experiment": "G1_CPLUS_CONTINUOUS_SIL", "capture_kind": "PARSED_TM",
        "run_id": run_id, "started_at_utc": started_at,
        "source_revisions": {"openobsw": pins["openobsw"], "opensvf": pins["opensvf"]},
        "simulator_sha256": pins["simulator_sha256"],
        "simulator_pid_during_run": pid, "simulator_lifecycle": "one initialize, two windows, one teardown",
        "interventions": interventions, "observations": full2,
        "link_health_at_first_assessment": link1,
        "link_health_at_second_assessment": link2,
        "windows": {
            "first": {"start_sim_time_s": start1, "end_sim_time_s": end1,
                      "original_packet_indices": sorted(w1)},
            "second": {"start_sim_time_s": start2, "end_sim_time_s": end2,
                       "original_packet_indices": sorted(w2)},
        },
    }
    source_digest = digest_bytes(as_json(source))
    view_one = {
        "kind": "g1.story_local_assessment_projection",
        "run_id": run_id, "source_sha256": source_digest,
        "window": {"start_sim_time_s": start1, "end_sim_time_s": end1},
        "omitted_source_indices": sorted(omitted),
        "method": "deliberate_post_capture_HK1_omission_only",
        "observations": retained1,
    }
    view_two = {
        "kind": "g1.story_local_assessment_projection",
        "run_id": run_id, "source_sha256": source_digest,
        "window": {"start_sim_time_s": start2, "end_sim_time_s": end2},
        "omitted_source_indices": sorted(w1),
        "method": "fresh_window_selection_excludes_earlier_window_entirely",
        "observations": view2,
    }
    assessments = {
        "experiment": "G1_CPLUS_CONTINUOUS_SIL",
        "status": "LOCAL_EXECUTED_CANDIDATE",
        "run_id": run_id, "core": core, "evaluator": "experimental-v0.4 (frozen)",
        "first": first, "observation_request": request, "second": second,
        "first_verdict_unchanged": True,
        "bounded_conclusion": "Only thermal five-second assessment; RC-03 partial, RC-04 not demonstrated",
        "not_claimed": ["full spacecraft readiness", "SAFE->NOMINAL authorization",
                        "historical telemetry reconstruction", "authenticated producer custody",
                        "upstream adapter projection", "physical telemetry drop"],
    }
    docs = [
        "# G1 C+ — one process, two observation windows", "",
        "**Status:** local host-SIL candidate; independent review pending.",
        f"Run: `{run_id}`; Simulator PID during run: `{pid}` (one process).",
        f"Core Input Set SHA-256: `{core['core_input_set_sha256']}`.",
        f"openSVF `{pins['opensvf']}`; openOBSW `{pins['openobsw']}`.", "",
        "| | First retained window | Second fresh window |", "|---|---|---|",
        f"| Simulated interval (s) | {start1:.1f}–{end1:.1f} | {start2:.1f}–{end2:.1f} |",
        f"| HK1 | {len(first['observed']['post_hk1_raw'])} of 5 | {len(second['observed']['post_hk1_raw'])} of 5 |",
        f"| HK3 SAFE | {len(first['observed']['post_hk3_modes'])} of 5 | {len(second['observed']['post_hk3_modes'])} of 5 |",
        f"| Frozen v0.4 verdict | `{first['verdict']}` | `{second['verdict']}` |", "",
        "First assessment was completed before fresh acquisition; the observation request",
        "was produced from its admitted UNKNOWN coverage criteria. Original omitted",
        f"HK1 packet indices: `{sorted(omitted)}`; these were not reconstructed.",
        "The second view retains initial fault-entry TM but uses **only new** post-fault",
        "HK from the second window. The full source capture retains both intervals.", "",
        "The second verdict applies only to the **later interval**. It does not",
        "revise the first verdict or prove unobserved recurrence absence.",
        "RC-03 remains partial and RC-04 not demonstrated. No SAFE exit command.", "",
        "Evidence manifests are unsigned SHA-256 checksums, **not** authenticated custody.",
    ]
    payloads = {
        "g1-cplus-full-capture.json": as_json(source),
        "g1-cplus-first-retained.json": as_json(view_one),
        "g1-cplus-second-fresh.json": as_json(view_two),
        "g1-cplus-assessments.json": as_json(assessments),
        "G1_CPLUS_REPORT.md": ("\n".join(docs) + "\n").encode("utf-8"),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, contents in payloads.items():
        (out_dir / filename).write_bytes(contents)
    checksums = [f"{digest_bytes(contents)}  {filename}" for filename, contents in sorted(payloads.items())]
    (out_dir / "g1-cplus.sha256").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print("G1 C+ CONTINUOUS HOST-SIL: PASS")
    print(f"One simulator process PID {pid}; windows {start1:.1f}-{end1:.1f} and {start2:.1f}-{end2:.1f}s")
    print(f"First: {first['verdict']} | HK1={len(first['observed']['post_hk1_raw'])} | HK3={len(first['observed']['post_hk3_modes'])}")
    print(f"Second: {second['verdict']} | HK1={len(second['observed']['post_hk1_raw'])} | HK3={len(second['observed']['post_hk3_modes'])}")
    print(f"Evidence: {out_dir}")


def cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gf", type=Path, required=True, help="existing G1 greenfield workspace")
    parser.add_argument("--core-dir", type=Path, required=True, help="real Core integration input set")
    parser.add_argument("--evaluator", type=Path, default=Path(__file__).with_name("g1_offline_evaluator_v0_4.py"))
    parser.add_argument("--out", type=Path, required=True, help="new, empty output directory")
    args = parser.parse_args()
    try:
        run_live(args.gf.resolve(), args.core_dir.resolve(), args.evaluator.resolve(), args.out.resolve())
    except (ValueError, AssertionError, RuntimeError, FileNotFoundError,
            OSError, subprocess.CalledProcessError) as exc:
        print(f"G1 C+ NOT QUALIFIED: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc


if __name__ == "__main__":
    cli()
