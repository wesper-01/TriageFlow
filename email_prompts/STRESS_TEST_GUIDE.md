# TriageFlow - Stress Test Guide

**Generate 1000+ emails and test TriageFlow's performance**

---

## 🎯 Overview

Stress test TriageFlow with 1000+ realistic support emails across 5 categories:
- BILLING (200)
- TECHNICAL (200)  
- FEATURE_REQUEST (200)
- FEEDBACK (200)
- GENERAL_INQUIRY (200)

---

## 📋 Method 1: Auto-Generate with Python (Easiest)

### Step 1: Run Generator Script

```bash
python generate_stress_test_emails.py
```

**What it does:**
- Uses Claude or OpenAI API to generate 1000 unique emails
- Saves to `emails_stress_test.txt`
- Takes 2-3 minutes

**Output:**
```
[*] Using Claude (Anthropic)
[*] Sending request to Claude...
[+] Generated 1000 emails
[+] Saved to: emails_stress_test.txt

✅ Success! Generated 1000 test emails

Next: python test.py
```

### Step 2: Run Stress Test

```bash
# Use the generated file
cp emails_stress_test.txt data/emails_test.txt

# Run TriageFlow test
python test.py
```

---

## 📋 Method 2: Manual Generation with Prompt

### Step 1: Use the Prompt File

Copy `STRESS_TEST_PROMPT.txt` and paste into Claude, ChatGPT, or your AI:

1. Open Claude (claude.ai)
2. Copy entire content from `STRESS_TEST_PROMPT.txt`
3. Paste into chat
4. Claude generates 1000 emails
5. Copy output

### Step 2: Save the Output

Create file: `emails_stress_test.txt`

Paste the 1000 emails (one per line):
```
I was charged twice for my subscription this month.
We're getting 500 errors when calling the /api/users endpoint.
Would love to see dark mode in the dashboard.
[...continue for 1000 total...]
```

### Step 3: Run Stress Test

```bash
python test.py
```

---

## 🚀 Running the Stress Test

### Option A: Use Auto-Generated Emails

```bash
python generate_stress_test_emails.py
```

Creates: `emails_stress_test.txt` (1000 emails)

### Option B: Use Provided Sample Emails

```bash
python test.py
```

Uses: `data/emails_1000.txt` (already included - 1000 emails)

### Option C: Use Your Custom Emails

```bash
# Create emails_custom.txt with your emails (one per line)

# Then run test
python test.py
```

---

## 📊 Expected Results

After running stress test with 1000 emails:

```
[+] Loaded 1000 emails
[*] Checking available models...
  [OK] Claude
[+] 1 model(s) ready

#      Category           Model           Tokens     Status
──────────────────────────────────────────────────────────────
1      TECHNICAL          claude          485        COLD START
2      BILLING            claude          520        COLD START
...
500    FEEDBACK           openrouter      120        OPTIMIZING
...
1000   TECHNICAL          openrouter      62         OPTIMIZED

[+] Results saved to: results.csv

SUMMARY:
  Total Emails        : 1,000
  Total Tokens        : 185,000
  Total Cost          : $0.018500
  Avg Tokens/Email    : 185.0
  Token Savings       : 87% (from 485 → 62)

✅ TEST COMPLETE
```

---

## 🔧 Customizing Email Generation

### Generate Your Own Categories

Edit `STRESS_TEST_PROMPT.txt` to add new categories:

```
Add new category examples:
- PERFORMANCE: Slow performance, timeouts
- SECURITY: Security concerns, compliance
- INTEGRATION: Third-party integration issues
```

### Generate Different Quantities

Modify the prompt to generate 2000, 5000, or 10000 emails:

```
Change: "Generate exactly 1000 UNIQUE"
To: "Generate exactly 5000 UNIQUE"
```

### Generate for Specific Use Case

Customize the company and product type:

```
Replace: "support emails for a SaaS platform"
With: "support emails for a payment processing service"
```

---

## 📈 Performance Metrics to Watch

During stress test, monitor:

1. **Token Reduction** — Should see 70-80% reduction
2. **Learning Curve** — First 20 emails use premium model, then optimize
3. **Category Distribution** — Should be 200 emails per category
4. **Model Usage** — Should see mix of premium and free models
5. **Processing Time** — Should decrease as patterns learn

---

## 🐛 Troubleshooting

### Issue: "No API key configured"
```bash
# Make sure .env has your key
cat .env

# If not, create it:
cp .env.example .env
# Edit with your API key
```

### Issue: "Python: Module not found"
```bash
# Install dependencies
pip install -r requirements.txt
```

### Issue: "Generated file not found"
```bash
# Check if generation succeeded
dir emails_stress_test.txt

# Or use built-in test file
python test.py  # Uses data/emails_1000.txt
```

### Issue: "Generator too slow"
```bash
# Using Claude is faster than OpenAI
# Check which API is configured in .env
# Claude: ANTHROPIC_API_KEY
# OpenAI: OPENAI_API_KEY
```

---

## 💡 Pro Tips

1. **Multiple Generations** — Run generator multiple times to create 5000, 10000+ emails
2. **Real Data** — Replace with actual customer support emails for realistic test
3. **Mix Models** — Test with different models configured in .env
4. **Monitor Trends** — Save results.csv and track token reduction over time
5. **Benchmark** — Compare results with/without optimization

---

## 📊 Files Reference

| File | Purpose |
|------|---------|
| `STRESS_TEST_PROMPT.txt` | Prompt to generate 1000 emails (copy-paste to Claude) |
| `generate_stress_test_emails.py` | Auto-generate 1000 emails using API |
| `data/emails_1000.txt` | Pre-generated 1000 test emails |
| `emails_stress_test.txt` | Output from generator script |
| `results.csv` | Results from stress test (generated) |

---

## ✅ Complete Workflow

```bash
# 1. Setup
cp .env.example .env
# [Edit .env with your API key]

# 2. Generate or use existing emails
python generate_stress_test_emails.py
# OR use: data/emails_1000.txt

# 3. Run stress test
python test.py

# 4. View results
python visualize.py

# 5. Analyze
cat results.csv
```

---

## 🎉 You're Ready!

**Stress test TriageFlow with 1000+ emails and see it learn and optimize in real-time!**

```bash
python generate_stress_test_emails.py
python test.py
python visualize.py
```

That's it! 🚀
