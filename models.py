#!/usr/bin/env python3
"""
Models module for interfacing with different LLM providers
"""

import os
import time
import anthropic
import google.generativeai as genai
import requests

class TriageModel:
    def __init__(self, model_type):
        self.model_type = model_type
        self.tokens_used = 0
        self.init_client()
    
    def init_client(self):
        """Initialize the appropriate API client"""
        if self.model_type == 'claude':
            self.client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        elif self.model_type == 'gemini':
            genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
            self.model = genai.GenerativeModel('gemini-pro')
        elif self.model_type == 'openrouter':
            self.api_key = os.getenv('OPENROUTER_API_KEY')
            self.base_url = "https://openrouter.ai/api/v1"
    
    def categorize_email(self, email_text):
        """Categorize an email"""
        system_prompt = """You are an email support triage assistant.
        Categorize the following email into ONE of these categories:
        - BILLING: Payment, invoicing, or subscription issues
        - TECHNICAL: Bug reports, API errors, technical issues
        - FEATURE_REQUEST: Feature requests or suggestions
        - FEEDBACK: Positive feedback or compliments
        - GENERAL_INQUIRY: Questions about the product
        
        Respond with ONLY the category name, nothing else."""
        
        start_time = time.time()
        
        if self.model_type == 'claude':
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=10,
                system=system_prompt,
                messages=[{"role": "user", "content": email_text}]
            )
            category = response.content[0].text.strip()
            self.tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        elif self.model_type == 'gemini':
            response = self.model.generate_content(f"{system_prompt}\n\nEmail: {email_text}")
            category = response.text.strip()
            self.tokens_used = len(email_text.split()) + len(category.split())  # Approximate
        
        elif self.model_type == 'openrouter':
            category = self._openrouter_call(system_prompt, email_text)
        
        processing_time = time.time() - start_time
        return category, self.tokens_used, processing_time
    
    def generate_response(self, email_text, category):
        """Generate a response to an email"""
        system_prompt = f"""You are a helpful support agent. Generate a professional, concise response 
        to the following support email. Category: {category}
        Keep the response under 100 words."""
        
        start_time = time.time()
        
        if self.model_type == 'claude':
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=150,
                system=system_prompt,
                messages=[{"role": "user", "content": email_text}]
            )
            generated_response = response.content[0].text.strip()
            self.tokens_used = response.usage.input_tokens + response.usage.output_tokens
        
        elif self.model_type == 'gemini':
            response = self.model.generate_content(f"{system_prompt}\n\nEmail: {email_text}")
            generated_response = response.text.strip()
            self.tokens_used = len(email_text.split()) + len(generated_response.split())
        
        elif self.model_type == 'openrouter':
            generated_response = self._openrouter_call(system_prompt, email_text)
        
        processing_time = time.time() - start_time
        return generated_response, self.tokens_used, processing_time
    
    def _openrouter_call(self, system_prompt, user_message):
        """Make a call to OpenRouter (uses free models)"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "mistralai/mistral-7b-instruct",  # Free model
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "max_tokens": 150
            }
            
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                return "Error: Could not reach OpenRouter"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_tokens_used(self):
        """Get total tokens used by this model"""
        return self.tokens_used
