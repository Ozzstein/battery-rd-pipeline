"""
Research Agent Team for Battery R&D Pipeline

This module provides research monitoring agents that continuously scan
academic sources for new battery RUL (Remaining Useful Life) methods.

Agents:
- ArxivMonitor: Daily arXiv scans
- JournalMonitor: Weekly journal scans  
- GitHubMonitor: Daily GitHub repo scans
- PDFProcessor: User-shared PDF processing
"""

from .arxiv_monitor import ArxivMonitor
from .journal_monitor import JournalMonitor
from .github_monitor import GitHubMonitor
from .pdf_processor import PDFProcessor, process_pdf

__all__ = [
    'ArxivMonitor',
    'JournalMonitor', 
    'GitHubMonitor',
    'PDFProcessor',
    'process_pdf'
]


def run_all_monitors():
    """Run all research monitors and aggregate results"""
    from datetime import datetime
    
    results = {
        'run_date': datetime.now().isoformat(),
        'arxiv': None,
        'journals': None,
        'github': None,
        'pdfs': None
    }
    
    # Run arXiv monitor
    try:
        from .arxiv_monitor import ArxivMonitor
        monitor = ArxivMonitor()
        results['arxiv'] = monitor.scan()
    except Exception as e:
        results['arxiv'] = {'error': str(e)}
    
    # Run journal monitor
    try:
        from .journal_monitor import JournalMonitor
        monitor = JournalMonitor()
        results['journals'] = monitor.scan()
    except Exception as e:
        results['journals'] = {'error': str(e)}
    
    # Run GitHub monitor
    try:
        from .github_monitor import GitHubMonitor
        monitor = GitHubMonitor()
        results['github'] = monitor.scan()
    except Exception as e:
        results['github'] = {'error': str(e)}
    
    # Process PDF inbox
    try:
        from .pdf_processor import PDFProcessor
        processor = PDFProcessor()
        pdf_results = processor.process_inbox()
        results['pdfs'] = {
            'processed': len(pdf_results),
            'candidates': pdf_results
        }
    except Exception as e:
        results['pdfs'] = {'error': str(e)}
    
    return results


if __name__ == '__main__':
    results = run_all_monitors()
    print("\n" + "=" * 60)
    print("RESEARCH AGENT TEAM - FULL SCAN SUMMARY")
    print("=" * 60)
    print(f"Run Date: {results['run_date']}")
    print(f"arXiv: {results['arxiv'].get('new_candidates', 0) if isinstance(results['arxiv'], dict) else 'Error'}")
    print(f"Journals: {results['journals'].get('new_candidates', 0) if isinstance(results['journals'], dict) else 'Error'}")
    print(f"GitHub: {results['github'].get('new_candidates', 0) if isinstance(results['github'], dict) else 'Error'}")
    print(f"PDFs: {results['pdfs'].get('processed', 0) if isinstance(results['pdfs'], dict) else 'Error'}")
    print("=" * 60)
