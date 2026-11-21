"""ElevenLabs TTS generation with a credit guard, caching, latency timing and a fake mode for testing."""
import json
import math
import os
import random
import re
import struct
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
import yaml

from . import prompts

ROOT = Path(__file__).resolve().parent.parent
FAKE = os.getenv("AUDIOBENCH_FAKE") == "1"
API = "https://api.elevenlabs.io/v1"


def load_config(path=None):
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parent / ".env")   # repo-level .env
    cfg = yaml.safe_load(open(path or ROOT / "config.yaml"))
    cfg["api_key"] = os.getenv(cfg["api_key_env"], "")
    return cfg


def strip_tags(text):
    return re.sub(r"\[[^\]]+\]\s*", "", text).strip()


def items():
    """All items as dicts: uid, suite, text (as written), reference (what should be heard)."""
    out = []
    for i, t in enumerate(prompts.S1):
        out.append(dict(uid=f"S1-{i:02d}", suite="S1", text=t, reference=t))
    for i, (t, forms) in enumerate(prompts.S2):
        out.append(dict(uid=f"S2-{i:02d}", suite="S2", text=t, reference=forms[0], accepted=forms))
    for i, (t, word, reading) in enumerate(prompts.S3):
        out.append(dict(uid=f"S3-{i:02d}", suite="S3", text=t, reference=t, target=word, reading=reading))
    for i, t in enumerate(prompts.S4):
        out.append(dict(uid=f"S4-{i:02d}", suite="S4", text=t, reference=strip_tags(t)))
    out.append(dict(uid="S5-00", suite="S5", text=prompts.S5, reference=prompts.S5))
    return out


def select(cfg, pilot, suites=None):
    its = [it for it in items() if not suites or it["suite"] in suites]
    if pilot:
        rnd = random.Random(cfg["seed"])
        chosen = []
        for s in sorted({i["suite"] for i in its}):
            group = [i for i in its if i["suite"] == s and s != "S5"]   # S5 too long for a pilot
            if group:
                chosen += rnd.sample(group, max(1, round(len(group) * cfg["pilot_fraction"])))
        return chosen
    return its


def text_for(model, it):
    return it["text"] if model["supports_tags"] else strip_tags(it["text"])


def audio_dir(pilot):
    d = ROOT / "audio" / ("pilot" if pilot else "main")
    d.mkdir(parents=True, exist_ok=True)
    return d


def ext():
    return "wav" if FAKE else "mp3"


def plan(cfg, pilot, models, suites=None):
    todo, credits = [], 0.0
    for m in models:
        for it in select(cfg, pilot, suites):
            runs = 1 if pilot else cfg["runs"][it["suite"]]
            for r in range(runs):
                path = audio_dir(pilot) / m["label"] / f"{it['uid']}_r{r}.{ext()}"
                if not path.exists():
                    txt = text_for(m, it)
                    todo.append((m, it, r, path, txt))
                    credits += len(txt) * m["credits_per_char"]
    return todo, credits


def spent_so_far():
    p = ROOT / "audio" / "ledger.jsonl"
    if not p.exists():
        return 0.0
    return sum(json.loads(l)["credits_est"] for l in open(p) if l.strip())


def subscription(cfg):
    if FAKE:
        return {"character_count": 0, "character_limit": 130000}
    r = requests.get(f"{API}/user/subscription", headers={"xi-api-key": cfg["api_key"]}, timeout=30)
    r.raise_for_status()
    return r.json()


def tts(cfg, model, text):
    """Streams one clip. Returns (bytes, ttfa_s, total_s, info)."""
    if FAKE:
        return _fake_wav(text), 0.05, 0.1, {"seed_used": True}
    url = f"{API}/text-to-speech/{cfg['voice_id']}/stream?output_format={cfg['output_format']}"
    body = {"text": text, "model_id": model["id"], "voice_settings": cfg["voice_settings"], "seed": cfg["seed"]}
    headers = {"xi-api-key": cfg["api_key"], "Content-Type": "application/json"}
    seed_used = True
    for attempt in range(5):
        t0 = time.time()
        try:
            with requests.post(url, json=body, headers=headers, stream=True, timeout=120) as r:
                if r.status_code == 422 and "seed" in body and "seed" in r.text:
                    body.pop("seed"); seed_used = False
                    continue
                if r.status_code in (429, 500, 502, 503):
                    time.sleep(2 ** attempt); continue
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
                chunks, ttfa = [], None
                for c in r.iter_content(4096):
                    if c:
                        ttfa = ttfa if ttfa is not None else time.time() - t0
                        chunks.append(c)
                info = {k: v for k, v in r.headers.items() if "char" in k.lower() or k.lower() == "request-id"}
                info["seed_used"] = seed_used
                return b"".join(chunks), ttfa, time.time() - t0, info
        except requests.RequestException:
            time.sleep(2 ** attempt)
    raise RuntimeError("TTS failed after retries")


def run(cfg, models, pilot=False, yes=False, suites=None):
    todo, est = plan(cfg, pilot, models, suites)
    spent = spent_so_far()
    print(f"{len(todo)} clips to generate, estimated {est:,.0f} credits "
          f"(already spent by this benchmark: {spent:,.0f}; cap {cfg['max_credits']:,}).")
    for m in models:
        mc = sum(len(t[4]) * m["credits_per_char"] for t in todo if t[0] is m)
        print(f"  {m['label']:<12} {mc:>9,.0f} credits")
    if not todo:
        return
    if spent + est > cfg["max_credits"]:
        raise SystemExit("This would exceed max_credits in config.yaml. Lower runs or raise the cap deliberately.")
    sub = subscription(cfg)
    remaining = sub.get("character_limit", 0) - sub.get("character_count", 0)
    print(f"ElevenLabs reports {remaining:,} credits remaining this period.")
    if est > remaining:
        raise SystemExit("Not enough credits left on the account for this run.")
    if not yes and input("Proceed? [y/N] ").strip().lower() != "y":
        raise SystemExit("Cancelled.")
    before = sub.get("character_count", 0)
    meta_path = audio_dir(pilot) / "clips.jsonl"
    consecutive_fail = 0
    for k, (m, it, r, path, txt) in enumerate(todo, 1):
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            audio, ttfa, total, info = tts(cfg, m, txt)
            consecutive_fail = 0
        except RuntimeError as e:
            print(f"  FAILED {m['label']} {it['uid']} r{r}: {e}")
            consecutive_fail += 1
            if consecutive_fail >= 5:
                raise SystemExit("5 failures in a row: stopping. Check the model ID, voice_id and API key.")
            continue
        path.write_bytes(audio)
        rec = dict(uid=it["uid"], suite=it["suite"], run=r, model=m["id"], model_label=m["label"],
                   text_sent=txt, chars=len(txt), credits_est=len(txt) * m["credits_per_char"],
                   ttfa_s=ttfa, total_s=total, path=str(path.relative_to(ROOT)),
                   ts=datetime.now(timezone.utc).isoformat(), **info)
        with open(meta_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        with open(ROOT / "audio" / "ledger.jsonl", "a") as f:
            f.write(json.dumps({"credits_est": rec["credits_est"], "model": m["label"]}) + "\n")
        print(f"  [{k}/{len(todo)}] {m['label']} {it['uid']} r{r}  ttfa={ttfa:.2f}s")
    after = subscription(cfg).get("character_count", before)
    print(f"Account usage moved by {after - before:,} credits (estimate was {est:,.0f}). "
          "If these differ a lot, fix credits_per_char in config.yaml.")


def _fake_wav(text):
    """A short tone whose length scales with the text, for pipeline tests only."""
    import io
    sr, dur = 16000, max(0.5, len(text) / 15)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(2 * math.pi * 220 * t / sr)))
                               for t in range(int(sr * dur))))
    return buf.getvalue()


def list_voices(cfg):
    r = requests.get(f"{API}/voices", headers={"xi-api-key": cfg["api_key"]}, timeout=30)
    r.raise_for_status()
    for v in r.json()["voices"]:
        print(f"{v['voice_id']}  {v['name']:<20} {v.get('category', '')}  {v.get('labels', {})}")
