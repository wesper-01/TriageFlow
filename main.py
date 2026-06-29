#!/usr/bin/env python3
"""
Email Support Triage MVP
Categorizes and responds to support emails using Claude, Gemini, and free models
"""

import os
import json
from pathlib import Path
from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

def load_sample_emails():
    """Load sample emails from file"""
    sample_file = Path(__file__).parent / "emails_sample.txt"
    if not sample_file.exists():
        return []
    
    with open(sample_file, 'r') as f:
        content = f.read()
    
    # Parse emails (simple format: one email per line)
    emails = [line.strip() for line in content.split('\n') if line.strip()]
    return emails

def main():
    print("=" * 60)
    print("EMAIL SUPPORT TRIAGE MVP")
    print("=" * 60)
    
    # Initialize database
    db = TriageDatabase()
    
    # Initialize models
    models = {
        'claude': TriageModel('claude'),
        'gemini': TriageModel('gemini'),
        'openrouter': TriageModel('openrouter')
    }
    
    # Initialize triage engine
    triage_engine = EmailTriage(db, models)
    
    # Load sample emails or ask for input
    print("\n[1] Load sample emails")
    print("[2] Input custom emails")
    choice = input("Choose option (1-2): ").strip()
    
    if choice == '1':
        emails = load_sample_emails()
        if not emails:
            print("No sample emails found. Creating default samples...")
            emails = [
                "Hi, I've been trying to reset my password for 3 days and nothing works!",
                "Your product is amazing! Just wanted to say thanks.",
                "How much does the premium plan cost?",
                "The API keeps returning 500 errors when I try to sync data.",
            ]
    else:
        print("\nEnter emails (one per line, empty line to finish):")
        emails = []
        while True:
            email = input("Email: ").strip()
            if not email:
                break
            emails.append(email)
    
    if not emails:
        print("No emails to process.")
        return
    
    print(f"\nProcessing {len(emails)} emails...\n")
    
    # Process emails
    results = triage_engine.process_emails(emails)
    
    # Display results
    print("\n" + "=" * 60)
    print("TRIAGE RESULTS")
    print("=" * 60)
    
    for i, result in enumerate(results, 1):
        print(f"\n[Email {i}]")
        print(f"Original: {result['email'][:60]}...")
        print(f"Category: {result['category']}")
        print(f"Model used: {result['model_used']}")
        print(f"Response: {result['response'][:100]}...")
        print(f"Tokens used: {result['tokens_used']}")
    
    # Show stats
    stats = triage_engine.get_stats()
    print("\n" + "=" * 60)
    print("PERFORMANCE STATS")
    print("=" * 60)
    print(f"Total emails processed: {stats['total']}")
    print(f"Total tokens used: {stats['total_tokens']}")
    print(f"Average tokens per email: {stats['avg_tokens']:.1f}")
    print(f"Best model (by speed): {stats['fastest_model']}")
    print(f"\nModel breakdown:")
    for model, count in stats['model_usage'].items():
        print(f"  {model}: {count} emails")
    
    print("\n[Next run will reuse patterns for similar emails = 70-80% token savings]")
    print("=" * 60)

if __name__ == "__main__":
    main()
