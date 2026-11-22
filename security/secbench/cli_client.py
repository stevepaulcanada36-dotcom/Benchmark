"""Runs prompts through a supported coding-agent CLI (default: plain opencode) instead of calling the API.

Why: AgentRouter only serves whitelisted clients (claude-code, codex, opencode, cline, ...). Our script
must not pretend to be one of them, so it runs the real client in non-interactive mode, once per prompt.

What changes scientifically: the client adds its own system prompt and its own sampling settings, so
results describe "model X inside client Y", not the bare model. Say so in the write-up.

Suite D (secret leakage): the system instructions are written to AGENTS.md in a fresh, empty folder
outside the repo, which opencode loads as project instructions. That is a realistic leak scenario for
coding agents (secrets in instruction files).
"""
import json
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# AgentRouter quota release times (from its System Notice): Claude and GPT batches at 02:00 and 11:00 UTC
# (10:00 and 19:00 Beijing). DeepSeek and gpt-6.1-sol were announced as unlimited.
RELEASES_UTC = [2, 11]

SANDBOX_CONFIG = {"$schema": "https://opencode.ai/config.json",
                  "permission": {"edit": "deny", "bash": "deny", "webfetch": "deny"}}


def next_releases(n=3):
    now = datetime.now(timezone.utc)
    out, day = [], now.replace(minute=0, second=0, microsecond=0)
    while len(out) < n:
        for h in RELEASES_UTC:
            t = day.replace(hour=h)
            if t > now and len(out) < n:
                out.append(t)
        day = (day + timedelta(days=1)).replace(hour=0)
    return [t.astimezone() for t in out]


def releases_text():
    lines = ["AgentRouter quota batches for Claude/GPT (02:00 and 11:00 UTC = 10:00 and 19:00 Beijing):"]
    for t in next_releases():
        lines.append(f"  {t:%a %d %b %H:%M} your local time ({t.tzname()})")
    lines.append("First come, first served: start right after a release. DeepSeek and gpt-6.1-sol are announced as unlimited.")
    return "\n".join(lines)


def final_error(err, out):
    """opencode ends a failed run with its own 'Error: ...' as the LAST line it prints. Everything before it can be
    tool activity (web searches, PowerShell output, a website's 403), which must never be read as an AgentRouter
    error. Return that final line, or '' if the run did not end with one."""
    for stream in (err, out):
        lines = [l.strip() for l in ANSI.sub("", stream or "").splitlines() if l.strip()]
        if lines and lines[-1].lower().startswith("error"):
            return lines[-1]
    return ""


def classify(text, returncode):
    """text = final_error(...). No final error line: ok if exit code 0, else a plain retryable error."""
    t = (text or "").strip().lower()
    if not t:
        return ("ok", None) if returncode == 0 else ("error", None)
    if "token quota is not enough" in t or "remain quota" in t or "insufficient balance" in t or "余额不足" in t:
        return "quota", 402
    # AgentRouter also answers in Chinese: 敏感词 = sensitive words, 额度/配额 = quota, 无可用渠道 = no channel
    if ("content-blocked" in t or "content blocked" in t or "sensitive words" in t or "敏感词" in t
            or "provider blocked" in t):
        return "blocked", 400
    if "free usage limit" in t or "usage limit reached" in t:
        return "quota", 402
    if ("402" in t and "quota" in t) or "budget pool" in t or (("额度" in t or "配额" in t) and ("用尽" in t or "不足" in t)):
        return "quota", 402
    if "无可用渠道" in t or "no available channel" in t:
        return "model", 404
    if "401" in t or "unauthorized" in t:
        return "auth", 401
    if "403" in t or "forbidden" in t:
        return "auth", 403
    if "429" in t or "rate limit" in t or "too many requests" in t:
        return "rate", 429
    if "model" in t and ("not found" in t or "unknown" in t or "does not exist" in t or "unavailable" in t):
        return "model", 404
    return "error", None

def parse_json_events(stdout):
    """Collects assistant text from --format json event lines (schema varies by version; be tolerant)."""
    parts = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        stack = [ev]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if x.get("type") in ("text", "text-delta") and isinstance(x.get("text"), str):
                    parts.append(x["text"])
                stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
            elif isinstance(x, list):
                stack.extend(x)
    return "".join(parts)


ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
HEADER = re.compile(r"^\s*>\s*\S+\s*·\s*\S+\s*$")     # opencode's "> build · model-name" status lines


def clean_text(out):
    return "\n".join(l for l in out.splitlines() if not HEADER.match(l)).strip()


def resolve_executable(exe):
    """Finds a directly runnable program. On Windows, npm installs `opencode` as a .cmd/.ps1 wrapper that
    Python cannot start safely with arbitrary prompt text, so look for the real opencode.exe behind it."""
    if Path(exe).is_file() and not exe.lower().endswith((".cmd", ".bat", ".ps1")):
        return exe
    found = shutil.which(exe)
    if found and not found.lower().endswith((".cmd", ".bat", ".ps1")):
        return found
    roots = []
    if found:
        roots.append(Path(found).parent / "node_modules")
    import os
    for env in ("APPDATA", "LOCALAPPDATA", "USERPROFILE"):
        if os.getenv(env):
            roots += [Path(os.environ[env]) / "npm" / "node_modules", Path(os.environ[env]) / ".opencode" / "bin"]
    for root in roots:
        if not root.exists():
            continue
        for pattern in (f"{exe}.exe", f"{exe}*/**/{exe}.exe", f"**/{exe}.exe"):
            hits = sorted(root.glob(pattern))
            if hits:
                return str(hits[0])
    raise SystemExit(
        f"Could not find a runnable '{exe}' program{' (found only ' + found + ')' if found else ''}.\n"
        f"Run  where.exe {exe}  and  Get-ChildItem -Recurse $env:APPDATA\\npm\\node_modules -Filter {exe}.exe\n"
        f"then put the full path to {exe}.exe as the first item of client.command in the config.")


class CliClient:
    def __init__(self, cfg):
        self.cfg = cfg
        self.c = cfg["client"]
        self.exe = resolve_executable(self.c["command"][0])
        print(f"Using client program: {self.exe}")

    def chat(self, model, messages, temperature=0, max_tokens=1024, system_mode="file"):
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        user = messages[-1]["content"]
        work = Path(tempfile.mkdtemp(prefix="secbench_"))
        try:
            if self.c.get("deny_tools", True):
                (work / "opencode.json").write_text(json.dumps(SANDBOX_CONFIG))
            if system and system_mode == "file":
                (work / "AGENTS.md").write_text(system, encoding="utf-8")
            elif system:
                user = f"{system}\n\n{user}"
            full = model if "/" in model else f"{self.c['provider']}/{model}"   # "x/y" ids bypass the provider
            cmd = [self.exe] + [a.replace("{provider}/{model}", full).replace("{provider}", self.c["provider"])
                                .replace("{model}", model).replace("{prompt}", user) for a in self.c["command"][1:]]
            last = None
            for attempt in range(self.cfg["generation"]["max_retries"]):
                t0 = time.time()
                try:
                    p = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", timeout=self.c["timeout_s"],
                                       shell=False, stdin=subprocess.DEVNULL)
                except subprocess.TimeoutExpired:
                    last = ("error", None, f"timeout after {self.c['timeout_s']}s")
                    continue
                out, err = ANSI.sub("", p.stdout), ANSI.sub("", p.stderr)
                kind, status = classify(final_error(err, out), p.returncode)
                if kind == "ok" and "error:" in out.lower() and not clean_text(out).lower().replace("error:", "").strip():
                    kind, status = classify(final_error('', out), 1)
                if kind == "ok":
                    text = parse_json_events(out) if self.c.get("output") == "json" else clean_text(out)
                    return dict(text=text, latency_s=round(time.time() - t0, 3), prompt_tokens=None,
                                completion_tokens=None, finish_reason="stop", error=None, temperature_used=None,
                                served_model=f"{full} via {Path(self.exe).stem}", status=200)
                if kind == "blocked":
                    return dict(text="", latency_s=round(time.time() - t0, 3), prompt_tokens=None,
                                completion_tokens=None, finish_reason="gateway_blocked", error=None,
                                temperature_used=None, served_model=None, status=400, gateway_blocked=1,
                                gateway_message=(err or out)[-200:])
                last = (kind, status, (err or out)[-400:].strip() or f"exit code {p.returncode}")
                if kind in ("auth", "quota", "model"):
                    break                       # retrying will not help
                time.sleep(min(60, 2 ** attempt * (5 if kind == "rate" else 1)))
            kind, status, msg = last
            return dict(text="", latency_s=None, prompt_tokens=None, completion_tokens=None, finish_reason="error",
                        error=f"[{kind}] {msg}", temperature_used=None, served_model=None, status=status)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def list_models(self):
        cmd = self.c.get("list_models_command")
        if not cmd:
            raise RuntimeError("no list_models_command configured")
        p = subprocess.run([self.exe] + [a.replace("{provider}", self.c["provider"]) for a in cmd[1:]], capture_output=True,
                           text=True, timeout=120, stdin=subprocess.DEVNULL)
        names = [l.strip() for l in ANSI.sub("", p.stdout).splitlines() if l.strip()]
        pre = self.c["provider"] + "/"
        return [n[len(pre):] if n.startswith(pre) else n for n in names]