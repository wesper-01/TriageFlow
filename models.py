#!/usr/bin/env python3
"""
Models module - supports ANY model with an API endpoint
Claude, Gemini, OpenRouter, Ollama, vLLM, LM Studio, or any OpenAI-compatible API
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

class TriageModel:
    def __init__(self, model_type, custom_url=None, custom_model_name=None):
        """
        model_type options:
          'claude'     - Anthropic Claude API
          'gemini'     - Google Gemini API
          'openrouter' - OpenRouter (50+ free/cheap models)
          'ollama'     - Local Ollama (Llama, Mistral, etc - FREE)
          'lmstudio'   - Local LM Studio (FREE)
          'custom'     - Any OpenAI-compatible API endpoint
        """
        self.model_type = model_type
        self.custom_url = custom_url
        self.custom_model_name = custom_model_name
        self.tokens_used = 0
        self.init_client()

    def init_client(self):
        """Initialize API client based on model type"""
        if self.model_type == 'claude':
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            except ImportError:
                print("[!] anthropic package not installed. Run: pip install anthropic")

        elif self.model_type == 'gemini':
            try:
                import google.generativeai as genai
                genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
                self.model = genai.GenerativeModel('gemini-pro')
            except ImportError:
                print("[!] google-generativeai not installed. Run: pip install google-generativeai")

        elif self.model_type == 'openrouter':
            self.api_key = os.getenv('OPENROUTER_API_KEY')
            self.base_url = "https://openrouter.ai/api/v1"
            self.model_name = self.custom_model_name or "mistralai/mistral-7b-instruct"  # Free model

        elif self.model_type == 'ollama':
            # Ollama runs locally - totally FREE
            self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
            self.model_name = self.custom_model_name or os.getenv('OLLAMA_MODEL', 'llama2')

        elif self.model_type == 'lmstudio':
            # LM Studio runs locally - totally FREE
            self.base_url = os.getenv('LMSTUDIO_URL', 'http://localhost:1234/v1')
            self.model_name = self.custom_model_name or "local-model"

        elif self.model_type == 'custom':
            # Any OpenAI-compatible API
            self.base_url = self.custom_url or os.getenv('CUSTOM_LLM_URL')
            self.api_key = os.getenv('CUSTOM_LLM_API_KEY', 'none')
            self.model_name = self.custom_model_name or os.getenv('CUSTOM_LLM_MODEL', 'default')

    def categorize_email(self, email_text):
        """Categorize an email into support categories"""
        system_prompt = """You are an email support triage assistant.
Categorize the following email into ONE of these categories:
- BILLING: Payment, invoicing, or subscription issues
- TECHNICAL: Bug reports, API errors, technical issues
- FEATURE_REQUEST: Feature requests or suggestions
- FEEDBACK: Positive feedback or compliments
- GENERAL_INQUIRY: Questions about the product

Respond with ONLY the category name, nothing else."""

        start_time = time.time()
        response_text = self._call_api(system_prompt, email_text, max_tokens=10)
        processing_time = time.time() - start_time

        # Clean and validate category
        category = response_text.strip().upper()
        valid = ["BILLING", "TECHNICAL", "FEATURE_REQUEST", "FEEDBACK", "GENERAL_INQUIRY"]
        if category not in valid:
            category = "GENERAL_INQUIRY"

        return category, self.tokens_used, processing_time

    def generate_response(self, email_text, category):
        """Generate a response to an email"""
        system_prompt = f"""You are a helpful support agent. 
Generate a professional, concise response to this support email.
Category: {category}
Keep the response under 100 words. Be helpful and empathetic."""

        start_time = time.time()
        response_text = self._call_api(system_prompt, email_text, max_tokens=150)
        processing_time = time.time() - start_time

        return response_text, self.tokens_used, processing_time

    def _call_api(self, system_prompt, user_message, max_tokens=150):
        """Route API call to correct provider"""
        try:
            if self.model_type == 'claude':
                return self._call_claude(system_prompt, user_message, max_tokens)
            elif self.model_type == 'gemini':
                return self._call_gemini(system_prompt, user_message)
            elif self.model_type == 'openrouter':
                return self._call_openai_compatible(
                    self.base_url, self.api_key, self.model_name,
                    system_prompt, user_message, max_tokens
                )
            elif self.model_type == 'ollama':
                return self._call_ollama(system_prompt, user_message)
            elif self.model_type in ['lmstudio', 'custom']:
                return self._call_openai_compatible(
                    self.base_url, getattr(self, 'api_key', 'none'), self.model_name,
                    system_prompt, user_message, max_tokens
                )
        except Exception as e:
            return f"Error: {str(e)}"

    def _call_claude(self, system_prompt, user_message, max_tokens):
        """Call Anthropic Claude API"""
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        self.tokens_used = response.usage.input_tokens + response.usage.output_tokens
        return response.content[0].text.strip()

    def _call_gemini(self, system_prompt, user_message):
        """Call Google Gemini API"""
        response = self.model.generate_content(f"{system_prompt}\n\nEmail: {user_message}")
        self.tokens_used = len(user_message.split()) + len(response.text.split())
        return response.text.strip()

    def _call_openai_compatible(self, base_url, api_key, model_name, system_prompt, user_message, max_tokens):
        """
        Generic OpenAI-compatible API call
        Works with: OpenRouter, LM Studio, vLLM, any local server
        """
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": max_tokens
        }
        response = requests.post(f"{base_url}/chat/completions", headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            usage = result.get('usage', {})
            self.tokens_used = usage.get('total_tokens', len(user_message.split()) + max_tokens)
            return result['choices'][0]['message']['content'].strip()
        else:
            return f"API Error {response.status_code}: {response.text[:100]}"

    def _call_ollama(self, system_prompt, user_message):
        """
        Call local Ollama instance - 100% FREE
        Install: https://ollama.ai
        Models: ollama pull llama2 / mistral / phi / etc
        """
        data = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            "stream": False
        }
        response = requests.post(f"{self.base_url}/api/chat", json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            content = result.get('message', {}).get('content', '')
            # Approximate token count for local models
            self.tokens_used = len(user_message.split()) + len(content.split())
            return content.strip()
        else:
            return f"Ollama Error: {response.status_code}"

    def get_tokens_used(self):
        return self.tokens_used

    def get_model_info(self):
        """Return info about this model for display"""
        info = {
            'claude': 'Anthropic Claude (Premium)',
            'gemini': 'Google Gemini (Free tier available)',
            'openrouter': f'OpenRouter: {getattr(self, "model_name", "free model")}',
            'ollama': f'Local Ollama: {getattr(self, "model_name", "llama2")} (FREE)',
            'lmstudio': f'LM Studio: {getattr(self, "model_name", "local")} (FREE)',
            'custom': f'Custom API: {getattr(self, "model_name", "custom")}',
        }
        return info.get(self.model_type, self.model_type)
