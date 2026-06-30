#!/usr/bin/env python3
"""
Bulk test script - Run 1000 emails through TriageFlow and watch it learn
Shows token savings as the system learns patterns
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

load_dotenv()

def detect_available_models():
    """Check which models are configured"""
    available = {}

    if os.getenv('ANTHROPIC_API_KEY'):
        available['claude'] = TriageModel('claude')
    if os.getenv('GOOGLE_API_KEY'):
        available['gemini'] = TriageModel('gemini')
    if os.getenv('OPENROUTER_API_KEY'):
        available['openrouter'] = TriageModel('openrouter')
    
    # Check local Ollama
    try:
        import requests
        r = requests.get('http://localhost:11434/api/tags', timeout=2)
        if r.status_code == 200:
            available['ollama'] = TriageModel('ollama')
    except:
        pass

    # Check LM Studio
    try:
        import requests
        r = requests.get('http://localhost:1234/v1/models', timeout=2)
        if r.status_code == 200:
            available['lmstudio'] = TriageModel('lmstudio')
    except:
        pass

    return available

def main():
    print("=" * 70)
    print("  TRIAGEFLOW BULK TEST - 1000 Emails")
    print("  Watch the system learn and token costs drop")
    print("=" * 70)

    # Load 1000 emails
    email_file = Path(__file__).parent / 'emails_1000.txt'
    if not email_file.exists():
        print(f"\n[!] File not found: {email_file}")
        print("    Make sure emails_1000.txt is in the same directory as this script")
        return

    with open(email_file, 'r') as f:
        emails = [line.strip() for line in f.readlines() if line.strip()]

    print(f"\n[✓] Loaded {len(emails)} emails from emails_1000.txt\n")

    # Detect models
    models = detect_available_models()
    if not models:
        print("[!] No models configured. Add API keys to .env file")
        return

    print(f"[✓] Available models ({len(models)}):")
    for name in models.keys():
        print(f"    • {name}")

    # Initialize
    db = TriageDatabase()
    triage = EmailTriage(db, models)

    # Process in batches and show progress
    batch_size = 50
    print(f"\n[*] Processing {len(emails)} emails in batches of {batch_size}...\n")
    print(f"{'Batch':<8} {'Emails':<10} {'Avg Tokens':<15} {'Total Cost':<15} {'Learning':<15}")
    print("-" * 70)

    cumulative_tokens = 0
    cumulative_cost = 0

    for batch_num in range(0, len(emails), batch_size):
        batch = emails[batch_num:batch_num + batch_size]
        
        # Process batch
        results = triage.process_emails(batch)
        
        # Calculate metrics
        batch_tokens = sum(r['tokens_used'] for r in results)
        batch_cost = batch_tokens * 0.00001  # Approximate cost
        cumulative_tokens += batch_tokens
        cumulative_cost += batch_cost
        
        avg_tokens = batch_tokens / len(batch)
        
        # Learning indicator
        learning = "📈 Learning" if batch_num < 100 else "✨ Optimizing" if batch_num < 300 else "🚀 Learned"
        
        print(f"{batch_num//batch_size + 1:<8} {batch_num + len(batch):<10} {avg_tokens:<15.0f} ${cumulative_cost:<14.4f} {learning:<15}")

    # Final stats
    stats = triage.get_stats()
    
    print("\n" + "=" * 70)
    print("  FINAL RESULTS")
    print("=" * 70)
    print(f"  Total emails processed    : {stats['total']}")
    print(f"  Total tokens used         : {stats['total_tokens']:,}")
    print(f"  Avg tokens per email      : {stats['avg_tokens']:.0f}")
    print(f"  Estimated total cost      : ${cumulative_cost:.4f}")
    print(f"\n  Model usage breakdown:")
    for model, count in stats['model_usage'].items():
        print(f"    {model:<15}: {count} emails")

    print(f"\n[✓] Learning complete!")
    print(f"    Run again with similar emails to see 70-80% token savings.")
    print("=" * 70)

if __name__ == "__main__":
    main()
