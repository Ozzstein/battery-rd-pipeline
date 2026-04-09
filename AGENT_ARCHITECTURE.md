# Persistent Sub-Agent Architecture for Battery R&D Pipeline

## 🤖 Agent Overview

| Agent | Role | Cadence | Tools |
|-------|------|---------|-------|
| **Research Agent** | Monitor sources, extract methods | Continuous (daily scans) | arXiv API, RSS, GitHub API, PDF OCR |
| **Development Agent** | Implement & test methods | Quarterly (triggered) | PyTorch, sklearn, pytest |
| **Evaluation Agent** | Benchmark & compare | Per method | Statistical tests, wandb |
| **Deployment Agent** | Shadow mode & production | Continuous monitoring | PostgreSQL, metrics dashboard |
| **Basket Agent** | Maintain method registry | On state changes | File system, registry.yaml |

---

## 📋 Agent Specifications

### 1. Research Agent

**Goal:** Continuously monitor research sources and catalog new methods

**Sources:**
- arXiv (cs.LG, eess.SP, physics.data-an) - Daily scan
- Journals (JPS, Electrochimica Acta) - Weekly scan
- GitHub repos - Daily scan
- PDFs from user - Immediate processing
- Conference proceedings - Seasonal

**Output:** Method cards in `src/basket/candidates/`

**Cron Schedule:**
```bash
# Daily arXiv scan
0 9 * * * python src/research/arxiv_monitor.py

# Weekly journal scan
0 10 * * 1 python src/research/journal_monitor.py

# Daily GitHub scan
0 11 * * * python src/research/github_monitor.py

# PDF watcher (continuous via inotify)
python src/research/pdf_watcher.py
```

**Sub-agent Team:**
```python
# src/research/team.py
RESEARCH_TEAM = {
    'arxiv_scraper': {
        'tool': 'arxiv',
        'frequency': 'daily',
        'keywords': ['battery', 'RUL', 'remaining useful life', 'lithium-ion', 'degradation']
    },
    'journal_monitor': {
        'tool': 'rss_feed',
        'frequency': 'weekly',
        'feeds': [
            'https://www.journals.elsevier.com/journal-of-power-sources/recent-articles',
            'https://www.journals.elsevier.com/electrochimica-acta/recent-articles'
        ]
    },
    'github_scout': {
        'tool': 'github_api',
        'frequency': 'daily',
        'topics': ['battery-ml', 'rul-estimation', 'battery-prediction']
    },
    'pdf_processor': {
        'tool': 'ocr_and_documents',
        'trigger': 'file_watch',
        'watch_dir': '~/.hermes/inbox/pdfs/'
    }
}
```

---

### 2. Development Agent

**Goal:** Implement and test new methods from candidates

**Trigger:** Quarterly review OR manual trigger

**Workflow:**
1. Review candidate methods from Research Agent
2. Select top 3-5 for implementation
3. Implement each method (following template)
4. Write unit tests
5. Run integration tests
6. Document hyperparameters and requirements

**Sub-agent Team:**
```python
# src/development/team.py
DEVELOPMENT_TEAM = {
    'implementation_lead': {
        'role': 'Implement method code from paper',
        'tools': ['terminal', 'file', 'execute_code'],
        'output': 'src/development/methods/<method_id>/method.py'
    },
    'test_engineer': {
        'role': 'Write unit and integration tests',
        'tools': ['terminal', 'file'],
        'output': 'tests/test_<method_id>.py'
    },
    'documenter': {
        'role': 'Document method, hyperparameters, usage',
        'tools': ['file'],
        'output': 'src/development/methods/<method_id>/README.md'
    }
}
```

---

### 3. Evaluation Agent

**Goal:** Fair benchmarking and statistical validation

**Workflow:**
1. Load baseline (current production)
2. Load candidate method
3. Run both on same test set
4. Compute metrics (MAE, RMSE, Relative Error, etc.)
5. Statistical significance testing
6. Generate evaluation report

**Sub-agent Team:**
```python
# src/evaluation/team.py
EVALUATION_TEAM = {
    'benchmark_runner': {
        'role': 'Execute fair comparison',
        'tools': ['terminal', 'execute_code'],
        'requirements': ['Same train/test split', 'Multiple seeds', 'Same features']
    },
    'statistician': {
        'role': 'Statistical validation',
        'tools': ['execute_code'],
        'tests': ['t-test', 'Wilcoxon', 'Effect size']
    },
    'reporter': {
        'role': 'Generate evaluation report',
        'tools': ['file', 'wandb'],
        'output': 'docs/evaluations/<method_id>_report.md'
    }
}
```

---

### 4. Deployment Agent

**Goal:** Manage shadow mode and production deployment

**Workflow:**
1. Deploy method to shadow mode (parallel to production)
2. Monitor predictions daily
3. Compare shadow vs production
4. Alert on anomalies
5. After 1 month: prepare promotion recommendation

**Sub-agent Team:**
```python
# src/deployment/team.py
DEPLOYMENT_TEAM = {
    'shadow_deployer': {
        'role': 'Deploy method in shadow mode',
        'tools': ['terminal', 'file'],
        'output': 'src/deployment/shadow/<method_id>/'
    },
    'monitor': {
        'role': 'Continuous monitoring',
        'tools': ['terminal', 'execute_code'],
        'frequency': 'hourly',
        'metrics': ['prediction_divergence', 'latency', 'error_rate']
    },
    'promoter': {
        'role': 'Handle promotion to production',
        'tools': ['file', 'terminal'],
        'trigger': 'manual_approval'
    }
}
```

---

### 5. Basket Agent

**Goal:** Maintain method registry and archive

**Workflow:**
1. Update registry.yaml on state changes
2. Archive old methods with metadata
3. Link methods to replacements
4. Maintain "hall of fame"

**Sub-agent Team:**
```python
# src/basket/team.py
BASKET_TEAM = {
    'registrar': {
        'role': 'Maintain registry.yaml',
        'tools': ['file'],
        'triggers': ['new_method', 'status_change', 'promotion', 'archive']
    },
    'archivist': {
        'role': 'Archive methods with full metadata',
        'tools': ['file'],
        'output': 'src/basket/archived/<method_id>/'
    },
    'curator': {
        'role': 'Generate basket reports',
        'tools': ['file'],
        'frequency': 'monthly',
        'output': 'docs/basket_reports/'
    }
}
```

---

## 🔄 Agent Communication Protocol

### Message Queue (File-based)

```
~/.hermes/projects/battery-rd/messages/
├── research_to_development/
│   └── new_candidates.json
├── development_to_evaluation/
│   └── ready_for_benchmark.json
├── evaluation_to_deployment/
│   └── promotion_recommendation.json
└── deployment_to_basket/
    └── status_change.json
```

### Message Schema

```json
{
  "message_id": "uuid",
  "timestamp": "ISO8601",
  "from_agent": "research",
  "to_agent": "development",
  "type": "new_candidates",
  "payload": {
    "candidates": [
      {
        "method_id": "battery_rul_transformer_003",
        "paper_title": "...",
        "paper_url": "...",
        "reported_performance": {...},
        "priority": "high"
      }
    ]
  },
  "status": "pending"
}
```

---

## 🛠️ Implementation: Agent Orchestration

### Main Orchestrator

```python
# src/orchestrator.py
from pathlib import Path
import yaml
import json
from datetime import datetime

class RDOrchestrator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.messages_dir = self.project_root / 'messages'
        self.registry_path = self.project_root / 'src' / 'basket' / 'registry.yaml'
    
    def check_messages(self, queue_name: str):
        """Check for new messages in a queue"""
        queue_path = self.messages_dir / queue_name
        messages = []
        for msg_file in queue_path.glob('*.json'):
            with open(msg_file) as f:
                messages.append(json.load(f))
        return messages
    
    def send_message(self, from_agent: str, to_agent: str, msg_type: str, payload: dict):
        """Send message to agent queue"""
        queue_path = self.messages_dir / f'{from_agent}_to_{to_agent}'
        msg_id = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{from_agent}_{to_agent}"
        
        message = {
            'message_id': msg_id,
            'timestamp': datetime.now().isoformat(),
            'from_agent': from_agent,
            'to_agent': to_agent,
            'type': msg_type,
            'payload': payload,
            'status': 'pending'
        }
        
        msg_path = queue_path / f'{msg_id}.json'
        with open(msg_path, 'w') as f:
            json.dump(message, f, indent=2)
        
        return msg_id
    
    def update_registry(self, method_id: str, **updates):
        """Update method status in registry"""
        with open(self.registry_path) as f:
            registry = yaml.safe_load(f)
        
        for method in registry['methods']:
            if method['id'] == method_id:
                method.update(updates)
                break
        
        with open(self.registry_path, 'w') as f:
            yaml.dump(registry, f, default_flow_style=False)
    
    def run_quarterly_cycle(self):
        """Trigger quarterly development cycle"""
        # Get all candidates from research
        candidates = self.get_candidates()
        
        # Select top methods
        selected = self.select_methods(candidates)
        
        # Send to development team
        self.send_message('orchestrator', 'development', 'start_implementation', {
            'methods': selected,
            'deadline': '3 months from now'
        })
```

---

## 📅 Cron Job Configuration

### All Agent Schedules

```bash
# ~/.hermes/cron/battery_rd_agents.yaml

# Research Agents
- name: research-arxiv-daily
  schedule: "0 9 * * *"
  agent: research
  task: "Scan arXiv for new battery RUL papers"
  script: "src/research/arxiv_monitor.py"
  
- name: research-journals-weekly
  schedule: "0 10 * * 1"
  agent: research
  task: "Scan journals for new methods"
  script: "src/research/journal_monitor.py"
  
- name: research-github-daily
  schedule: "0 11 * * *"
  agent: research
  task: "Scan GitHub for new repos"
  script: "src/research/github_monitor.py"

# Deployment Agent (Continuous Monitoring)
- name: deployment-shadow-monitor
  schedule: "0 * * * *"  # Every hour
  agent: deployment
  task: "Compare shadow vs production predictions"
  script: "src/deployment/shadow_monitor.py"

# Basket Agent (Monthly Reports)
- name: basket-monthly-report
  schedule: "0 12 1 * *"
  agent: basket
  task: "Generate monthly basket report"
  script: "src/basket/monthly_report.py"

# Quarterly Development Cycle
- name: quarterly-development-cycle
  schedule: "0 9 1 1,4,7,10 *"  # First day of Jan, Apr, Jul, Oct
  agent: orchestrator
  task: "Start quarterly development cycle"
  script: "src/orchestrator.py --quarterly-cycle"
```

---

## 🎯 Persistent Agent Deployment

### Using Hermes Cron System

Each agent runs as a cron job with persistent state:

```python
# Example: Deploy Research Agent
from hermes_tools import cronjob

# Create daily arXiv monitoring job
cronjob(
    action='create',
    prompt="""
    Research Agent Task: Scan arXiv for new battery RUL papers
    
    1. Search arXiv for: 'battery RUL', 'lithium-ion degradation', 'remaining useful life'
    2. Filter by categories: cs.LG, eess.SP, physics.data-an
    3. Extract paper metadata (title, authors, abstract, URL)
    4. Check if method is novel (compare against basket)
    5. Create candidate method card in src/basket/candidates/
    
    Output: Summary of new papers found and candidate methods extracted
    """,
    schedule='0 9 * * *',
    name='research-arxiv-daily',
    deliver='origin',  # Report back to chat
    skills=['research-monitor', 'arxiv', 'basket-manager']
)
```

---

## 🔧 Worker Team Coordination

### Team Lead Pattern

Each agent has a "team lead" that coordinates sub-agents:

```python
# src/research/team_lead.py
class ResearchTeamLead:
    def __init__(self):
        self.subagents = {
            'arxiv_scraper': ArxivScraper(),
            'journal_monitor': JournalMonitor(),
            'github_scout': GitHubScout(),
            'pdf_processor': PDFProcessor()
        }
    
    def run_daily_cycle(self):
        """Coordinate daily research cycle"""
        results = {}
        
        # Run all sub-agents in parallel
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(agent.scan): name
                for name, agent in self.subagents.items()
            }
            
            for future in as_completed(futures):
                name = futures[future]
                results[name] = future.result()
        
        # Aggregate results
        candidates = self.aggregate_candidates(results)
        
        # Send to orchestrator
        orchestrator.send_message('research', 'development', 'new_candidates', {
            'candidates': candidates,
            'date': datetime.now().isoformat()
        })
        
        return candidates
```

---

## 📊 Monitoring Dashboard

### Agent Health & Status

```python
# src/monitoring/dashboard.py
class AgentDashboard:
    def get_agent_status(self):
        """Get status of all agents"""
        return {
            'research': {
                'last_run': self.get_last_run('research'),
                'status': 'healthy' if recent else 'stale',
                'candidates_found': self.count_candidates(),
                'next_scheduled': self.get_next_run('research')
            },
            'development': {
                'active_implementations': self.count_active_dev(),
                'status': 'idle' if no_active else 'active',
                'quarterly_cycle': self.get_cycle_status()
            },
            'evaluation': {
                'pending_evaluations': self.count_pending(),
                'completed_this_month': self.count_completed()
            },
            'deployment': {
                'shadow_methods': self.list_shadow(),
                'production_method': self.get_production(),
                'alerts': self.get_alerts()
            }
        }
```

---

## 🚀 Deployment Steps

1. **Create GitHub repo** - Done via setup script
2. **Initialize project structure** - Done via setup script
3. **Configure PostgreSQL** - User provides connection details
4. **Deploy Research Agent** - Daily cron jobs
5. **Deploy Deployment Agent** - Hourly monitoring
6. **Set up message queues** - File-based IPC
7. **Create initial registry** - Empty basket with schema
8. **Test agent communication** - End-to-end message flow

---

**This is your autonomous R&D organization.** 🧠

Each agent runs independently, communicates via messages, and maintains persistent state. The system evolves continuously with zero manual intervention (except for manual approvals at key decision points).
