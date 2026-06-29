#!/usr/bin/env python3
"""
Email triage engine - routes emails to best models and learns patterns
"""

class EmailTriage:
    def __init__(self, database, models):
        self.db = database
        self.models = models  # Dict of model_name -> TriageModel
        self.results = []
    
    def process_emails(self, emails):
        """Process a batch of emails"""
        self.results = []
        
        for email in emails:
            result = self.process_single_email(email)
            self.results.append(result)
        
        return self.results
    
    def process_single_email(self, email_text):
        """Process a single email through triage"""
        
        # Step 1: Choose model for categorization
        # First check if we have a pattern for this type of email
        # For MVP, we'll use Claude for first email of each type
        category_model = self._select_model_for_categorization(email_text)
        
        # Step 2: Categorize the email
        category, tokens_cat, time_cat = category_model.categorize_email(email_text)
        
        # Step 3: Choose model for response generation
        # Check patterns for this category
        response_model = self._select_model_for_response(category)
        
        # Step 4: Generate response
        response, tokens_resp, time_resp = response_model.generate_response(email_text, category)
        
        # Step 5: Log results
        total_tokens = tokens_cat + tokens_resp
        total_time = time_cat + time_resp
        
        self.db.log_email_result(
            email_text=email_text,
            category=category,
            response=response,
            model_used=response_model.model_type,
            tokens_used=total_tokens,
            processing_time=total_time
        )
        
        # Step 6: Update patterns for learning
        self.db.update_pattern(
            category=category,
            model_name=response_model.model_type,
            tokens_used=total_tokens,
            processing_time=total_time
        )
        
        return {
            'email': email_text,
            'category': category,
            'response': response,
            'model_used': response_model.model_type,
            'tokens_used': total_tokens,
            'processing_time': total_time
        }
    
    def _select_model_for_categorization(self, email_text):
        """Select best model for categorization"""
        # For MVP: always use Claude for high accuracy
        return self.models['claude']
    
    def _select_model_for_response(self, category):
        """Select best model for response generation based on patterns"""
        
        # Check if we have a learned pattern for this category
        best_model = self.db.get_best_model_for_category(category)
        
        if best_model and best_model in self.models:
            return self.models[best_model]
        
        # If no pattern yet, use Claude (most reliable)
        return self.models['claude']
    
    def get_stats(self):
        """Get statistics about processing"""
        db_stats = self.db.get_stats()
        
        # Calculate fastest model
        fastest_model = 'claude'
        if db_stats['model_usage']:
            fastest_model = min(db_stats['model_usage'].keys())
        
        return {
            'total': db_stats['total'],
            'total_tokens': db_stats['total_tokens'],
            'avg_tokens': db_stats['avg_tokens'],
            'model_usage': db_stats['model_usage'],
            'fastest_model': fastest_model
        }
