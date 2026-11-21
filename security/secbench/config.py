import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"          # raw model outputs (gitignored: may contain harmful text)
RESULTS = ROOT / "results"      # aggregated, shareable results
LABELS = ROOT / "labels"        # human labelling files


def load_config(path=None):
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT.parent / ".env")   # repo-level .env
    with open(path or ROOT / "config.yaml") as f:
        cfg = yaml.safe_load(f)
    p = cfg["provider"]
    cfg["provider"]["base_url"] = os.getenv(p["base_url_env"], "https://agentrouter.org/v1")
    cfg["provider"]["api_key"] = os.getenv(p["api_key_env"], "")
    for d in (DATA, OUT, RESULTS, LABELS):
        d.mkdir(exist_ok=True)
    return cfg
