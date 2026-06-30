#!/usr/bin/env python3
"""
TriageFlow Test - Quick test runner
Processes sample emails through every ACTUALLY WORKING free/paid model
(verified live via health_check.py) and shows results.
"""

import sys
import csv
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from health_check import discover_working_models
from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

load_dotenv()


def build_models(discovered):
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
    print("\n" + "=" * 70)
    print("  TRIAGEFLOW TEST")
    print("=" * 70)

    email_file = Path(__file__).parent / "data" / "emails_1000.txt"
    if not email_file.exists():
        print(f"\nERROR: {email_file} not found")
        sys.exit(1)

    with open(email_file, "r") as f:
        emails = [line.strip() for line in f.readlines() if line.strip()][:25]

    print(f"\n[+] Loaded {len(emails)} emails")

    discovered = discover_working_models(verbose=True)
    if not discovered:
        print("\nERROR: No working AI provider found.")
        print("Set a free API key in .env (Groq, OpenRouter, Gemini, Cerebras)")
        print("or install Ollama for a 100% local free option: https://ollama.ai")
        sys.exit(1)

    models = build_models(discovered)
    print(f"[+] {len(models)} model(s) ready\n")

    db = TriageDatabase()
    triage = EmailTriage(db, models)

    print(f"{'#':<6} {'Category':<18} {'Provider':<14} {'Tokens':<8} {'Status'}")
    print("-" * 70)

    results = []
    cumulative_cost = 0.0

    for idx, email in enumerate(emails, 1):
        result = triage.process_single_email(email)
        model_used = result["model_used"]
        is_free = models[model_used].free if model_used in models else True
        cost = 0.0 if is_free else result["tokens_used"] * 0.00001
        cumulative_cost += cost

        if idx <= 20:
            status = "COLD START"
        elif idx <= 100:
            status = "LEARNING"
        elif idx <= 500:
            status = "OPTIMIZING"
        else:
            status = "OPTIMIZED"

        print(f"{idx:<6} {result['category']:<18} {model_used:<14} "
              f"{result['tokens_used']:<8} {status}")

        results.append({
            "number": idx,
            "category": result["category"],
            "model": model_used,
            "tokens": result["tokens_used"],
            "free": is_free,
            "cost": cost,
            "cumulative_cost": cumulative_cost,
        })

        if idx % 100 == 0:
            print(f"  [{idx}/{len(emails)}] ${cumulative_cost:.6f}")

    csv_file = Path(__file__).parent / "results.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    stats = triage.get_stats()

    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"\n  Total Emails    : {stats['total']:,}")
    print(f"  Total Tokens    : {stats['total_tokens']:,}")
    print(f"  Total Cost      : ${cumulative_cost:.6f}"
          + ("  (100% free run!)" if cumulative_cost == 0 else ""))
    print(f"  Avg Tokens      : {stats['avg_tokens']:.0f}")
    print(f"\n  Provider Usage:")
    for model, count in stats["model_usage"].items():
        pct = (count / stats["total"]) * 100
        free_tag = "FREE" if models.get(model) and models[model].free else "PAID"
        print(f"    {model:<14} [{free_tag}]: {count:>4} ({pct:>5.1f}%)")

    print(f"\n[+] Results saved to: {csv_file}")
    print(f"[+] Run: python visualize.py")
    print()


if __name__ == "__main__":
    main()
