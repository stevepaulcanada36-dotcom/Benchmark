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
    (WORK / "checklist.html").write_text(checklist(cfg, rows), encoding="utf-8")
    print(f"{n} clips per model x {len(cfg['models'])} model(s) = {n * len(cfg['models'])} clips of {cfg['duration_secs']} s.")
    print("Wrote videogen/prompts.csv and videogen/checklist.html (open it in a browser and work down the list).")
    for m in cfg["models"]:
        have = sum(clip_path(m["name"], c["cid"]).exists() for c in rows)
        print(f"  {m['name']}: {have}/{n} clips present")


def checklist(cfg, rows):
    """A page to work through in the ElevenLabs web app: copy the prompt, generate, save under the given name, tick."""
    import html
    m = cfg["models"][0]
    trs = "".join(
        f'<tr data-id="{c["cid"]}"><td><input type="checkbox"></td><td><b>{c["cid"]}.mp4</b><br><button data-copy="{c["cid"]}">Copy file name</button></td>'
        f'<td>{c["sb"]} · {"shot " + c["shot"] if c["kind"] == "shot" else {"repeat": "shot 1 again, SAME seed", "reseed": "shot 1 again, NEW seed", "control": "control"}[c["kind"]]}'
        f'<br><span class="seed">seed {c["seed"]}</span></td><td class="p">{html.escape(c["prompt"])}<br>'
        f'<button data-copy="{html.escape(c["prompt"], quote=True)}">Copy prompt</button></td></tr>' for c in rows)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clip Generation Checklist</title><style>
body{{margin:0;background:#14181e;color:#e8eaed;font:15px/1.5 system-ui,Segoe UI,Arial,sans-serif}}.w{{max-width:1100px;margin:auto;padding:16px}}
ol li{{margin:4px 0}}code{{background:#252c36;padding:1px 5px;border-radius:4px}}table{{border-collapse:collapse;width:100%}}
td{{border-bottom:1px solid #2e3742;padding:10px 8px;vertical-align:top}}td.p{{color:#cfd3d8;font-size:14px}}.seed{{color:#E3B341;font-family:monospace}}
button{{background:#1d232b;color:#e8eaed;border:1px solid #2e3742;border-radius:6px;padding:4px 9px;margin-top:6px;cursor:pointer}}
tr.done{{opacity:.45}}input[type=checkbox]{{width:20px;height:20px}}.box{{background:#1d232b;border:1px solid #2e3742;border-radius:10px;padding:12px 16px}}
#n{{color:#E3B341;font-weight:700}}</style></head><body><div class="w">
<h1>Make the {len(rows)} clips in the ElevenLabs web app</h1>
<div class="box"><b>Use the same settings for every clip</b>: video model <b>{html.escape(m["name"])}</b> (or one model of your choice, the same for all),
<b>{cfg["duration_secs"]} seconds</b>, <b>{cfg["resolution"]}</b>, <b>{cfg["aspect_ratio"]}</b>, sound <b>{"on" if cfg["generate_audio"] else "off"}</b>,
prompt enhancement <b>off</b> if there is such a switch.
<ol><li>Click <b>Copy prompt</b> and paste it into the ElevenLabs video prompt box. Change nothing in it.</li>
<li>If there is a <b>seed</b> box, type the seed shown. If there is none, carry on and import with <code>--no-seed</code> (step 5).</li>
<li>Generate. If it fails, just try again (failed generations are not charged).</li>
<li>Download the video, and when saving, click <b>Copy file name</b> and paste it as the name (e.g. <code>SB1-1.mp4</code>). Keep all of them in one folder.</li>
<li>Tick the box. When all are done, in <code>videogen/</code> run:<br><code>python -m vgbench import C:\\path\\to\\folder --model {html.escape(m["name"])}</code> (add <code>--no-seed</code> if you could not set seeds)</li>
<li>Then <code>python -m vgbench auto</code> and <code>python -m vgbench rate</code>, and rate the clips.</li></ol>
Tip: do not watch closely while generating. Rate them later on the blind page, so you judge them fresh.</div>
<p><span id="n">0</span> / {len(rows)} done</p><table>{trs}</table></div><script>
const K='vgcheck-v1';let S={{}};try{{S=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{}}
const upd=()=>{{let n=0;document.querySelectorAll('tr[data-id]').forEach(r=>{{const on=!!S[r.dataset.id];r.querySelector('input').checked=on;r.classList.toggle('done',on);n+=on}});document.getElementById('n').textContent=n}};
document.querySelectorAll('tr[data-id] input').forEach(b=>b.onchange=()=>{{S[b.closest('tr').dataset.id]=b.checked;try{{localStorage.setItem(K,JSON.stringify(S))}}catch(e){{}};upd()}});
document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{{const t=b.dataset.copy;await navigator.clipboard.writeText(b.textContent.includes('file')?t+'.mp4':t);const o=b.textContent;b.textContent='Copied';setTimeout(()=>b.textContent=o,900)}});
upd();</script></body></html>"""


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


def seeds_set(model):
    """False if any clip of this model was imported without a seed (then 'same seed' pairs are just two tries)."""
    p = CLIPS / model / "log.jsonl"
    return not p.exists() or all(json.loads(l).get("seed_set", True) for l in open(p, encoding="utf-8") if l.strip())


def import_clips(cfg, folder, model, no_seed=False):
    """Copy clips made by hand (named like prompts.csv's file_name) into clips/<model>/."""
    if model not in {m["name"] for m in cfg["models"]}:
        raise SystemExit(f"Unknown model '{model}'. Add it under models: in config.yaml first.")
    want = {c["cid"] for c in clips(cfg)}
    got = 0
    for p in Path(folder).glob("*.mp4"):
        if p.stem in want:
            dst = clip_path(model, p.stem)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(p, dst)
            log(model, dict(cid=p.stem, source="web app", file=p.name, seed_set=not no_seed))
            got += 1
        else:
            print(f"  skipped {p.name}: not a file name from prompts.csv")
    print(f"Imported {got} clip(s) for {model}. {len(want) - sum(clip_path(model, c).exists() for c in want)} still missing.")
