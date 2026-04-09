"""
PDF Processor for Battery R&D Pipeline
Processes PDFs shared by users to extract method metadata
Supports direct PDF upload, PDF URLs, and local PDF files
"""

import os
import sys
import yaml
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import fitz  # PyMuPDF

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
CANDIDATES_DIR = PROJECT_ROOT / 'src' / 'basket' / 'candidates'
LOGS_DIR = PROJECT_ROOT / 'logs'
PDF_INBOX_DIR = PROJECT_ROOT / 'inbox' / 'pdfs'

# Ensure directories exist
CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
PDF_INBOX_DIR.mkdir(parents=True, exist_ok=True)


class PDFProcessor:
    """Process PDFs to extract battery RUL method metadata"""
    
    def __init__(self):
        self.log_file = LOGS_DIR / f'pdf_processor_{datetime.now().strftime("%Y%m%d")}.log'
        
    def log(self, message: str):
        """Log message to file and stdout"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)
        with open(self.log_file, 'a') as f:
            f.write(log_entry + '\n')
    
    def extract_text_from_pdf(self, pdf_path: str, max_pages: int = None) -> str:
        """Extract text content from PDF file"""
        try:
            doc = fitz.open(pdf_path)
            
            if max_pages:
                doc = doc[:max_pages]
            
            text = ""
            for page in doc:
                text += page.get_text()
            
            doc.close()
            self.log(f"Extracted {len(text)} characters from {pdf_path}")
            return text
            
        except Exception as e:
            self.log(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def extract_text_from_pdf_url(self, pdf_url: str) -> str:
        """Extract text from PDF URL (e.g., arXiv)"""
        try:
            import requests
            
            # Download PDF
            self.log(f"Downloading PDF from {pdf_url}")
            response = requests.get(pdf_url, timeout=60)
            
            if response.status_code != 200:
                self.log(f"Failed to download PDF: {response.status_code}")
                return ""
            
            # Save temporarily
            temp_path = PDF_INBOX_DIR / f"temp_{hashlib.md5(pdf_url.encode()).hexdigest()[:8]}.pdf"
            with open(temp_path, 'wb') as f:
                f.write(response.content)
            
            # Extract text
            text = self.extract_text_from_pdf(str(temp_path))
            
            # Clean up
            temp_path.unlink()
            
            return text
            
        except Exception as e:
            self.log(f"Error processing PDF URL {pdf_url}: {e}")
            return ""
    
    def parse_paper_metadata(self, text: str) -> Dict:
        """Parse paper metadata from extracted text"""
        metadata = {
            'title': None,
            'authors': [],
            'abstract': None,
            'sections': {},
            'references_count': 0
        }
        
        # Extract title (usually at the beginning, capitalized)
        lines = text.split('\n')
        for i, line in enumerate(lines[:20]):
            line = line.strip()
            if len(line) > 20 and len(line) < 200 and line[0].isupper():
                # Check if next lines look like authors
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip().lower()
                    if any(word in next_line for word in ['university', 'institute', 'department', 'lab', 'center']):
                        metadata['title'] = line
                        break
        
        # Extract abstract
        abstract_patterns = [
            r'abstract[:\s]*(.+?)(?:\n\n|\n[0-9]|\nIntroduction)',
            r'Abstract[:\s]*(.+?)(?:\n\n|\n[0-9]|\nIntroduction)',
            r'ABSTRACT[:\s]*(.+?)(?:\n\n|\n[0-9]|\nIntroduction)'
        ]
        
        for pattern in abstract_patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                metadata['abstract'] = match.group(1).strip()
                break
        
        # Extract authors (look for patterns like "John Smith, Jane Doe")
        # This is simplified - real author extraction is complex
        author_pattern = r'([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+\s+[A-Z][a-z]+)*)'
        if lines and len(lines) > 1:
            for line in lines[1:10]:
                if ',' in line and len(line) < 200:
                    potential_authors = re.findall(author_pattern, line)
                    if potential_authors:
                        metadata['authors'] = [a.strip() for a in potential_authors[0].split(',')]
                        break
        
        # Count references
        ref_patterns = [r'references', r'bibliography', r'references\s*\[', r'\[\d+\]']
        for pattern in ref_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                # Count [1], [2], etc.
                refs = re.findall(r'\[\d+\]', text)
                metadata['references_count'] = len(set(refs))
                break
        
        # Extract key sections
        section_patterns = {
            'introduction': r'(?:\n|^)(Introduction|I\.\s*Introduction)(.+?)(?=\n[A-Z]|\n\d|\Z)',
            'method': r'(?:\n|^)(Method|Methodology|Approach|Model|II\.?[^A-Z]*)(.+?)(?=\n[A-Z]|\n\d|\Z)',
            'results': r'(?:\n|^)(Results|Experiments|Evaluation|III\.?[^A-Z]*)(.+?)(?=\n[A-Z]|\n\d|\Z)',
            'conclusion': r'(?:\n|^)(Conclusion|Summary|V\.?[^A-Z]*)(.+?)(?=\n[A-Z]|\n\d|\Z)'
        }
        
        for section_name, pattern in section_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                metadata['sections'][section_name] = match.group(2)[:500]  # Limit section length
        
        return metadata
    
    def extract_method_info(self, text: str) -> Dict:
        """Extract method information from paper text"""
        method_info = {
            'method_type': None,
            'architecture': None,
            'features': [],
            'reported_metrics': {}
        }
        
        text_lower = text.lower()
        
        # Identify method type
        method_types = [
            ('lstm', ['lstm', 'long short-term memory']),
            ('gru', ['gru', 'gated recurrent unit']),
            ('transformer', ['transformer', 'attention mechanism', 'self-attention']),
            ('cnn', ['cnn', 'convolutional neural', 'convolutional layer']),
            ('rnn', ['rnn', 'recurrent neural']),
            ('random_forest', ['random forest']),
            ('xgboost', ['xgboost', 'gradient boosting']),
            ('svm', ['svm', 'support vector']),
            ('gaussian_process', ['gaussian process', 'gp regression']),
            ('bayesian', ['bayesian', 'probabilistic']),
            ('ensemble', ['ensemble', 'stacking', 'voting']),
            ('autoencoder', ['autoencoder', 'ae', 'variational autoencoder']),
            ('reinforcement_learning', ['reinforcement learning', 'rl', 'policy gradient']),
            ('deep_learning', ['deep learning', 'deep neural', 'dnn'])
        ]
        
        for method_name, keywords in method_types:
            if any(kw in text_lower for kw in keywords):
                method_info['method_type'] = method_name
                break
        
        # Extract reported metrics
        metric_patterns = [
            (r'(\d+\.?\d*)\s*(?:cycles?)?\s*(?:mae|mean absolute error)', 'mae'),
            (r'(\d+\.?\d*)\s*(?:cycles?)?\s*(?:rmse|root mean square)', 'rmse'),
            (r'(\d+\.?\d*)\s*%\s*(?:accuracy)', 'accuracy'),
            (r'(\d+\.?\d*)\s*%\s*(?:error|relative error)', 'error'),
            (r'(\d+\.?\d*)\s*(?:r[²2]|\br2\b|\br-squared\b)', 'r2'),
            (r'(\d+\.?\d*)\s*(?:mpe|mean percentage error)', 'mpe'),
        ]
        
        for pattern, metric_name in metric_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    # Take the first reasonable value
                    values = [float(m) for m in matches if float(m) < 1000]
                    if values:
                        method_info['reported_metrics'][metric_name] = values[0]
                except:
                    pass
        
        # Extract features used
        feature_keywords = [
            'voltage', 'current', 'capacity', 'impedance', 'temperature',
            'soc', 'dod', 'cycle number', 'time', 'charge', 'discharge',
            'health indicator', 'hi', 'feature extraction'
        ]
        
        for feature in feature_keywords:
            if feature in text_lower:
                method_info['features'].append(feature)
        
        return method_info
    
    def is_battery_rul_paper(self, text: str) -> bool:
        """Check if paper is about battery RUL with ML"""
        text_lower = text.lower()
        
        # Battery terms
        battery_terms = [
            'battery', 'lithium-ion', 'li-ion', 'lithium ion', 'battery cell',
            'energy storage', 'battery pack', 'battery management'
        ]
        
        # RUL/prognostics terms
        rul_terms = [
            'remaining useful life', 'rul', 'state of health', 'soh',
            'health estimation', 'degradation prediction', 'prognostics',
            'end of life', 'lifetime prediction', 'capacity estimation',
            'cycle life', 'battery degradation', 'capacity fade'
        ]
        
        # ML terms
        ml_terms = [
            'machine learning', 'deep learning', 'neural network', 'lstm',
            'gru', 'transformer', 'attention', 'cnn', 'rnn', 'random forest',
            'xgboost', 'gradient boosting', 'reinforcement learning',
            'gaussian process', 'bayesian', 'data-driven', 'model'
        ]
        
        has_battery = any(term in text_lower for term in battery_terms)
        has_rul = any(term in text_lower for term in rul_terms)
        has_ml = any(term in text_lower for term in ml_terms)
        
        return has_battery and has_rul and has_ml
    
    def generate_method_id(self, title: str, authors: List[str]) -> str:
        """Generate unique method ID from paper info"""
        # Use first author last name + year + short hash
        if authors:
            first_author = authors[0].split()[-1].lower()
        else:
            first_author = 'unknown'
        
        year = datetime.now().year
        
        hash_input = f"{title}_{authors}_{datetime.now().isoformat()}"
        short_hash = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        
        return f"battery_rul_{first_author}_{year}_{short_hash}"
    
    def calculate_priority(self, metrics: Dict, method_type: str, journal_impact: float = 0) -> str:
        """Calculate priority based on method and metrics"""
        # High priority methods
        high_priority_methods = [
            'transformer', 'attention', 'reinforcement learning',
            'gaussian_process', 'deep_learning', 'autoencoder'
        ]
        
        # Check metrics
        if metrics:
            if metrics.get('mae', 100) < 20 or metrics.get('rmse', 100) < 25:
                return 'high'
            if metrics.get('accuracy', 0) > 90:
                return 'high'
        
        if method_type in high_priority_methods:
            return 'high'
        
        if journal_impact >= 10:
            return 'high'
        elif journal_impact >= 5:
            return 'medium'
        
        return 'medium'
    
    def candidate_exists(self, method_id: str) -> bool:
        """Check if candidate already exists"""
        candidate_file = CANDIDATES_DIR / f"{method_id}.yaml"
        return candidate_file.exists()
    
    def save_candidate(self, metadata: Dict, pdf_path: str = None):
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
            'source': 'pdf',
            
            'paper_info': {
                'title': metadata['paper_title'],
                'authors': metadata['authors'],
                'url': metadata.get('paper_url', ''),
                'abstract': metadata['abstract'],
                'pdf_path': pdf_path or metadata.get('pdf_path', ''),
                'sections': metadata.get('sections', {})
            },
            
            'method_info': {
                'type': metadata['method_type'],
                'architecture': metadata.get('architecture'),
                'features': metadata.get('features', []),
                'description': f"Method extracted from PDF: {metadata['paper_title']}",
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
            
            'notes': f"Extracted from user-shared PDF on {metadata['extracted_date']}"
        }
        
        # Save to YAML
        with open(candidate_file, 'w') as f:
            yaml.dump(candidate_card, f, default_flow_style=False, sort_keys=False)
        
        self.log(f"Saved candidate: {method_id}")
        return True
    
    def process_pdf_file(self, pdf_path: str, paper_url: str = None) -> Optional[Dict]:
        """Process a local PDF file"""
        self.log(f"Processing PDF: {pdf_path}")
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text:
            self.log("No text extracted from PDF")
            return None
        
        # Check if relevant
        if not self.is_battery_rul_paper(text):
            self.log("PDF is not about battery RUL with ML")
            return None
        
        # Parse metadata
        paper_metadata = self.parse_paper_metadata(text)
        method_info = self.extract_method_info(text)
        
        # Build metadata
        title = paper_metadata['title'] or os.path.basename(pdf_path).replace('.pdf', '')
        authors = paper_metadata['authors'] or []
        
        method_id = self.generate_method_id(title, authors)
        priority = self.calculate_priority(
            method_info['reported_metrics'],
            method_info['method_type']
        )
        
        metadata = {
            'method_id': method_id,
            'paper_title': title,
            'paper_url': paper_url or '',
            'authors': authors,
            'abstract': paper_metadata['abstract'] or '',
            'sections': paper_metadata['sections'],
            'method_type': method_info['method_type'],
            'architecture': method_info['architecture'],
            'features': method_info['features'],
            'reported_metrics': method_info['reported_metrics'],
            'pdf_path': pdf_path,
            'source': 'pdf',
            'priority': priority,
            'extracted_date': datetime.now().isoformat()
        }
        
        # Save candidate
        self.save_candidate(metadata, pdf_path)
        
        return metadata
    
    def process_pdf_url(self, pdf_url: str) -> Optional[Dict]:
        """Process a PDF from URL"""
        self.log(f"Processing PDF URL: {pdf_url}")
        
        # Extract text
        text = self.extract_text_from_pdf_url(pdf_url)
        
        if not text:
            self.log("No text extracted from PDF URL")
            return None
        
        # Check if relevant
        if not self.is_battery_rul_paper(text):
            self.log("PDF is not about battery RUL with ML")
            return None
        
        # Parse metadata
        paper_metadata = self.parse_paper_metadata(text)
        method_info = self.extract_method_info(text)
        
        # Build metadata
        title = paper_metadata['title'] or pdf_url.split('/')[-1].replace('.pdf', '')
        authors = paper_metadata['authors'] or []
        
        method_id = self.generate_method_id(title, authors)
        priority = self.calculate_priority(
            method_info['reported_metrics'],
            method_info['method_type']
        )
        
        metadata = {
            'method_id': method_id,
            'paper_title': title,
            'paper_url': pdf_url,
            'authors': authors,
            'abstract': paper_metadata['abstract'] or '',
            'sections': paper_metadata['sections'],
            'method_type': method_info['method_type'],
            'architecture': method_info['architecture'],
            'features': method_info['features'],
            'reported_metrics': method_info['reported_metrics'],
            'source': 'pdf_url',
            'priority': priority,
            'extracted_date': datetime.now().isoformat()
        }
        
        # Save candidate
        self.save_candidate(metadata)
        
        return metadata
    
    def process_inbox(self) -> List[Dict]:
        """Process all PDFs in the inbox directory"""
        self.log("Processing PDF inbox...")
        
        results = []
        pdf_files = list(PDF_INBOX_DIR.glob('*.pdf'))
        
        for pdf_path in pdf_files:
            metadata = self.process_pdf_file(str(pdf_path))
            if metadata:
                results.append(metadata)
                # Move processed PDF to archive
                archive_dir = PDF_INBOX_DIR / 'processed'
                archive_dir.mkdir(exist_ok=True)
                pdf_path.rename(archive_dir / pdf_path.name)
        
        self.log(f"Processed {len(results)} PDFs from inbox")
        return results


def process_pdf(pdf_path: str, pdf_url: str = None) -> Optional[Dict]:
    """Convenience function to process a single PDF"""
    processor = PDFProcessor()
    
    if pdf_url:
        return processor.process_pdf_url(pdf_url)
    else:
        return processor.process_pdf_file(pdf_path)


def main():
    """Main entry point - process inbox"""
    processor = PDFProcessor()
    results = processor.process_inbox()
    
    # Print summary
    print("\n" + "=" * 60)
    print("PDF PROCESSOR SUMMARY")
    print("=" * 60)
    print(f"Processed: {len(results)} papers")
    for r in results:
        print(f"  - {r['method_id']}: {r['paper_title'][:50]}...")
    print("=" * 60)
    
    return results


if __name__ == '__main__':
    main()
