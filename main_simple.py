#!/usr/bin/env python3
"""
TriageFlow - Main CLI
Email triage system with AI routing
"""

import os
import sys
from dotenv import load_dotenv

from models import TriageModel
from database import TriageDatabase
from triage import EmailTriage

load_dotenv()

def main():
    """Main CLI"""
    
    # Initialize
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
        sys.exit(1)
    
    triage = EmailTriage(db, available_models)
    
    # Read emails from stdin or file
    print("Enter emails (one per line, empty line to finish):")
    print()
    
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
    
    # Process
    print("\nProcessing...\n")
    print(f"{'Category':<20} {'Model':<15} {'Tokens':<10} {'Response':<40}")
    print("-" * 85)
    
    for email in emails:
        result = triage.process_single_email(email)
        response = result.get('response', 'N/A')[:35] + "..."
        
        print(f"{result['category']:<20} {result['model_used']:<15} "
              f"{result['tokens_used']:<10} {response:<40}")
    
    print()

if __name__ == "__main__":
    main()
