# TriageFlow: Documentation

**Status:** Development stopped (on hold)
**Last updated:** November 2026
**Tested on:** 1,000-email sample batch, plus a live Hermes Agent deployment on a server

This documentation explains what went wrong with TriageFlow, why I decided to stop rather than keep patching it, and where I'd take it if I came back to it.

The short version: **TriageFlow didn't fail because the idea or the core logic was wrong. It failed because the thing it was built on, free-tier AI APIs, isn't reliable enough to build a working product on.** Testing showed the framework works: a 1,000-email run completed, and providers switched automatically when one failed. A live setup with Hermes Agent on a server also worked. But both depended on free APIs that kept hitting rate limits and latency spikes, so instead of being reliable the system became a nightmare to run. It worked, but it can't be sustained or relied on.

---

## 1. What TriageFlow was meant to be

A free, open-source email triage tool:

1. Ping every configured AI provider to find out which models actually work right now.
2. Use the best available model to **categorize** an email (BILLING, TECHNICAL, FEATURE_REQUEST, FEEDBACK, GENERAL_INQUIRY).
3. Use the cheapest/free working model to **draft a reply**.
4. Learn over time which model performs best per category.

The core promise was **$0 cost**: run entirely on free tiers (Groq, OpenRouter, Gemini, Cerebras) or local models (Ollama, LM Studio).

That promise is exactly what broke it.

---

## 2. What testing showed

I tested TriageFlow in two ways.

### 2.1 Bulk test: 1,000 sample emails

I ran the full pipeline (`test.py`) on a 1,000-email sample dataset.

- **What worked:** the framework did its job. Emails were categorized and answered, and when a provider failed, the router **switched to another model automatically**, as designed.
- **What didn't:** the providers **kept hitting rate limits**, and latency spikes stacked up. Requests waited so long that they ran into **request queue time limits**: calls timed out while waiting, not because the model was wrong. Model switching kept the run going, but most of the effort went into recovering from provider failures instead of triaging emails.

### 2.2 Live test: Hermes Agent on a server

I also ran **Hermes Agent hosted on a server** and sent real emails to it to check the framework end to end in a realistic setup.

- **What worked:** it ran, and the results were alright. The agent received emails, the triage logic ran, and it produced sensible output.
- **What didn't:** it had the same weakness underneath. Every step still went through the same free-tier APIs, so the same rate limits and latency showed up. It proved the idea can work in practice, but not that it can run day after day.

### 2.3 Verdict

**The framework works. It isn't sustainable or reliable.** The logic holds up; the free API layer under it doesn't. A tool that only works when the providers are having a good day isn't something anyone can depend on, least of all for email.

---

## 3. What went wrong

### 3.1 Latency: unpredictable, sometimes extreme

Free-tier response times weren't just slow. They were **inconsistent**. The same provider could answer in a few hundred milliseconds and then take 30+ seconds on the next call. One health check run showed responses ranging from about 360 ms to about 31,000 ms across providers.

Every email needs **two sequential calls** (categorize, then respond), and each call has a 25-second timeout (`TRIAGEFLOW_TIMEOUT` in `models.py`). With fallback across providers and up to 3 retry rounds (`triage.py`), one bad email could stall the pipeline for minutes. In the 1,000-email test, this is what caused requests to run into queue time limits: the requests themselves were fine, they just waited too long. Over a 1,000-email batch that's not a slowdown. The tool becomes unusable.

### 3.2 Rate limits: the free tier runs out mid-batch

Free tiers come with tight requests-per-minute and requests-per-day caps. A triage batch is exactly the kind of workload that hits them: many short requests, back to back. Providers that passed the health check started returning `HTTP 429` partway through a run.

The code's response is a fixed `sleep(5)` and a retry, which doesn't match how rate limits actually reset (often per minute or per day). There's no way to optimize your way around a daily quota you don't control.

### 3.3 Unavailability: "working" doesn't stay working

The health check (`health_check.py`) was designed to stop silent failures by testing each model with a real call at startup. It works, but it's a **snapshot**. A model that passes at startup can be overloaded, throttled, or removed a few minutes later.

On top of that, free-tier model IDs change constantly. Models get deprecated, renamed, moved behind paid tiers, or have their `:free` variant pulled. Keeping `providers.py` up to date turned into ongoing maintenance just to stand still.

### 3.4 The failures cascaded into the logic

This is the part that made the whole framework "fall apart" instead of just running slower:

- **Silent misclassification.** In `models.py`, `categorize_email()` turns any response that isn't a known category into `GENERAL_INQUIRY`. When a provider returns an error like `API Error 429`, that also becomes `GENERAL_INQUIRY`. The fallback logic in `triage.py` then sees a "valid" category and never tries another provider. API failures quietly turn into wrong results.
- **Poisoned learning.** `database.py` learns which model is best per category from processing time and tokens. When latency is driven by provider load rather than model quality, and categories are skewed by masked errors, the learned patterns reflect API noise, not real performance.
- **Unstable routing.** Providers get sidelined after 3 consecutive failures, then un-sidelined on retry, then fail again. Under real free-tier conditions the router spent more effort shuffling between unreliable providers than doing triage.

None of these are bugs in the usual sense. Each piece works on its own. But they all assumed the API layer would be *mostly* reliable, and on free tiers it isn't.

---

## 4. Why stopping was the right call

I could have kept going: added exponential backoff, read `Retry-After` headers, added more providers, cached results, rate-limited myself. Some of that is worth doing. But I decided to stop because:

1. **The bottleneck isn't in my code.** Latency, quotas and uptime belong to the providers. Every hour spent working around them is spent on symptoms, not on the product.
2. **"Free" and "reliable" pulled in opposite directions.** Making it reliable means paid APIs or capable local hardware. Both break the original $0, runs-anywhere promise. That's a design decision to make deliberately, not something to drift into by patching.
3. **The next features would have made it worse.** The roadmap had Gmail integration next. Connecting a real inbox to a pipeline that silently misclassifies emails when an API hiccups would be worse than having no integration. An email tool that's wrong *quietly* isn't safe to point at real mail.
4. **Building more on an unstable base only adds complexity.** Every new feature would inherit the same unreliability and multiply the ways it can fail.

So TriageFlow is **unoptimized and not functional in practice yet**, but not a failure. It proved the architecture (live health checks, cost-aware routing, per-category learning) and showed exactly where the limit is.

---

## 5. What was planned next

### 5.1 Email integrations

- **Gmail** via the Gmail API (OAuth2): read unread mail, triage it, and **save replies as drafts only**. Never auto-send; a human reviews everything.
- Flag sensitive emails (billing disputes, critical bugs) with a `[NEEDS HUMAN REVIEW]` marker.
- Other providers (Outlook / IMAP) after Gmail.

### 5.2 An LLM agent harness

Instead of hand-rolling every piece (tool calls, retries, memory, scheduling), the plan was to run TriageFlow's logic inside an existing open-source agent harness. Two candidates:

- **Hermes Agent**: my preferred direction, and **already tested**. I ran it on a server and sent emails to it (see section 2.2). It worked.
- **OpenClaw**: considered as an alternative.

**Why Hermes is my vision:** for a tool that reads someone's inbox, security matters more than anything else. From what I've seen, Hermes has had far fewer security problems than OpenClaw, which has had a range of publicly reported issues. An email agent handles private data and processes untrusted input (any stranger can send you an email). I want the harness with the smaller attack surface and the cleaner track record, even if it means fewer features.

The server test confirmed something important: **a harness doesn't fix the API problem by itself.** Hermes ran fine, but an agent built on unreliable free endpoints is just as unreliable as the endpoints. That's why the integration is on hold together with everything else, not instead of it.

---

## 6. What it would take to restart

If I pick TriageFlow back up, these are the prerequisites, roughly in order:

1. **A reliable model backend.** Either a local model on capable hardware (Ollama / LM Studio) or a paid API tier with real rate limits and an uptime guarantee. Free tiers become an optional extra, not the foundation.
2. **Fail loudly, never silently.** Errors must never turn into a valid category. A failed call should be marked as failed and retried or flagged, not guessed.
3. **Proper rate-limit handling.** Exponential backoff with jitter, respecting `Retry-After`, and client-side throttling so we stay under quota instead of hitting it.
4. **Continuous health tracking.** Track provider health throughout the run, not just at startup, and keep failed calls out of the learning data.
5. **Then the harness (Hermes Agent) and Gmail integration**, with drafts-only output, human review, and treating every incoming email as untrusted input (prompt-injection defense).

---

## 7. Takeaways

- **"It works" and "it's reliable" are different things.** Both tests passed functionally. Neither setup could be run sustainably.
- **Check your dependencies before building features on them.** The health check was a good instinct; it should have tracked provider health continuously, not just once at startup.
- **"Free" has a cost.** It's paid in latency, quotas and maintenance instead of money.
- **Silent fallbacks are dangerous.** Turning errors into a default value made failures invisible, which is worse than a crash.
- **Stopping is a valid engineering decision.** Pausing a project whose foundation isn't ready is better than shipping something that looks like it works and doesn't.

The code stays public under the MIT license. Anyone is welcome to fork it, learn from it, or run it on a more dependable backend.
