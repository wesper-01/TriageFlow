# Quick Start Guide

Get TriageFlow running in 5 minutes, for free.

---

## Step 1: Clone & Install

```bash
git clone https://github.com/wesper-01/TriageFlow.git
cd TriageFlow

python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

---

## Step 2: Get a Free API Key

You only need **one**. Recommended for beginners: **Groq** (no credit card, generous limits, fast).

- Groq: https://console.groq.com/keys
- OpenRouter: https://openrouter.ai/keys
- Google Gemini: https://aistudio.google.com/apikey
- Cerebras: https://cloud.cerebras.ai/

Or skip API keys entirely and install **Ollama** for a 100% local, unlimited, free option: https://ollama.ai
After installing, run `ollama pull llama3.2`.

---

## Step 3: Configure

```bash
cp .env.example .env
```

Open `.env` and paste your key into the matching line, e.g.:

```
GROQ_API_KEY=gsk_your_key_here
```

---

## Step 4: Verify It Works

```bash
python health_check.py
```

You should see something like:

```
[✓] Groq    llama-3.1-8b-instant   [FREE]
2 model(s) ready (2 free, 0 paid)
```

If you instead see `[x]` with an error, read the error message — it tells you exactly what failed (wrong key, model not found, rate limited, etc).

---

## Step 5: Run a Test

```bash
python test.py
```

This processes 1000 sample emails and shows live progress:

```
#      Category           Provider       Tokens   Status
──────────────────────────────────────────────────────────
1      TECHNICAL          groq           210      COLD START
2      BILLING            groq           198      COLD START
...
1000   FEEDBACK           groq           60       OPTIMIZED

[+] Results saved to: results.csv
```

---

## Step 6: Visualize

```bash
python visualize.py
```

Shows terminal charts: token trend, category breakdown, provider usage.

---

## Step 7: Use It On Your Own Emails

```bash
python triageflow.py
```

Then type or paste emails, one per line, and press Enter twice when done.

---

## Troubleshooting

**"No working AI provider found"**
Your `.env` key is missing, wrong, or the provider's free tier rejected the request. Run `python health_check.py` for a clear error per provider.

**"API Error 404" on a specific model**
That model id doesn't exist or isn't available on your account's tier. `providers.py` lists multiple fallback model ids per provider — if all of them 404, the provider's free model lineup may have changed; check their docs for current free model ids and update `providers.py`.

**Ollama shows "not running locally"**
Make sure the Ollama app/service is actually started before running TriageFlow.

---

That's it — you're running a fully free AI email triage pipeline. 🚀
