#!/usr/bin/env python3
"""G1 offline evidence evaluator, experimental policy v0.4 (G1-SEM-01).

Standard library only; no imports from openSVF or openOBSW. Admission validates
source and faithful derived projections. Each admitted case is assessed by a
separate subprocess that receives ONLY that case's normalized observations,
window and link-health values over stdin. No scenario label, omitted source A
packets or intervention history reaches the assessor.

This is a logical/process boundary, NOT a hardened sandbox, producer signature,
or qualified flight-recovery authorization. Unsigned hashes do not authenticate
a malicious producer able to rewrite both evidence and manifest.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import re
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

OBSW_PIN = "a4c56715cbf57e34d7812b71a4d5f32cf9285b18"
SVF_PIN = "9bf3f3a29696f695a6406080ad4436cb4a5154fc"
# Pinned host-SIL executable: equality to this independently recorded audit digest
# is a bounded identity check, NOT a producer signature or authenticated custody.
SIMULATOR_SHA256 = "4672bdc9473d6097b6a7dfba4085992b4013b6e99b84f4f1e97c628ef662ba7b"
LIMIT_RAW = 1250  # The specific hard-limit set by the G1 test scenario.
WINDOW_S = 5.0
MIN_SAMPLES = 5  # Five nominal 1 Hz HK reports expected over this G1 window.
MAX_GAP_S = 1.2  # Tolerance for 1 Hz sample phase, not a general SRDB contract.
SAFE_MODE = 1
RESULTS = {"SATISFIED", "VIOLATED", "UNKNOWN"}


class InputRejected(ValueError):
    """Admission failed; NOT a fourth recovery verdict."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise InputRejected(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_manifest(path: Path) -> dict[str, str]:
    require(path.is_file(), f"missing checksum manifest: {path.name}")
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})  ([a-zA-Z0-9_.-]+\.json)", line)
        require(match is not None, f"malformed manifest line: {line!r}")
        digest, name = match.group(1).lower(), match.group(2)
        require(name not in entries, f"duplicate manifest entry: {name}")
        entries[name] = digest
    require(bool(entries), "empty checksum manifest")
    return entries


def load_and_verify(path: Path, manifest: dict[str, str]) -> tuple[dict[str, Any], str]:
    require(path.name in manifest, f"missing digest for {path.name}")
    require(path.is_file(), f"missing input: {path.name}")
    contents = path.read_bytes()
    digest = sha256(contents)
    require(digest == manifest[path.name], f"checksum mismatch: {path.name}")
    try:
        record = json.loads(contents)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InputRejected(f"invalid JSON: {exc}") from exc
    require(isinstance(record, dict), "JSON root must be an object")
    return record, digest


def is_integer(value: Any) -> bool:
    return type(value) is int


def is_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def is_digest(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def check_link_counters(health: Any, parsed_count: int) -> None:
    """Qualify producer summary consistency; does not authenticate that summary.

    C supplies counts from its original A capture, not its redacted observation set.
    """
    require(isinstance(health, dict), "missing link health")
    for field in ("tm_received", "tm_parsed", "tm_dropped", "desyncs", "hk_undecoded"):
        x = health.get(field)
        require(is_integer(x) and x >= 0, f"invalid link counter: {field}")
    require(health["tm_parsed"] == parsed_count, "tm_parsed != original parsed-TM capture count")
    require(health["tm_received"] >= health["tm_parsed"], "tm_received < tm_parsed")
    # Pinned openSVF _parse_tm increments tm_received once per packet and then
    # exactly one of tm_parsed or tm_dropped (verified at source revision pin).
    require(health["tm_received"] == health["tm_parsed"] + health["tm_dropped"],
            "tm_received != tm_parsed + tm_dropped")
    # Counters don't prove lossless wire capture or independently attest producer truth.


def check_timeline_and_obt(obs: list[dict[str, Any]], start: float, end: float) -> None:
    """G1-specific phase ordering and bounded OBT/HK3 correlation.

    The original run intentionally sets onboard time from 0 to 100 near startup;
    do NOT impose a global sim-time ↔ OBT mapping across that commanded step.
    """
    phases = {"initialization": 0, "nominal_setup": 1,
              "monitor_configuration": 2, "fault_activation": 3,
              "post_fault_observation": 4}
    rank = -1
    post: list[dict[str, Any]] = []
    hk3_anchors: list[tuple[float, int]] = []
    for p in obs:
        phase = p["phase"]
        require(phases[phase] >= rank, f"backwards phase annotation at packet {p['index']}")
        rank = phases[phase]
        t = p["sim_time_s"]
        if phase == "post_fault_observation":
            require(start - 1e-6 <= t <= end + 1e-6,
                    f"post-fault packet {p['index']} outside window")
            post.append(p)
        else:
            require(t < start - 1e-6,
                    f"pre-window phase annotation after start: packet {p['index']}")
        if (p["service"], p["subservice"]) == (3, 25):
            payload = bytes.fromhex(p["app_data_hex"])
            if payload[0] == 3:
                onboard_hk3_obt = int.from_bytes(payload[2:6], "big")
                require(onboard_hk3_obt == p["obt_seconds"],
                        f"HK3 payload OBT differs from TM header OBT: packet {p['index']}")
                if phase == "post_fault_observation":
                    hk3_anchors.append((float(t), onboard_hk3_obt))
    # If HK3 anchors are absent, coverage remains UNKNOWN in assessment. If they
    # exist, near-in-time post-fault TM must not contradict onboard clock.
    for p in post:
        if not hk3_anchors:
            break
        t = float(p["sim_time_s"])
        anchor_t, anchor_obt = min(hk3_anchors, key=lambda item: abs(t - item[0]))
        if abs(t - anchor_t) <= 0.6 + 1e-7:
            # One-second tolerance covers integer-second packet timestamps and
            # the 0.5 s offset between successive sets in this pinned simulator.
            require(abs((p["obt_seconds"] - anchor_obt) - (t - anchor_t)) <= 1.01,
                    f"post-fault TM OBT inconsistent with nearby HK3: packet {p['index']}")


def check_observations(obs: Any) -> list[dict[str, Any]]:
    require(isinstance(obs, list) and bool(obs), "observations must be nonempty")
    indices: list[int] = []
    times: list[float] = []
    allowed = {"initialization", "nominal_setup", "monitor_configuration",
               "fault_activation", "post_fault_observation"}
    for i, packet in enumerate(obs):
        require(isinstance(packet, dict), f"packet {i} not an object")
        idx, t = packet.get("index"), packet.get("sim_time_s")
        require(is_integer(idx) and idx >= 0, f"packet {i} invalid index")
        require(is_number(t) and t >= 0, f"packet {i} invalid sim time")
        require(packet.get("phase") in allowed, f"packet {i} invalid phase")
        for name, maximum in (("service", 255), ("subservice", 255),
                              ("apid", 0x7FF), ("sequence_count", 0x3FFF),
                              ("obt_seconds", 0xFFFFFFFF)):
            require(is_integer(packet.get(name)) and 0 <= packet[name] <= maximum,
                    f"packet {i} invalid {name} (out of protocol range)")
        encoded = packet.get("app_data_hex")
        require(isinstance(encoded, str) and len(encoded) % 2 == 0,
                f"packet {i} invalid payload encoding")
        try:
            data = bytes.fromhex(encoded)
        except ValueError as exc:
            raise InputRejected(f"packet {i} invalid hex payload") from exc
        svc, sub = packet["service"], packet["subservice"]
        if (svc, sub) == (3, 25):
            require(len(data) >= 1, f"packet {i} truncated HK header")
            if data[0] == 1:
                require(len(data) >= 3, f"packet {i} truncated HK1 temperature")
            elif data[0] == 3:
                require(len(data) >= 6, f"packet {i} truncated HK3 mode/OBT")
        if svc == 5:
            require(len(data) >= 2, f"packet {i} truncated S5 event")
            event = int.from_bytes(data[:2], "big")
            if event == 0x0051:
                require(sub == 4 and len(data) == 6,
                        f"packet {i} hard-limit S5 severity/aux encoding mismatch")
                observed_raw = struct.unpack(">f", data[2:6])[0]
                require(math.isfinite(observed_raw) and observed_raw >= LIMIT_RAW,
                        f"packet {i} hard-limit S5 auxiliary contradicts threshold")
        indices.append(idx)
        times.append(float(t))
    require(indices == sorted(set(indices)), "capture indices not strictly increasing")
    require(times == sorted(times), "sim times not monotonic")
    return obs


def check_record(name: str, record: dict[str, Any], a_digest: str) -> tuple[list[dict[str, Any]], float, float]:
    """Validate schema, declared omissions and provenance; do not decide from metadata."""
    is_c = name == "C"
    expect_kind = "DECLARED_DERIVED_PARSED_TM" if is_c else "PARSED_TM"
    require(record.get("scenario") == name, f"scenario mismatch: expected {name}")
    require(record.get("capture_kind") == expect_kind, "unexpected capture kind")
    obs = check_observations(record.get("observations"))
    indices = [p["index"] for p in obs]

    if is_c:
        require(record.get("experiment") == "G1_THERMAL_C_COVERAGE_PROJECTION",
                "unexpected experiment identifier")
        source = record.get("source")
        require(isinstance(source, dict), "missing source provenance")
        require(source.get("artifact") == "g1-thermal-a.json", "wrong source artifact")
        require(source.get("sha256") == a_digest, "C source digest disagrees with A manifest")
        require(source.get("openobsw") == OBSW_PIN and source.get("opensvf") == SVF_PIN,
                "C source revision mismatch")
        require(source.get("simulator_sha256") == SIMULATOR_SHA256,
                "source simulator digest differs from pinned executable")
        deriv = record.get("derivation")
        require(isinstance(deriv, dict), "missing derivation declaration")
        require(deriv.get("method") in {"intentional_hk1_coverage_reduction",
                                         "declared_post_fault_hk1_projection"},
                "unexpected derivation method")
        require(deriv.get("scope") == "post_fault_observation", "unexpected derivation scope")
        total, count = deriv.get("original_packet_count"), deriv.get("exported_packet_count")
        omissions = deriv.get("omitted_original_indices")
        require(is_integer(total) and total > 0, "invalid original packet count")
        require(count == len(obs), "exported count disagrees with data")
        require(isinstance(omissions, list) and all(is_integer(i) and 0 <= i < total for i in omissions),
                "invalid declared omissions")
        require(omissions == sorted(set(omissions)), "duplicate/unsorted declared omissions")
        if not omissions:
            require(deriv.get("method") == "declared_post_fault_hk1_projection",
                    "identity projection must be explicitly declared")
        require(len(obs) + len(omissions) == total, "wrong omission count")
        require(set(indices) == set(range(total)) - set(omissions),
                "observations do not match declared omitted indices")
        require(len(deriv.get("omitted_sim_times_s", [])) == len(omissions),
                "omission-time declaration inconsistent")
        require(deriv.get("expected_post_fault_hk1") == 5,
                "unknown expected HK1 cadence contract")
        actual_post_hk1 = sum(1 for p in obs if p["phase"] == "post_fault_observation"
                              and p["service"] == 3 and p["subservice"] == 25
                              and p["app_data_hex"].startswith("01"))
        require(deriv.get("exported_post_fault_hk1") == actual_post_hk1,
                "exported HK1 count inconsistent")
        health = record.get("source_link_health")
        check_link_counters(health, total)
        window = record.get("observation_window")
    else:
        require(record.get("experiment") == "G1_THERMAL_AB_CAPTURE",
                "unexpected experiment identifier")
        pins = record.get("source_revisions")
        require(isinstance(pins, dict) and pins.get("openobsw") == OBSW_PIN
                and pins.get("opensvf") == SVF_PIN, "G1 source revision mismatch")
        require(record.get("simulator_sha256") == SIMULATOR_SHA256,
                "simulator digest differs from pinned executable")
        require(indices == list(range(len(obs))), "undeclared gap in direct capture")
        health = record.get("link_health")
        check_link_counters(health, len(obs))
        window = record.get("post_fault_window")

    require(isinstance(window, dict), "missing post-fault window")
    start, end = window.get("start_sim_time_s"), window.get("end_sim_time_s")
    require(is_number(start) and is_number(end) and end > start,
            "invalid post-fault window")
    require(abs(float(end) - float(start) - WINDOW_S) <= 0.01,
            "post-fault observation window is not the configured 5 seconds")
    check_timeline_and_obt(obs, float(start), float(end))
    return obs, float(start), float(end)



def check_projection_fidelity(c: dict[str, Any], a: dict[str, Any],
                              verified_a_digest: str) -> None:
    """G1-specific input admission: C must be A minus its declared HK1 samples.

    Source A must already have passed manifest and structural validation.
    This checks exact data equality, not merely matching counts or indices.
    No omitted A telemetry is used by the downstream recovery assessment.
    """
    require(c["source"]["sha256"] == verified_a_digest,
            "C does not reference the verified A input")
    original = a["observations"]
    exported = c["observations"]
    deriv = c["derivation"]
    omissions = deriv["omitted_original_indices"]
    omitted_set = set(omissions)

    require(deriv["original_packet_count"] == len(original),
            "C original packet count differs from verified A")
    require([p["index"] for p in original] == list(range(len(original))),
            "A source capture indices are not continuous")
    omitted_packets = [p for p in original if p["index"] in omitted_set]
    require(len(omitted_packets) == len(omissions),
            "C omits unknown A packet indices")

    def post_hk1(p: dict[str, Any]) -> bool:
        return (p["phase"] == "post_fault_observation"
                and (p["service"], p["subservice"]) == (3, 25)
                and bytes.fromhex(p["app_data_hex"])[:1] == b"\x01")

    source_hk1 = [p for p in original if post_hk1(p)]
    require(len(source_hk1) == MIN_SAMPLES,
            "C projection source A has unexpected post-fault HK1 count")
    eligible = {p["index"] for p in source_hk1}
    require(omitted_set.issubset(eligible),
            "C omissions include packets outside post-fault HK1")
    # Different declared subsets are allowed. The v0.3 policy does not equate
    # "derived" with "insufficient" or require an original, label-specific set.
    require(deriv.get("expected_post_fault_hk1") == len(source_hk1),
            "C expected post-fault HK1 differs from source A")
    require(deriv["omitted_sim_times_s"] ==
            [p["sim_time_s"] for p in omitted_packets],
            "C omission times differ from original packets")
    require(exported == [p for p in original if p["index"] not in omitted_set],
            "C contains altered, missing or additional surviving packets")
    require(c["source"]["openobsw"] == a["source_revisions"]["openobsw"]
            and c["source"]["opensvf"] == a["source_revisions"]["opensvf"]
            and c["source"]["simulator_sha256"] == a["simulator_sha256"],
            "C producer provenance differs from A")
    require(c["source_link_health"] == a["link_health"],
            "C source link-health metadata differs from A")
    require(c.get("interventions") == a.get("interventions"),
            "C intervention provenance differs from A")
    a_win = a["post_fault_window"]
    c_win = c["observation_window"]
    require(c_win["start_sim_time_s"] == a_win["start_sim_time_s"]
            and c_win["end_sim_time_s"] == a_win["end_sim_time_s"],
            "C observation window differs from A")

def event_ids(obs: list[dict[str, Any]], phase: str | None = None) -> list[int]:
    return [int.from_bytes(bytes.fromhex(p["app_data_hex"])[:2], "big")
            for p in obs if p["service"] == 5 and (phase is None or p["phase"] == phase)]


def samples(obs: list[dict[str, Any]], phase: str, set_id: int) -> list[tuple[float, int]]:
    out = []
    for p in obs:
        if p["phase"] != phase or (p["service"], p["subservice"]) != (3, 25):
            continue
        payload = bytes.fromhex(p["app_data_hex"])
        if not payload or payload[0] != set_id:
            continue
        v = struct.unpack_from(">h", payload, 1)[0] if set_id == 1 else payload[1]
        out.append((float(p["sim_time_s"]), int(v)))
    return out


def coverage_complete(sample_list: list[tuple[float, int]], start: float, end: float) -> bool:
    if len(sample_list) < MIN_SAMPLES:
        return False
    timeline = [start] + [t for t, _ in sample_list] + [end]
    return all(0 <= timeline[i+1] - timeline[i] <= MAX_GAP_S + 1e-7
               for i in range(len(timeline)-1))


def criterion(state: str, reason: str) -> dict[str, str]:
    assert state in RESULTS
    return {"state": state, "reason": reason}


def assess(obs: list[dict[str, Any]], start: float, end: float,
           health: dict[str, Any]) -> dict[str, Any]:
    """Blind decision: evidence only. No scenario/derived flag, source A or TC inputs.

    The admission gate confirms a direct contiguous capture OR a projection that
    deletes only eligible post-fault HK1 samples. Consequently, the S5 stream
    is preserved in the admitted projection. Its absence is still inconclusive
    if producer link-health counters report any discontinuity.
    """
    fault_events = event_ids(obs, "fault_activation")
    fault_modes = samples(obs, "fault_activation", 3)
    post_events = event_ids(obs, "post_fault_observation")
    temps = samples(obs, "post_fault_observation", 1)
    modes = samples(obs, "post_fault_observation", 3)
    healthy = (health.get("tm_dropped") == 0 and health.get("desyncs") == 0
               and health.get("hk_undecoded") == 0
               and health.get("obsw_exit_status") is None)

    fault_proven = (fault_events.count(0x0051) == 1
                    and fault_events.count(0x0002) == 1
                    and bool(fault_modes) and fault_modes[-1][1] == SAFE_MODE)
    c_fault = criterion("SATISFIED" if fault_proven else "UNKNOWN",
                        "S5 hard-limit, S5 SAFE-entry and fault-phase HK3" if fault_proven
                        else "SAFE fault-entry evidence not sufficient")

    temp_coverage = coverage_complete(temps, start, end)
    if any(raw >= LIMIT_RAW for _, raw in temps):
        c_temp = criterion("VIOLATED", "post-fault HK1 at/above hard limit")
    elif healthy and temp_coverage and all(raw < LIMIT_RAW for _, raw in temps):
        c_temp = criterion("SATISFIED", "HK1 below limit with 5 s sampled coverage")
    else:
        c_temp = criterion("UNKNOWN", "no persistent high sample, but clearance coverage or link continuity insufficient")

    mode_coverage = coverage_complete(modes, start, end)
    if any(mode != SAFE_MODE for _, mode in modes) or 0x0005 in post_events:
        c_mode = criterion("VIOLATED", "post-fault TM contradicts SAFE mode")
    elif healthy and mode_coverage and all(mode == SAFE_MODE for _, mode in modes):
        c_mode = criterion("SATISFIED", "HK3 SAFE sampled throughout window; S5 stream admitted intact")
    else:
        c_mode = criterion("UNKNOWN", "SAFE-mode observation coverage or link continuity insufficient")

    # Completeness means required evidence coverage, not all source TM preserved.
    required_coverage = healthy and temp_coverage and mode_coverage
    c_coverage = criterion("SATISFIED" if required_coverage else "UNKNOWN",
                           "required HK1/HK3 windows covered and link reports no faults"
                           if required_coverage else "required samples or link continuity missing")
    criteria = {"safe_entry": c_fault, "thermal_clearance": c_temp,
                "safe_mode_observation": c_mode, "capture_coverage": c_coverage}
    values = [c["state"] for c in criteria.values()]
    if "VIOLATED" in values:
        verdict = "NOT_ADMISSIBLE"
    elif all(v == "SATISFIED" for v in values):
        verdict = "ADMISSIBLE"
    else:
        verdict = "INDETERMINATE"
    return {"verdict": verdict, "criteria": criteria,
            "observed": {"post_hk1_raw": [v for _, v in temps],
                         "post_hk3_modes": [v for _, v in modes],
                         "safe_entry_event_count": fault_events.count(0x0002),
                         "hard_limit_event_count": fault_events.count(0x0051),
                         "post_hk1_coverage_5s": temp_coverage,
                         "post_hk3_coverage_5s": mode_coverage,
                         "required_observation_coverage_5s": required_coverage,
                         "source_link_zero_faults": healthy}}


def admitted_envelope(obs: list[dict[str, Any]], start: float, end: float,
                      health: dict[str, Any]) -> dict[str, Any]:
    """No case ID, source A, interventions, provenance class, or omission metadata."""
    return {"contract": "g1-admitted-observation-v0.4",
            "observations": obs,
            "window": {"start_sim_time_s": start, "end_sim_time_s": end},
            "link_health": health}


def assess_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    """Entry point of the blind worker; NO file reads or upstream imports."""
    require(isinstance(envelope, dict) and
            set(envelope) == {"contract", "observations", "window", "link_health"},
            "unexpected blind-assessment envelope structure")
    require(envelope["contract"] == "g1-admitted-observation-v0.4",
            "unexpected admitted-envelope contract")
    window = envelope["window"]
    require(isinstance(window, dict), "invalid window")
    start, end = window.get("start_sim_time_s"), window.get("end_sim_time_s")
    require(is_number(start) and is_number(end) and end > start and
            abs(end - start - WINDOW_S) <= 0.01, "invalid assessment window")
    health = envelope["link_health"]
    require(isinstance(health, dict), "invalid link health")
    obs = check_observations(envelope["observations"])
    return assess(obs, float(start), float(end), health)


def blind_assessment_subprocess(envelope: dict[str, Any]) -> dict[str, Any]:
    """Invoke a separate Python process with only this admitted case over stdin."""
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--assess-stdin"],
        input=json.dumps(envelope, allow_nan=False), capture_output=True,
        text=True, timeout=45, check=False,
    )
    require(completed.returncode == 0,
            "blind assessor failed: " + (completed.stderr or completed.stdout)[-600:])
    try:
        result = json.loads(completed.stdout)
    except ValueError as exc:
        raise InputRejected("invalid blind-assessor response") from exc
    require(isinstance(result, dict) and result.get("verdict") in
            {"ADMISSIBLE", "NOT_ADMISSIBLE", "INDETERMINATE"},
            "unexpected blind-assessor result")
    return result


def run(artifacts: Path) -> int:
    ab = read_manifest(artifacts / "g1-thermal-ab.sha256")
    c = read_manifest(artifacts / "g1-thermal-c.sha256")
    require("g1-thermal-a.json" in ab, "A digest missing from A/B manifest")
    out: dict[str, Any] = {"experiment": "G1_OFFLINE_ASSESSMENT",
       "policy": {"version": "experimental-v0.4", "hard_limit_raw": LIMIT_RAW,
                  "required_5s_hk_samples": MIN_SAMPLES, "max_gap_s": MAX_GAP_S,
                  "openobsw_pin": OBSW_PIN, "opensvf_pin": SVF_PIN,
                  "simulator_sha256_pin": SIMULATOR_SHA256},
       "evaluated_at_utc": datetime.now(timezone.utc).isoformat(),
       "cases": {}}
    failure = False
    verified_a: dict[str, Any] | None = None
    verified_a_digest: str | None = None
    for name in ("A", "B", "C"):
        filename = f"g1-thermal-{name.lower()}.json"
        manifest = c if name == "C" else ab
        try:
            record, digest = load_and_verify(artifacts / filename, manifest)
            obs, start, end = check_record(name, record, ab["g1-thermal-a.json"])
            if name == "A":
                verified_a = record
                verified_a_digest = digest
            elif name == "C":
                require(verified_a is not None and verified_a_digest is not None,
                        "cannot admit C: source A was not admitted")
                check_projection_fidelity(record, verified_a, verified_a_digest)
            health = record["source_link_health"] if name == "C" else record["link_health"]
            envelope = admitted_envelope(obs, start, end, health)
            result = blind_assessment_subprocess(envelope)
            result.update({"admission": "ACCEPTED", "input_sha256": digest,
                           "packet_count": len(obs)})
            print(f"{name}: {result['verdict']} | TM={len(obs)} | "
                  f"HK1={result['observed']['post_hk1_raw']} | "
                  f"integrity=OK")
        except (InputRejected, OSError, ValueError, TypeError, KeyError) as exc:
            result = {"admission": "REJECTED", "verdict": None, "error": str(exc)}
            print(f"{name}: INPUT REJECTED | {exc}")
            failure = True
        out["cases"][name] = result
    target = artifacts / "g1-offline-verdicts-v0_4.json"
    target.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    checksum = sha256(target.read_bytes())
    (artifacts / "g1-offline-verdicts-v0_4.sha256").write_text(
        f"{checksum}  {target.name}\n", encoding="utf-8")
    print(f"Report: {target}")
    return 2 if failure else 0


def self_test() -> None:
    """Small synthetic regression set. Never treats upstream test results as evidence."""
    def p(index: int, t: float, phase: str, svc: int, sub: int, payload: bytes) -> dict:
        return {"index": index, "sim_time_s": t, "phase": phase,
                "service": svc, "subservice": sub, "apid": 1,
                "sequence_count": index, "obt_seconds": int(t),
                "app_data_hex": payload.hex()}
    def make(value: int, count: int) -> list[dict]:
        records = [p(0, 4.9, "fault_activation", 5, 4,
                     b"\x00\x51" + struct.pack(">f", 1300.0)),
                   p(1, 4.9, "fault_activation", 5, 4, b"\x00\x02"),
                   p(2, 4.9, "fault_activation", 3, 25,
                     b"\x03\x01" + (4).to_bytes(4, "big"))]
        for j in range(5):
            t = 5.5 + j
            records.append(p(len(records), t, "post_fault_observation", 3, 25,
                             b"\x03\x01" + int(t).to_bytes(4, "big")))
            if j < count:
                records.append(p(len(records), t, "post_fault_observation", 3, 25,
                                 b"\x01" + struct.pack(">h", value)))
        return records
    health = {"tm_dropped": 0, "desyncs": 0, "hk_undecoded": 0, "obsw_exit_status": None}
    a = blind_assessment_subprocess(admitted_envelope(make(650, 5), 5.0, 10.0, health))
    b = blind_assessment_subprocess(admitted_envelope(make(1300, 5), 5.0, 10.0, health))
    c = blind_assessment_subprocess(admitted_envelope(make(650, 2), 5.0, 10.0, health))
    assert [x["verdict"] for x in (a, b, c)] == [
        "ADMISSIBLE", "NOT_ADMISSIBLE", "INDETERMINATE"]
    # Causal counterfactual: identical complete observations, independent of
    # direct/derived origin, reach ADMISSIBLE. Removal of critical HK1 reduces
    # evidence sufficiency; no hardcoded 'C' or 'derived' downgrade exists.
    complete = admitted_envelope(make(650, 5), 5.0, 10.0, health)
    assert "scenario" not in json.dumps(complete)
    assert "derived" not in json.dumps(complete)
    assert blind_assessment_subprocess(complete)["verdict"] == "ADMISSIBLE"
    assert blind_assessment_subprocess(admitted_envelope(make(650, 2), 5.0, 10.0, health))["verdict"] == "INDETERMINATE"
    assert blind_assessment_subprocess(admitted_envelope(make(1300, 1), 5.0, 10.0, health))["verdict"] == "NOT_ADMISSIBLE"
    altered_health = dict(health, desyncs=1)
    assert blind_assessment_subprocess(admitted_envelope(make(650, 5), 5.0, 10.0, altered_health))["verdict"] == "INDETERMINATE"
    try:
        corrupted = make(650, 5)
        corrupted[1]["index"] = 0
        check_observations(corrupted)
    except InputRejected:
        pass
    else:
        raise AssertionError("duplicate capture index was not rejected")
    # Admission test: a self-consistent, hashable C must still match A's TM exactly.
    import copy
    ao = make(650, 5)
    omission_packets = [p for p in ao if p["phase"] == "post_fault_observation"
                        and p["service"] == 3 and p["app_data_hex"].startswith("01")][2:]
    oi = [p["index"] for p in omission_packets]
    c_observations = [p for p in ao if p["index"] not in set(oi)]
    a_record = {
        "observations": ao,
        "source_revisions": {"openobsw": OBSW_PIN, "opensvf": SVF_PIN},
        "simulator_sha256": "0" * 64,
        "link_health": {"tm_parsed": len(ao)},
        "interventions": [],
        "post_fault_window": {"start_sim_time_s": 5.0, "end_sim_time_s": 10.0},
    }
    c_record = {
        "observations": c_observations,
        "source": {"sha256": "a" * 64, "openobsw": OBSW_PIN,
                   "opensvf": SVF_PIN, "simulator_sha256": "0" * 64},
        "derivation": {"original_packet_count": len(ao),
                       "expected_post_fault_hk1": len(omission_packets) + 2,
                       "omitted_original_indices": oi,
                       "omitted_sim_times_s": [p["sim_time_s"] for p in omission_packets]},
        "source_link_health": a_record["link_health"],
        "interventions": [],
        "observation_window": a_record["post_fault_window"],
    }
    check_projection_fidelity(c_record, a_record, "a" * 64)
    altered = copy.deepcopy(c_record)
    altered["observations"][0]["apid"] = 99
    try:
        check_projection_fidelity(altered, a_record, "a" * 64)
    except InputRejected:
        pass
    else:
        raise AssertionError("modified surviving C packet was not rejected")
    # SEM-01 synthetic admission checks for the full evidence envelope.
    good = make(650, 5)
    check_observations(good)
    check_timeline_and_obt(good, 5.0, 10.0)
    from copy import deepcopy
    for mutate in (lambda q: q[0].update(apid=99999),
                   lambda q: q[0].update(app_data_hex="005144228000"),
                   lambda q: q[-1].update(obt_seconds=999999),
                   lambda q: q[-1].update(phase="fault_activation")):
        damaged = deepcopy(good)
        mutate(damaged)
        try:
            check_timeline_and_obt(check_observations(damaged), 5.0, 10.0)
        except InputRejected:
            pass
        else:
            raise AssertionError("SEM-01 probe was not rejected")
    print("Evaluator v0.4 SELFTEST: PASS (A/B/C; blind worker; derived counterfactual; projection fidelity; SEM-01 malformed inputs)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, default=Path(__file__).resolve().parent.parent / "artifacts")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--assess-stdin", action="store_true",
                        help="Internal assessor worker: one admitted evidence envelope from stdin")
    args = parser.parse_args()
    if args.assess_stdin:
        try:
            envelope = json.load(sys.stdin)
            print(json.dumps(assess_envelope(envelope), allow_nan=False))
        except (InputRejected, ValueError, KeyError, TypeError) as exc:
            print(f"BLIND ASSESSMENT ERROR: {exc}", file=sys.stderr)
            sys.exit(2)
    elif args.self_test:
        self_test()
    else:
        try:
            sys.exit(run(args.artifacts))
        except (InputRejected, OSError) as exc:
            print(f"GLOBAL INPUT REJECTED: {exc}", file=sys.stderr)
            sys.exit(2)
