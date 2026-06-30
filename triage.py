#!/usr/bin/env python3
"""
Triage engine - routes emails to best available model
Learns over time which model works best for each category
Works with any model (premium, free API, or local)
"""

import providers as P


class EmailTriage:
    def __init__(self, database, models):
        self.db = database
        self.models = models  # Dict: provider_id -> TriageModel (pre-verified working)
        self.results = []

        # Priority order for picking a model when no learned pattern exists.
        # Free/local providers first so the system defaults to $0 cost.
        self.priority_order = list(P.DEFAULT_PRIORITY)
        self.free_models = [pid for pid in self.models if self.models[pid].free]
        self.paid_models = [pid for pid in self.models if not self.models[pid].free]

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
        Get the most reliable available model for the categorization
        (manager) step. A paid model is preferred here ONLY if one is
        configured, since accuracy matters most for this decision;
        otherwise the best free model is used so the whole pipeline
        stays $0.
        """
        if self.paid_models:
            # paid_models is built from self.models which preserves
            # provider_id keys; pick the first paid one in priority order
            for pid in self.priority_order:
                if pid in self.paid_models:
                    return pid
        # No paid model configured (or none working) - use best free one
        for pid in self.priority_order:
            if pid in self.free_models:
                return pid
        # Fallback to whatever exists
        return list(self.models.keys())[0]

    def _select_best_model_for(self, category):
        """
        Select best model for a given category based on:
        1. Learned patterns from database (if exists and still working)
        2. Cheapest (free) available model first
        3. Falls back to most reliable model

        Over time, this gets smarter and cheaper.
        """
        # Check learned pattern first - only use it if that provider is
        # still alive in this run (it was re-verified by health_check)
        best_from_db = self.db.get_best_model_for_category(category)
        if best_from_db and best_from_db in self.models:
            return best_from_db

        # No pattern yet - prefer free models, in priority order
        for pid in self.priority_order:
            if pid in self.free_models:
                return pid

        # No free models available - fall back to paid
        for pid in self.priority_order:
            if pid in self.models:
                return pid

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
