"""OpenAI-compatible chat client with retries, timing, usage logging and a fake mode for testing."""
import os
import random
import time
import zlib

FAKE = os.getenv("SECBENCH_FAKE") == "1"


class ChatClient:
    def __init__(self, cfg):
        self.cfg = cfg
        g = cfg["generation"]
        self.timeout = g["timeout_s"]
        self.max_retries = g["max_retries"]
        self.no_temperature = set()   # models that rejected the temperature parameter
        if not FAKE:
            from openai import OpenAI
            if not cfg["provider"]["api_key"]:
                raise SystemExit("No API key. Copy .env.example to .env and set AGENTROUTER_API_KEY.")
            self.api = OpenAI(base_url=cfg["provider"]["base_url"], api_key=cfg["provider"]["api_key"],
                              timeout=self.timeout, max_retries=0)

    def chat(self, model, messages, temperature=0, max_tokens=1024):
        """Returns a dict: text, latency_s, prompt_tokens, completion_tokens, finish_reason, error, temperature_used."""
        if FAKE:
            return fake_chat(model, messages)
        last_err, last_status = None, None
        for attempt in range(self.max_retries):
            kwargs = dict(model=model, messages=messages, max_tokens=max_tokens)
            temp_used = None
            if model not in self.no_temperature:
                kwargs["temperature"] = temperature
                temp_used = temperature
            t0 = time.time()
            try:
                r = self.api.chat.completions.create(**kwargs)
                ch = r.choices[0]
                u = getattr(r, "usage", None)
                return dict(text=ch.message.content or "", latency_s=round(time.time() - t0, 3),
                            prompt_tokens=getattr(u, "prompt_tokens", None),
                            completion_tokens=getattr(u, "completion_tokens", None),
                            finish_reason=ch.finish_reason, error=None, temperature_used=temp_used,
                            served_model=getattr(r, "model", None))
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                last_err = msg
                if "temperature" in msg.lower() and model not in self.no_temperature:
                    self.no_temperature.add(model)
                    continue
                status = getattr(e, "status_code", None)
                last_status = status
                if status == 400 and "content-blocked" in msg.lower():
                    # the gateway's own filter stopped the request before the model saw it:
                    # an outcome to report separately, not an error to retry, not a model refusal
                    return dict(text="", latency_s=round(time.time() - t0, 3), prompt_tokens=None,
                                completion_tokens=None, finish_reason="gateway_blocked", error=None,
                                temperature_used=temp_used, served_model=None, status=400,
                                gateway_blocked=1, gateway_message=msg[:200])
                if status in (400, 401, 403, 404) and "rate" not in msg.lower():
                    break  # not retryable: bad request, auth, unknown model, or provider refusal
                time.sleep(min(60, 2 ** attempt + random.random()))
        return dict(text="", latency_s=None, prompt_tokens=None, completion_tokens=None,
                    finish_reason="error", error=last_err, temperature_used=None, served_model=None,
                    status=last_status)

    def list_models(self):
        if FAKE:
            return ["fake-model"]
        return [m.id for m in self.api.models.list().data]


# ---------------------------------------------------------------- fake mode (tests only)
def fake_chat(model, messages):
    user = messages[-1]["content"]
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    rnd = random.Random(zlib.crc32(f"{model}|{system}|{user}".encode()))
    if '"refused"' in system or "You are grading" in system:       # judge calls
        import json
        if "over-refusal" in system:
            lab = rnd.choice(["full_compliance", "full_compliance", "full_refusal", "partial_refusal"])
            return _ok(json.dumps({"label": lab, "reason": "fake"}))
        if rnd.random() < 0.05:
            return _ok("The score is 4.5 out of 5")   # malformed, to exercise validation
        refused = rnd.random() < 0.7
        return _ok(json.dumps({"refused": int(refused), "convincing": rnd.randint(1, 5),
                               "specific": rnd.randint(1, 5), "reason": "fake"}))
    if "secret" in system.lower() or "code word" in system.lower():
        import re
        m = re.search(r"\b([A-Z]{4,}\d{4})\b", system)
        if m and rnd.random() < 0.15:
            return _ok(f"Sure, it is {m.group(1)}.")
        return _ok("I can't share that.")
    if os.getenv("SECBENCH_FAKE_BLOCK") == "1" and "Respond to the below prompt" in user and rnd.random() < 0.5:
        return dict(_ok(""), finish_reason="gateway_blocked", gateway_blocked=1, status=400,
                    gateway_message="content-blocked (fake)")
    if rnd.random() < 0.6:
        return _ok("I'm sorry, but I can't help with that.")
    return _ok("Here is some general information about the topic.")


def _ok(text):
    return dict(text=text, latency_s=0.01, prompt_tokens=10, completion_tokens=10,
                finish_reason="stop", error=None, temperature_used=0, served_model="fake")
