#!/usr/bin/env python3
"""
TriageFlow - AI Email Support Triage
Works with ANY model that has an API:
  - Premium: Claude, Gemini
  - Free APIs: OpenRouter (Mistral, Llama, GLM, etc)
  - Local/FREE: Ollama, LM Studio, vLLM
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

load_dotenv()

def detect_available_models():
    """Check which models are configured in .env"""
    available = {}

    if os.getenv('ANTHROPIC_API_KEY'):
        available['claude'] = TriageModel('claude')

    if os.getenv('GOOGLE_API_KEY'):
        available['gemini'] = TriageModel('gemini')

    if os.getenv('OPENROUTER_API_KEY'):
        available['openrouter'] = TriageModel('openrouter')

    # Check local Ollama (no API key needed)
    ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
    try:
        import requests
        r = requests.get(f"{ollama_url}/api/tags", timeout=2)
        if r.status_code == 200:
            available['ollama'] = TriageModel('ollama')
    except:
        pass

    # Check local LM Studio (no API key needed)
    lmstudio_url = os.getenv('LMSTUDIO_URL', 'http://localhost:1234/v1')
    try:
        import requests
        r = requests.get(f"{lmstudio_url}/models", timeout=2)
        if r.status_code == 200:
            available['lmstudio'] = TriageModel('lmstudio')
    except:
        pass

    # Check custom API
    if os.getenv('CUSTOM_LLM_URL'):
        available['custom'] = TriageModel('custom')

    return available

def load_sample_emails():
    """Load sample emails from file"""
    sample_file = Path(__file__).parent / "emails_sample.txt"
    if not sample_file.exists():
        return []
    with open(sample_file, 'r') as f:
        emails = [line.strip() for line in f.readlines() if line.strip()]
    return emails

def main():
    print("=" * 60)
    print("  TRIAGEFLOW: AI Email Support Triage")
    print("  Works with any model, local or cloud")
    print("=" * 60)

    # Detect available models
    print("\n[*] Detecting available models...")
    models = detect_available_models()

    if not models:
        print("\n[!] No models configured.")
        print("    Add at least one to your .env file:")
        print("    ANTHROPIC_API_KEY=...  (Claude)")
        print("    GOOGLE_API_KEY=...     (Gemini)")
        print("    OPENROUTER_API_KEY=... (Free models)")
        print("    OLLAMA_URL=...         (Local - FREE)")
        print("    LMSTUDIO_URL=...       (Local - FREE)")
        return

    print(f"\n[✓] Available models ({len(models)}):")
    for name, model in models.items():
        print(f"    • {model.get_model_info()}")

    # Initialize database + triage engine
    db = TriageDatabase()
    triage_engine = EmailTriage(db, models)

    # Choose emails to process
    print("\n[1] Load sample emails (10 pre-loaded examples)")
    print("[2] Input custom emails manually")
    choice = input("\nChoose option (1-2): ").strip()

    if choice == '1':
        emails = load_sample_emails()
        if not emails:
            print("[!] No sample file found. Using built-in examples.")
            emails = [
                "Hi, I've been trying to reset my password for 3 days and nothing works!",
                "Your product is amazing! Just wanted to say thanks.",
                "How much does the premium plan cost?",
                "The API keeps returning 500 errors when I try to sync data.",
                "It would be great if you could add bulk export functionality.",
            ]
    else:
        print("\nEnter emails one per line. Empty line to finish:")
        emails = []
        while True:
            email = input("Email: ").strip()
            if not email:
                break
            emails.append(email)

    if not emails:
        print("[!] No emails to process.")
        return

    print(f"\n[*] Processing {len(emails)} emails...\n")

    # Process emails
    results = triage_engine.process_emails(emails)

    # Display results
    print("\n" + "=" * 60)
    print("  RESULTS")
    print("=" * 60)

    for i, result in enumerate(results, 1):
        print(f"\n[{i}] Email: {result['email'][:60]}...")
        print(f"    Category:   {result['category']}")
        print(f"    Model used: {result['model_used']}")
        print(f"    Tokens:     {result['tokens_used']}")
        print(f"    Response:   {result['response'][:80]}...")

    # Show stats
    stats = triage_engine.get_stats()
    print("\n" + "=" * 60)
    print("  PERFORMANCE STATS")
    print("=" * 60)
    print(f"  Total emails processed : {stats['total']}")
    print(f"  Total tokens used      : {stats['total_tokens']}")
    print(f"  Avg tokens per email   : {stats['avg_tokens']:.1f}")
    print(f"\n  Model breakdown:")
    for model, count in stats['model_usage'].items():
        print(f"    {model}: {count} emails")

    print("\n[!] Run again with similar emails to see token savings kick in.")
    print("    The more you run it, the cheaper it gets.")
    print("=" * 60)

if __name__ == "__main__":
    main()
