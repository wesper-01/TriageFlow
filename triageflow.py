#!/usr/bin/env python3
"""
TriageFlow - Main CLI
Free & open-source AI email triage that auto-discovers which AI
providers are actually working (pinged live) and routes emails to the
cheapest (ideally free) reliable option for each task.
"""

import sys
from dotenv import load_dotenv

from health_check import discover_working_models
from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

load_dotenv()


def build_models(discovered):
    """Turn health_check results into a {provider_id: TriageModel} dict."""
    models = {}
    for d in discovered:
        models[d["provider"]] = TriageModel(
            provider_id=d["provider"],
            model_name=d["model"],
            label=d["label"],
            free=d["free"],
        )
    return models


def main():
    db = TriageDatabase()

    discovered = discover_working_models(verbose=True)

    if not discovered:
        print("ERROR: No working AI provider found.\n")
        print("TriageFlow is 100% free-tier friendly. To get started, set ONE")
        print("of these in your .env file (free tiers, no credit card needed):\n")
        print("  GROQ_API_KEY        -> https://console.groq.com/keys")
        print("  OPENROUTER_API_KEY  -> https://openrouter.ai/keys")
        print("  GOOGLE_API_KEY      -> https://aistudio.google.com/apikey")
        print("  CEREBRAS_API_KEY    -> https://cloud.cerebras.ai/")
        print("\nOr install Ollama for a 100% local, unlimited, free option:")
        print("  https://ollama.ai")
        sys.exit(1)

    models = build_models(discovered)
    triage = EmailTriage(db, models)

    print("=" * 70)
    print("  TRIAGEFLOW - Free & Open Source Email Triage")
    print("=" * 70)
    print("\nEnter emails (one per line, empty line to finish):\n")

    emails = []
    while True:
        try:
            line = input()
            if not line.strip():
                break
            emails.append(line)
        except EOFError:
            break

    if not emails:
        print("No emails provided")
        return

    print("\n" + "=" * 70)
    print("  PROCESSING")
    print("=" * 70 + "\n")
    print(f"{'Category':<18} {'Provider':<14} {'Tokens':<8} {'Cost':<10} {'Response':<30}")
    print("-" * 85)

    total_tokens = 0
    total_cost = 0.0

    for email in emails:
        result = triage.process_single_email(email)

        tokens = result["tokens_used"]
        model_used = result["model_used"]
        is_free = models[model_used].free if model_used in models else True
        cost = 0.0 if is_free else tokens * 0.00001
        total_tokens += tokens
        total_cost += cost

        response_preview = result.get("response", "")[:25]
        cost_display = "FREE" if is_free else f"${cost:.6f}"

        print(f"{result['category']:<18} {model_used:<14} {tokens:<8} "
              f"{cost_display:<10} {response_preview:<30}")

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"\n  Emails Processed    : {len(emails)}")
    print(f"  Total Tokens Used   : {total_tokens:,}")
    print(f"  Total Cost          : ${total_cost:.6f}"
          + ("  (100% free run!)" if total_cost == 0 else ""))
    print(f"  Avg Tokens/Email    : {total_tokens/len(emails):.0f}")
    print()


if __name__ == "__main__":
    main()
