"""Complexity measures and verdicts. The verdicts are pure; one test drives the real lizard binary."""
import datetime
import subprocess
import sys

import pytest

from conftest import REPO

sys.path.insert(0, str(REPO / "tools"))
import quality_complexity
import quality_waivers

SRC = '''
class Board:
    def lights(self, items):
        for item in items:
            if item.a:
                pass
            elif item.b:
                with open(item) as f:
                    pass
        def inner():
            if True:
                pass
        return inner
'''
ROWS = {("plugin/lib/vela/x.py", 3): {"ccn": 5, "nloc": 10, "params": 2},
        ("plugin/lib/vela/x.py", 10): {"ccn": 2, "nloc": 3, "params": 0}}
PATH = "plugin/lib/vela/reading.py"
KEY = PATH + "::style_problems"
TODAY = datetime.date(2026, 10, 27)


def test_layers():
    assert [quality_complexity.layer_of(p) for p in [
        "plugin/lib/vela/reading.py", "plugin/lib/vela/cli.py", "plugin/lib/vela/commands/map.py",
        "plugin/lib/vela/edge/atomic.py", "plugin/lib/vela/flowcheck/build.py", "tools/check_site.py",
        ".claude/hooks/gates.py", "tests/test_x.py", "plugin/lib/vela/__pycache__/x.py"]] == \
        ["core", "shell", "shell", "edge", "core", "tools", "hooks", None, None]


def test_measures_join_qualnames_and_nesting():
    m = {x.key: x for x in quality_complexity.function_measures("plugin/lib/vela/x.py", SRC, ROWS)}
    assert m["plugin/lib/vela/x.py::Board.lights"].values == {"ccn": 5, "nloc": 10, "params": 2, "nesting": 3}
    assert m["plugin/lib/vela/x.py::Board.lights.<locals>.inner"].values["nesting"] == 1


def test_a_def_lizard_did_not_measure_is_an_error():
    only_lights = {k: v for k, v in ROWS.items() if k[1] == 3}
    with pytest.raises(quality_complexity.MeasureError, match="inner"):
        quality_complexity.function_measures("plugin/lib/vela/x.py", SRC, only_lights)


def test_two_defs_with_one_qualname_become_one_measure_at_the_maximum():
    src = "def f(a):\n    pass\n\n\nif True:\n    def f(a, b):\n        pass\n"
    rows = {("p.py", 1): {"ccn": 2, "nloc": 5, "params": 1}, ("p.py", 6): {"ccn": 1, "nloc": 9, "params": 2}}
    (only,) = quality_complexity.function_measures("p.py", src, rows)
    assert only.line == 1 and only.values == {"ccn": 2, "nloc": 9, "params": 2, "nesting": 0}


def test_lizard_csv_is_read_by_file_and_start_line():
    text = '5,2,30,1,6,"f@3-8@a.py","a.py","f","f( a )",3,8\n'
    assert quality_complexity.parse_lizard_csv(text) == {("a.py", 3): {"nloc": 5, "ccn": 2, "params": 1}}


def test_a_malformed_lizard_row_is_an_error():
    with pytest.raises(quality_complexity.MeasureError):
        quality_complexity.parse_lizard_csv("1,2,3\n")


def measure(ccn=5, key=KEY, path=PATH, **more):
    return quality_complexity.Measure(key, path, 7, {"ccn": ccn, "nloc": 10, "params": 1, "nesting": 1, **more})


def waiver(limits, expires=datetime.date(2027, 4, 27), key=KEY):
    return {key: quality_waivers.Waiver(key, limits, "smalls257", expires, "debt", 2)}


def judged(measures, waivers=None, scanned=(PATH,), today=TODAY):
    return quality_complexity.judge(measures, waivers or {}, set(scanned), today)


def test_unwaived_function_over_cap_is_a_finding():
    (found,) = judged([measure(ccn=11)])
    assert found.gate == "QG-CPX" and "CCN 11 > 10" in found.message and found.path == PATH


def test_waived_function_within_its_recorded_limits_passes():
    assert judged([measure(ccn=14)], waiver({"ccn": 14})) == []


def test_waived_function_that_grew_fails():
    (found,) = judged([measure(ccn=16)], waiver({"ccn": 14}))
    assert found.gate == "QG-CPX" and "grew past its waiver: CCN 16 > 14 recorded" in found.message


def test_waived_function_over_an_unrecorded_metric_fails():
    found = judged([measure(ccn=14, params=7)], waiver({"ccn": 14}))
    assert [f.gate for f in found] == ["QG-CPX"] and "PARAMS 7 > 6" in found[0].message


def test_waiver_for_a_function_now_under_caps_is_stale():
    (found,) = judged([measure(ccn=5)], waiver({"ccn": 14}))
    assert found.gate == "QG-WAIVER" and "meets its caps now" in found.message


def test_waiver_for_a_missing_function_is_stale_and_names_the_reseed():
    (found,) = judged([], waiver({"ccn": 14}))
    assert found.gate == "QG-WAIVER" and "quality_seed.py" in found.message


def test_expired_waiver_fails():
    found = judged([measure(ccn=14)], waiver({"ccn": 14}), today=datetime.date(2027, 4, 28))
    assert [f.gate for f in found] == ["QG-WAIVER"] and "expired on 2027-04-27" in found[0].message


def test_waivers_outside_the_scanned_paths_are_not_judged():
    assert judged([measure(ccn=16)], waiver({"ccn": 14}), scanned=()) == []
    assert judged([], waiver({"ccn": 14}), scanned=()) == []


def test_file_over_its_line_cap():
    big = quality_complexity.Measure(PATH, PATH, 1, {"lines": 501})
    (found,) = judged([big])
    assert found.gate == "QG-LEN" and "LINES 501 > 500" in found.message
    assert judged([big], waiver({"lines": 501}, key=PATH)) == []


def test_real_lizard_measures_every_def(tmp_path):
    f = tmp_path / "plugin/lib/vela/y.py"
    f.parent.mkdir(parents=True)
    f.write_text(SRC, encoding="utf-8")
    out = subprocess.run(["lizard", "-l", "python", "--csv", "plugin/lib/vela/y.py"], cwd=tmp_path,
                         capture_output=True, text=True, timeout=30).stdout
    rows = quality_complexity.parse_lizard_csv(out)
    assert len(quality_complexity.function_measures("plugin/lib/vela/y.py", SRC, rows)) == 2
