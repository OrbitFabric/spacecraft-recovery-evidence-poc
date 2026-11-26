#!/usr/bin/env python3
"""Offline unit/admission tests. Synthetic second window != executed C+ SIL proof."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import g1_cplus as c


class CPlusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ev = c.load_evaluator(HERE / "g1_offline_evaluator_v0_4.py")
        fixture = HERE / "fixtures"
        cls.a = c.load_json(fixture / "g1-thermal-a.json")
        cls.b = c.load_json(fixture / "g1-thermal-b.json")
        cls.old_c = c.load_json(fixture / "g1-thermal-c.json")
        cls.verdicts = c.load_json(fixture / "g1-offline-verdicts-v0_4.json")

    def test_baseline_files_match_existing_qualified_verdicts(self) -> None:
        fixture = HERE / "fixtures"
        a, b, cc = self.a, self.b, self.old_c
        ed = self.ev
        digest_a = c.file_digest(fixture / "g1-thermal-a.json")
        for name, record in (("A", a), ("B", b), ("C", cc)):
            digest = c.file_digest(fixture / f"g1-thermal-{name.lower()}.json")
            self.assertEqual(self.verdicts["cases"][name]["input_sha256"], digest)
            obs, start, end = ed.check_record(name, record, digest_a)
            ed.check_observations(obs)
            ed.check_timeline_and_obt(obs, start, end)
        ed.check_projection_fidelity(cc, a, digest_a)
        self.assertEqual(
            [self.verdicts["cases"][name]["verdict"] for name in "ABC"],
            ["ADMISSIBLE", "NOT_ADMISSIBLE", "INDETERMINATE"],
        )

    def _first(self):
        ev = self.ev
        source = self.a["observations"]
        start, end = (self.a["post_fault_window"][k] for k in
                      ("start_sim_time_s", "end_sim_time_s"))
        hk = [p["index"] for p in source
              if p["phase"] == "post_fault_observation" and c.packet_is_hk(p, 1)]
        self.assertEqual(len(hk), 5)
        omit = set(hk[2:])
        selected = set(range(len(source)))
        view = c.select_view(source, selected, omit)
        return source, selected, omit, view, start, end

    def _second_synthetic(self):
        """Append a *synthetic* shifted A window for admission unit tests only."""
        original = self.a["observations"]
        post = [p for p in original if p["phase"] == "post_fault_observation"]
        source = copy.deepcopy(original)
        second_ids = set()
        for p in post:
            new = copy.deepcopy(p)
            new["index"] = len(source)
            new["sim_time_s"] = round(new["sim_time_s"]+5.0, 6)
            new["obt_seconds"] += 5
            if c.packet_is_hk(new, 3):
                raw = bytearray.fromhex(new["app_data_hex"])
                raw[2:6] = (int.from_bytes(raw[2:6], "big")+5).to_bytes(4, "big")
                new["app_data_hex"] = raw.hex()
            second_ids.add(new["index"])
            source.append(new)
        pre = {p["index"] for p in original if p["phase"] != "post_fault_observation"}
        return source, pre | second_ids, second_ids

    def _link(self, count):
        return {"healthy": True, "tm_received": count, "tm_parsed": count,
                "tm_dropped": 0, "desyncs": 0, "hk_undecoded": 0,
                "obsw_exit_status": None}

    def test_two_assessments_with_original_a_and_synthetic_second(self) -> None:
        ev = self.ev
        original, selected1, omit, view1, start1, end1 = self._first()
        first = c.assess_view(ev, original, view1, selected1, omit,
                              start1, end1, self._link(len(original)))
        self.assertEqual(first["verdict"], "INDETERMINATE")
        self.assertEqual(first["criteria"]["thermal_clearance"]["state"], "UNKNOWN")
        request = c.cplus_request(first, {"core_input_set_sha256": "a"*64}, end1, ev)
        self.assertEqual(request["core_entity"], "telemetry:obc.temperature_raw")
        self.assertEqual(request["fresh_window_s"], 5.0)
        self.assertIn("no backfill", request["window_rule"])

        extended, selected2, second_ids = self._second_synthetic()
        new_view = c.select_view(extended, selected2)
        c.assert_window_hk(extended, second_ids, expected_raw=650,
                           expected_mode=1, expected_count=5)
        second = c.assess_view(ev, extended, new_view, selected2, set(),
                               end1, end1+5, self._link(len(extended)))
        self.assertEqual(second["verdict"], "ADMISSIBLE")
        self.assertEqual(first["verdict"], "INDETERMINATE")

    def test_modified_surviving_packet_is_rejected(self) -> None:
        original, selected, omitted, view, start, end = self._first()
        view[0]["apid"] += 1
        with self.assertRaisesRegex(ValueError, "view differs"):
            c.checked_view(self.ev, original, view, selected, omitted, start, end)

    def test_non_hk1_omission_is_not_accepted(self) -> None:
        original, selected, omitted, view, start, end = self._first()
        hk3_id = next(p["index"] for p in original
                      if p["phase"] == "post_fault_observation" and c.packet_is_hk(p, 3))
        bad = [p for p in view if p["index"] != hk3_id]
        with self.assertRaisesRegex(ValueError, "view differs"):
            c.checked_view(self.ev, original, bad, selected, omitted, start, end)

    def test_replayed_earlier_window_cannot_be_fresh(self) -> None:
        source, selected, _ = self._second_synthetic()
        # The first window packet times cannot be relabelled as a later window.
        first_post = next(p for p in source if p["phase"] == "post_fault_observation")
        earlier = copy.deepcopy(source[first_post["index"]])
        second_pos = min(i for i, p in enumerate(source) if i >= len(self.a["observations"]))
        source[second_pos]["sim_time_s"] = earlier["sim_time_s"]
        # Structural ordering fails before the blind evaluator can receive it.
        with self.assertRaises(ValueError):
            c.checked_view(self.ev, source, c.select_view(source, selected),
                           selected, set(), 10.0, 15.0)

    def test_second_window_recurrent_fault_does_not_pass_native_checks(self) -> None:
        extended, selected, second_ids = self._second_synthetic()
        changed = next(p for p in extended if p["index"] in second_ids and c.packet_is_hk(p, 1))
        old = changed["app_data_hex"]
        changed["app_data_hex"] = "01" + (1300).to_bytes(2,"big",signed=True).hex() + old[6:]
        with self.assertRaisesRegex(ValueError, "native HK contradicts"):
            c.assert_window_hk(extended, second_ids, 650, 1, 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
