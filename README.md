# TriageFlow

**Free, open-source AI email triage. No required API costs. No guessing which model works — TriageFlow pings every provider live and only uses what's actually working.**

---

## ⚡ How It Works

```
Your email
    ↓
[Health Check] Pings every configured AI provider with a real test call
    ↓
[Manager] Best available model: categorize the email
    ↓
[Worker] Cheapest/free working model: generate a response
    ↓
Categorized email + response, at $0 cost (if using free tier)
```

---

## 🎯 Why TriageFlow

Most "AI cost optimizer" tools assume you're already paying for a premium API. TriageFlow doesn't.

- **Free by default.** Routes to free-tier providers (Groq, OpenRouter, Gemini, Cerebras) or 100% local models (Ollama, LM Studio) first. Paid APIs (Claude, OpenAI) are optional, used only if you add a key.
- **No silent failures.** Before processing anything, TriageFlow pings every provider you've configured with a real request. If a model id is wrong, deprecated, or rate-limited, you're told immediately — not after burning through a batch of emails.
- **Anyone can run it.** No credit card required. Works for a solo developer testing locally just as well as a team with premium API access.

---

## 🚀 Quick Start (5 Minutes)

### 1. Clone & Setup

```bash
git clone https://github.com/wesper-01/TriageFlow.git
cd TriageFlow
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get a Free API Key (pick ONE)

| Provider | Free tier | Get a key |
|---|---|---|
| **Groq** | Generous, no card | https://console.groq.com/keys |
| **OpenRouter** | Free models available | https://openrouter.ai/keys |
| **Google Gemini** | Free with daily limits | https://aistudio.google.com/apikey |
| **Cerebras** | Free, very fast | https://cloud.cerebras.ai/ |
| **Ollama (local)** | 100% free, no key | https://ollama.ai |

### 3. Configure

```bash
cp .env.example .env
# paste your key into .env
```

### 4. Run

```bash
# Check which providers are actually working right now
python health_check.py

# Test with 1000 sample emails
python test.py

# Or process your own emails interactively
python triageflow.py
```

---

## 🔧 How Health Checking Works

On startup, TriageFlow doesn't assume a model id works just because you have a key. It sends a real 10-token request to every candidate model for every provider you've configured. It then **measures the latency** of each response and dynamically sorts the providers so that the fastest working model is always preferred:

```
======================================================================
  CHECKING AVAILABLE MODELS (pinging providers...)
======================================================================
  [x] Ollama (local)       no working model (Ollama not running locally)
  [x] LM Studio (local)    no working model (connection refused (is it running?))
  [-] Groq                 not configured (no API key set)
  [OK] Cerebras             gemma-4-31b                              [FREE] (362ms)
  [OK] OpenRouter           meta-llama/llama-3.3-70b-instruct:free  [FREE] (891ms)
  [x] Google Gemini        no working model (HTTP 404: model not found)
  [OK] NVIDIA (DeepSeek)    moonshotai/kimi-k2.6                     [PAID] (31204ms)
  [-] OpenAI               not configured (no API key set)
  [-] Claude (Anthropic)   not configured (no API key set)
----------------------------------------------------------------------
  3 model(s) ready  (2 free, 1 paid)
======================================================================
```

This is what prevents the classic "API Error 404 even though my key works" problem — that's almost always a wrong/deprecated model id, not a bad key, and now you find out before processing any real data.

---

## 🤖 Supported Providers

| Provider | Cost | Type |
|---|---|---|
| Groq | Free | Hosted |
| OpenRouter | Free (`:free` models) | Hosted |
| Google Gemini | Free tier | Hosted |
| Cerebras | Free | Hosted |
| Ollama | $0 forever | Local |
| LM Studio | $0 forever | Local |
| Claude | Paid | Hosted (optional manager) |
| OpenAI | Paid | Hosted (optional manager) |
| NVIDIA NIM | Paid | Hosted (optional manager) |

Adding a new provider is one entry in `providers.py` — no other code changes needed.

---

## 🏗️ Architecture

```
triageflow.py / test.py
    │
    ├─ health_check.py   → pings every configured provider, returns only working ones
    │     └─ providers.py → registry of providers + their known-good model ids
    │
    ├─ models.py          → uniform interface to call any provider (TriageModel)
    │
    ├─ triage.py           → routing logic: free models first, learns patterns over time
    │
    └─ database.py        → SQLite: logs results, learns which model works best per category
```

---

## 📊 What Gets Learned

As TriageFlow processes more emails, `database.py` tracks which model performs best for each category (BILLING, TECHNICAL, FEATURE_REQUEST, FEEDBACK, GENERAL_INQUIRY) and routes future emails of that type straight to it — skipping the trial-and-error on subsequent runs.

---

## 📁 Project Structure

```
TriageFlow/
├── triageflow.py        ← Main entry point
├── providers.py         ← Provider/model registry
├── health_check.py      ← Live ping/verification
├── models.py            ← Unified API wrapper
├── triage.py            ← Routing + learning logic
├── database.py          ← SQLite persistence
├── test.py              ← Bulk test runner (1000 emails)
├── visualize.py         ← Terminal charts from results.csv
├── requirements.txt
├── .env.example
├── QUICKSTART.md        ← Setup guide
├── ARCHITECTURE.md      ← Deep dive into system design
├── data/
│   ├── emails_sample.txt
│   └── emails_1000.txt
```

---

## 📝 License

MIT — free to use, modify, and build on.

---

## 🤝 Contributing

This is meant to be a genuinely useful free tool, not a paid product wrapper. PRs adding new free-tier providers, fixing model ids that have gone stale, or improving the learning logic are welcome.
