#!/usr/bin/env python3
"""
Generate 1000+ test emails using Claude API
For stress testing TriageFlow
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def generate_emails_with_claude():
    """Generate 1000 test emails using Claude API"""
    
    try:
        import anthropic
    except ImportError:
        print("ERROR: anthropic library not installed")
        print("Run: pip install anthropic")
        sys.exit(1)
    
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)
    
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt = """Generate exactly 1000 UNIQUE support emails for a SaaS platform.

Requirements:
- 200 BILLING emails (payment, invoicing, subscription issues)
- 200 TECHNICAL emails (bugs, errors, API problems)
- 200 FEATURE_REQUEST emails (feature suggestions)
- 200 FEEDBACK emails (positive and negative feedback)
- 200 GENERAL_INQUIRY emails (general questions)

Each email should be:
- 1-3 sentences
- Realistic and diverse in tone
- Unique (no duplicates)
- Varied in writing style (professional, casual, frustrated, grateful)

Output format: ONE EMAIL PER LINE, no numbering, no category tags, just raw text.

Example of 5 emails:
I was charged twice for my subscription - please refund the duplicate charge immediately.
We're getting 500 errors when calling the /api/users endpoint after the latest update.
Would love to see a mobile app - our team is mostly on the go.
Your new dashboard is amazing, really improves our workflow!
How long does the free trial last and what payment methods do you accept?

Generate 1000 unique emails now:"""

    print("\n" + "=" * 80)
    print("  GENERATING 1000 STRESS TEST EMAILS")
    print("  Using Claude API (this may take 2-3 minutes)")
    print("=" * 80 + "\n")
    
    print("[*] Sending request to Claude...")
    
    message = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=8000,  # Large enough for many emails
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    emails_text = message.content[0].text
    
    # Parse emails (one per line)
    emails = [email.strip() for email in emails_text.strip().split('\n') if email.strip()]
    
    print(f"[+] Generated {len(emails)} emails")
    
    # Save to file
    output_file = Path(__file__).parent / 'emails_stress_test.txt'
    
    with open(output_file, 'w') as f:
        for email in emails:
            f.write(email + '\n')
    
    print(f"[+] Saved to: {output_file}")
    print(f"\n✅ Success! Generated {len(emails)} test emails")
    print(f"\nNext: python test.py")
    
    return output_file

def generate_emails_with_openai():
    """Alternative: Generate with OpenAI"""
    
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai library not installed")
        print("Run: pip install openai")
        sys.exit(1)
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)
    
    client = OpenAI(api_key=api_key)
    
    prompt = """Generate exactly 1000 UNIQUE support emails for a SaaS platform.
    
Requirements:
- 200 BILLING emails (payment, invoicing, subscription issues)
- 200 TECHNICAL emails (bugs, errors, API problems)
- 200 FEATURE_REQUEST emails (feature suggestions)
- 200 FEEDBACK emails (positive and negative feedback)
- 200 GENERAL_INQUIRY emails (general questions)

Each email should be 1-3 sentences, realistic, and unique.
Output: ONE EMAIL PER LINE, no numbering, just raw text."""

    print("\n" + "=" * 80)
    print("  GENERATING 1000 STRESS TEST EMAILS")
    print("  Using OpenAI API")
    print("=" * 80 + "\n")
    
    print("[*] Sending request to OpenAI...")
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        max_tokens=8000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    emails_text = response.choices[0].message.content
    emails = [email.strip() for email in emails_text.strip().split('\n') if email.strip()]
    
    output_file = Path(__file__).parent / 'emails_stress_test.txt'
    
    with open(output_file, 'w') as f:
        for email in emails:
            f.write(email + '\n')
    
    print(f"[+] Generated {len(emails)} emails")
    print(f"[+] Saved to: {output_file}")
    print(f"\n✅ Success!")
    
    return output_file

def main():
    print("\n" + "=" * 80)
    print("  TRIAGEFLOW - STRESS TEST EMAIL GENERATOR")
    print("=" * 80)
    
    # Check for .env
    if not Path('.env').exists():
        print("\nERROR: .env file not found")
        print("Create it from .env.example and add your API key")
        sys.exit(1)
    
    # Detect which model to use
    has_claude = bool(os.getenv('ANTHROPIC_API_KEY'))
    has_openai = bool(os.getenv('OPENAI_API_KEY'))
    
    if has_claude:
        print("\n[*] Using Claude (Anthropic)")
        generate_emails_with_claude()
    elif has_openai:
        print("\n[*] Using OpenAI")
        generate_emails_with_openai()
    else:
        print("\nERROR: No API key configured!")
        print("Add to .env:")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        print("  OR")
        print("  OPENAI_API_KEY=sk-...")
        sys.exit(1)

if __name__ == "__main__":
    main()
