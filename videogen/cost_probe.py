"""One test clip from the ElevenLabs video API, to measure the real credit cost before designing VideoGenBench.

Run from the repo root:  python videogen/cost_probe.py
Writes videogen/probe/<id>.mp4 and appends the measured cost to videogen/probe/cost_probe.jsonl.
Failed generations are not charged (ElevenLabs docs).
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
API = "https://api.elevenlabs.io/v1"
load_dotenv(ROOT.parent / ".env")
H = {"xi-api-key": os.environ["ELEVENLABS_API_KEY"]}

BODY = dict(
    model_id="veo-3.1-fast-generate-001",
    prompt=("Static close-up of a plain wooden table in a quiet, well-lit room. "
            "A pair of hands claps exactly three times, slowly, then rests on the table. No music, no speech."),
    duration_secs=4, resolution="720p", aspect_ratio="16:9",
    generate_audio=True, seed=2453, enhance_prompt=False,
)


def balance():
    d = requests.get(f"{API}/user/subscription", headers=H, timeout=30).json()
    return d.get("character_count", 0), d.get("character_limit", 0)


def usage_since(start_ms):
    r = requests.get(f"{API}/usage/character-stats", headers=H, timeout=30,
                     params=dict(start_unix=start_ms, end_unix=int(time.time() * 1000) + 3_600_000,
                                 breakdown_type="product_type", aggregation_interval="cumulative"))
    r.raise_for_status()
    return {k: sum(v) for k, v in r.json().get("usage", {}).items() if sum(v)}


def main():
    out = ROOT / "probe"
    out.mkdir(exist_ok=True)
    used0, limit = balance()
    print(f"Balance before: {limit - used0:,} credits left. Request: {json.dumps(BODY)}")
    start = int(time.time() * 1000)
    r = requests.post(f"{API}/flows/video", headers=H, json=BODY, timeout=60)
    if r.status_code != 200:
        sys.exit(f"Create failed: HTTP {r.status_code} {r.text[:500]}")
    gid = r.json()["id"]
    print(f"Generation {gid} started.")
    t0 = time.time()
    while True:
        time.sleep(10)
        g = requests.get(f"{API}/flows/video/{gid}", headers=H, timeout=30).json()
        st = g.get("status")
        print(f"  {time.time() - t0:5.0f}s  {st}")
        if st == "completed":
            break
        if st == "failed":
            sys.exit(f"Failed (not charged): {g.get('failure_reason')} {g.get('error_message')}")
        if time.time() - t0 > 900:
            sys.exit(f"Still not done after 15 min. Check later: GET /v1/flows/video/{gid}")
    gen_s = round(time.time() - t0)
    mp4 = out / f"{gid}.mp4"
    mp4.write_bytes(requests.get(g["content_url"], timeout=120).content)
    print(f"Saved {mp4} ({mp4.stat().st_size / 1e6:.1f} MB) after {gen_s}s.")

    print("Waiting for ElevenLabs to report the cost (it lags a few minutes)...")
    last, u = None, {}
    for _ in range(30):                       # up to ~10 min
        u = usage_since(start)
        if u and u == last:
            break
        last = u
        time.sleep(20)
    used1, _ = balance()
    rec = dict(ts=datetime.now(timezone.utc).isoformat(), id=gid, body=BODY, gen_seconds=gen_s,
               usage_api=u, balance_delta=used1 - used0, left=limit - used1)
    with open(out / "cost_probe.jsonl", "a") as f:
        f.write(json.dumps(rec) + "\n")
    print(f"Usage API since start: {u or 'nothing reported yet'}; account total moved {used1 - used0:,}. "
          f"Left: {limit - used1:,}.")


if __name__ == "__main__":
    main()
