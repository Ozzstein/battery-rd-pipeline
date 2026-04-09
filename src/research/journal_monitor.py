"""
Journal Monitor for Battery R&D Pipeline
Scans academic journals weekly for battery RUL papers
Journals: Journal of Power Sources, Electrochimica Acta, etc.
Uses RSS feeds and web scraping
"""

import os
import sys
import yaml
import json
import hashlib
import feedparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import re

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
CANDIDATES_DIR = PROJECT_ROOT / 'src' / 'basket' / 'candidates'
LOGS_DIR = PROJECT_ROOT / 'logs'

# Ensure directories exist
CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Journal RSS feeds and URLs
JOURNAL_FEEDS = {
    'journal_of_power_sources': {
        'name': 'Journal of Power Sources',
        'rss_url': 'https://www.journals.elsevier.com/journal-of-power-sources/recent-articles',
        'publisher': 'Elsevier',
        'impact_factor': 9.2,
        'keywords': ['battery', 'energy storage', 'lithium-ion', 'fuel cell']
    },
    'electrochimica_acta': {
        'name': 'Electrochimica Acta',
        'rss_url': 'https://www.journals.elsevier.com/electrochimica-acta/recent-articles',
        'publisher': 'Elsevier',
        'impact_factor': 6.6,
        'keywords': ['electrochemistry', 'battery', 'supercapacitor', 'corrosion']
    },
    'energy_storage_materials': {
        'name': 'Energy Storage Materials',
        'rss_url': 'https://www.journals.elsevier.com/energy-storage-materials/recent-articles',
        'publisher': 'Elsevier',
        'impact_factor': 18.9,
        'keywords': ['energy storage', 'battery', 'supercapacitor', 'materials']
    },
    'journal_of_energy_storage': {
        'name': 'Journal of Energy Storage',
        'rss_url': 'https://www.journals.elsevier.com/journal-of-energy-storage/recent-articles',
        'publisher': 'Elsevier',
        'impact_factor': 8.9,
        'keywords': ['energy storage', 'battery', 'thermal', 'grid']
    },
    'applied_energy': {
        'name': 'Applied Energy',
        'rss_url': 'https://www.journals.elsevier.com/applied-energy/recent-articles',
        'publisher': 'Elsevier',
        'impact_factor': 11.2,
        'keywords': ['energy', 'battery', 'renewable', 'efficiency']
    }
}

# Keywords for filtering relevant papers
BATTERY_KEYWORDS = [
    'battery', 'lithium-ion', 'li-ion', 'lithium ion', 'battery management',
    'battery degradation', 'capacity fade', 'cycle life'
]

RUL_KEYWORDS = [
    'remaining useful life', 'rul', 'state of health', 'soh', 'health estimation',
    'degradation prediction', 'prognostics', 'end of life', 'lifetime prediction',
    'capacity estimation', 'soc estimation', 'state estimation'
]

ML_KEYWORDS = [
    'machine learning', 'deep learning', 'neural network', 'lstm', 'gru',
    'transformer', 'attention mechanism', 'random forest', 'gradient boosting',
    'xgboost', 'reinforcement learning', 'gaussian process', 'bayesian',
    'data-driven', 'model predictive', 'prediction', 'estimation', 'forecasting'
]


class JournalMonitor:
    """Monitor academic journals for new battery RUL papers"""
    
    def __init__(self, days_back: int = 14):
        self.days_back = days_back
        self.log_file = LOGS_DIR / f'journal_monitor_{datetime.now().strftime("%Y%m%d")}.log'
        
    def log(self, message: str):
        """Log message to file and stdout"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def fetch_rss_feed(self, journal_key: str) -> List[Dict]:
        """Fetch articles from journal RSS feed"""
        journal = JOURNAL_FEEDS.get(journal_key)
        if not journal:
            self.log(f"Unknown journal: {journal_key}")
            return []
        
        try:
            # Note: Some journal RSS feeds may require authentication or may not be publicly available
            # This is a simplified implementation - in production, you'd use institutional access
            feed = feedparser.parse(journal['rss_url'])
            
            articles = []
            for entry in feed.entries:
                article = {
                    'title': entry.get('title', ''),
                    'link': entry.get('link', ''),
                    'published': entry.get('published', ''),
                    'summary': entry.get('summary', entry.get('description', '')),
                    'authors': entry.get('authors', []),
                    'journal': journal['name'],
                    'journal_key': journal_key,
                    'impact_factor': journal['impact_factor']
                }
                
                # Parse publication date
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    article['published_date'] = datetime(*entry.published_parsed[:6])
                else:
                    article['published_date'] = datetime.now()
                
                articles.append(article)
            
            self.log(f"Fetched {len(articles)} articles from {journal['name']}")
            return articles
            
        except Exception as e:
            self.log(f"Error fetching RSS for {journal['name']}: {e}")
            return []
    
    def is_recent(self, article: Dict) -> bool:
        """Check if article was published within specified days"""
        cutoff = datetime.now() - timedelta(days=self.days_back)
        pub_date = article.get('published_date', datetime.now())
        return pub_date > cutoff
    
    def is_relevant(self, article: Dict) -> bool:
        """Check if article is relevant to battery RUL with ML"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        text = f"{title} {summary}"
        
        # Check for battery terms
        has_battery = any(term in text for term in BATTERY_KEYWORDS)
        
        # Check for RUL/prognostics terms
        has_rul = any(term in text for term in RUL_KEYWORDS)
        
        # Check for ML/data-driven terms
        has_ml = any(term in text for term in ML_KEYWORDS)
        
        return has_battery and has_rul and has_ml
    
    def extract_method_metadata(self, article: Dict) -> Optional[Dict]:
        """Extract method metadata from article"""
        title = article.get('title', '').lower()
        summary = article.get('summary', '').lower()
        
        # Extract method type
        method_type = None
        for term in ML_KEYWORDS:
            if term in title or term in summary:
                method_type = term
                break
        
        # Extract reported metrics from summary
        metrics = {}
        metric_patterns = [
            (r'(\d+\.?\d*)\s*%?\s*(?:mae|mean absolute error)', 'mae'),
            (r'(\d+\.?\d*)\s*%?\s*(?:rmse|root mean square error)', 'rmse'),
            (r'(\d+\.?\d*)\s*%?\s*(?:accuracy)', 'accuracy'),
            (r'(\d+\.?\d*)\s*%?\s*(?:error)', 'error'),
            (r'(\d+\.?\d*)\s*%?\s*(?:r[²2]|\br2\b)', 'r2'),
        ]
        for pattern, metric_name in metric_patterns:
            match = re.search(pattern, summary, re.IGNORECASE)
            if match:
                try:
                    metrics[metric_name] = float(match.group(1))
                except ValueError:
                    pass
        
        # Generate unique method ID
        method_id = self.generate_method_id(article)
        
        # Calculate priority
        priority = self.calculate_priority(metrics, method_type, article.get('impact_factor', 0))
        
        return {
            'method_id': method_id,
            'paper_title': article['title'],
            'paper_url': article['link'],
            'authors': [a.get('name', str(a)) for a in article.get('authors', [])] if article.get('authors') else [],
            'published': article.get('published', ''),
            'journal': article['journal'],
            'impact_factor': article.get('impact_factor', 0),
            'abstract': article.get('summary', ''),
            'method_type': method_type,
            'reported_metrics': metrics,
            'source': 'journal',
            'priority': priority,
            'extracted_date': datetime.now().isoformat()
        }
    
    def generate_method_id(self, article: Dict) -> str:
        """Generate unique method ID from article"""
        # Use first author + year + short hash
        authors = article.get('authors', [])
        if authors:
            first_author = str(authors[0].get('name', authors[0])).split()[-1].lower()
        else:
            first_author = 'unknown'
        
        pub_date = article.get('published_date', datetime.now())
        year = pub_date.year
        
        hash_input = f"{article['title']}_{article['link']}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        
        return f"battery_rul_{first_author}_{year}_{short_hash}"
    
    def calculate_priority(self, metrics: Dict, method_type: str, impact_factor: float) -> str:
        """Calculate priority based on journal impact and reported performance"""
        # High priority for high impact journals
        if impact_factor >= 10:
            base_priority = 'high'
        elif impact_factor >= 5:
            base_priority = 'medium'
        else:
            base_priority = 'low'
        
        # Upgrade priority for good metrics or novel methods
        high_priority_methods = ['transformer', 'attention', 'reinforcement learning', 
                                 'gaussian process', 'deep learning']
        
        if metrics:
            if metrics.get('mae', 100) < 20 or metrics.get('rmse', 100) < 25:
                return 'high'
        
        if method_type in high_priority_methods:
            return 'high'
        
        return base_priority
    
    def candidate_exists(self, method_id: str) -> bool:
        """Check if candidate already exists"""
        candidate_file = CANDIDATES_DIR / f"{method_id}.yaml"
        return candidate_file.exists()
    
    def save_candidate(self, metadata: Dict):
        """Save candidate method card to YAML file"""
        method_id = metadata['method_id']
        candidate_file = CANDIDATES_DIR / f"{method_id}.yaml"
        
        if self.candidate_exists(method_id):
            self.log(f"Candidate {method_id} already exists, skipping")
            return False
        
        # Create candidate card
        candidate_card = {
            'method_id': metadata['method_id'],
            'name': metadata['paper_title'],
            'domain': 'battery_rul',
            'status': 'candidate',
            'source': 'journal',
            
            'paper_info': {
                'title': metadata['paper_title'],
                'authors': metadata['authors'],
                'url': metadata['paper_url'],
                'journal': metadata['journal'],
                'impact_factor': metadata['impact_factor'],
                'published': metadata['published'],
                'abstract': metadata['abstract']
            },
            
            'method_info': {
                'type': metadata['method_type'],
                'description': f"Method extracted from {metadata['journal']}: {metadata['paper_title']}",
                'reported_metrics': metadata['reported_metrics']
            },
            
            'timeline': {
                'extracted': metadata['extracted_date'],
                'implemented': None,
                'shadow_start': None,
                'promoted': None
            },
            
            'evaluation': {
                'priority': metadata['priority'],
                'selected': False,
                'selection_date': None,
                'evaluation_report': None
            },
            
            'notes': f"Automatically extracted by journal monitor on {metadata['extracted_date']}"
        }
        
        # Save to YAML
        with open(candidate_file, 'w') as f:
            yaml.dump(candidate_card, f, default_flow_style=False, sort_keys=False)
        
        self.log(f"Saved candidate: {method_id}")
        return True
    
    def scan(self) -> Dict:
        """Run full journal scan"""
        self.log("=" * 60)
        self.log("Starting weekly journal scan for battery RUL papers")
        self.log("=" * 60)
        
        all_articles = []
        new_candidates = 0
        
        # Scan each journal
        for journal_key in JOURNAL_FEEDS.keys():
            self.log(f"Scanning {JOURNAL_FEEDS[journal_key]['name']}...")
            articles = self.fetch_rss_feed(journal_key)
            
            for article in articles:
                if self.is_recent(article) and self.is_relevant(article):
                    metadata = self.extract_method_metadata(article)
                    if metadata:
                        if self.save_candidate(metadata):
                            new_candidates += 1
                        all_articles.append(metadata)
        
        self.log("=" * 60)
        self.log(f"Scan complete: {len(all_articles)} relevant articles, {new_candidates} new candidates")
        self.log("=" * 60)
        
        return {
            'scan_date': datetime.now().isoformat(),
            'journals_scanned': list(JOURNAL_FEEDS.keys()),
            'total_articles_found': len(all_articles),
            'new_candidates': new_candidates,
            'candidates': all_articles
        }


def main():
    """Main entry point"""
    monitor = JournalMonitor(days_back=14)
    results = monitor.scan()
    
    # Print summary
    print("\n" + "=" * 60)
    print("JOURNAL MONITOR SUMMARY")
    print("=" * 60)
    print(f"Scan Date: {results['scan_date']}")
    print(f"Journals Scanned: {len(results['journals_scanned'])}")
    print(f"Total Articles Found: {results['total_articles_found']}")
    print(f"New Candidates: {results['new_candidates']}")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    main()
