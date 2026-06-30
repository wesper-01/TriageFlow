#!/usr/bin/env python3
"""
TriageFlow - Main CLI
Intelligent AI email triage system with automatic cost optimization
"""

import os
import sys
from dotenv import load_dotenv

from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

load_dotenv()

def main():
    """TriageFlow CLI - Process emails with AI routing"""
    
    # Initialize database
    db = TriageDatabase()
    
    # Detect available models
    available_models = {}
    
    for model_type in ['claude', 'openai', 'gemini', 'openrouter', 'ollama']:
        try:
            model = TriageModel(model_type)
            if model.api_connected:
                available_models[model_type] = model
        except:
            pass
    
    if not available_models:
        print("ERROR: No models available")
        print("Configure .env with at least one API key")
        print("\nSupported models:")
        print("  - ANTHROPIC_API_KEY (Claude)")
        print("  - OPENAI_API_KEY (GPT-4, GPT-3.5)")
        print("  - GOOGLE_API_KEY (Gemini)")
        print("  - OPENROUTER_API_KEY (Free models)")
        sys.exit(1)
    
    # Initialize triage system
    triage = EmailTriage(db, available_models)
    
    # Read emails from stdin or arguments
    print("=" * 70)
    print("  TRIAGEFLOW - Intelligent Email Triage")
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
    
    # Process emails
    print("\n" + "=" * 70)
    print("  PROCESSING")
    print("=" * 70 + "\n")
    print(f"{'Category':<20} {'Model':<15} {'Tokens':<10} {'Cost':<12} {'Response':<30}")
    print("-" * 85)
    
    total_tokens = 0
    total_cost = 0
    
    for email in emails:
        result = triage.process_single_email(email)
        
        tokens = result['tokens_used']
        cost = tokens * 0.00001
        total_tokens += tokens
        total_cost += cost
        
        response = result.get('response', 'Generated')[:25] + "..."
        
        print(f"{result['category']:<20} {result['model_used']:<15} "
              f"{tokens:<10} ${cost:<11.6f} {response:<30}")
    
    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"\n  Emails Processed    : {len(emails)}")
    print(f"  Total Tokens Used   : {total_tokens:,}")
    print(f"  Total Cost          : ${total_cost:.6f}")
    print(f"  Avg Tokens/Email    : {total_tokens/len(emails):.0f}")
    print(f"  Avg Cost/Email      : ${total_cost/len(emails):.6f}")
    print()

if __name__ == "__main__":
    main()
