#!/usr/bin/env python3
"""
health_check.py — Pings every configured provider to find out which
models are ACTUALLY working right now, before any real traffic is sent.

This solves the "API Error 404 even though my key works" problem:
a key can be valid while the specific model id is wrong, deprecated,
not enabled for your account tier, or temporarily down. We test the
real chat-completion call (not just an auth ping) so we catch all of
these cases up front, then only route to models that passed.
"""

import time
import requests
import providers as P


def _ping_openai_compatible(base_url, api_key, model_name, extra_headers=None, extra_payload=None, timeout=30):
    """Send a 1-token request to confirm the model actually responds."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if extra_headers:
        headers.update(extra_headers)
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }
    if extra_payload:
        payload.update(extra_payload)
    try:
        r = requests.post(f"{base_url}/chat/completions",
                           headers=headers, json=payload, timeout=timeout)
        if r.status_code == 200:
            return True, None
        return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except requests.exceptions.ConnectionError:
        return False, "connection refused (is it running?)"
    except requests.exceptions.Timeout:
        return False, "timed out"
    except Exception as e:
        return False, str(e)[:120]


def _ping_anthropic(api_key, model_name, timeout=10):
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        client.messages.create(
            model=model_name, max_tokens=1,
            messages=[{"role": "user", "content": "hi"}],
        )
        return True, None
    except Exception as e:
        return False, str(e)[:120]


def _ping_gemini(api_key, model_name, base_url, timeout=10):
    try:
        url = f"{base_url}/models/{model_name}:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": "hi"}]}]}
        r = requests.post(url, json=payload, timeout=timeout)
        if r.status_code == 200:
            return True, None
        return False, f"HTTP {r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, str(e)[:120]


def ping_provider_model(provider_id, model_name, timeout=30):
    """Returns (ok: bool, error: str|None)"""
    p = P.PROVIDERS[provider_id]
    kind = p["kind"]
    base_url = P.get_base_url(provider_id)
    api_key = P.get_api_key(provider_id)

    if kind == "openai_compatible":
        extra_headers = p.get("extra_headers", {})
        extra_payload = p.get("extra_payload", {})
        return _ping_openai_compatible(base_url, api_key, model_name, extra_headers, extra_payload, timeout)
    elif kind == "anthropic":
        return _ping_anthropic(api_key, model_name, timeout)
    elif kind == "gemini":
        return _ping_gemini(api_key, model_name, base_url, timeout)
    elif kind == "ollama":
        try:
            r = requests.post(
                f"{base_url}/api/chat",
                json={"model": model_name,
                      "messages": [{"role": "user", "content": "hi"}],
                      "stream": False},
                timeout=timeout,
            )
            if r.status_code == 200:
                return True, None
            return False, f"HTTP {r.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Ollama not running locally"
        except Exception as e:
            return False, str(e)[:120]
    return False, "unknown provider kind"


def discover_working_models(verbose=True, priority=None, timeout=30):
    """
    Probe every configured provider's candidate models in priority order.
    Stops at the FIRST working model per provider (no need to test all
    of them once one works — saves time and free-tier quota).

    Returns: list of dicts: [{provider, model, label, free}, ...]
             ordered by priority (cheapest/local first).
    """
    priority = priority or P.DEFAULT_PRIORITY
    working = []

    if verbose:
        print("\n" + "=" * 70)
        print("  CHECKING AVAILABLE MODELS (pinging providers...)")
        print("=" * 70)

    for provider_id in priority:
        p = P.PROVIDERS[provider_id]

        if not P.is_configured(provider_id):
            if verbose:
                print(f"  [-] {p['label']:<20} not configured (no API key set)")
            continue

        candidates = P.get_candidate_models(provider_id)
        found = False
        last_err = None
        start_time = time.time()

        for model_name in candidates:
            ok, err = ping_provider_model(provider_id, model_name, timeout=timeout)
            if ok:
                latency = time.time() - start_time
                found = True
                working.append({
                    "provider": provider_id,
                    "model": model_name,
                    "label": p["label"],
                    "free": p["free"],
                    "latency": latency,
                })
                tag = "FREE" if p["free"] else "PAID"
                if verbose:
                    print(f"  [OK] {p['label']:<20} {model_name:<40} [{tag}] ({latency*1000:.0f}ms)")
                break
            else:
                last_err = err

        if not found and verbose:
            print(f"  [x] {p['label']:<20} no working model "
                  f"({last_err or 'all candidates failed'})")

    working.sort(key=lambda x: x["latency"])

    if verbose:
        free_count = sum(1 for w in working if w["free"])
        print("-" * 70)
        print(f"  {len(working)} model(s) ready  "
              f"({free_count} free, {len(working) - free_count} paid)")
        print("=" * 70 + "\n")

    return working


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    results = discover_working_models()
    if not results:
        print("\nNo working models found. Set at least one API key in .env,")
        print("or install Ollama for a 100% free local option:")
        print("  https://ollama.ai")
