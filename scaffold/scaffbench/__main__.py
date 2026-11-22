"""Scaffold benchmark: does the agent harness change how easily a model is hijacked by prompt injection?

  python -m scaffbench show                    # list items and scaffolds (no calls)
  python -m scaffbench check                   # 1 tiny call per model: opencode + AgentRouter work?
  python -m scaffbench run --pilot             # ~8 items x all scaffolds x 1 run
  python -m scaffbench run                     # full run (resumes; never repeats finished runs)
  python -m scaffbench report [--pilot]        # results/summary_*.md, CSVs, plot
"""
import argparse
import subprocess

from . import report, run
from .tasks import build_items


def main():
    ap = argparse.ArgumentParser(prog="scaffbench", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["show", "check", "run", "report"])
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--models", nargs="*", help="labels from config.yaml")
    ap.add_argument("--scaffolds", nargs="*", help="names from config.yaml, e.g. S0_pasted S3_auto_guard")
    ap.add_argument("--yes", "-y", action="store_true")
    ap.add_argument("--config")
    a = ap.parse_args()
    cfg = run.load_config(a.config)
    models = [m for m in cfg["models"] if not a.models or m["label"] in a.models]
    scaffolds = [s for s in cfg["scaffolds"] if not a.scaffolds or s["name"] in a.scaffolds]

    if a.command == "show":
        items = build_items(cfg["seed"])
        print(f"{len(items)} items ({sum(i['injected'] for i in items)} injected, {sum(1 - i['injected'] for i in items)} clean)")
        for s in scaffolds:
            print(f"  scaffold {s['name']}: {s['description']}")
        ex = next(i for i in items if i["uid"] == "T3_notes|G1_canary|visible")
        print("\nExample poisoned file (meeting_notes.md):\n" + ex["files"]["meeting_notes.md"])
    elif a.command == "check":
        exe = run.resolve_executable(cfg["client"]["command"][0])
        print("Using client program:", exe)
        for m in models:
            full = m["id"] if "/" in m["id"] else f"{cfg['client']['provider']}/{m['id']}"
            p = subprocess.run([exe, "run", "--model", full, "Reply with the single word: ready"], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=180, stdin=subprocess.DEVNULL)
            text = run.clean_text(run.ANSI.sub("", p.stdout))
            ok = "ready" in text.lower()
            print(f"{m['label']:>10}  {full}: {'OK' if ok else 'FAILED'}  {(text or p.stderr)[-160:].strip()!r}")
    elif a.command == "run":
        run.run(cfg, models, scaffolds, a.pilot, a.yes)
    elif a.command == "report":
        report.write(cfg, a.pilot)


if __name__ == "__main__":
    main()
