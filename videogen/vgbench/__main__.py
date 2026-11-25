import argparse

from . import auto, core, rate, report


def main():
    ap = argparse.ArgumentParser(prog="vgbench", description="VideoGenBench: consistency of AI-generated video for a short game demo")
    ap.add_argument("command", choices=["plan", "generate", "import", "auto", "rate", "report"])
    ap.add_argument("folder", nargs="?", help="for import: folder of .mp4 files named as in prompts.csv")
    ap.add_argument("--model", help="for import: model name from config.yaml")
    ap.add_argument("--models", nargs="*", help="for generate: limit to these model names")
    ap.add_argument("--yes", "-y", action="store_true")
    a = ap.parse_args()
    cfg = core.load_config()
    if a.command == "plan":
        core.plan(cfg)
    elif a.command == "generate":
        core.generate(cfg, a.models, a.yes)
    elif a.command == "import":
        if not a.folder or not a.model:
            raise SystemExit("Usage: python -m vgbench import <folder> --model <name from config.yaml>")
        core.import_clips(cfg, a.folder, a.model)
    elif a.command == "auto":
        auto.run(cfg)
    elif a.command == "rate":
        rate.build(cfg)
    elif a.command == "report":
        report.report()


if __name__ == "__main__":
    main()
