#!/usr/bin/env python3
"""
Database module for storing triage results and patterns
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

class TriageDatabase:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = Path(__file__).parent / "triage_results.db"
        
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Table for storing processed emails
        c.execute('''
            CREATE TABLE IF NOT EXISTS email_results (
                id INTEGER PRIMARY KEY,
                email_text TEXT NOT NULL,
                category TEXT NOT NULL,
                response TEXT NOT NULL,
                model_used TEXT NOT NULL,
                tokens_used INTEGER,
                processing_time REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Table for patterns (what works best for what)
        c.execute('''
            CREATE TABLE IF NOT EXISTS patterns (
                id INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                model_name TEXT NOT NULL,
                success_count INTEGER DEFAULT 0,
                avg_tokens INTEGER,
                avg_time REAL,
                last_used TIMESTAMP
            )
        ''')
        
        # Table for model performance tracking
        c.execute('''
            CREATE TABLE IF NOT EXISTS model_performance (
                id INTEGER PRIMARY KEY,
                model_name TEXT UNIQUE,
                total_uses INTEGER DEFAULT 0,
                avg_tokens_per_task INTEGER,
                success_rate REAL,
                last_updated TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def log_email_result(self, email_text, category, response, model_used, tokens_used, processing_time):
        """Log a processed email result"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO email_results 
            (email_text, category, response, model_used, tokens_used, processing_time)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email_text, category, response, model_used, tokens_used, processing_time))
        
        conn.commit()
        conn.close()
    
    def update_pattern(self, category, model_name, tokens_used, processing_time):
        """Update pattern for a category/model combination"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check if pattern exists
        c.execute('''
            SELECT id, success_count, avg_tokens, avg_time FROM patterns
            WHERE category = ? AND model_name = ?
        ''', (category, model_name))
        
        result = c.fetchone()
        
        if result:
            pattern_id, count, avg_tokens, avg_time = result
            new_count = count + 1
            new_avg_tokens = (avg_tokens * count + tokens_used) // new_count
            new_avg_time = (avg_time * count + processing_time) / new_count
            
            c.execute('''
                UPDATE patterns 
                SET success_count = ?, avg_tokens = ?, avg_time = ?, last_used = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_count, new_avg_tokens, new_avg_time, pattern_id))
        else:
            c.execute('''
                INSERT INTO patterns (category, model_name, success_count, avg_tokens, avg_time, last_used)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (category, model_name, 1, tokens_used, processing_time))
        
        conn.commit()
        conn.close()
    
    def get_best_model_for_category(self, category):
        """Get the best model for a given email category"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT model_name, avg_tokens, success_count
            FROM patterns
            WHERE category = ?
            ORDER BY success_count DESC, avg_tokens ASC
            LIMIT 1
        ''', (category,))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            return result[0]  # Return model name
        return None
    
    def get_all_results(self):
        """Get all processed email results"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT * FROM email_results ORDER BY created_at DESC')
        results = c.fetchall()
        conn.close()
        
        return results
    
    def get_stats(self):
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*), SUM(tokens_used), AVG(tokens_used) FROM email_results')
        total, total_tokens, avg_tokens = c.fetchone()
        
        c.execute('''
            SELECT model_used, COUNT(*) FROM email_results
            GROUP BY model_used
        ''')
        model_usage = dict(c.fetchall())
        
        conn.close()
        
        return {
            'total': total or 0,
            'total_tokens': total_tokens or 0,
            'avg_tokens': avg_tokens or 0,
            'model_usage': model_usage
        }
