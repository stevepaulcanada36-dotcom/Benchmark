"""Runs the whole pipeline for free: fake clips, automatic measures, the rating page, simulated ratings, the report.
Everything is written to a temp folder; nothing here touches real clips or real ratings."""
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def run(tmp, *args):
    env = dict(os.environ, VG_FAKE="1", VG_WORK=str(tmp), PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, "-m", "vgbench", *args], cwd=HERE, env=env, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr + p.stdout
    return p.stdout


def test_pipeline(tmp_path):
    shutil.copy(HERE / "config.yaml", tmp_path / "config.yaml")
    assert "32 clips per model" in run(tmp_path, "plan")
    run(tmp_path, "generate", "--yes")
    assert len(list((tmp_path / "clips").rglob("*.mp4"))) == 32
    run(tmp_path, "auto")
    auto = list(csv.DictReader(open(tmp_path / "results/auto.csv", encoding="utf-8")))
    sb1 = next(r for r in auto if r["cid"] == "SB1-1")
    assert float(sb1["repeat_diff"]) == 0.0          # same prompt + seed -> identical fake clip
    out = run(tmp_path, "rate")
    assert "storyboard" in out
    page = (tmp_path / "rating/index.html").read_text(encoding="utf-8")
    tasks = json.loads(re.search(r"const T=(\[.*?\]),Q=", page, re.S).group(1))
    assert "veo" not in json.dumps(tasks)            # blind: no model name in the page
    # simulated ratings, only to exercise the report
    cols = ["rater", "task", "type", "identity", "objects", "motion", "prompt", "text", "sound", "demo",
            "character", "style", "place", "state", "story", "similar", "note"]
    (tmp_path / "ratings").mkdir()
    with open(tmp_path / "ratings/sim.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for k, t in enumerate(tasks):
            v = str(1 + k % 5)
            w.writerow(["sim", t["id"], t["type"], v, v, v, v, "yes", v, "yes" if k % 2 else "no",
                        v, v, v, "partly", v, "nearly identical", ""])
    run(tmp_path, "report")
    s = (tmp_path / "results/summary.md").read_text(encoding="utf-8")
    assert "Across the three shots" in s and "Rater consistency" in s and "Spearman" in s
