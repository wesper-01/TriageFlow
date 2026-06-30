#!/usr/bin/env python3
"""
providers.py — Registry of AI providers TriageFlow can use.

Design goals (per project philosophy):
  - 100% optional cost. Every provider listed here has a real free tier
    or is local/free by nature (Ollama).
  - No guessing model names. Each provider lists EXACT model ids known
    to work on the free tier as of this writing. OpenRouter especially
    requires the ":free" suffix on most models — that's the #1 cause
    of mysterious 404s, so we hardcode only verified-working ids.
  - Every provider is "pingable" — we can cheaply check if it's alive
    and authenticated BEFORE we try to route real traffic to it.
  - Adding a new provider/model later = add one dict entry. No other
    code changes required.
"""

import os
import requests

# ---------------------------------------------------------------------------
# PROVIDER REGISTRY
# ---------------------------------------------------------------------------
# Each provider entry:
#   env_key       : name of env var holding the API key (None if no key needed)
#   base_url      : API base url
#   models        : list of model ids to try, IN ORDER OF PREFERENCE.
#                    First one that passes a ping is used; if a ping
#                    later fails mid-run we fall over to the next.
#   kind          : 'anthropic' | 'openai_compatible' | 'gemini' | 'ollama'
#   free          : True if this provider/model combo is free to use
#   ping_path     : endpoint used to verify the key/model works (cheap call)
#   notes         : human-readable note shown in CLI

PROVIDERS = {

    "groq": {
        "label": "Groq",
        "env_key": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "kind": "openai_compatible",
        "free": True,
        "models": [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "gemma2-9b-it",
        ],
        "notes": "Generous free tier, very fast inference.",
    },

    "openrouter": {
        "label": "OpenRouter",
        "env_key": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "kind": "openai_compatible",
        "free": True,
        "models": [
            "nvidia/nemotron-3-super-120b-a12b:free",
            "meta-llama/llama-3.1-8b-instruct:free",
            "mistralai/mistral-7b-instruct:free",
            "google/gemma-2-9b-it:free",
            "qwen/qwen-2-7b-instruct:free",
            "microsoft/phi-3-mini-128k-instruct:free",
        ],
        "notes": "Free models REQUIRE the ':free' suffix or you get 404s.",
        "extra_headers": {
            "HTTP-Referer": "https://github.com/wesper-01/TriageFlow",
            "X-Title": "TriageFlow",
        },
    },

    "gemini": {
        "label": "Google Gemini",
        "env_key": "GOOGLE_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "kind": "gemini",
        "free": True,
        "models": [
            "gemini-1.5-flash",
            "gemini-1.5-flash-8b",
        ],
        "notes": "Free tier with daily request limits.",
    },

    "cerebras": {
        "label": "Cerebras",
        "env_key": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "kind": "openai_compatible",
        "free": True,
        "models": [
            "llama3.1-8b",
        ],
        "notes": "Free tier, extremely fast inference.",
    },

    "ollama": {
        "label": "Ollama (local)",
        "env_key": None,
        "base_url_env": "OLLAMA_URL",
        "base_url_default": "http://localhost:11434",
        "kind": "ollama",
        "free": True,
        "models_env": "OLLAMA_MODEL",
        "models": [
            "llama3.2",
            "llama3.1",
            "mistral",
            "phi3",
        ],
        "notes": "100% free and private, runs on your machine. Needs Ollama installed.",
    },

    "lmstudio": {
        "label": "LM Studio (local)",
        "env_key": None,
        "base_url_env": "LMSTUDIO_URL",
        "base_url_default": "http://localhost:1234/v1",
        "kind": "openai_compatible",
        "free": True,
        "models_env": "LMSTUDIO_MODEL",
        "models": ["local-model"],
        "notes": "100% free and private, runs locally via LM Studio app.",
    },

    # --- Paid / premium (optional, used as the "manager" tier if present) ---
    "claude": {
        "label": "Claude (Anthropic)",
        "env_key": "ANTHROPIC_API_KEY",
        "base_url": "https://api.anthropic.com",
        "kind": "anthropic",
        "free": False,
        "models": ["claude-3-5-haiku-20241022", "claude-3-5-sonnet-20241022"],
        "notes": "Optional premium tier for highest-accuracy categorization.",
    },

    "openai": {
        "label": "OpenAI",
        "env_key": "OPENAI_API_KEY",
        "base_url": "https://api.openai.com/v1",
        "kind": "openai_compatible",
        "free": False,
        "models": ["gpt-4o-mini", "gpt-3.5-turbo"],
        "notes": "Optional premium tier.",
    },
}

# Order in which we prefer to use providers when multiple are available
# and equally "free". Local-first (zero cost, zero rate limit risk from
# us bombarding a shared free tier), then fast hosted free tiers.
DEFAULT_PRIORITY = [
    "ollama", "lmstudio",          # local, unlimited, $0
    "groq", "cerebras",            # hosted free, very fast
    "openrouter", "gemini",        # hosted free, slower / stricter limits
    "openai", "claude",            # paid, last resort / manager tier
]


def get_base_url(provider_id):
    p = PROVIDERS[provider_id]
    if "base_url" in p:
        return p["base_url"]
    return os.getenv(p["base_url_env"], p["base_url_default"])


def get_api_key(provider_id):
    p = PROVIDERS[provider_id]
    if p["env_key"] is None:
        return None
    return os.getenv(p["env_key"])


def get_candidate_models(provider_id):
    p = PROVIDERS[provider_id]
    models = list(p["models"])
    # allow user override via env (e.g. OLLAMA_MODEL=mymodel)
    if "models_env" in p:
        override = os.getenv(p["models_env"])
        if override:
            models = [override] + [m for m in models if m != override]
    return models


def get_extra_headers(provider_id):
    """Optional extra headers (e.g. OpenRouter app ranking headers)."""
    return PROVIDERS[provider_id].get("extra_headers", {})


def is_configured(provider_id):
    """Does the user have what's needed to even attempt this provider?"""
    p = PROVIDERS[provider_id]
    if p["env_key"] is None:
        return True  # local providers: we'll find out via ping
    return bool(get_api_key(provider_id))
