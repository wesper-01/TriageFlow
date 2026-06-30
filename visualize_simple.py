#!/usr/bin/env python3
"""
TriageFlow Visualize - Terminal charts
Reads results.csv and shows terminal visualization
"""

import csv
from pathlib import Path
from collections import defaultdict

def load_csv(csv_file):
    """Load results CSV"""
    if not csv_file.exists():
        print(f"\nERROR: {csv_file} not found")
        print("Run: python test.py")
        return None
    
    data = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append({
                'number': int(row['number']),
                'category': row['category'],
                'model': row['model'],
                'tokens': int(row['tokens']),
                'cost': float(row['cost']),
                'cumulative': float(row['cumulative_cost']),
            })
    return data

def print_section(title):
    print(f"\n{title}")
    print("─" * 70)

def visualize(data):
    print("\n" + "=" * 70)
    print("  TRIAGEFLOW - RESULTS VISUALIZATION")
    print("=" * 70)
    
    # Metrics
    total = len(data)
    total_tokens = sum(d['tokens'] for d in data)
    total_cost = data[-1]['cumulative']
    
    cold_start = sum(d['tokens'] for d in data[:20]) / 20
    warm_state = sum(d['tokens'] for d in data[-20:]) / 20
    savings = ((cold_start - warm_state) / cold_start * 100)
    
    print_section("METRICS")
    print(f"  Total Emails        : {total:,}")
    print(f"  Total Tokens        : {total_tokens:,}")
    print(f"  Total Cost          : ${total_cost:.6f}")
    print(f"  Avg Tokens/Email    : {total_tokens/total:.0f}")
    print(f"  Token Savings       : {savings:.1f}%")
    
    # Learning curve
    print_section("LEARNING CURVE")
    print(f"  Cold Start (1-20)   : {cold_start:.0f} tokens/email")
    print(f"  Warm State (980+)   : {warm_state:.0f} tokens/email")
    print(f"  Improvement         : {savings:.1f}%")
    
    # Token chart
    print("\n  Token Trend (100-email batches):")
    batches = []
    for i in range(0, total, 100):
        batch = data[i:i+100]
        if batch:
            avg = sum(d['tokens'] for d in batch) / len(batch)
            batches.append(avg)
    
    max_tokens = max(batches)
    min_tokens = min(batches)
    
    for row in range(int(max_tokens), 0, -50):
        line = f"  {row:>4} |"
        for avg in batches:
            if avg >= row:
                line += " # "
            else:
                line += " . "
        print(line)
    
    print("       +" + "─" * (len(batches) * 3))
    print(f"       Min: {min_tokens:.0f} | Max: {max_tokens:.0f}")
    
    # Category breakdown
    print_section("BY CATEGORY")
    categories = defaultdict(int)
    for d in data:
        categories[d['category']] += 1
    
    max_cat = max(categories.values())
    for cat in sorted(categories.keys()):
        count = categories[cat]
        pct = (count / total) * 100
        bar_len = int(pct / 2)
        bar = "#" * bar_len + "-" * (25 - bar_len)
        print(f"  {cat:<18} |{bar}| {pct:>5.1f}% ({count})")
    
    # Model usage
    print_section("MODEL USAGE")
    models = defaultdict(int)
    for d in data:
        models[d['model']] += 1
    
    max_model = max(models.values())
    for model in sorted(models.keys()):
        count = models[model]
        pct = (count / total) * 100
        bar_len = int(pct / 2)
        bar = "#" * bar_len + "-" * (25 - bar_len)
        print(f"  {model:<18} |{bar}| {pct:>5.1f}% ({count})")
    
    print("\n" + "=" * 70)
    print("  ANALYSIS COMPLETE")
    print("=" * 70 + "\n")

def main():
    csv_file = Path(__file__).parent / 'results.csv'
    
    print("\n[*] Loading results...")
    data = load_csv(csv_file)
    
    if not data:
        return
    
    print(f"[+] Loaded {len(data)} results\n")
    visualize(data)

if __name__ == "__main__":
    main()
