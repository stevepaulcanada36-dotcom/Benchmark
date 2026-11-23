"""ListenBench command line (run from the listen/ folder).

  python -m listenbench estimate              # what build + transcribe will cost, nothing spent
  python -m listenbench build                 # sound effects + dialogues (ElevenLabs), then mixes all clips locally
  python -m listenbench transcribe --pilot    # ~10% of clips, 1 run; prints the real Scribe credits per minute
  python -m listenbench transcribe            # everything (resumes; never repeats a finished call)
  python -m listenbench report                # grades against ground truth -> results/summary.md
  python -m listenbench credits               # real ElevenLabs usage since this benchmark started, and the balance
"""
import argparse
import json
from datetime import datetime

from . import build, report, systems


def main():
    ap = argparse.ArgumentParser(prog="listenbench", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["estimate", "build", "transcribe", "report", "credits"])
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--systems", nargs="*", help="names from config.yaml, e.g. scribe-v3 whisper-v3")
    ap.add_argument("--yes", "-y", action="store_true")
    a = ap.parse_args()
    cfg = build.load_config()
    chosen = [s for s in cfg["systems"] if not a.systems or s["name"] in a.systems]

    if a.command == "estimate":
        todo = build.asset_plan(cfg)
        print(f"build: {len(todo)} assets to generate, ~{sum(t[2] for t in todo):,.0f} credits")
        try:
            man = build.manifest()
        except SystemExit:
            print("transcribe: build first to know the exact audio length (about 21 minutes of audio).")
            return
        mins = sum(m["duration"] for m in man) / 60
        for s in chosen:
            cost = mins * s["runs"] * cfg["stt_credits_per_minute"] if s["kind"] == "scribe" else 0
            print(f"transcribe {s['name']:<15} {mins * s['runs']:6.1f} min  ~{cost:,.0f} credits"
                  + ("" if s["kind"] == "scribe" else "  (local, free)"))
        print(f"Already spent by this benchmark: {build.spent():,.0f} (cap {cfg['max_credits']:,}). "
              "stt_credits_per_minute is an estimate until the pilot measures it.")
    elif a.command == "build":
        build.build(cfg, a.yes)
    elif a.command == "transcribe":
        systems.transcribe(cfg, chosen, a.pilot, a.yes)
    elif a.command == "report":
        report.write(cfg, chosen)
    elif a.command == "credits":
        credits(cfg)


def credits(cfg):
    if build.FAKE:
        print("Fake mode: nothing is spent.")
        return
    if not cfg["api_key"]:
        raise SystemExit("No ELEVENLABS_API_KEY in the repo's .env file.")
    used, limit = build.balance(cfg)
    print(f"Account: {used:,} of {limit:,} credits used this billing period ({limit - used:,} left).")
    p = build.WORK / "ledger.jsonl"
    rows = [json.loads(l) for l in open(p) if l.strip()] if p.exists() else []
    if not rows:
        print("This benchmark has not spent anything yet.")
        return
    first = rows[0]["ts"]
    start = int(datetime.fromisoformat(first).timestamp() * 1000) - 60_000
    u = build.usage_since(cfg, start)
    print(f"Real usage since this benchmark's first call ({first[:16].replace('T', ' ')} UTC): {build.fmt_usage(u)}"
          f" = {sum(u.values()):,.0f} credits. (Includes anything else this account did in that time.)")
    print(f"The benchmark's own ledger estimate: {build.spent():,.0f} credits.")
    for r in rows:
        if r["kind"].startswith("measured"):
            print(f"  {r['ts'][:16].replace('T', ' ')}  {r['kind']}: {r['note']}")


if __name__ == "__main__":
    main()
