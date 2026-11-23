"""Restores the GPT-5.6 scaffold results from git commit 22a950d (the raw GPT-5.6 file was deleted later)
and writes combined GPT-5.6 + GPT-6.1 results. Run from the repo root:  python restore_scaffold_gpt56.py
"""
import io
import subprocess
from pathlib import Path

import pandas as pd

COMMIT = "22a950d"
R = Path("scaffold/results")


def old(path):
    return subprocess.check_output(["git", "show", f"{COMMIT}:{path}"], text=True, encoding="utf-8")


# 1. keep both per-model summaries side by side
(R / "summary_main_GPT-5.6.md").write_text(old("scaffold/results/summary_main.md"), encoding="utf-8")
(R / "summary_main_GPT-6.1.md").write_text((R / "summary_main.md").read_text(encoding="utf-8"), encoding="utf-8")

# 2. combined CSVs (metrics, pairwise scaffold tests, attacks to review by hand)
for name in ("metrics_main.csv", "pairwise_main.csv", "review_attacks_main.csv"):
    a = pd.read_csv(io.StringIO(old(f"scaffold/results/{name}")))
    b = pd.read_csv(R / name)
    model_col = "model_label" if "model_label" in b.columns else "model"
    a = a[a[model_col] == "GPT-5.6"]
    b = b[b[model_col] != "GPT-5.6"]
    pd.concat([a, b], ignore_index=True).to_csv(R / name.replace("_main", "_combined"), index=False)

# 3. one combined headline table
m = pd.read_csv(R / "metrics_combined.csv")
keep = ["attack_success", "injection_flagged", "utility_clean", "utility_under_attack", "gateway_block_rate"]
t = m[m.metric.isin(keep)].copy()
t["value"] = t.apply(lambda r: f"{100*r.estimate:.1f}% ({100*r.ci_low:.1f}-{100*r.ci_high:.1f})", axis=1)
wide = t.pivot_table(index=["metric", "model"], columns="scaffold", values="value", aggfunc="first")
lines = ["# Scaffold benchmark: combined results (GPT-5.6 + GPT-6.1)", "",
         "Each cell: estimate (95% CI), cluster bootstrap over items. GPT-5.6 restored from commit 22a950d.", "",
         wide.to_markdown(), ""]
(R / "summary_combined.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
print("Wrote scaffold/results/summary_combined.md, metrics/pairwise/review_attacks_combined.csv,"
      " summary_main_GPT-5.6.md and summary_main_GPT-6.1.md")
