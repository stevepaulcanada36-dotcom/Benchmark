"""Runs every clip through every system and saves the raw output (resumable).

Output per call: text, words [{text, start, end, speaker}], events [{text, start, end}].
Scribe: ElevenLabs speech-to-text (diarization + audio-event tags on). Whisper: faster-whisper, local.
"""
import json
import math
import random
import re
import time
from datetime import datetime, timezone

import requests

from .build import API, CLIPS, FAKE, WORK, fmt_usage, ledger, manifest, measure, now_ms, spent

BRACKET = re.compile(r"^[\[\(].*[\]\)]$")


def out_path(system):
    d = WORK / "outputs"
    d.mkdir(exist_ok=True)
    return d / f"{system['name']}.jsonl"


def done(system):
    p = out_path(system)
    if not p.exists():
        return {}
    recs = {}
    for l in open(p, encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            recs[(r["uid"], r["run"])] = r
    return recs


def select(cfg, pilot):
    man = manifest()
    if not pilot:
        return man
    rnd, out = random.Random(cfg["seed"]), []
    for s in ("L1", "L3", "L4", "L5"):
        g = [m for m in man if m["suite"] == s]
        out += rnd.sample(g, max(2, round(len(g) * cfg["pilot_fraction"])))
    return out


# ---------------------------------------------------------------- Scribe
def scribe(cfg, system, clip, run):
    with open(CLIPS / f"{clip['uid']}.wav", "rb") as fh:
        body = fh.read()
    form = {"model_id": system["model_id"], "language_code": "en", "diarize": "true", "tag_audio_events": "true",
            "timestamps_granularity": "word", "temperature": "0", "seed": str(cfg["seed"])}
    for attempt in range(5):
        t0 = time.time()
        r = requests.post(f"{API}/speech-to-text", headers={"xi-api-key": cfg["api_key"]}, data=form,
                          files={"file": (f"{clip['uid']}.wav", body, "audio/wav")}, timeout=300)
        if r.status_code == 200:
            j = r.json()
            words, events = [], []
            for w in j.get("words", []):
                if w.get("type") == "word":
                    words.append(dict(text=w["text"], start=w.get("start"), end=w.get("end"), speaker=w.get("speaker_id")))
                elif w.get("type") == "audio_event":
                    events.append(dict(text=w["text"], start=w.get("start"), end=w.get("end")))
            return dict(text=" ".join(w["text"] for w in words), words=words, events=events,
                        latency_s=round(time.time() - t0, 2), error=None)
        if r.status_code in (429, 500, 502, 503):
            time.sleep(2 ** attempt + 1); continue
        if r.status_code in (400, 422) and ("temperature" in form or "seed" in form) and (
                "temperature" in r.text or "seed" in r.text):
            form.pop("temperature", None); form.pop("seed", None)   # model does not accept them: record and retry
            system["sampling_controls"] = "unsupported"
            continue
        if r.status_code in (401, 403):
            raise SystemExit(f"ElevenLabs rejected the key ({r.status_code}): {r.text[:200]}")
        return dict(error=f"HTTP {r.status_code}: {r.text[:200]}")
    return dict(error="rate limited / server errors after 5 tries")


# ---------------------------------------------------------------- Whisper
_whisper = {}


def whisper(cfg, system, clip, run):
    key = system["model"]
    if key not in _whisper:
        from faster_whisper import WhisperModel
        dev = cfg.get("whisper_device", "cpu")
        _whisper[key] = WhisperModel(key, device=dev, compute_type="float16" if dev == "cuda" else "int8")
    t0 = time.time()
    segs, _ = _whisper[key].transcribe(str(CLIPS / f"{clip['uid']}.wav"), language="en", beam_size=5,
                                       temperature=0.0, condition_on_previous_text=False, word_timestamps=True,
                                       vad_filter=bool(system.get("vad")))
    words, events = [], []
    for s in segs:
        for w in s.words or []:
            t = w.word.strip()
            if not t:
                continue
            (events if BRACKET.match(t) else words).append(dict(text=t, start=round(w.start, 3), end=round(w.end, 3), speaker=None))
    return dict(text=" ".join(w["text"] for w in words), words=words, events=events,
                latency_s=round(time.time() - t0, 2), error=None)


# ---------------------------------------------------------------- fake (pipeline tests only)
def fake(cfg, system, clip, run):
    rnd = random.Random(f"{system['name']}|{clip['uid']}|{run}")
    words, events = [], []
    if clip["reference"]:
        toks = clip["reference"].split()
        noisy = "0db" in clip["condition"]
        span = (clip["speech_end"] - clip["speech_start"]) / len(toks)
        for k, t in enumerate(toks):
            if noisy and rnd.random() < 0.15:
                continue
            spk = None
            if system["kind"] == "scribe":
                spk = "speaker_0"
                if clip["turns"]:
                    mid = clip["speech_start"] + (k + 0.5) * span
                    spk = "speaker_0" if any(tr["speaker"] == "A" and tr["start"] <= mid <= tr["end"] for tr in clip["turns"]) else "speaker_1"
            st = clip["speech_start"] + k * span + (rnd.uniform(-0.3, 0.3) if system["kind"] == "whisper" else rnd.uniform(-0.05, 0.05))
            words.append(dict(text=t, start=round(st, 3), end=round(st + span, 3), speaker=spk))
    if system["kind"] == "whisper" and not system.get("vad") and clip["suite"] == "L3" and rnd.random() < 0.5:
        words.append(dict(text="Thank you.", start=0.0, end=1.0, speaker=None))
    if system["kind"] == "scribe" and clip["event"] and rnd.random() < 0.7:
        events.append(dict(text=f"({clip['event']['keywords'][0]})", start=clip["event"]["start"] + 0.1, end=clip["event"]["end"]))
    return dict(text=" ".join(w["text"] for w in words), words=words, events=events, latency_s=0.01, error=None)


def transcribe(cfg, systems, pilot=False, yes=False):
    clips = select(cfg, pilot)
    jobs = []
    for s in systems:
        prev = done(s)
        runs = 1 if pilot else s["runs"]
        jobs += [(s, c, r) for c in clips for r in range(runs) if (c["uid"], r) not in prev or prev[(c["uid"], r)].get("error")]
    paid = [j for j in jobs if j[0]["kind"] == "scribe"]
    mins = sum(c["duration"] for _, c, _ in paid) / 60
    est = mins * cfg["stt_credits_per_minute"]
    print(f"{len(jobs)} transcriptions to do ({len(paid)} paid Scribe calls, {mins:.1f} min of audio, "
          f"~{est:,.0f} credits at {cfg['stt_credits_per_minute']} credits/min; Whisper runs locally for free).")
    if not jobs:
        return
    if paid and not FAKE:
        if not cfg["api_key"]:
            raise SystemExit("No ELEVENLABS_API_KEY in the repo's .env file.")
        if spent() + est > cfg["max_credits"]:
            raise SystemExit("Would exceed max_credits in listen/config.yaml.")
    if not yes and input("Proceed? [y/N] ").strip().lower() != "y":
        raise SystemExit("Cancelled.")
    start = now_ms()
    fails, dead = 0, set()
    for k, (s, c, r) in enumerate(jobs, 1):
        if s["name"] in dead:
            continue
        fn = fake if FAKE else {"scribe": scribe, "whisper": whisper}[s["kind"]]
        rec = fn(cfg, s, c, r)
        rec.update(uid=c["uid"], run=r, system=s["name"], ts=datetime.now(timezone.utc).isoformat())
        if rec.get("error"):
            fails += 1
            print(f"  FAILED {s['name']} {c['uid']}: {rec['error']}")
            if "HTTP 422" in rec["error"] or "HTTP 404" in rec["error"]:
                dead.add(s["name"]); print(f"  Skipping {s['name']} for the rest of this run.")
        elif s["kind"] == "scribe":
            ledger("stt", c["duration"] / 60 * cfg["stt_credits_per_minute"], f"{s['name']} {c['uid']}")
        with open(out_path(s), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        if k % 20 == 0 or k == len(jobs):
            print(f"  {k}/{len(jobs)} done")
    if paid and not FAKE:
        # Only the STT line counts: TTS or sound-effect charges from an earlier build can arrive late and
        # must not be billed to Scribe. Failed calls are included in mins, so the rate errs on the high side.
        u, settled = measure(cfg, start, {"STT"})
        stt = u.get("STT", 0)
        per_min = stt / mins if mins else float("nan")
        ledger("measured_stt", 0, f"usage API: STT {stt:.0f} credits for {mins:.2f} min -> {per_min:.1f} credits/min"
                                  + ("" if settled else " [not final]"))
        if settled:
            print(f"Real Scribe usage: {stt:,.0f} credits for {mins:.1f} min of audio = {per_min:.1f} credits/min.")
            if pilot:
                print(f"Put stt_credits_per_minute: {max(1, math.ceil(per_min))} in listen/config.yaml before the main run.")
        else:
            print(f"ElevenLabs has reported {stt:,.0f} Scribe credits so far for {mins:.1f} min of audio; it may not be final.\n"
                  "  Check again in a few minutes with: python -m listenbench credits")
    print(f"Done. {fails} failed call(s); re-run to retry them.")
