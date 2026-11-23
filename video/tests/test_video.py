import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from videobench.report import grade_answer, norm  # noqa: E402
from videobench.run import parse  # noqa: E402
from videobench.scenes import designs  # noqa: E402

CFG = dict(seed=2453, clips_per_suite=8, long_durations_s=[60, 150], long_clips_per_duration=3, shift_s=1.5,
           time_tolerance_s=1.5)


def test_grading_rules():
    choice = dict(kind="choice", truth="red circle", accept=[])
    assert grade_answer(choice, "Red_Circle.")[0] == 1 and grade_answer(choice, "blue circle")[0] == 0
    assert grade_answer(dict(kind="choice", truth="no_audio", accept=[]), "cannot_tell")[0] == 1
    assert grade_answer(dict(kind="choice", truth="no_audio", accept=[]), "dog barking")[0] == 0
    num = dict(kind="number", truth=4.0, tol=1.5)
    assert grade_answer(num, "about 5.2 seconds") == (1, 1.2000000000000002)
    assert grade_answer(num, 7)[0] == 0
    assert grade_answer(dict(kind="number", truth="no_audio", tol=1.5), "no_audio")[0] == 1
    assert grade_answer(dict(kind="count", truth=3), "3")[0] == 1
    assert grade_answer(choice, None)[0] == 0
    assert norm("No-Audio") == "no audio"


def test_parse_json_inside_text():
    assert parse('Sure: {"q1": {"answer": "yes"}} done')["q1"]["answer"] == "yes"
    assert parse("not json") is None


def test_designs_are_consistent():
    ds = designs(CFG)
    assert len(ds) == 8 * 3 + 6
    for d in ds:
        conds = d.get("conditions", ["av", "video_only", "shifted", "swapped"])
        for q in d["questions"]:
            for c in conds:
                t = q["truth"][c]
                if q["kind"] == "choice":
                    assert t in q["options"], (d["cid"], q["qid"], t)
            if "video_only" in conds and q["tag"] in ("audio", "sync"):
                assert q["truth"]["video_only"] == "no_audio"
        if d["suite"] == "temporal":   # shifted sound never lands on another appearance
            assert d["questions"][5]["truth"]["shifted"] == "none"


def test_fake_pipeline(tmp_path):
    env = dict(os.environ, VIDEOBENCH_FAKE="1", VIDEOBENCH_HOME=str(tmp_path))
    for cmd in (["build"], ["run", "--pilot", "-y"], ["report"]):
        subprocess.run([sys.executable, "-m", "videobench", *cmd], cwd=ROOT, env=env, check=True, capture_output=True)
    man = [json.loads(l) for l in open(tmp_path / "clips" / "manifest.jsonl")]
    assert len(man) == 24 * 4 + 6
    assert (tmp_path / "results" / "summary.md").exists()
