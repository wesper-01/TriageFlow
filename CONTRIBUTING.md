# Contributing to TriageFlow

First off, thank you for considering contributing to TriageFlow! It's people like you that make the open-source community such a great place to learn, inspire, and create.

## 🛠️ What We Are Building
TriageFlow is designed to be the ultimate **zero-cost, multi-provider AI email triage system**. Our core philosophy is:
- **Free-Tier First**: The system should run on 100% free or local APIs out of the box.
- **Fail-Fast**: We verify model configurations live before we process data.
- **Dynamic Optimization**: The system inherently learns and optimizes for speed and accuracy without manual intervention.

## 🤝 How You Can Help

### 1. Adding New Providers 🔌
If you know of a new AI provider with a legitimate free tier, we want it! 
Adding a new provider is as simple as adding an entry to `PROVIDERS` in `providers.py`.
- Ensure you document the exact Free model IDs.
- Make sure they use OpenAI-compatible, Anthropic, or Gemini schemas (or add a new adapter in `models.py`).

### 2. Updating Model IDs 🔄
Free-tier model IDs frequently change or get deprecated (e.g., `llama-3.1-8b` -> `llama-3.1-8b-instant`). If you notice a provider returning 404s during the health check, PRs to update the fallback arrays in `providers.py` are highly appreciated.

### 3. Improving the Triage Engine 🧠
If you have ideas for improving the dynamic routing latency measurements or the mid-run fallback logic, please open an issue first so we can discuss the architecture!

## 📜 Pull Request Process
1. Fork the repo and create your branch from `main`.
2. Ensure you have tested your changes locally using `python health_check.py` and `python test.py`.
3. Update the `README.md` with details of changes to the interface or new providers.
4. Issue a PR with a clear description of the problem and your solution.

Happy hacking! 🚀
