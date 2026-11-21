"""security-bench command line.

  python -m secbench download                 # fetch XSTest + StrongREJECT CSVs
  python -m secbench check-models             # confirm model IDs and that each answers
  python -m secbench run   --suite D --pilot  # generate responses (pilot = ~5% of items, 1 run)
  python -m secbench judge --suite D --pilot  # grade them (regex for D, LLM judge for A-C)
  python -m secbench report --pilot           # metrics with 95% CIs -> results/
  python -m secbench all --pilot              # run + judge every suite, then report
  python -m secbench label-sample             # blinded CSVs for two human labellers
  python -m secbench agreement                # kappa + judge precision/recall -> judge-corrected CIs
"""
import argparse

from . import labels, report, runner, suites
from .client import ChatClient
from .config import load_config


def check_models(client, cfg, models):
    try:
        available = client.list_models()
        print("Models listed by the endpoint:", ", ".join(available))
    except Exception as e:  # noqa: BLE001
        available = None
        print("Could not list models:", e)
    ok = True
    for m in models + [{"id": cfg["judge"]["model"], "label": "judge"}]:
        r = client.chat(m["id"], [{"role": "user", "content": "Reply with the single word: ready"}], max_tokens=20)
        status = "OK" if not r["error"] else f"FAILED: {r['error'][:200]}"
        ok &= not r["error"]
        listed = "" if available is None else (" (listed)" if m["id"] in available else " (NOT in list)")
        print(f"{m['label']:>10}  {m['id']}{listed}: {status}  -> {r['text'][:40]!r} served_by={r['served_model']}")
    return ok


def main():
    ap = argparse.ArgumentParser(prog="secbench", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["download", "check-models", "run", "judge", "report", "all",
                                        "label-sample", "agreement", "show-items"])
    ap.add_argument("--suite", choices=list("ABCD"), help="suite to run/judge")
    ap.add_argument("--pilot", action="store_true", help="~5%% of items, 1 run; stored separately")
    ap.add_argument("--models", nargs="*", help="labels from config.yaml to restrict to, e.g. Claude DeepSeek")
    ap.add_argument("--yes", "-y", action="store_true", help="skip the confirmation prompt")
    ap.add_argument("--config", help="alternative config file")
    a = ap.parse_args()
    cfg = load_config(a.config)
    models = [m for m in cfg["models"] if not a.models or m["label"] in a.models]

    if a.command == "download":
        suites.download()
    elif a.command == "show-items":
        for it in suites.build(cfg, a.suite or "D", a.pilot)[:5]:
            print(it["uid"], "|", it["messages"][-1]["content"][:120].replace("\n", " "))
    elif a.command == "check-models":
        client = ChatClient(cfg)
        if not check_models(client, cfg, models):
            raise SystemExit("Fix the failing lines above (key, base URL or model ID) before running suites.")
    elif a.command in ("run", "judge"):
        if not a.suite:
            ap.error("--suite is required")
        client = ChatClient(cfg)
        (runner.generate(client, cfg, a.suite, models, a.pilot, a.yes) if a.command == "run"
         else runner.judge(client, cfg, a.suite, a.pilot, a.yes))
    elif a.command == "all":
        client = ChatClient(cfg)
        if not check_models(client, cfg, models):
            raise SystemExit("Stopped before spending anything: fix the failing lines above first.")
        for s in (a.suite and [a.suite]) or ["D", "C", "A", "B"]:
            runner.generate(client, cfg, s, models, a.pilot, a.yes)
            runner.judge(client, cfg, s, a.pilot, a.yes)
        report.write(a.pilot)
    elif a.command == "report":
        report.write(a.pilot)
    elif a.command == "label-sample":
        labels.make_sample(cfg, pilot=a.pilot)
    elif a.command == "agreement":
        labels.agreement()


if __name__ == "__main__":
    main()
