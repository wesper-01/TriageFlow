#!/usr/bin/env python3
"""
Triage engine - routes emails to best available model
Learns over time which model works best for each category
Works with any model (premium, free API, or local)
"""

import providers as P

# How many consecutive failures before a provider is sidelined mid-batch
_FAILURE_THRESHOLD = 3


class EmailTriage:
    def __init__(self, database, models):
        self.db = database
        self.models = models  # Dict: provider_id -> TriageModel (pre-verified working)
        self.results = []

        # Use the dynamic priority order from health_check (sorted by latency)
        self.priority_order = list(self.models.keys())
        self.free_models = [pid for pid in self.models if self.models[pid].free]
        self.paid_models = [pid for pid in self.models if not self.models[pid].free]

        # Mid-run fallback tracking: consecutive failure counts per provider
        self._failure_counts: dict[str, int] = {pid: 0 for pid in self.models}
        self._sidelined: set[str] = set()

    def process_emails(self, emails):
        """Process a batch of emails"""
        self.results = []
        for email in emails:
            result = self.process_single_email(email)
            self.results.append(result)
        return self.results

    def _record_outcome(self, provider_id: str, success: bool):
        """Track consecutive failures; sideline a provider that keeps failing."""
        if success:
            self._failure_counts[provider_id] = 0
            self._sidelined.discard(provider_id)
        else:
            self._failure_counts[provider_id] = self._failure_counts.get(provider_id, 0) + 1
            if self._failure_counts[provider_id] >= _FAILURE_THRESHOLD:
                if provider_id not in self._sidelined:
                    print(f"  [!] {provider_id} sidelined mid-batch after "
                          f"{_FAILURE_THRESHOLD} consecutive failures — falling back")
                    self._sidelined.add(provider_id)

    def _active_models(self):
        """Return priority-ordered list of provider_ids that aren't sidelined."""
        return [pid for pid in self.priority_order if pid not in self._sidelined]

    def _call_with_fallback(self, call_fn, providers_to_try):
        """
        Try call_fn(provider_id) across providers_to_try in order.
        If all fail, sleep and retry up to 3 times before raising RuntimeError.
        """
        import time
        max_retries = 3
        for attempt in range(max_retries):
            for pid in providers_to_try:
                if pid not in self.models or pid in self._sidelined:
                    continue
                result = call_fn(pid)
                text = result[0] if isinstance(result, tuple) else result
                if not str(text).startswith(("Error", "API Error", "Ollama Error")):
                    self._record_outcome(pid, success=True)
                    return result, pid
                self._record_outcome(pid, success=False)
            
            if attempt < max_retries - 1:
                print(f"  [!] Exhausted providers on attempt {attempt+1}/{max_retries}. Sleeping 5s before retry...")
                time.sleep(5)
                # Un-sideline everyone for the retry
                self._sidelined.clear()
                for p in self._failure_counts:
                    self._failure_counts[p] = 0
                
        raise RuntimeError("All available providers failed for this email after retries.")

    def process_single_email(self, email_text):
        """Process a single email through triage"""
        active = self._active_models()
        if not active:
            # Reset sidelined set and try again (all providers may have recovered)
            self._sidelined.clear()
            self._failure_counts = {pid: 0 for pid in self.models}
            active = list(self.priority_order)

        # Step 1: Pick best model for categorization (paid preferred, then free)
        paid_active = [p for p in active if p in self.paid_models]
        free_active  = [p for p in active if p in self.free_models]
        cat_order = (paid_active or free_active) + [p for p in active if p not in (paid_active + free_active)]

        (category, tokens_cat, time_cat), category_model_name = self._call_with_fallback(
            lambda pid: self.models[pid].categorize_email(email_text),
            cat_order,
        )

        # Step 2: Check if we have a learned pattern for this category
        # Step 3: Generate response — prefer free models
        best_from_db = self.db.get_best_model_for_category(category)
        resp_order = (
            [best_from_db] if best_from_db and best_from_db in self.models and best_from_db not in self._sidelined
            else []
        ) + free_active + [p for p in active if p not in free_active]

        (response, tokens_resp, time_resp), response_model_name = self._call_with_fallback(
            lambda pid: self.models[pid].generate_response(email_text, category),
            resp_order,
        )

        # Log and learn
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
