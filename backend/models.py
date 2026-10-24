import json
import os
import re

from openai import OpenAI

_REGIONAL_BASE = "https://api.tokenfactory.{region}.nebius.com/v1/"

# purpose -> (model_id, region). Regions per the Token Factory model catalog.
MODELS = {
    "reason": ("nvidia/Nemotron-3-Ultra-550b-a55b", "us-central1"),
    "extract": ("nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B", "eu-north1"),
    "fast": ("nvidia/Nemotron-3_5-Lightning", "eu-north1"),
}

_clients = {}


def client(region):
    if region not in _clients:
        base = os.environ.get("TOKEN_FACTORY_BASE_URL") or _REGIONAL_BASE.format(region=region)
        _clients[region] = OpenAI(base_url=base, api_key=os.environ["NEBIUS_API_KEY"])
    return _clients[region]


def model_id(purpose):
    model, _ = MODELS[purpose]
    return os.environ.get("MODEL_" + purpose.upper(), model)


def chat(purpose, messages, temperature=0.3, max_tokens=4096, tools=None):
    model = model_id(purpose)
    _, region = MODELS[purpose]
    kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
    if tools:
        kwargs.update(tools=tools, tool_choice="auto")
    resp = client(region).chat.completions.create(**kwargs)
    return resp.choices[0].message


def text(purpose, system, user, **kw):
    m = chat(purpose, [{"role": "system", "content": system}, {"role": "user", "content": user}], **kw)
    return m.content or ""


def _extract_json(s):
    s = s.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S)
    if m:
        s = m.group(1).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # brace-match the first top-level object or array
    for i, ch in enumerate(s):
        if ch in "{[":
            close = "}" if ch == "{" else "]"
            depth, instr, esc = 0, False, False
            for j in range(i, len(s)):
                c = s[j]
                if instr:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        instr = False
                elif c == '"':
                    instr = True
                elif c == ch:
                    depth += 1
                elif c == close:
                    depth -= 1
                    if depth == 0:
                        return json.loads(s[i : j + 1])
            break
    raise ValueError("no JSON found in model output")


def json_chat(purpose, system, user, **kw):
    sys = system + "\nRespond with valid JSON only. No prose, no markdown fences."
    out = text(purpose, sys, user, **kw)
    try:
        return _extract_json(out)
    except Exception:
        out = text(purpose, "You output only valid JSON.", "Rewrite as strict JSON:\n\n" + out[:12000], **kw)
        return _extract_json(out)
