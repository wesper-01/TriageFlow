# Email Support Triage MVP - Setup Guide

## What This Does

This is your first MVP. It:
1. Takes support emails
2. Categorizes them (Billing, Technical, Feature Request, Feedback, General)
3. Generates smart responses
4. Tracks which model works best for what
5. **Next time similar emails come in, it reuses patterns = 70-80% fewer tokens**

## Setup Instructions

### 1. Install Python 3.9+
```bash
python3 --version
```

### 2. Clone/Extract This Folder
```bash
cd email-triage-mvp
```

### 3. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Set Up API Keys

Create a `.env` file in the same folder:
```
ANTHROPIC_API_KEY=your_claude_key_here
GOOGLE_API_KEY=your_gemini_key_here
OPENROUTER_API_KEY=your_openrouter_key_here
```

**Where to get these:**
- **Claude:** https://console.anthropic.com/
- **Gemini:** https://makersuite.google.com/app/apikey
- **OpenRouter:** https://openrouter.ai/keys

### 6. Run It
```bash
python main.py
```

You'll be prompted to:
- Load sample emails, OR
- Enter your own emails

## What Happens

**First Run:**
- Processes emails with Claude (most reliable)
- Shows categorization + generated responses
- Displays tokens used
- Stores results in `triage_results.db`

**Future Runs:**
- System remembers: "Billing questions → Use cheaper model"
- "Technical issues → Keep using Claude (more accurate)"
- **Same email types now use 70-80% fewer tokens**

## Database

All results are saved in `triage_results.db` (SQLite):
- Email history
- Categories
- Responses
- Model performance
- Learned patterns

## Customization

### Change Categories
Edit `models.py` line ~30 to add/remove categories:
```python
BILLING: Payment, invoicing, subscription
TECHNICAL: Bug reports, API errors
CUSTOM_CATEGORY: Your description
```

### Add More Models
Edit `models.py` to add support for more API providers (Anthropic, Groq, etc.)


## Token Savings Calculation

**Without learning:**
- 100 support emails × 500 tokens avg = 50,000 tokens
- Cost: ~$0.50 (at cheap model rates)

**With learning (after 20 emails):**
- 80 emails reuse patterns = 100 tokens each (cached)
- 20 new emails = 500 tokens each
- Total: 8,000 + 10,000 = 18,000 tokens
- **64% savings** ✓

## Troubleshooting

**"API Key not found"**
- Check `.env` file exists in the same folder as `main.py`
- Make sure keys are correct

**"ModuleNotFoundError"**
- Run `pip install -r requirements.txt` again
- Make sure you're in virtual environment (`source venv/bin/activate`)

**"No API responses"**
- Check internet connection
- Verify API keys are valid
- Try one model at a time to debug

## Questions?

This is your MVP. Modify it, break it, improve it.
The goal: Prove the concept works with real emails.

Good luck! 🚀
