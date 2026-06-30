#!/usr/bin/env python3
"""
models.py — Wraps a single (provider, model) pair discovered by
health_check.py and exposes a uniform .categorize_email() /
.generate_response() interface, regardless of which API it's calling.
"""

import os
import time
import requests
from dotenv import load_dotenv

import providers as P

load_dotenv()

CATEGORIES = ["BILLING", "TECHNICAL", "FEATURE_REQUEST", "FEEDBACK", "GENERAL_INQUIRY"]

# Hard ceiling on any single API call during a real triage run (seconds)
API_CALL_TIMEOUT = int(os.getenv("TRIAGEFLOW_TIMEOUT", "25"))

# Errors we recognise as "this provider failed" — used for clean log suppression
_ERROR_PREFIXES = ("API Error", "Ollama Error", "Error:")

# How many times we silently swallow a repeated error before showing it again
_ERROR_REPEAT_SUPPRESS = 5


class TriageModel:
    def __init__(self, provider_id, model_name, label=None, free=True):
        """
        provider_id : key into providers.PROVIDERS, e.g. 'groq', 'ollama'
        model_name  : exact model id to call, e.g. 'llama-3.1-8b-instant'
        """
        self.provider_id = provider_id
        self.model_name = model_name
        self.label = label or P.PROVIDERS[provider_id]["label"]
        self.free = free
        self.kind = P.PROVIDERS[provider_id]["kind"]
        self.base_url = P.get_base_url(provider_id)
        self.api_key = P.get_api_key(provider_id)
        self.extra_headers = P.get_extra_headers(provider_id)
        self.tokens_used = 0
        self.api_connected = True  # assumed pre-verified by health_check
        self._error_counts: dict[str, int] = {}  # tracks repeated identical errors

    # ------------------------------------------------------------------
    # Public triage methods
    # ------------------------------------------------------------------

    def categorize_email(self, email_text):
        system_prompt = (
            "You are an email support triage assistant.\n"
            "Categorize the following email into ONE of these categories:\n"
            "- BILLING: Payment, invoicing, or subscription issues\n"
            "- TECHNICAL: Bug reports, API errors, technical issues\n"
            "- FEATURE_REQUEST: Feature requests or suggestions\n"
            "- FEEDBACK: Positive feedback or compliments\n"
            "- GENERAL_INQUIRY: Questions about the product\n\n"
            "Respond with ONLY the category name, nothing else."
        )
        start = time.time()
        text, tokens = self._call_api(system_prompt, email_text, max_tokens=10)
        elapsed = time.time() - start
        self.tokens_used = tokens

        category = text.strip().upper()
        if category not in CATEGORIES:
            category = "GENERAL_INQUIRY"
        return category, tokens, elapsed

    def generate_response(self, email_text, category):
        system_prompt = (
            "You are a helpful support agent. "
            "Generate a professional, concise response to this support email. "
            f"Category: {category}. "
            "Keep the response under 100 words. Be helpful and empathetic."
        )
        start = time.time()
        text, tokens = self._call_api(system_prompt, email_text, max_tokens=150)
        elapsed = time.time() - start
        self.tokens_used = tokens
        return text, tokens, elapsed

    def get_tokens_used(self):
        return self.tokens_used

    def get_model_info(self):
        tag = "FREE" if self.free else "PAID"
        return f"\u2713 {self.label} / {self.model_name} [{tag}]"

    # ------------------------------------------------------------------
    # Internal routing
    # ------------------------------------------------------------------

    def _log_error(self, error_msg: str):
        """Print an error, but suppress repetitions to keep logs readable."""
        count = self._error_counts.get(error_msg, 0) + 1
        self._error_counts[error_msg] = count
        if count == 1:
            print(f"  [!] {self.label}: {error_msg}")
        elif count % _ERROR_REPEAT_SUPPRESS == 0:
            print(f"  [!] {self.label}: {error_msg} (x{count} times)")

    def _call_api(self, system_prompt, user_message, max_tokens=150):
        try:
            if self.kind == "anthropic":
                return self._call_anthropic(system_prompt, user_message, max_tokens)
            elif self.kind == "gemini":
                return self._call_gemini(system_prompt, user_message, max_tokens)
            elif self.kind == "ollama":
                return self._call_ollama(system_prompt, user_message, max_tokens)
            else:  # openai_compatible
                return self._call_openai_compatible(system_prompt, user_message, max_tokens)
        except requests.exceptions.Timeout:
            error_msg = f"timed out after {API_CALL_TIMEOUT}s"
            self._log_error(error_msg)
            estimated = len(user_message.split()) + len(system_prompt.split())
            return f"Error: {error_msg}", estimated
        except Exception as e:
            error_msg = str(e)[:80]
            self._log_error(error_msg)
            estimated = len(user_message.split()) + len(system_prompt.split())
            return f"Error: {error_msg}", estimated

    def _call_openai_compatible(self, system_prompt, user_message, max_tokens):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
        }
        r = requests.post(f"{self.base_url}/chat/completions",
                           headers=headers, json=data, timeout=API_CALL_TIMEOUT)
        if r.status_code == 200:
            result = r.json()
            usage = result.get("usage", {})
            tokens = usage.get("total_tokens", len(user_message.split()) + max_tokens)
            text = result["choices"][0]["message"]["content"].strip()
            return text, tokens
        else:
            error = f"HTTP {r.status_code}"
            self._log_error(error)
            estimated = len(user_message.split()) + max_tokens
            return f"API Error {r.status_code}", estimated

    def _call_anthropic(self, system_prompt, user_message, max_tokens):
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return response.content[0].text.strip(), tokens

    def _call_gemini(self, system_prompt, user_message, max_tokens):
        url = (f"{self.base_url}/models/{self.model_name}:generateContent"
               f"?key={self.api_key}")
        payload = {
            "contents": [{"parts": [{"text": f"{system_prompt}\n\nEmail: {user_message}"}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        r = requests.post(url, json=payload, timeout=API_CALL_TIMEOUT)
        if r.status_code == 200:
            result = r.json()
            text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            tokens = len(user_message.split()) + len(text.split()) + 50
            return text, tokens
        else:
            self._log_error(f"HTTP {r.status_code}")
            estimated = len(user_message.split()) + max_tokens
            return f"API Error {r.status_code}", estimated

    def _call_ollama(self, system_prompt, user_message, max_tokens):
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "stream": False,
        }
        r = requests.post(f"{self.base_url}/api/chat", json=data, timeout=API_CALL_TIMEOUT)
        if r.status_code == 200:
            result = r.json()
            content = result.get("message", {}).get("content", "")
            tokens = len(user_message.split()) + len(content.split())
            return content.strip(), tokens
        else:
            self._log_error(f"HTTP {r.status_code}")
            estimated = len(user_message.split()) + 50
            return f"Ollama Error: {r.status_code}", estimated
