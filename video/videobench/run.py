"""Sends each clip with its questions to each model and stores the raw answer (resumable, rate-limited)."""
import json
import os
import random
import re
import time
from datetime import datetime, timezone

import yaml
from dotenv import load_dotenv

from .scenes import CLIPS, FAKE, ROOT, WORK, manifest

PROMPT = """You are given one video clip with its audio track (if it has one).
Answer every question using ONLY what you can see and hear in this clip.
- If the clip has no audio track at all, answer "no_audio" to questions about sound.
- If the clip does not show or let you hear what a question asks about, answer "cannot_tell" (or "none" where offered).
- Do not guess events that are not in the clip.
- Times are seconds from the start of the clip.

Questions:
{questions}

Return ONLY a JSON object with one key per question id, for example:
{{"q1": {{"answer": "...", "time_s": 3.0, "evidence": "video", "confidence": 0.9}}}}
"answer": for choice questions copy one option exactly; for number/count questions give a number (or "no_audio"/"cannot_tell").
"time_s": the time in the clip that supports your answer, or null.
"evidence": one of "video", "audio", "both", "none".
"confidence": your probability (0 to 1) that the answer is correct."""


def load_config(path=None):
    load_dotenv(ROOT.parent / ".env")
    cfg = yaml.safe_load(open(path or ROOT / "config.yaml"))
    cfg["api_key"] = os.getenv(cfg["api_key_env"], "")
    return cfg


def prompt_for(clip):
    lines = []
    for qq in clip["questions"]:
        if qq["kind"] == "choice":
            lines.append(f'{qq["qid"]} (choice): {qq["text"]} Options: {", ".join(qq["options"])}')
        else:
            lines.append(f'{qq["qid"]} ({qq["kind"]}): {qq["text"]}')
    return PROMPT.format(questions="\n".join(lines))


def parse(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        j = json.loads(m.group(0))
        return j if isinstance(j, dict) else None
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------- Gemini
_client = None


class DailyQuota(Exception):
    pass


def gemini(cfg, system, clip, run):
    global _client
    from google import genai
    from google.genai import types
    if _client is None:
        _client = genai.Client(api_key=cfg["api_key"])
    data = (CLIPS / f"{clip['uid']}.mp4").read_bytes()
    part = types.Part(inline_data=types.Blob(data=data, mime_type="video/mp4"),
                      video_metadata=types.VideoMetadata(fps=system["fps"]) if system.get("fps") else None)
    conf = types.GenerateContentConfig(temperature=0, seed=cfg["seed"], max_output_tokens=cfg["max_output_tokens"],
                                       response_mime_type="application/json")
    for attempt in range(6):
        t0 = time.time()
        try:
            r = _client.models.generate_content(model=system["model"], contents=types.Content(parts=[part, types.Part(text=prompt_for(clip))]), config=conf)
            u = r.usage_metadata
            return dict(raw=r.text, latency_s=round(time.time() - t0, 2), error=None,
                        prompt_tokens=getattr(u, "prompt_token_count", None), output_tokens=getattr(u, "candidates_token_count", None),
                        served_model=getattr(r, "model_version", None))
        except Exception as e:  # noqa: BLE001 - the SDK raises several error classes
            msg = str(e)
            code = getattr(e, "code", None)
            if code == 429 or "RESOURCE_EXHAUSTED" in msg:
                if "PerDay" in msg or "per day" in msg.lower():
                    raise DailyQuota(msg[:300])
                time.sleep(min(90, 10 * 2 ** attempt)); continue
            if code in (500, 502, 503, 504) or "UNAVAILABLE" in msg:
                time.sleep(5 * 2 ** attempt); continue
            if code in (401, 403) or "API_KEY_INVALID" in msg or "PERMISSION_DENIED" in msg:
                raise SystemExit(f"Gemini rejected the key: {msg[:300]}")
            return dict(error=f"{code}: {msg[:300]}")
    return dict(error="rate limited / unavailable after 6 tries")


def fake(cfg, system, clip, run):
    rnd = random.Random(f"{system['name']}|{clip['uid']}|{run}")
    skill = 0.85 if "lite" not in system["name"] else 0.7
    ans = {}
    for qq in clip["questions"]:
        truth = qq["truth"]
        if rnd.random() < skill:
            a = truth
        elif qq["kind"] == "choice":
            a = rnd.choice(qq["options"])
        else:
            a = (truth + rnd.uniform(-4, 4)) if isinstance(truth, (int, float)) else rnd.uniform(0, 10)
        if qq["tag"] == "audio" and clip["condition"] == "video_only" and rnd.random() < 0.3:
            a = qq["options"][0] if qq["kind"] == "choice" else 3.0       # pretend to hear something
        ans[qq["qid"]] = dict(answer=a, time_s=(qq["time_truth"] or 0) + rnd.uniform(-1, 1) if qq.get("time_truth") is not None else None,
                              evidence="video", confidence=round(rnd.uniform(0.5, 1.0), 2))
    return dict(raw=json.dumps(ans), latency_s=0.01, error=None, prompt_tokens=0, output_tokens=0, served_model="fake")


# ---------------------------------------------------------------- loop
def out_path(system):
    d = WORK / "outputs"
    d.mkdir(exist_ok=True)
    return d / f"{system['name'].replace('@', '_at_')}.jsonl"


def done(system):
    p = out_path(system)
    recs = {}
    if p.exists():
        for l in open(p, encoding="utf-8"):
            if l.strip():
                r = json.loads(l)
                recs[(r["uid"], r["run"])] = r
    return recs


def select(cfg, pilot):
    man = manifest()
    if not pilot:
        return man
    cids = sorted({m["cid"] for m in man if not m["suite"].startswith("long")})
    keep = set(random.Random(cfg["seed"]).sample(cids, min(cfg["pilot_scenes"], len(cids))))
    return [m for m in man if m["cid"] in keep]


def run(cfg, systems, pilot=False, yes=False):
    clips = select(cfg, pilot)
    jobs = []
    for s in systems:
        prev = done(s)
        for c in clips:
            for r in range(1 if pilot else s["runs"]):
                old = prev.get((c["uid"], r))
                if old is None or old.get("error"):
                    jobs.append((s, c, r))
    mins = len(jobs) / cfg["requests_per_minute"]
    print(f"{len(jobs)} requests to send ({len(clips)} clips). Free tier: $0. At {cfg['requests_per_minute']}/min "
          f"this takes about {mins:.0f} minutes.")
    if not jobs:
        return
    if not FAKE and not cfg["api_key"]:
        raise SystemExit("No GEMINI_API_KEY in the repo's .env. Get a free key at https://aistudio.google.com/apikey")
    if not yes and input("Proceed? [y/N] ").strip().lower() != "y":
        raise SystemExit("Cancelled.")
    gap, last, fails = 60.0 / cfg["requests_per_minute"], 0.0, 0
    exhausted = set()                  # models at their daily free quota; the quota is per model, so skip only those
    for k, (s, c, r) in enumerate(jobs, 1):
        if s["model"] in exhausted:
            continue
        if not FAKE:
            time.sleep(max(0.0, gap - (time.time() - last)))
            last = time.time()
        try:
            rec = fake(cfg, s, c, r) if FAKE else gemini(cfg, s, c, r)
        except DailyQuota as e:
            exhausted.add(s["model"])
            print(f"  Daily free-tier quota reached for {s['model']}: skipping it for the rest of this run ({str(e)[:120]}).")
            continue
        rec.update(uid=c["uid"], run=r, system=s["name"], model=s["model"], fps=s.get("fps"),
                   ts=datetime.now(timezone.utc).isoformat())
        if rec.get("error"):
            fails += 1
            print(f"  FAILED {s['name']} {c['uid']}: {rec['error']}")
        else:
            rec["parsed"] = parse(rec["raw"])
        with open(out_path(s), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        if k % 10 == 0 or k == len(jobs):
            print(f"  {k}/{len(jobs)} done")
    if exhausted:
        left = sum(s["model"] in exhausted for s, _, _ in jobs)
        print(f"Out of daily quota: {', '.join(sorted(exhausted))} ({left} requests not sent). "
              "Run the same command tomorrow; finished requests are kept.")
    print(f"Done. {fails} failed request(s); re-run to retry them.")


def check_models(cfg, systems):
    """One tiny real request per model: does it accept video with audio and return JSON?"""
    clip = next(m for m in manifest() if m["condition"] == "av" and m["suite"] == "halluc")
    for s in systems:
        rec = fake(cfg, s, clip, 0) if FAKE else gemini(cfg, s, clip, 0)
        if rec.get("error"):
            print(f"  {s['name']:<24} FAILED: {rec['error'][:150]}")
        else:
            ok = parse(rec["raw"]) is not None
            print(f"  {s['name']:<24} OK  (valid JSON: {ok}; prompt tokens {rec.get('prompt_tokens')}; served {rec.get('served_model')})")
