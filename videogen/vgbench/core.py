"""Config, the clip plan, generation through the ElevenLabs video API, and importing clips made by hand."""
import csv
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

from .items import clips

WORK = Path(os.environ.get("VG_WORK") or Path(__file__).resolve().parent.parent)   # VG_WORK: tests use a temp folder
CLIPS = WORK / "clips"
API = "https://api.elevenlabs.io/v1"
FAKE = os.environ.get("VG_FAKE") == "1"


def load_config():
    cfg = yaml.safe_load(open(WORK / "config.yaml", encoding="utf-8"))
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
    cfg["api_key"] = os.environ.get("ELEVENLABS_API_KEY", "")
    return cfg


def clip_path(model, cid):
    return CLIPS / model / f"{cid}.mp4"


def log(model, rec):
    (CLIPS / model).mkdir(parents=True, exist_ok=True)
    rec.update(model=model, ts=datetime.now(timezone.utc).isoformat())
    with open(CLIPS / model / "log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def plan(cfg):
    """Write prompts.csv: every clip with its full prompt and seed, ready to paste into the ElevenLabs web app."""
    rows = clips(cfg)
    with open(WORK / "prompts.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file_name", "storyboard", "shot", "kind", "seed", "prompt"])
        for c in rows:
            w.writerow([f"{c['cid']}.mp4", c["sb"], c["shot"], c["kind"], c["seed"], c["prompt"]])
    n = len(rows)
    print(f"{n} clips per model x {len(cfg['models'])} model(s) = {n * len(cfg['models'])} clips of {cfg['duration_secs']} s.")
    print("Wrote videogen/prompts.csv. Generate each row (same model settings for all), save it as file_name, then import.")
    for m in cfg["models"]:
        have = sum(clip_path(m["name"], c["cid"]).exists() for c in rows)
        print(f"  {m['name']}: {have}/{n} clips present")


# ---------------------------------------------------------------- generation (needs the ElevenLabs Pro plan)
def _usage_since(cfg, start_ms):
    import requests
    r = requests.get(f"{API}/usage/character-stats", headers={"xi-api-key": cfg["api_key"]}, timeout=30,
                     params=dict(start_unix=start_ms, end_unix=int(time.time() * 1000) + 3_600_000,
                                 breakdown_type="product_type", aggregation_interval="cumulative"))
    r.raise_for_status()
    return {k: sum(v) for k, v in r.json().get("usage", {}).items() if sum(v)}


def _fake_clip(path, c):
    """A synthetic stand-in so the whole pipeline can be tested for free (VG_FAKE=1)."""
    import imageio_ffmpeg
    import zlib
    rng = np.random.default_rng(zlib.crc32(f"{c['prompt']}|{c['seed']}".encode()))
    base = rng.integers(40, 200, 3)
    w = imageio_ffmpeg.write_frames(str(path), (160, 90), fps=8, macro_block_size=1)
    w.send(None)
    for t in range(32):
        f = np.zeros((90, 160, 3), np.uint8) + base.astype(np.uint8)
        x = (t * 4) % 140
        f[30:60, x:x + 20] = 255 - base
        w.send(f.tobytes())
    w.close()


def generate(cfg, models, yes=False):
    import requests
    rows = clips(cfg)
    jobs = [(m, c) for m in cfg["models"] if not models or m["name"] in models for c in rows
            if not clip_path(m["name"], c["cid"]).exists()]
    print(f"{len(jobs)} clips to generate. Spending guard: {cfg['max_credits']:,} credits.")
    if not jobs or (not yes and input("Proceed? [y/N] ").strip().lower() != "y"):
        return
    H = {"xi-api-key": cfg["api_key"]}
    start = int(time.time() * 1000)
    for k, (m, c) in enumerate(jobs, 1):
        path = clip_path(m["name"], c["cid"])
        path.parent.mkdir(parents=True, exist_ok=True)
        if FAKE:
            _fake_clip(path, c)
            log(m["name"], dict(cid=c["cid"], source="fake"))
            continue
        spent = sum(_usage_since(cfg, start).values())
        if spent >= cfg["max_credits"]:
            print(f"Stopping: {spent:,} credits used, at the guard of {cfg['max_credits']:,}.")
            break
        body = dict(model_id=m["model_id"], prompt=c["prompt"], duration_secs=cfg["duration_secs"],
                    resolution=cfg["resolution"], aspect_ratio=cfg["aspect_ratio"],
                    generate_audio=cfg["generate_audio"], seed=c["seed"], enhance_prompt=False)
        r = requests.post(f"{API}/flows/video", headers=H, json=body, timeout=60)
        if r.status_code == 402:
            raise SystemExit("ElevenLabs says the video API needs a paid (Pro) plan. Make the clips in the web app "
                             "instead: see prompts.csv, then `python -m vgbench import <folder> --model <name>`.")
        if r.status_code != 200:
            print(f"  {c['cid']}: create failed HTTP {r.status_code} {r.text[:200]}")
            continue
        gid, t0 = r.json()["id"], time.time()
        while True:
            time.sleep(10)
            g = requests.get(f"{API}/flows/video/{gid}", headers=H, timeout=30).json()
            if g.get("status") in ("completed", "failed") or time.time() - t0 > 900:
                break
        if g.get("status") != "completed":
            print(f"  {c['cid']}: {g.get('status')} {g.get('failure_reason') or ''} (failed generations are not charged)")
            continue
        path.write_bytes(requests.get(g["content_url"], timeout=120).content)
        log(m["name"], dict(cid=c["cid"], source="api", id=gid, gen_seconds=round(time.time() - t0)))
        print(f"  {k}/{len(jobs)} {m['name']} {c['cid']} ({round(time.time() - t0)} s)")
    print(f"Credits used this run (ElevenLabs usage report, may lag a few minutes): {_usage_since(cfg, start) or 'none yet'}")


def import_clips(cfg, folder, model):
    """Copy clips made by hand (named like prompts.csv's file_name) into clips/<model>/."""
    want = {c["cid"] for c in clips(cfg)}
    got = 0
    for p in Path(folder).glob("*.mp4"):
        if p.stem in want:
            dst = clip_path(model, p.stem)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, dst)
            log(model, dict(cid=p.stem, source="web app", file=p.name))
            got += 1
        else:
            print(f"  skipped {p.name}: not a file name from prompts.csv")
    print(f"Imported {got} clip(s) for {model}. {len(want) - sum(clip_path(model, c).exists() for c in want)} still missing.")
