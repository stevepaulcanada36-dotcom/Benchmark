"""audio-bench command line.

  python -m audiobench list-voices            # pick a voice_id for config.yaml
  python -m audiobench estimate [--pilot]     # credits needed, per model, without spending
  python -m audiobench run --pilot            # ~5% of items, 1 run (asks before spending)
  python -m audiobench score --pilot          # Whisper WER, S2 pass/fail, UTMOS, speaker similarity
  python -m audiobench report --pilot         # metrics with 95% CIs -> results/
  python -m audiobench run                    # full run (resumes; never regenerates existing clips)
  python -m audiobench listening-test         # blinded MOS + A/B page for listeners
  python -m audiobench listening-analyze      # MOS CIs, pronunciation accuracy, Bradley-Terry Elo
"""
import argparse

from . import generate, listening, metrics, report


def main():
    ap = argparse.ArgumentParser(prog="audiobench", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["list-voices", "estimate", "run", "score", "report",
                                        "listening-test", "listening-analyze"])
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--models", nargs="*", help="labels from config.yaml, e.g. v3 flash-v2.5")
    ap.add_argument("--suites", nargs="*", choices=["S1", "S2", "S3", "S4", "S5"])
    ap.add_argument("--yes", "-y", action="store_true")
    ap.add_argument("--asr-model", help="override metrics.asr_model, e.g. small for a fast CPU check")
    ap.add_argument("--n-mos", type=int, default=60)
    ap.add_argument("--n-ab", type=int, default=40)
    a = ap.parse_args()
    cfg = generate.load_config()
    if a.asr_model:
        cfg["metrics"]["asr_model"] = a.asr_model
    models = [m for m in cfg["models"] if not a.models or m["label"] in a.models]
    if a.command in ("run", "list-voices") and not cfg["api_key"] and not generate.FAKE:
        raise SystemExit("No API key. Copy .env.example to .env and set ELEVENLABS_API_KEY.")

    if a.command == "list-voices":
        generate.list_voices(cfg)
    elif a.command == "estimate":
        todo, est = generate.plan(cfg, a.pilot, models, a.suites)
        print(f"{len(todo)} clips still to generate; estimated {est:,.0f} credits.")
        for m in models:
            print(f"  {m['label']:<12} {sum(len(t[4]) * m['credits_per_char'] for t in todo if t[0] is m):>9,.0f}")
        print(f"Already spent by this benchmark: {generate.spent_so_far():,.0f} (cap {cfg['max_credits']:,}).")
    elif a.command == "run":
        generate.run(cfg, models, a.pilot, a.yes, a.suites)
    elif a.command == "score":
        metrics.compute(cfg, a.pilot)
    elif a.command == "report":
        report.write(cfg, a.pilot)
    elif a.command == "listening-test":
        listening.make(cfg, a.n_mos, a.n_ab, a.pilot)
    elif a.command == "listening-analyze":
        listening.analyze()


if __name__ == "__main__":
    main()
