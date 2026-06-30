#!/usr/bin/env python3
"""
TriageFlow Test - Quick test runner
Processes 1000 sample emails and shows results
"""

import os
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))

from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

load_dotenv()

def detect_models():
    """Detect available models"""
    available = {}
    
    print("\n[*] Checking available models...\n")
    
    tests = [
        ('claude', 'ANTHROPIC_API_KEY', 'Claude'),
        ('openai', 'OPENAI_API_KEY', 'OpenAI'),
        ('gemini', 'GOOGLE_API_KEY', 'Gemini'),
        ('openrouter', 'OPENROUTER_API_KEY', 'OpenRouter'),
    ]
    
    for model_type, key_name, name in tests:
        if os.getenv(key_name):
            try:
                model = TriageModel(model_type)
                if model.api_connected:
                    print(f"  [OK] {name}")
                    available[model_type] = model
            except:
                pass
    
    if not available:
        print("  [ERROR] No models configured!")
        print("  Add API keys to .env and try again")
        sys.exit(1)
    
    return available

def main():
    print("\n" + "=" * 70)
    print("  TRIAGEFLOW TEST - 1000 EMAILS")
    print("=" * 70)
    
    # Load emails
    email_file = Path(__file__).parent / 'data' / 'emails_1000.txt'
    if not email_file.exists():
        print(f"\nERROR: {email_file} not found")
        sys.exit(1)
    
    with open(email_file, 'r') as f:
        emails = [line.strip() for line in f.readlines() if line.strip()]
    
    print(f"\n[+] Loaded {len(emails)} emails")
    
    # Detect models
    models = detect_models()
    print(f"[+] {len(models)} model(s) ready\n")
    
    # Initialize
    db = TriageDatabase()
    triage = EmailTriage(db, models)
    
    # Process
    print(f"{'#':<6} {'Category':<18} {'Model':<15} {'Tokens':<10} {'Status'}")
    print("-" * 70)
    
    results = []
    cumulative_cost = 0
    
    for idx, email in enumerate(emails, 1):
        result = triage.process_single_email(email)
        cost = result['tokens_used'] * 0.00001
        cumulative_cost += cost
        
        # Status
        if idx <= 20:
            status = "COLD START"
        elif idx <= 100:
            status = "LEARNING"
        elif idx <= 500:
            status = "OPTIMIZING"
        else:
            status = "OPTIMIZED"
        
        print(f"{idx:<6} {result['category']:<18} {result['model_used']:<15} "
              f"{result['tokens_used']:<10} {status}")
        
        results.append({
            'number': idx,
            'category': result['category'],
            'model': result['model_used'],
            'tokens': result['tokens_used'],
            'cost': cost,
            'cumulative_cost': cumulative_cost,
        })
        
        if idx % 100 == 0:
            print(f"  [{idx}/{len(emails)}] ${cumulative_cost:.6f}")
    
    # Export CSV
    csv_file = Path(__file__).parent / 'results.csv'
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)
    
    # Stats
    stats = triage.get_stats()
    
    print("\n" + "=" * 70)
    print("  RESULTS")
    print("=" * 70)
    print(f"\n  Total Emails    : {stats['total']:,}")
    print(f"  Total Tokens    : {stats['total_tokens']:,}")
    print(f"  Total Cost      : ${cumulative_cost:.6f}")
    print(f"  Avg Tokens      : {stats['avg_tokens']:.0f}")
    print(f"\n  Model Usage:")
    for model, count in stats['model_usage'].items():
        pct = (count / stats['total']) * 100
        print(f"    {model:<15}: {count:>4} ({pct:>5.1f}%)")
    
    print(f"\n[+] Results saved to: {csv_file}")
    print(f"[+] Run: python visualize.py")
    print()

if __name__ == "__main__":
    main()
