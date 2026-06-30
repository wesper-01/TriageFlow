# Architecture

## Design Goals

1. **Free-first.** Default routing prefers $0 providers (local or free-tier hosted) over paid ones.
2. **No guessing.** Every model id TriageFlow might call is verified with a live ping before any real email is processed.
3. **Extensible.** Adding a provider or model is a registry entry, not a code change.

---

## Components

### `providers.py` — The Registry

A single dictionary, `PROVIDERS`, describing every AI backend TriageFlow knows about:

```python
"groq": {
    "label": "Groq",
    "env_key": "GROQ_API_KEY",
    "base_url": "https://api.groq.com/openai/v1",
    "kind": "openai_compatible",
    "free": True,
    "models": ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "gemma2-9b-it"],
}
```

- `kind` determines which call adapter `models.py` uses (`openai_compatible`, `anthropic`, `gemini`, `ollama`).
- `models` is an ordered list of candidate model ids — first one that passes a live ping wins.
- `free` flags whether usage of this provider should count toward cost in reports.

`DEFAULT_PRIORITY` controls the order providers are tried in: local providers (Ollama, LM Studio) first since they're unlimited and free, then fast hosted free tiers (Groq, Cerebras), then OpenRouter/Gemini, with paid providers (OpenAI, Claude) last.

---

### `health_check.py` — Live Verification

Before TriageFlow routes a single email, `discover_working_models()`:

1. For each provider in priority order, checks if it's configured (has a key, or is local).
2. For each candidate model of that provider, sends a real 1-token chat completion.
3. Stops at the first model that returns HTTP 200 — that's the model used for that provider this run.
4. If none of a provider's candidates work, reports why (auth error, 404, connection refused, timeout) and moves on.

This is the fix for the most common failure mode in naive multi-provider tools: a valid API key paired with a stale/wrong/paid-only model id, which silently 404s deep into a batch run instead of failing fast and clearly.

---

### `models.py` — Unified Call Interface

`TriageModel` wraps one verified `(provider_id, model_name)` pair and exposes:

- `categorize_email(text)` → `(category, tokens, time)`
- `generate_response(text, category)` → `(response_text, tokens, time)`

Internally it dispatches to one of four adapters based on `kind`:
- `_call_openai_compatible` — used by Groq, Cerebras, OpenRouter, OpenAI, LM Studio (all speak the OpenAI chat-completions schema)
- `_call_anthropic` — Claude's native SDK
- `_call_gemini` — Gemini's REST API
- `_call_ollama` — Ollama's local chat API

---

### `triage.py` — Routing & Learning

`EmailTriage` decides, per email:

1. **Manager step (categorization):** prefers a paid/premium model if one is configured (accuracy matters most here), otherwise the best available free model.
2. **Worker step (response generation):** checks `database.py` for a learned pattern — "what model worked best for this category before" — and reuses it if that provider is still alive this run. Otherwise picks the highest-priority free model.

Over repeated runs, the database accumulates per-category performance data, so routing gets both cheaper and more consistent over time without any manual tuning.

---

### `database.py` — Persistence

SQLite-backed. Three concerns:
- `email_results` — full log of every processed email, category, response, model, tokens, time.
- `patterns` — per-category success counts and average tokens/time per model, used to pick the "best" model for a category.
- `model_performance` — aggregate usage stats across all categories.

---

## Adding a New Free Provider

1. Add an entry to `PROVIDERS` in `providers.py` with its base URL, env var name, `kind`, and a list of known-working free model ids (check the provider's docs for the exact, current ids — these change).
2. Add the provider id to `DEFAULT_PRIORITY` wherever you want it tried relative to others.
3. That's it — `health_check.py` and `models.py` already know how to ping and call any `kind` they support.
