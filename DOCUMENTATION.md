# TriageFlow: Documentation

| | |
| --- | --- |
| **Status** | Paused |
| **Last updated** | November 2026 |
| **Tested on** | A 1,000-email sample batch, and Hermes Agent on a server with real emails |
| **Verdict** | The framework works, but it is not reliable enough to deploy on free-tier APIs |

This document records what testing showed, what went wrong, why development is paused, and what a restart would need.

## Summary

TriageFlow was built to triage support email at zero cost, using only free-tier and local AI models. Both tests completed: the 1,000-email batch ran to the end, and the Hermes Agent setup triaged real emails end to end. Neither ran reliably. Free-tier APIs kept hitting rate limits and latency spikes, and a bug in my error handling made those failures harder to detect. I paused development rather than keep patching around a foundation I don't control.

## 1. Design goals

1. Check every configured provider with a real request before processing anything.
2. Categorize each email with the best available model (billing, technical, feature request, feedback, general inquiry).
3. Draft the reply with the cheapest working model.
4. Learn which model performs best for each category.

The defining constraint was **$0 cost**: free tiers (Groq, OpenRouter, Gemini, Cerebras) or local models (Ollama, LM Studio). That constraint is also what made the system unreliable.

## 2. Test results

### 2.1 Batch test: 1,000 sample emails

The full pipeline (`test.py`) ran on the 1,000-email sample set.

- **Worked:** the run completed, and emails were categorized and answered. Failover worked for hard failures: when a provider was down or returned a visible error, the next provider took over.
- **Did not work:** failover did not trigger for errors masked as normal results (section 3.4). Rate limits, latency spikes and request queue timeouts dominated the run. Requests timed out while waiting, not because a model gave a wrong answer.

**Measurements.** I did not record exact figures for this run (HTTP 429 count, timeouts, total runtime). The only measured latencies come from a single health check, where responses ranged from about 360 ms to about 31,000 ms across providers. That is one measurement, not an average.

### 2.2 Live test: Hermes Agent on a server

I ran Hermes Agent on a server and sent real emails to it.

- **Worked:** emails were received and triaged end to end, and the output was acceptable.
- **Did not work:** every step still called the same free-tier APIs, so the same rate limits and latency appeared. The test showed the approach works in practice, not that it can run day after day.

## 3. Causes

### 3.1 Latency

Free-tier response times were inconsistent: a provider could answer in a few hundred milliseconds, then take over 30 seconds on the next call.

Each email needs two sequential calls (categorize, then reply), each with a 25-second timeout (`TRIAGEFLOW_TIMEOUT` in `models.py`). With fallback across providers and up to three retry rounds (`triage.py`), one slow email could hold the pipeline for minutes. Across a 1,000-email batch, this is what pushed requests past their queue time limits.

### 3.2 Rate limits

Free tiers cap requests per minute and per day. A triage batch, many short requests back to back, is exactly the workload that hits those caps. Providers that passed the startup health check began returning `HTTP 429` partway through the run. The code waits a fixed five seconds before retrying, which does not match how these limits reset.

### 3.3 Availability

The health check (`health_check.py`) tests each model once, at startup. A model that passes can be throttled, overloaded or withdrawn minutes later. Free-tier model IDs are also renamed, retired or moved to paid tiers often, so keeping `providers.py` current became ongoing maintenance.

### 3.4 How the failures compounded

- **Silent misclassification (a bug in my code).** `categorize_email()` in `models.py` maps any response that isn't a known category to `GENERAL_INQUIRY`, including error strings such as `API Error 429`. The fallback in `triage.py` saw a valid category and never tried another provider, and wrong categories were written into the learning data.
- **Distorted learning.** `database.py` ranks models by processing time and tokens. With latency driven by provider load and categories skewed by masked errors, the learned rankings reflected API noise rather than model quality.
- **Unstable routing.** Providers were set aside after three consecutive failures, restored to the active pool on retry, then failed again. Under free-tier conditions, the router spent more effort switching providers than triaging.

The first is a bug and is fixable. The other two are design weaknesses: both assumed the API layer would be mostly reliable.

## 4. Why development is paused

Better rate-limit handling, caching and more providers would all help. I paused anyway, for four reasons:

1. **The main constraint is outside the code.** Latency, quotas and uptime belong to the providers. Fixing the masked-error bug would not make free APIs faster or more available.
2. **Free and reliable conflict.** Reliability requires paid APIs or capable local hardware, which changes the project's core promise. That should be a deliberate decision, not something reached through patches.
3. **The next feature raised the stakes.** Gmail integration would have connected a real inbox to a pipeline that could misclassify email silently.
4. **New features would inherit the instability.** Each addition would add more ways for the same API problems to surface.

The architecture (live health checks, cost-aware routing, per-category learning) is sound. Testing showed where its limit is.

## 5. Planned work, on hold

### 5.1 Email integrations

- Gmail through the Gmail API (OAuth2): read unread mail, triage it, and save replies as **drafts only**, for a person to review. Nothing is sent automatically.
- Flag sensitive emails (billing disputes, critical bugs) with a `[NEEDS HUMAN REVIEW]` marker.
- Outlook and IMAP after Gmail.

### 5.2 Agent harness

The plan was to run TriageFlow inside an existing open-source agent harness rather than build retries, memory and scheduling from scratch. Two candidates were considered:

- **Hermes Agent:** preferred, and already tested on a server (section 2.2).
- **OpenClaw:** considered as an alternative.

An email agent handles private data and processes untrusted input from anyone who can send an email, so security comes first. I prefer Hermes over OpenClaw for security reasons. This is my current understanding: I have not audited or independently verified the security of either.

The server test also showed that a harness does not solve the API problem. An agent built on unreliable endpoints is as unreliable as those endpoints.

## 6. Requirements for a restart

1. **A reliable model backend:** a local model on capable hardware, or a paid API tier with predictable limits and uptime. Free tiers become optional.
2. **Fail loudly:** an error must never become a valid category. Failed calls are retried or flagged, never guessed.
3. **Proper rate-limit handling:** exponential backoff with jitter, respect for `Retry-After`, and client-side throttling to stay under quota.
4. **Continuous health tracking:** monitor providers throughout a run and keep failed calls out of the learning data.
5. **Measurement:** record 429s, timeouts and runtime for every batch.
6. **Then** Gmail integration and Hermes Agent, with drafts-only output, human review, and every incoming email treated as untrusted input.

## 7. Lessons

- **Working and reliable are different.** Both tests completed, but with timeouts, rate-limit errors and queue failures, so neither showed reliable operation.
- **Monitor dependencies continuously.** A single health check at startup is not enough.
- **Free has a cost,** paid in latency, quotas and maintenance.
- **Silent fallbacks hide failures.** My code turned errors into a default category, which is worse than a crash.
- **Measure from the start.** Without recorded figures, the extent of the problems can only be described, not quantified.
- **Pausing is a valid decision** when the foundation isn't ready.

The code remains public under the MIT license. You're welcome to fork it, learn from it, or run it on a more dependable backend.
