"""Adds AgentRouter models to your opencode config by copying the working gpt-5.6-sol entry.
Makes a backup first (opencode.json.bak). Never prints your API key.

Usage (PowerShell):  python add_opencode_models.py
"""
import copy
import json
import shutil
import sys
from pathlib import Path

NEW_MODELS = ["gpt-6.1-sol", "gpt-6.2-sol", "gpt-6-astra", "claude-opus-5-5"]
TEMPLATE = "gpt-5.6-sol"

candidates = [Path.home() / ".config" / "opencode" / n for n in ("opencode.json", "opencode.jsonc")]
path = next((p for p in candidates if p.exists()), None)
if not path:
    sys.exit("Could not find ~/.config/opencode/opencode.json. Tell Claude where your opencode config is.")

text = path.read_text(encoding="utf-8")
try:
    cfg = json.loads(text)
except json.JSONDecodeError as e:
    sys.exit(f"{path} is not plain JSON (it may contain comments): {e}. Add the models by hand instead.")

providers = cfg.get("provider") or cfg.get("providers") or {}
ar = providers.get("agentrouter")
if not ar:
    sys.exit(f"No 'agentrouter' provider found in {path}. Provider names found: {list(providers)}")
models = ar.get("models")
if not isinstance(models, dict) or TEMPLATE not in models:
    sys.exit(f"'{TEMPLATE}' not found under agentrouter models. Models found: {list(models or {})}")

added = []
for mid in NEW_MODELS:
    if mid in models:
        continue
    entry = copy.deepcopy(models[TEMPLATE])
    if isinstance(entry, dict):
        if "name" in entry:
            entry["name"] = mid
        for key in ("id", "modelID", "model"):
            if key in entry:
                entry[key] = mid
    models[mid] = entry
    added.append(mid)

if not added:
    print("All models were already present. Nothing changed.")
    sys.exit(0)

shutil.copy(path, path.with_name(path.name + ".bak"))
path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Added to {path}: {', '.join(added)}")
print(f"Backup saved as {path.name}.bak. Now test, for example:")
print('  opencode run -m agentrouter/gpt-6.1-sol "Reply with the single word: ready"')
