# 🔋 Battery R&D Pipeline - Next Steps TODO

**Status:** ⏳ Waiting for PostgreSQL connection details

---

## 🔴 Phase 1: Database Setup (Immediate)

- [ ] **Configure PostgreSQL connection**
  - [ ] Update `.env` with database credentials
  - [ ] Test connection: `python src/data/postgres_loader.py`
  - [ ] Verify schema matches expected structure
  - [ ] Load sample data and inspect

- [ ] **Database schema validation**
  - [ ] Check `battery_cycles` table exists
  - [ ] Verify columns: battery_id, cycle, capacity, voltage, current, temperature, RUL
  - [ ] Count total rows and unique batteries
  - [ ] Check data quality (missing values, outliers)

---

## 🟡 Phase 2: First Quarterly Cycle (Once DB is Ready)

### 2.1 Review Candidate Methods

- [ ] Load all 8 candidate methods from `src/basket/candidates/`
- [ ] For each method, extract:
  - [ ] Method name and architecture
  - [ ] Reported performance (MAE, RMSE, etc.)
  - [ ] Data requirements
  - [ ] Implementation complexity
- [ ] Create comparison table

### 2.2 Select Methods for Implementation

- [ ] Define selection criteria:
  - [ ] Performance improvement over baseline
  - [ ] Novelty of approach
  - [ ] Feasibility (data, compute)
  - [ ] Relevance to our battery chemistry
- [ ] Select top 3-5 methods
- [ ] Document rationale for each selection

### 2.3 Deploy Development Agent Team

- [ ] Choose implementation model:
  - [ ] **Recommended:** Claude Code (`claude-sonnet-4`)
  - [ ] Alternative: Codex CLI
- [ ] Create implementation tasks for each selected method
- [ ] Set deadlines and success criteria
- [ ] Spawn sub-agents with `delegate_task(acp_command="claude")`

### 2.4 Implementation Sprint

For each selected method:
- [ ] Create method directory: `src/development/methods/<method_id>/`
- [ ] Implement `method.py` (following template)
- [ ] Create `config.yaml` with hyperparameters
- [ ] Write `README.md` with usage instructions
- [ ] Write unit tests: `tests/test_<method_id>.py`
- [ ] Run tests and fix issues
- [ ] Document any deviations from paper

---

## 🟢 Phase 3: Evaluation (After Implementation)

### 3.1 Prepare Benchmark Dataset

- [ ] Load all battery data from PostgreSQL
- [ ] Create train/test split (by battery ID, not cycle)
- [ ] Normalize/scale features
- [ ] Create data loaders for each method

### 3.2 Run Benchmarks

For each implemented method:
- [ ] Train on training set (multiple seeds: 5+)
- [ ] Evaluate on test set
- [ ] Compute metrics:
  - [ ] MAE (Mean Absolute Error)
  - [ ] RMSE (Root Mean Square Error)
  - [ ] Relative Error (%)
  - [ ] Accuracy @10% (predictions within 10% of true RUL)
  - [ ] Accuracy @20%
- [ ] Log to Weights & Biases (if API key available)

### 3.3 Statistical Validation

- [ ] Compare each method against baseline
- [ ] Run statistical tests:
  - [ ] Paired t-test
  - [ ] Wilcoxon signed-rank test
  - [ ] Effect size (Cohen's d)
- [ ] Determine statistical significance (p < 0.05)

### 3.4 Generate Evaluation Report

- [ ] Create report in `docs/evaluations/<method_id>_report.md`
- [ ] Include:
  - [ ] Method description
  - [ ] Performance metrics (table)
  - [ ] Comparison plots (MAE, RMSE by method)
  - [ ] Statistical test results
  - [ ] Recommendation: promote to shadow / reject
- [ ] Send to deployment agent via message queue

---

## 🔵 Phase 4: Deployment (After Evaluation Approval)

### 4.1 Shadow Mode Setup

- [ ] Deploy top-performing method to `src/deployment/shadow/`
- [ ] Update `registry.yaml`: status = "shadow"
- [ ] Set shadow mode start date
- [ ] Configure hourly monitoring

### 4.2 Continuous Monitoring

- [ ] Deployment agent runs hourly:
  - [ ] Load recent 100 cycles from PostgreSQL
  - [ ] Run predictions with production and shadow methods
  - [ ] Compare: divergence, error rates, latency
  - [ ] Log to `logs/shadow_comparison.log`
- [ ] Alert thresholds:
  - [ ] Divergence > 15% → ALERT
  - [ ] Shadow error > production error → WARNING
  - [ ] Latency > 5x → WARNING
  - [ ] Crashes → CRITICAL

### 4.3 Shadow Mode Review (After 30 Days)

- [ ] Aggregate 30 days of comparison data
- [ ] Compute final metrics
- [ ] Prepare promotion recommendation
- [ ] Request manual approval from user

### 4.4 Production Promotion (After Approval)

- [ ] Update `registry.yaml`: status = "active"
- [ ] Set `production.method_id` to new method
- [ ] Archive old production method
- [ ] Document promotion in `docs/basket_reports/`

---

## 🟣 Phase 5: Continuous R&D Loop (Ongoing)

### 5.1 Research Agent (Daily @ 9 AM)

- [ ] Scan arXiv for new papers
- [ ] Extract novel methods
- [ ] Create candidate cards
- [ ] Add to basket/candidates/

### 5.2 Quarterly Cycle (Every 3 Months)

- [ ] Review accumulated candidates
- [ ] Select new methods for implementation
- [ ] Deploy development team
- [ ] Repeat Phases 2-4

### 5.3 Monthly Basket Report

- [ ] Generate report of all methods:
  - [ ] Active methods
  - [ ] Shadow methods
  - [ ] Archived methods
  - [ ] Performance trends
- [ ] Save to `docs/basket_reports/monthly_YYYY_MM.md`

---

## 📊 Success Metrics

### Technical
- [ ] At least 1 baseline method implemented and tested
- [ ] PostgreSQL data loading working
- [ ] All 3 cron agents running without errors
- [ ] First quarterly cycle completed

### Performance
- [ ] Baseline MAE < 20 cycles
- [ ] Baseline RMSE < 25 cycles
- [ ] At least 1 method shows improvement over baseline

### Operational
- [ ] Shadow mode running for 30 days
- [ ] No critical alerts during monitoring
- [ ] First method promoted to production

---

## 🚨 Blockers

- [ ] **PostgreSQL connection details** (CRITICAL - waiting from user)
- [ ] OpenRouter API key (for LLM agents)
- [ ] Weights & Biases API key (for experiment tracking)

---

## 📝 Notes

- **Repository:** https://github.com/Ozzstein/battery-rd-pipeline
- **Current candidates:** 8 methods in `src/basket/candidates/`
- **Next quarterly cycle:** April 2026 (this month!)
- **Recommended model for development:** Claude Code (`claude-sonnet-4`)

---

**Last Updated:** April 9, 2026
**Status:** ⏳ Waiting for PostgreSQL credentials
