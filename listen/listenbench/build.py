"""Builds the test clips and their exact ground truth.

Assets (cached in listen/assets/, generated once):
  speech   the audio benchmark's S1 clips (reused, free); TTS only if they are missing
  dialog   two-voice dialogue turns (ElevenLabs TTS)
  sfx      six sound events + two background beds (ElevenLabs sound effects)
Clips (listen/clips/*.wav, 16 kHz mono) are then mixed locally, so every timestamp is known to the sample.
"""
import json
import math
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import requests
import soundfile as sf
import yaml
from dotenv import load_dotenv

from . import data

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.elevenlabs.io/v1"
FAKE = os.getenv("LISTENBENCH_FAKE") == "1"
WORK = Path(os.getenv("LISTENBENCH_HOME", ROOT))   # tests point this at a temp folder
ASSETS, CLIPS = WORK / "assets", WORK / "clips"


def load_config(path=None):
    load_dotenv(ROOT.parent / ".env")
    cfg = yaml.safe_load(open(path or ROOT / "config.yaml"))
    cfg["api_key"] = os.getenv(cfg["api_key_env"], "")
    return cfg


# ---------------------------------------------------------------- credits
def ledger(kind, credits, note=""):
    with open(WORK / "ledger.jsonl", "a") as f:
        f.write(json.dumps(dict(kind=kind, credits=credits, note=note, ts=datetime.now(timezone.utc).isoformat())) + "\n")


def spent():
    p = WORK / "ledger.jsonl"
    return sum(json.loads(l)["credits"] for l in open(p) if l.strip()) if p.exists() else 0.0


def now_ms():
    return int(time.time() * 1000)


def balance(cfg):
    """(credits used this billing period, credit limit) from the account."""
    r = requests.get(f"{API}/user/subscription", headers={"xi-api-key": cfg["api_key"]}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d.get("character_count", 0), d.get("character_limit", 0)


def usage_since(cfg, start_ms):
    """Credits charged since start_ms, per product ("TTS", "STT", "Sound Effects"), from the usage API.
    Unlike the account's running total, this filters by exact time, so earlier work is not mixed in."""
    if FAKE:
        return {}
    r = requests.get(f"{API}/usage/character-stats", headers={"xi-api-key": cfg["api_key"]}, timeout=30,
                     params=dict(start_unix=start_ms, end_unix=now_ms() + 3_600_000,
                                 breakdown_type="product_type", aggregation_interval="cumulative"))
    r.raise_for_status()
    return {k: sum(v) for k, v in r.json().get("usage", {}).items() if sum(v)}


def measure(cfg, start_ms, products, wait_s=240, every_s=20):
    """ElevenLabs reports usage a few minutes late, so a reading taken right after the calls can be 0.
    Poll until every product we used shows up and two readings agree. Returns (usage, settled)."""
    last, t0 = None, time.time()
    while True:
        try:
            u = usage_since(cfg, start_ms)
        except requests.RequestException as e:
            print(f"  Could not read ElevenLabs usage ({e}).")
            return {}, False
        if all(u.get(p, 0) > 0 for p in products) and u == last:
            return u, True
        if time.time() - t0 > wait_s:
            return u, False
        if last is None:
            print(f"  Waiting for ElevenLabs to report the usage (it lags by a few minutes; up to {wait_s // 60} min)...")
        last = u
        time.sleep(every_s)


def fmt_usage(u):
    return ", ".join(f"{k} {v:,.0f}" for k, v in sorted(u.items())) or "nothing yet"


# ---------------------------------------------------------------- audio helpers
def load(path, sr):
    import librosa
    y, _ = librosa.load(str(path), sr=sr, mono=True)
    return y.astype(np.float32)


def trim(y, top_db=35):
    import librosa
    t, _ = librosa.effects.trim(y, top_db=top_db)
    return t


def rms(y):
    return float(np.sqrt(np.mean(np.square(y)) + 1e-12))


def _post(cfg, url, body):
    headers = {"xi-api-key": cfg["api_key"], "Content-Type": "application/json"}
    for attempt in range(5):
        r = requests.post(url, json=body, headers=headers, timeout=180)
        if r.status_code == 200:
            return r.content
        if r.status_code in (429, 500, 502, 503):
            time.sleep(2 ** attempt); continue
        raise SystemExit(f"ElevenLabs HTTP {r.status_code} for {url.split('/v1/')[1][:40]}: {r.text[:300]}")
    raise SystemExit("ElevenLabs kept failing (rate limit or server error). Try again later.")


def _fake_audio(seconds, kind, sr):
    rnd = np.random.default_rng(abs(hash(kind)) % 2**32)
    t = np.arange(int(seconds * sr)) / sr
    if kind == "speech":   # syllable-like bursts
        env = (np.sin(2 * np.pi * 3 * t) > 0).astype(np.float32)
        return (0.3 * env * np.sin(2 * np.pi * 180 * t)).astype(np.float32)
    return (0.2 * rnd.standard_normal(len(t))).astype(np.float32)


def tts(cfg, text, voice, out):
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        if FAKE:
            sf.write(out.with_suffix(".wav"), _fake_audio(len(text) / 15, "speech", cfg["sample_rate"]), cfg["sample_rate"])
            return out.with_suffix(".wav")
        audio = _post(cfg, f"{API}/text-to-speech/{voice}?output_format=mp3_44100_128",
                      {"text": text, "model_id": cfg["tts_model"], "seed": cfg["seed"],
                       "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}})
        out.write_bytes(audio)
        ledger("tts", len(text) * cfg["tts_credits_per_char"], out.name)
    return out


def sfx(cfg, key, prompt, seconds, out):
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        if FAKE:
            sf.write(out.with_suffix(".wav"), _fake_audio(seconds, key, cfg["sample_rate"]), cfg["sample_rate"])
            return out.with_suffix(".wav")
        audio = _post(cfg, f"{API}/sound-generation?output_format=mp3_44100_128",
                      {"text": prompt, "duration_seconds": seconds, "prompt_influence": 0.6,
                       "model_id": cfg["sfx_model"]})
        out.write_bytes(audio)
        ledger("sfx", cfg["sfx_credits_est"], out.name)
    return out


def _existing(p):
    for q in (p, p.with_suffix(".wav")):
        if q.exists():
            return q
    return None


# ---------------------------------------------------------------- plan / cost
def asset_plan(cfg):
    """What still has to be generated: list of (kind, description, est. credits)."""
    todo = []
    src = (ROOT / cfg["speech_source"]).resolve()
    for i, s in enumerate(data.SENTENCES):
        if not (src / f"S1-{i:02d}_r0.mp3").exists() and not _existing(ASSETS / "speech" / f"S1-{i:02d}.mp3"):
            todo.append(("tts", f"S1-{i:02d}", len(s) * cfg["tts_credits_per_char"]))
    for d, turns in enumerate(data.DIALOGUES):
        for t, s in enumerate(turns):
            if not _existing(ASSETS / "dialog" / f"D{d}_t{t}.mp3"):
                todo.append(("tts", f"D{d}_t{t}", len(s) * cfg["tts_credits_per_char"]))
    for key, *_ in data.EVENTS + data.BEDS:
        if not _existing(ASSETS / "sfx" / f"{key}.mp3"):
            todo.append(("sfx", key, cfg["sfx_credits_est"]))
    return todo


# ---------------------------------------------------------------- build
def build(cfg, yes=False):
    sr = cfg["sample_rate"]
    todo = asset_plan(cfg)
    est = sum(t[2] for t in todo)
    print(f"Assets to generate: {len(todo)} ({sum(t[0] == 'tts' for t in todo)} speech, "
          f"{sum(t[0] == 'sfx' for t in todo)} sound effects), estimated {est:,.0f} credits. "
          f"Already spent by this benchmark: {spent():,.0f} (cap {cfg['max_credits']:,}).")
    if todo and not FAKE:
        if not cfg["api_key"]:
            raise SystemExit("No ELEVENLABS_API_KEY in the repo's .env file.")
        if spent() + est > cfg["max_credits"]:
            raise SystemExit("Would exceed max_credits in listen/config.yaml.")
        if not yes and input("Proceed? [y/N] ").strip().lower() != "y":
            raise SystemExit("Cancelled.")
    start = now_ms()

    src = (ROOT / cfg["speech_source"]).resolve()
    speech = []
    for i, s in enumerate(data.SENTENCES):
        p = src / f"S1-{i:02d}_r0.mp3"
        if not p.exists():
            p = _existing(ASSETS / "speech" / f"S1-{i:02d}.mp3") or tts(cfg, s, cfg["voice_a"], ASSETS / "speech" / f"S1-{i:02d}.mp3")
        speech.append(trim(load(p, sr)))
    dialog = [[trim(load(_existing(ASSETS / "dialog" / f"D{d}_t{t}.mp3") or
                         tts(cfg, s, cfg["voice_a"] if t % 2 == 0 else cfg["voice_b"], ASSETS / "dialog" / f"D{d}_t{t}.mp3"), sr))
               for t, s in enumerate(turns)] for d, turns in enumerate(data.DIALOGUES)]
    snd = {}
    for key, prompt, secs, *_ in data.EVENTS + data.BEDS:
        p = _existing(ASSETS / "sfx" / f"{key}.mp3") or sfx(cfg, key, prompt, secs, ASSETS / "sfx" / f"{key}.mp3")
        y = load(p, sr)
        snd[key] = trim(y, top_db=40) if key in dict((e[0], 1) for e in data.EVENTS) else y
    if todo and not FAKE:
        products = {"TTS" if t[0] == "tts" else "Sound Effects" for t in todo}
        u, settled = measure(cfg, start, products)
        ledger("measured_build", 0, f"usage API: {fmt_usage(u)} for {len(todo)} assets (estimate {est:.0f})"
                                    + ("" if settled else " [not final]"))
        print(f"Real ElevenLabs usage for the build: {fmt_usage(u)} (estimate was {est:,.0f}).")
        if not settled:
            print("  ElevenLabs had not finished reporting it. Check later with: python -m listenbench credits")

    CLIPS.mkdir(exist_ok=True)
    rnd = random.Random(cfg["seed"])
    man = []

    def write(uid, y, **gt):
        peak = float(np.max(np.abs(y))) if len(y) else 0
        if peak > 0.95:
            y = y * (0.95 / peak)
        sf.write(CLIPS / f"{uid}.wav", y.astype(np.float32), sr, subtype="PCM_16")
        man.append(dict(uid=uid, duration=round(len(y) / sr, 3), **gt))

    def bed_segment(key, n, start):
        b = snd[key]
        reps = int(math.ceil((start + n) / len(b))) + 1
        return np.tile(b, reps)[start:start + n]

    # L1 (+ L2 timestamps): every sentence under every acoustic condition, same placement across conditions
    for i, y in enumerate(speech):
        lead, trail = rnd.uniform(0.5, 2.5), 3.0
        n_lead, n_trail = int(lead * sr), int(trail * sr)
        clean = np.concatenate([np.zeros(n_lead), y, np.zeros(n_trail)]).astype(np.float32)
        offs = {b[0]: rnd.randrange(0, int(10 * sr)) for b in data.BEDS}
        for cond, bed, snr in data.CONDITIONS:
            mix = clean.copy()
            if bed:
                noise = bed_segment(bed, len(clean), offs[bed])
                gain = rms(y) / (rms(noise) * 10 ** (snr / 20))
                mix = mix + gain * noise
            write(f"L1-S1-{i:02d}-{cond}", mix, suite="L1", item=f"S1-{i:02d}", condition=cond,
                  reference=data.SENTENCES[i], speech_start=round(lead, 3), speech_end=round(lead + len(y) / sr, 3),
                  event=None, turns=None)

    # L3: clips with no speech at all (any word is a hallucination)
    events = {e[0]: e for e in data.EVENTS}
    for suffix, kind, secs in data.NONSPEECH:
        if kind == "silence":
            y = np.zeros(int(secs * sr))
        elif kind == "hum":
            t = np.arange(int(secs * sr)) / sr
            y = 0.05 * (np.sin(2 * np.pi * 60 * t) + 0.5 * np.sin(2 * np.pi * 120 * t))
        elif kind == "white":
            y = 0.03 * np.random.default_rng(cfg["seed"]).standard_normal(int(secs * sr))
        elif kind in ("cafe", "street"):
            y = 0.3 * bed_segment(kind, int(secs * sr), rnd.randrange(0, int(5 * sr))) / max(1e-6, rms(snd[kind])) * 0.1
        else:
            y = np.concatenate([np.zeros(sr), snd[kind], np.zeros(2 * sr)])
        ev = None if kind not in events else dict(key=kind, start=1.0, end=round(1.0 + len(snd[kind]) / sr, 3),
                                                  keywords=events[kind][3])
        write(f"L3-{suffix}", y, suite="L3", item=suffix, condition=kind, reference="",
              speech_start=None, speech_end=None, event=ev, turns=None)

    # L4: a sentence plus one sound event, before or after the speech
    for k, (key, _, _, kws) in enumerate(data.EVENTS):
        for j, where in enumerate(("before", "after")):
            idx = (2 * k + j) % len(speech)
            sp, ev = speech[idx], snd[key] * (rms(speech[idx]) / max(1e-6, rms(snd[key])))
            lead, gap = int(1.0 * sr), int(0.7 * sr)
            parts = [np.zeros(lead)] + ([ev, np.zeros(gap), sp] if where == "before" else [sp, np.zeros(gap), ev]) + [np.zeros(2 * sr)]
            y = np.concatenate(parts)
            if where == "before":
                e0, s0 = 1.0, 1.0 + (len(ev) + gap) / sr
            else:
                s0, e0 = 1.0, 1.0 + (len(sp) + gap) / sr
            write(f"L4-{key}-{where}", y, suite="L4", item=f"{key}-{where}", condition=where,
                  reference=data.SENTENCES[idx], speech_start=round(s0, 3), speech_end=round(s0 + len(sp) / sr, 3),
                  event=dict(key=key, start=round(e0, 3), end=round(e0 + len(ev) / sr, 3), keywords=kws), turns=None)

    # L5: two-speaker dialogues
    for d, turns in enumerate(dialog):
        t, parts, gt = 0.8, [np.zeros(int(0.8 * sr))], []
        for j, y in enumerate(turns):
            gt.append(dict(speaker="A" if j % 2 == 0 else "B", start=round(t, 3), end=round(t + len(y) / sr, 3),
                           text=data.DIALOGUES[d][j]))
            parts += [y, np.zeros(int(0.4 * sr))]
            t += len(y) / sr + 0.4
        parts.append(np.zeros(2 * sr))
        write(f"L5-D{d}", np.concatenate(parts), suite="L5", item=f"D{d}", condition="dialogue",
              reference=" ".join(data.DIALOGUES[d]), speech_start=gt[0]["start"], speech_end=gt[-1]["end"],
              event=None, turns=gt)

    with open(CLIPS / "manifest.jsonl", "w") as f:
        for m in man:
            f.write(json.dumps(m) + "\n")
    (WORK / "results").mkdir(exist_ok=True)
    (WORK / "results" / "manifest.jsonl").write_text((CLIPS / "manifest.jsonl").read_text())
    mins = sum(m["duration"] for m in man) / 60
    print(f"Built {len(man)} clips ({mins:.1f} minutes of audio) in listen/clips/. Ground truth: listen/results/manifest.jsonl")
    return man


def manifest():
    p = CLIPS / "manifest.jsonl"
    if not p.exists():
        raise SystemExit("No clips yet. Run: python -m listenbench build")
    return [json.loads(l) for l in open(p)]
