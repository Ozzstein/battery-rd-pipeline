# Battery R&D Pipeline

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status](https://img.shields.io/badge/status-active-development-green)]()

> **Continuous R&D system for Battery Remaining Useful Life (RUL) estimation using ML & RL**

---

## 🎯 Vision

A living, autonomous R&D organization that:
- **Continuously monitors** research (arXiv, journals, GitHub, PDFs)
- **Quarterly develops** new methods from cutting-edge papers
- **Rigorously evaluates** against baselines with statistical validation
- **Safely deploys** via shadow mode before production
- **Preserves all knowledge** in a "basket" of proven methods

---

## 🔄 The R&D Cycle

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│   │  RESEARCH   │────▶│DEVELOPMENT  │────▶│ EVALUATION  │       │
│   │   PHASE     │     │   PHASE     │     │   PHASE     │       │
│   │ (Daily)     │     │ (Quarterly) │     │ (Per Method)│       │
│   └─────────────┘     └─────────────┘     └─────────────┘       │
│          ▲                                      │                │
│          │                                      ▼                │
│          │                            ┌─────────────┐           │
│          │                            │ DEPLOYMENT  │           │
│          │                            │   PHASE     │           │
│          │                            │ (Continuous)│           │
│          │                            └─────────────┘           │
│          │                                      │                │
│          └──────────────────────────────────────┘                │
│                     (Continuous Loop)                            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
battery-rd-pipeline/
├── src/
│   ├── research/           # Research monitoring agents
│   │   ├── arxiv_monitor.py
│   │   ├── journal_monitor.py
│   │   ├── github_monitor.py
│   │   └── pdf_processor.py
│   ├── development/        # Method implementation
│   │   ├── methods/        # Implemented methods
│   │   └── templates/      # Implementation templates
│   ├── evaluation/         # Benchmarking & validation
│   │   ├── benchmark.py
│   │   └── statistics.py
│   ├── deployment/         # Shadow & production
│   │   ├── shadow/         # Shadow mode methods
│   │   └── production/     # Active production method
│   ├── basket/             # Method registry
│   │   ├── candidates/     # New methods to evaluate
│   │   ├── active/         # Current production
│   │   ├── shadow/         # In shadow mode
│   │   ├── archived/       # Hall of fame
│   │   └── registry.yaml   # Master catalog
│   └── data/               # Data layer
│       └── postgres_loader.py
├── tests/                  # Unit & integration tests
├── scripts/                # Automation scripts
├── config/                 # Configuration files
├── docs/                   # Documentation
├── logs/                   # Agent logs
├── messages/               # Inter-agent communication
├── .env                    # Environment variables (gitignored)
├── .env.example            # Template
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL database with battery cycling data
- GitHub account (for repo access)
- OpenRouter API key (for LLM agents)

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/battery-rd-pipeline.git
cd battery-rd-pipeline

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and API keys

# Test connection
python src/data/postgres_loader.py
```

### Running Agents

```bash
# Manual agent runs
python src/research/arxiv_monitor.py      # Scan arXiv
python src/deployment/shadow_monitor.py   # Monitor shadow mode
python src/orchestrator.py                # Run quarterly cycle

# Or wait for scheduled cron jobs (already configured)
```

---

## 🤖 Persistent Agents

| Agent | Schedule | Purpose |
|-------|----------|---------|
| **Research Agent** | Daily (9 AM) | Scan arXiv for new papers |
| **Deployment Monitor** | Hourly | Compare shadow vs production |
| **Quarterly Orchestrator** | Quarterly | Trigger development cycles |

### Agent Communication

Agents communicate via file-based message queues:

```
messages/
├── research_to_development/
│   └── new_candidates.json
├── development_to_evaluation/
│   └── ready_for_benchmark.json
├── evaluation_to_deployment/
│   └── promotion_recommendation.json
└── deployment_to_basket/
    └── status_change.json
```

---

## 🗄️ The Basket (Method Registry)

All methods are tracked through their lifecycle:

```yaml
# registry.yaml example
methods:
  - id: "battery_rul_lstm_001"
    name: "LSTM-based RUL Estimation"
    domain: "battery_rul"
    status: "active"  # active | shadow | archived | rejected
    
    timeline:
      extracted: "2026-01-15"
      implemented: "2026-02-01"
      shadow_start: "2026-02-15"
      promoted: "2026-03-20"
    
    performance:
      mae: 18.5
      rmse: 23.2
    
    replaced_by: null
    notes: "Current production baseline"
```

### Status Lifecycle

```
[New] → [Implemented] → [Shadow Mode (1 month)] → [Active] → [Archived]
   │           │              │                        │
   │           │              │                        └─▶ Still in basket
   │           │              └─▶ Manual approval required
   │           └─▶ Code + tests ready
   └─▶ Paper extracted
```

---

## 📊 Database Schema

Expected PostgreSQL schema for `battery_cycles` table:

```sql
CREATE TABLE battery_cycles (
    battery_id      VARCHAR(50) NOT NULL,
    cycle           INTEGER NOT NULL,
    capacity        FLOAT,
    v_charge        FLOAT,
    v_discharge     FLOAT,
    i_charge        FLOAT,
    i_discharge     FLOAT,
    impedance       FLOAT,
    temperature     FLOAT,
    rul             INTEGER,  -- Remaining Useful Life (cycles)
    timestamp       TIMESTAMP DEFAULT NOW(),
    
    PRIMARY KEY (battery_id, cycle)
);
```

---

## 📈 Evaluation Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| **MAE** | mean(\|pred - true\|) | < 20 cycles |
| **RMSE** | √(mean((pred - true)²)) | < 25 cycles |
| **Relative Error** | mean(\|pred - true\| / true) | < 15% |
| **Accuracy @10%** | % within 10% error | > 70% |
| **Accuracy @20%** | % within 20% error | > 90% |

---

## 🛠️ Development Workflow

### Quarterly Cycle

1. **Week 1-2:** Research review & method selection
2. **Week 3-8:** Implementation & testing
3. **Week 9-10:** Evaluation & benchmarking
4. **Week 11-14:** Shadow mode deployment
5. **Week 15:** Manual review & promotion decision

### Adding a New Method

```bash
# 1. Research extracts method to candidates/
# 2. Quarterly cycle selects it
# 3. Development team implements:
mkdir -p src/development/methods/battery_rul_newmethod_001
cd src/development/methods/battery_rul_newmethod_001

# Create implementation following template
cp ../../templates/method_template.py method.py
cp ../../templates/config_template.yaml config.yaml

# 4. Write tests
cd ../../../../tests
# Create test_battery_rul_newmethod_001.py

# 5. Run benchmarks
python src/evaluation/benchmark.py --method battery_rul_newmethod_001
```

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🎓 References

1. NASA PCoE Battery Dataset: https://ti.arc.nasa.gov/tech/dash/groups/pcoe/prognostic-data-repository/
2. GRPO: "Group Relative Policy Optimization" (DeepSeek AI, 2025)
3. RUL Survey: "A Review on Remaining Useful Life Estimation for Lithium-Ion Batteries" (IEEE, 2023)

---

## 📞 Contact

- **GitHub Issues:** For bugs and feature requests
- **Discussions:** For questions and ideas

---

**Built with ❤️ by the Battery R&D Team (Human + AI)**
