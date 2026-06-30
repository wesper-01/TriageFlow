#!/usr/bin/env python3
"""
Triage engine - routes emails to best available model
Learns over time which model works best for each category
Works with any model (premium, free API, or local)
"""

class EmailTriage:
    def __init__(self, database, models):
        self.db = database
        self.models = models  # Dict: model_name -> TriageModel
        self.results = []

        # Define model priority order (cheapest first after learning)
        # System tries these in order when no pattern exists yet
        self.priority_order = ['ollama', 'lmstudio', 'openrouter', 'gemini', 'claude', 'custom']

    def process_emails(self, emails):
        """Process a batch of emails"""
        self.results = []
        for email in emails:
            result = self.process_single_email(email)
            self.results.append(result)
        return self.results

    def process_single_email(self, email_text):
        """Process a single email through triage"""

        # Step 1: Pick best model for categorization
        # Use most reliable available model first time
        category_model_name = self._get_reliable_model()
        category_model = self.models[category_model_name]

        # Step 2: Categorize
        category, tokens_cat, time_cat = category_model.categorize_email(email_text)

        # Step 3: Check if we have a learned pattern for this category
        response_model_name = self._select_best_model_for(category)
        response_model = self.models[response_model_name]

        # Step 4: Generate response
        response, tokens_resp, time_resp = response_model.generate_response(email_text, category)

        # Step 5: Log everything
        total_tokens = tokens_cat + tokens_resp
        total_time = time_cat + time_resp

        self.db.log_email_result(
            email_text=email_text,
            category=category,
            response=response,
            model_used=response_model_name,
            tokens_used=total_tokens,
            processing_time=total_time
        )

        # Step 6: Update learning pattern
        self.db.update_pattern(
            category=category,
            model_name=response_model_name,
            tokens_used=total_tokens,
            processing_time=total_time
        )

        return {
            'email': email_text,
            'category': category,
            'response': response,
            'model_used': response_model_name,
            'tokens_used': total_tokens,
            'processing_time': round(total_time, 2)
        }

    def _get_reliable_model(self):
        """
        Get most reliable available model for categorization
        Prefers: claude > gemini > openrouter > local models
        Falls back to whatever is available
        """
        preferred = ['claude', 'gemini', 'openrouter', 'lmstudio', 'ollama', 'custom']
        for model_name in preferred:
            if model_name in self.models:
                return model_name
        # Fallback to first available
        return list(self.models.keys())[0]

    def _select_best_model_for(self, category):
        """
        Select best model for a given category based on:
        1. Learned patterns from database (if exists)
        2. Cheapest available model (to minimize cost)
        3. Falls back to most reliable model

        Over time, this gets smarter and cheaper
        """

        # Check learned pattern first
        best_from_db = self.db.get_best_model_for_category(category)
        if best_from_db and best_from_db in self.models:
            return best_from_db

        # No pattern yet - try cheapest available model first
        # Priority: local (free) > openrouter (cheap) > gemini > claude
        for model_name in self.priority_order:
            if model_name in self.models:
                return model_name

        # Fallback
        return list(self.models.keys())[0]

    def get_stats(self):
        """Get processing statistics"""
        db_stats = self.db.get_stats()
        fastest_model = 'N/A'
        if db_stats['model_usage']:
            fastest_model = max(db_stats['model_usage'], key=db_stats['model_usage'].get)

        return {
            'total': db_stats['total'],
            'total_tokens': db_stats['total_tokens'],
            'avg_tokens': db_stats['avg_tokens'],
            'model_usage': db_stats['model_usage'],
            'fastest_model': fastest_model
        }
