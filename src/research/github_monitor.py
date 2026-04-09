"""
GitHub Monitor for Battery R&D Pipeline
Scans GitHub repositories daily for battery RUL projects
Topics: battery-ml, rul-estimation, battery-prediction, etc.
"""

import os
import sys
import yaml
import json
import hashlib
import requests
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

# GitHub API configuration
GITHUB_API_BASE = 'https://api.github.com'
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', None)  # Optional, increases rate limit

# Search topics and keywords
BATTERY_ML_TOPICS = [
    'battery-ml',
    'rul-estimation',
    'battery-prediction',
    'battery-health',
    'lithium-ion-ml',
    'battery-prognostics',
    'battery-degradation',
    'battery-ai',
    'battery-data-science',
    'energy-storage-ml'
]

SEARCH_QUERIES = [
    'battery remaining useful life language:python stars:>10',
    'battery RUL prediction language:python stars:>10',
    'lithium-ion degradation machine learning language:python stars:>10',
    'battery health estimation deep learning language:python stars:>10',
    'battery state of health neural network language:python stars:>10',
    'battery cycle life prediction language:python stars:>10'
]


class GitHubMonitor:
    """Monitor GitHub for new battery RUL repositories"""
    
    def __init__(self, max_results: int = 30, min_stars: int = 10):
        self.max_results = max_results
        self.min_stars = min_stars
        self.session = requests.Session()
        
        if GITHUB_TOKEN:
            self.session.headers.update({'Authorization': f'token {GITHUB_TOKEN}'})
        
        self.session.headers.update({
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Battery-RD-Pipeline-Monitor'
        })
        
        self.log_file = LOGS_DIR / f'github_monitor_{datetime.now().strftime("%Y%m%d")}.log'
        
    def log(self, message: str):
        """Log message to file and stdout"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def search_repositories(self, query: str) -> List[Dict]:
        """Search GitHub repositories"""
        try:
            url = f"{GITHUB_API_BASE}/search/repositories"
            params = {
                'q': query,
                'sort': 'updated',
                'order': 'desc',
                'per_page': min(self.max_results, 100)
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                repos = data.get('items', [])
                self.log(f"Query '{query[:50]}...': found {len(repos)} repos")
                return repos
            elif response.status_code == 403:
                # Rate limited
                self.log(f"Rate limited on GitHub API. Reset: {response.headers.get('X-RateLimit-Reset', 'unknown')}")
                return []
            else:
                self.log(f"Error searching GitHub: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.log(f"Error searching GitHub for '{query}': {e}")
            return []
    
    def search_by_topic(self, topic: str) -> List[Dict]:
        """Search repositories by topic"""
        try:
            url = f"{GITHUB_API_BASE}/search/repositories"
            params = {
                'q': f'topic:{topic} language:python stars:>{self.min_stars}',
                'sort': 'updated',
                'order': 'desc',
                'per_page': min(self.max_results, 100)
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                repos = data.get('items', [])
                self.log(f"Topic '{topic}': found {len(repos)} repos")
                return repos
            else:
                self.log(f"Error searching topic {topic}: {response.status_code}")
                return []
                
        except Exception as e:
            self.log(f"Error searching topic {topic}: {e}")
            return []
    
    def is_recently_updated(self, repo: Dict, days: int = 30) -> bool:
        """Check if repo was updated within specified days"""
        updated_at = repo.get('updated_at', '')
        if not updated_at:
            return False
        
        try:
            update_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            cutoff = datetime.now(update_date.tzinfo) - timedelta(days=days)
            return update_date > cutoff
        except:
            return False
    
    def is_relevant(self, repo: Dict) -> bool:
        """Check if repo is relevant to battery RUL with ML"""
        name = repo.get('name', '').lower()
        description = (repo.get('description') or '').lower()
        topics = [t.lower() for t in repo.get('topics', [])]
        
        text = f"{name} {description} {' '.join(topics)}"
        
        # Check for battery terms
        battery_terms = ['battery', 'lithium-ion', 'li-ion', 'cell', 'energy storage']
        has_battery = any(term in text for term in battery_terms)
        
        # Check for RUL/prognostics terms
        rul_terms = ['rul', 'remaining useful life', 'health', 'degradation', 
                     'prognostics', 'prediction', 'estimation', 'forecasting',
                     'state of health', 'soh', 'capacity']
        has_rul = any(term in text for term in rul_terms)
        
        # Check for ML terms
        ml_terms = ['machine learning', 'deep learning', 'neural', 'lstm', 'gru',
                    'transformer', 'pytorch', 'tensorflow', 'sklearn', 'ml',
                    'artificial intelligence', 'ai', 'model', 'network']
        has_ml = any(term in text for term in ml_terms)
        
        return has_battery and has_rul and has_ml
    
    def extract_method_metadata(self, repo: Dict) -> Optional[Dict]:
        """Extract method metadata from repository"""
        # Fetch README for more details
        readme_content = self.fetch_readme(repo)
        
        # Extract method type from description and README
        description = (repo.get('description') or '').lower()
        readme_lower = (readme_content or '').lower()
        text = f"{description} {readme_lower}"
        
        method_type = None
        ml_methods = [
            'transformer', 'attention', 'lstm', 'gru', 'rnn', 'cnn',
            'random forest', 'xgboost', 'gradient boosting', 'svm',
            'gaussian process', 'bayesian', 'reinforcement learning',
            'deep learning', 'neural network', 'ensemble', 'autoencoder'
        ]
        
        for method in ml_methods:
            if method in text:
                method_type = method
                break
        
        # Extract reported metrics from README
        metrics = {}
        if readme_content:
            metric_patterns = [
                (r'(\d+\.?\d*)\s*%?\s*(?:mae|mean absolute error)', 'mae'),
                (r'(\d+\.?\d*)\s*%?\s*(?:rmse|root mean square error)', 'rmse'),
                (r'(\d+\.?\d*)\s*%?\s*(?:accuracy)', 'accuracy'),
                (r'(\d+\.?\d*)\s*%?\s*(?:error)', 'error'),
                (r'(\d+\.?\d*)\s*%?\s*(?:r[²2]|\br2\b)', 'r2'),
            ]
            for pattern, metric_name in metric_patterns:
                match = re.search(pattern, readme_content, re.IGNORECASE)
                if match:
                    try:
                        metrics[metric_name] = float(match.group(1))
                    except ValueError:
                        pass
        
        # Generate unique method ID
        method_id = self.generate_method_id(repo)
        
        # Calculate priority
        priority = self.calculate_priority(
            metrics, 
            method_type, 
            repo.get('stargazers_count', 0),
            repo.get('forks_count', 0)
        )
        
        return {
            'method_id': method_id,
            'repo_name': repo['full_name'],
            'repo_url': repo['html_url'],
            'owner': repo['owner']['login'],
            'description': repo.get('description', ''),
            'stars': repo.get('stargazers_count', 0),
            'forks': repo.get('forks_count', 0),
            'topics': repo.get('topics', []),
            'language': repo.get('language', ''),
            'updated_at': repo.get('updated_at', ''),
            'created_at': repo.get('created_at', ''),
            'method_type': method_type,
            'reported_metrics': metrics,
            'readme_excerpt': readme_content[:1000] if readme_content else None,
            'source': 'github',
            'priority': priority,
            'extracted_date': datetime.now().isoformat()
        }
    
    def fetch_readme(self, repo: Dict) -> Optional[str]:
        """Fetch README content from repository"""
        try:
            owner = repo['owner']['login']
            name = repo['name']
            url = f"{GITHUB_API_BASE}/repos/{owner}/{name}/readme"
            
            response = self.session.get(url, timeout=30)
            
            if response.status_code == 200:
                import base64
                data = response.json()
                content = base64.b64decode(data['content']).decode('utf-8')
                return content
            else:
                return None
                
        except Exception as e:
            self.log(f"Error fetching README for {repo['full_name']}: {e}")
            return None
    
    def generate_method_id(self, repo: Dict) -> str:
        """Generate unique method ID from repository"""
        owner = repo['owner']['login'].lower()
        name = repo['name'].lower().replace('-', '_').replace(' ', '_')
        
        hash_input = f"{repo['full_name']}_{repo['html_url']}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        
        return f"battery_rul_{owner}_{name}_{short_hash}"
    
    def calculate_priority(self, metrics: Dict, method_type: str, stars: int, forks: int) -> str:
        """Calculate priority based on repo popularity and method"""
        # High priority for popular repos
        if stars >= 100 or forks >= 50:
            base_priority = 'high'
        elif stars >= 50 or forks >= 25:
            base_priority = 'medium'
        else:
            base_priority = 'low'
        
        # Upgrade priority for good metrics or novel methods
        high_priority_methods = ['transformer', 'attention', 'reinforcement learning', 
                                 'gaussian process', 'deep learning', 'autoencoder']
        
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
            'name': metadata['repo_name'],
            'domain': 'battery_rul',
            'status': 'candidate',
            'source': 'github',
            
            'repo_info': {
                'name': metadata['repo_name'],
                'url': metadata['repo_url'],
                'owner': metadata['owner'],
                'description': metadata['description'],
                'stars': metadata['stars'],
                'forks': metadata['forks'],
                'topics': metadata['topics'],
                'language': metadata['language'],
                'updated_at': metadata['updated_at'],
                'readme_excerpt': metadata['readme_excerpt']
            },
            
            'method_info': {
                'type': metadata['method_type'],
                'description': f"Method extracted from GitHub repo: {metadata['repo_name']}",
                'reported_metrics': metadata['reported_metrics'],
                'implementation_available': True
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
            
            'notes': f"Automatically extracted by GitHub monitor on {metadata['extracted_date']}"
        }
        
        # Save to YAML
        with open(candidate_file, 'w') as f:
            yaml.dump(candidate_card, f, default_flow_style=False, sort_keys=False)
        
        self.log(f"Saved candidate: {method_id}")
        return True
    
    def scan(self) -> Dict:
        """Run full GitHub scan"""
        self.log("=" * 60)
        self.log("Starting daily GitHub scan for battery RUL repositories")
        self.log("=" * 60)
        
        all_repos = []
        new_candidates = 0
        seen_repos = set()
        
        # Search by queries
        for query in SEARCH_QUERIES:
            repos = self.search_repositories(query)
            
            for repo in repos:
                repo_id = repo['full_name']
                if repo_id in seen_repos:
                    continue
                seen_repos.add(repo_id)
                
                if self.is_recently_updated(repo) and self.is_relevant(repo):
                    metadata = self.extract_method_metadata(repo)
                    if metadata:
                        if self.save_candidate(metadata):
                            new_candidates += 1
                        all_repos.append(metadata)
        
        # Search by topics
        for topic in BATTERY_ML_TOPICS:
            repos = self.search_by_topic(topic)
            
            for repo in repos:
                repo_id = repo['full_name']
                if repo_id in seen_repos:
                    continue
                seen_repos.add(repo_id)
                
                if self.is_recently_updated(repo) and self.is_relevant(repo):
                    metadata = self.extract_method_metadata(repo)
                    if metadata:
                        if self.save_candidate(metadata):
                            new_candidates += 1
                        all_repos.append(metadata)
        
        self.log("=" * 60)
        self.log(f"Scan complete: {len(all_repos)} relevant repos, {new_candidates} new candidates")
        self.log("=" * 60)
        
        return {
            'scan_date': datetime.now().isoformat(),
            'queries_searched': len(SEARCH_QUERIES),
            'topics_searched': len(BATTERY_ML_TOPICS),
            'total_repos_found': len(all_repos),
            'new_candidates': new_candidates,
            'candidates': all_repos
        }


def main():
    """Main entry point"""
    monitor = GitHubMonitor(max_results=30, min_stars=10)
    results = monitor.scan()
    
    # Print summary
    print("\n" + "=" * 60)
    print("GITHUB MONITOR SUMMARY")
    print("=" * 60)
    print(f"Scan Date: {results['scan_date']}")
    print(f"Queries Searched: {results['queries_searched']}")
    print(f"Topics Searched: {results['topics_searched']}")
    print(f"Total Repos Found: {results['total_repos_found']}")
    print(f"New Candidates: {results['new_candidates']}")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    main()
