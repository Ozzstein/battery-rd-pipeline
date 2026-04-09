"""
arXiv Monitor for Battery R&D Pipeline
Scans arXiv daily for battery RUL (Remaining Useful Life) papers
Categories: cs.LG, eess.SP, physics.data-an
"""

import os
import sys
import arxiv
import yaml
import json
import hashlib
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

# Search keywords for battery RUL research
SEARCH_KEYWORDS = [
    'battery remaining useful life',
    'lithium-ion battery degradation',
    'battery RUL prediction',
    'battery health estimation',
    'battery state of health',
    'lithium-ion capacity fade',
    'battery cycle life prediction',
    'battery prognostics',
    'electrochemical impedance spectroscopy battery',
    'battery neural network prediction'
]

# arXiv categories to search
ARXIV_CATEGORIES = ['cs.LG', 'eess.SP', 'physics.data-an', 'cs.AI', 'stat.ML']


class ArxivMonitor:
    """Monitor arXiv for new battery RUL papers"""
    
    def __init__(self, max_results: int = 50, days_back: int = 30):
        self.max_results = max_results
        self.days_back = days_back
        self.client = arxiv.Client()
        self.log_file = LOGS_DIR / f'arxiv_monitor_{datetime.now().strftime("%Y%m%d")}.log'
        
    def log(self, message: str):
        """Log message to file and stdout"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def search_arxiv(self, query: str) -> List[arxiv.Result]:
        """Search arXiv with a specific query"""
        try:
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            results = list(self.client.results(search))
            self.log(f"Query '{query}': found {len(results)} results")
            return results
        except Exception as e:
            self.log(f"Error searching arXiv for '{query}': {e}")
            return []
    
    def build_query(self, keyword: str) -> str:
        """Build arXiv search query with category filters"""
        category_query = ' OR '.join([f'cat:{cat}' for cat in ARXIV_CATEGORIES])
        return f'({keyword}) AND ({category_query})'
    
    def is_recent(self, paper: arxiv.Result, days: int = None) -> bool:
        """Check if paper was published within specified days"""
        if days is None:
            days = self.days_back
        cutoff = datetime.now() - timedelta(days=days)
        # Handle timezone-aware datetime
        paper_date = paper.published.replace(tzinfo=None) if paper.published.tzinfo else paper.published
        return paper_date > cutoff
    
    def extract_method_metadata(self, paper: arxiv.Result) -> Optional[Dict]:
        """Extract method metadata from paper abstract"""
        abstract = paper.summary.lower()
        title = paper.title.lower()
        
        # Check if paper is relevant to battery RUL
        battery_terms = ['battery', 'lithium-ion', 'li-ion', 'lithium ion', 'cell degradation', 'capacity fade', 'li-ion']
        rul_terms = ['remaining useful life', 'rul', 'state of health', 'soh', 'health estimation', 
                     'degradation prediction', 'cycle life', 'end of life', 'prognostics', 'health forecasting',
                     'health prediction', 'capacity estimation', 'degradation estimation']
        ml_terms = ['neural network', 'deep learning', 'machine learning', 'lstm', 'gru', 'transformer',
                    'attention', 'cnn', 'rnn', 'random forest', 'gradient boosting', 'xgboost',
                    'reinforcement learning', 'gaussian process', 'bayesian', 'ensemble', 'kolmogorov',
                    'transfer learning', 'hybrid', 'learning']
        
        has_battery = any(term in abstract or term in title for term in battery_terms)
        has_rul = any(term in abstract or term in title for term in rul_terms)
        has_ml = any(term in abstract or term in title for term in ml_terms)
        
        if not (has_battery and has_rul and has_ml):
            return None
        
        # Extract method type
        method_type = None
        for term in ml_terms:
            if term in abstract or term in title:
                method_type = term
                break
        
        # Extract reported metrics
        metrics = {}
        metric_patterns = [
            (r'(\d+\.?\d*)\s*%?\s*(?:mae|mean absolute error)', 'mae'),
            (r'(\d+\.?\d*)\s*%?\s*(?:rmse|root mean square error)', 'rmse'),
            (r'(\d+\.?\d*)\s*%?\s*(?:accuracy)', 'accuracy'),
            (r'(\d+\.?\d*)\s*%?\s*(?:error)', 'error'),
        ]
        for pattern, metric_name in metric_patterns:
            match = re.search(pattern, abstract)
            if match:
                metrics[metric_name] = float(match.group(1))
        
        # Generate unique method ID
        method_id = self.generate_method_id(paper)
        
        return {
            'method_id': method_id,
            'paper_title': paper.title,
            'paper_url': str(paper.pdf_url),
            'arxiv_id': paper.entry_id.split('/')[-1],
            'authors': [str(a) for a in paper.authors],
            'published': paper.published.isoformat() if hasattr(paper.published, 'isoformat') else str(paper.published),
            'abstract': paper.summary,
            'categories': [str(c) for c in paper.categories],
            'method_type': method_type,
            'reported_metrics': metrics,
            'source': 'arxiv',
            'priority': self.calculate_priority(metrics, method_type),
            'extracted_date': datetime.now().isoformat()
        }
    
    def generate_method_id(self, paper: arxiv.Result) -> str:
        """Generate unique method ID from paper"""
        # Use first author last name + year + short hash
        first_author = str(paper.authors[0]).split()[-1].lower() if paper.authors else 'unknown'
        year = paper.published.year if hasattr(paper.published, 'year') else datetime.now().year
        hash_input = f"{paper.title}_{paper.published}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        return f"battery_rul_{first_author}_{year}_{short_hash}"
    
    def calculate_priority(self, metrics: Dict, method_type: str) -> str:
        """Calculate priority based on reported performance"""
        # High priority if good metrics reported or novel method
        high_priority_methods = ['transformer', 'attention', 'reinforcement learning', 'gaussian process']
        
        if metrics:
            # Check if metrics are good (adjust thresholds as needed)
            if metrics.get('mae', 100) < 20 or metrics.get('rmse', 100) < 25:
                return 'high'
        
        if method_type in high_priority_methods:
            return 'high'
        
        return 'medium'
    
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
            'source': 'arxiv',
            
            'paper_info': {
                'title': metadata['paper_title'],
                'authors': metadata['authors'],
                'url': metadata['paper_url'],
                'arxiv_id': metadata['arxiv_id'],
                'published': metadata['published'],
                'categories': metadata['categories'],
                'abstract': metadata['abstract']
            },
            
            'method_info': {
                'type': metadata['method_type'],
                'description': f"Method extracted from arXiv paper: {metadata['paper_title']}",
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
            
            'notes': f"Automatically extracted by arXiv monitor on {metadata['extracted_date']}"
        }
        
        # Save to YAML
        with open(candidate_file, 'w') as f:
            yaml.dump(candidate_card, f, default_flow_style=False, sort_keys=False)
        
        self.log(f"Saved candidate: {method_id}")
        return True
    
    def scan(self) -> Dict:
        """Run full arXiv scan"""
        self.log("=" * 60)
        self.log("Starting arXiv scan for battery RUL papers")
        self.log("=" * 60)
        
        all_papers = []
        new_candidates = 0
        
        # Search for each keyword
        for keyword in SEARCH_KEYWORDS:
            query = self.build_query(keyword)
            papers = self.search_arxiv(query)
            
            for paper in papers:
                if self.is_recent(paper):
                    metadata = self.extract_method_metadata(paper)
                    if metadata:
                        if self.save_candidate(metadata):
                            new_candidates += 1
                        all_papers.append(metadata)
        
        self.log("=" * 60)
        self.log(f"Scan complete: {len(all_papers)} relevant papers, {new_candidates} new candidates")
        self.log("=" * 60)
        
        return {
            'scan_date': datetime.now().isoformat(),
            'total_papers_found': len(all_papers),
            'new_candidates': new_candidates,
            'keywords_searched': SEARCH_KEYWORDS,
            'candidates': all_papers
        }


def main():
    """Main entry point"""
    monitor = ArxivMonitor(max_results=50, days_back=7)
    results = monitor.scan()
    
    # Print summary
    print("\n" + "=" * 60)
    print("ARXIV MONITOR SUMMARY")
    print("=" * 60)
    print(f"Scan Date: {results['scan_date']}")
    print(f"Total Papers Found: {results['total_papers_found']}")
    print(f"New Candidates: {results['new_candidates']}")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    main()
