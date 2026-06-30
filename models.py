#!/usr/bin/env python3
"""
Models module - supports ANY model with an API endpoint
Claude, Gemini, OpenAI, OpenRouter, Ollama, vLLM, LM Studio, or any OpenAI-compatible API
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
          'openai'     - OpenAI (GPT-4, GPT-3.5-turbo)
          'openrouter' - OpenRouter (50+ free/cheap models)
          'ollama'     - Local Ollama (FREE)
          'lmstudio'   - Local LM Studio (FREE)
          'custom'     - Any OpenAI-compatible API
        """
        self.model_type = model_type
        self.custom_url = custom_url
        self.custom_model_name = custom_model_name
        self.tokens_used = 0
        self.api_connected = False
        self.init_client()

    def init_client(self):
        """Initialize API client based on model type"""
        try:
            if self.model_type == 'openai':
                from openai import OpenAI
                self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
                self.api_connected = True
                print(f"    [✓] OpenAI API connected")

            elif self.model_type == 'claude':
                import anthropic
                self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
                self.api_connected = True
                print(f"    [✓] Claude API connected")

            elif self.model_type == 'gemini':
                import google.generativeai as genai
                genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
                self.model = genai.GenerativeModel('gemini-pro')
                self.api_connected = True
                print(f"    [✓] Gemini API connected")

            elif self.model_type == 'openrouter':
                self.api_key = os.getenv('OPENROUTER_API_KEY')
                self.base_url = "https://openrouter.ai/api/v1"
                self.model_name = self.custom_model_name or os.getenv('OPENROUTER_MODEL', 'mistralai/mistral-7b-instruct')
                headers = {"Authorization": f"Bearer {self.api_key}"}
                r = requests.get(f"{self.base_url}/models", headers=headers, timeout=5)
                if r.status_code == 200:
                    self.api_connected = True
                    print(f"    [✓] OpenRouter API connected")

            elif self.model_type == 'ollama':
                self.base_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
                self.model_name = self.custom_model_name or os.getenv('OLLAMA_MODEL', 'llama2')
                r = requests.get(f"{self.base_url}/api/tags", timeout=5)
                if r.status_code == 200:
                    self.api_connected = True
                    print(f"    [✓] Ollama connected ({self.model_name})")

            elif self.model_type == 'lmstudio':
                self.base_url = os.getenv('LMSTUDIO_URL', 'http://localhost:1234/v1')
                self.model_name = self.custom_model_name or os.getenv('LMSTUDIO_MODEL', 'local-model')
                r = requests.get(f"{self.base_url}/models", timeout=5)
                if r.status_code == 200:
                    self.api_connected = True
                    print(f"    [✓] LM Studio connected ({self.model_name})")

            elif self.model_type == 'custom':
                self.base_url = self.custom_url or os.getenv('CUSTOM_LLM_URL')
                self.api_key = os.getenv('CUSTOM_LLM_API_KEY', 'none')
                self.model_name = self.custom_model_name or os.getenv('CUSTOM_LLM_MODEL', 'default')
                self.api_connected = True
                print(f"    [✓] Custom API configured")
        except Exception as e:
            print(f"    [!] Connection error: {str(e)[:60]}")
            self.api_connected = False

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
        response_text, tokens = self._call_api(system_prompt, email_text, max_tokens=10)
        processing_time = time.time() - start_time
        self.tokens_used = tokens

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
        response_text, tokens = self._call_api(system_prompt, email_text, max_tokens=150)
        processing_time = time.time() - start_time
        self.tokens_used = tokens

        return response_text, self.tokens_used, processing_time

    def _call_api(self, system_prompt, user_message, max_tokens=150):
        """Route API call to correct provider - returns (text, tokens)"""
        try:
            if self.model_type == 'openai':
                return self._call_openai(system_prompt, user_message, max_tokens)
            elif self.model_type == 'claude':
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
            error_msg = f"Error: {str(e)[:50]}"
            estimated_tokens = len(user_message.split()) + len(system_prompt.split())
            return error_msg, estimated_tokens

    def _call_openai(self, system_prompt, user_message, max_tokens):
        """Call OpenAI API (GPT-4, GPT-3.5-turbo, etc)"""
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        tokens = response.usage.total_tokens
        return response.choices[0].message.content.strip(), tokens

    def _call_claude(self, system_prompt, user_message, max_tokens):
        """Call Anthropic Claude API"""
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )
        tokens = response.usage.input_tokens + response.usage.output_tokens
        return response.content[0].text.strip(), tokens

    def _call_gemini(self, system_prompt, user_message):
        """Call Google Gemini API"""
        response = self.model.generate_content(f"{system_prompt}\n\nEmail: {user_message}")
        text = response.text.strip()
        tokens = len(user_message.split()) + len(text.split()) + 50
        return text, tokens

    def _call_openai_compatible(self, base_url, api_key, model_name, system_prompt, user_message, max_tokens):
        """Generic OpenAI-compatible API call"""
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
            tokens = usage.get('total_tokens', len(user_message.split()) + max_tokens)
            text = result['choices'][0]['message']['content'].strip()
            return text, tokens
        else:
            error = f"API Error {response.status_code}"
            estimated = len(user_message.split()) + max_tokens
            return error, estimated

    def _call_ollama(self, system_prompt, user_message):
        """Call local Ollama instance - 100% FREE"""
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
            tokens = len(user_message.split()) + len(content.split())
            return content.strip(), tokens
        else:
            error = f"Ollama Error: {response.status_code}"
            estimated = len(user_message.split()) + 50
            return error, estimated

    def get_tokens_used(self):
        return self.tokens_used

    def get_model_info(self):
        """Return info about this model"""
        info = {
            'openai': 'OpenAI (GPT-3.5/GPT-4)',
            'claude': 'Claude (Premium)',
            'gemini': 'Gemini (Free tier)',
            'openrouter': 'OpenRouter (Free models)',
            'ollama': 'Ollama (Local)',
            'lmstudio': 'LM Studio (Local)',
            'custom': 'Custom API',
        }
        status = "✓" if self.api_connected else "✗"
        return f"{status} {info.get(self.model_type, self.model_type)}"
