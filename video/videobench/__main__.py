"""VideoBench command line (run from the video/ folder).

  python -m videobench build            # renders all clips locally (free; needs ListenBench's sound effects)
  python -m videobench check-models     # one request per model: does it take video+audio and return JSON?
  python -m videobench run --pilot      # 4 scenes x 4 audio conditions, 1 run
  python -m videobench run              # everything (resumes; stops cleanly at the daily free quota)
  python -m videobench report           # results/summary.md, metrics.csv, pairwise.csv, plot.png
"""
import argparse

from . import report, run, scenes


def main():
    ap = argparse.ArgumentParser(prog="videobench", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["build", "check-models", "run", "report"])
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--systems", nargs="*", help="names from config.yaml")
    ap.add_argument("--yes", "-y", action="store_true")
    a = ap.parse_args()
    cfg = run.load_config()
    chosen = [s for s in cfg["systems"] if not a.systems or s["name"] in a.systems]
    if a.command == "build":
        scenes.build(cfg)
    elif a.command == "check-models":
        run.check_models(cfg, chosen)
    elif a.command == "run":
        run.run(cfg, chosen, a.pilot, a.yes)
    elif a.command == "report":
        report.write(cfg, chosen)


if __name__ == "__main__":
    main()
