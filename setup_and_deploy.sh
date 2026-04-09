#!/bin/bash
# Battery R&D Pipeline - Setup and Deployment Script
# This script sets up the GitHub repo, configures agents, and deploys worker teams

set -e

echo "🔋 Battery R&D Pipeline - Setup & Deployment"
echo "=============================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project config
PROJECT_NAME="battery-rd-pipeline"
GITHUB_ORG=""  # Will be set by user
REPO_URL=""

echo -e "${BLUE}Step 1: GitHub Authentication${NC}"
echo "----------------------------------------"

# Check if gh is available
if command -v gh &> /dev/null; then
    echo "✓ GitHub CLI (gh) found"
    if gh auth status &> /dev/null; then
        echo "✓ Already authenticated with GitHub"
        GITHUB_USER=$(gh api user | jq -r '.login')
        echo "  Logged in as: $GITHUB_USER"
    else
        echo -e "${YELLOW}Not authenticated. Running gh auth login...${NC}"
        gh auth login
        GITHUB_USER=$(gh api user | jq -r '.login')
    fi
else
    echo -e "${YELLOW}GitHub CLI (gh) not installed. Using git + token method.${NC}"
    echo ""
    echo "Please create a personal access token:"
    echo "  1. Go to: https://github.com/settings/tokens"
    echo "  2. Click 'Generate new token (classic)'"
    echo "  3. Scopes: repo, workflow, read:org"
    echo "  4. Copy the token"
    echo ""
    read -p "Enter your GitHub username: " GITHUB_USER
    read -sp "Enter your personal access token: " GITHUB_TOKEN
    echo ""
    
    # Configure git
    git config --global credential.helper store
    echo "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com" > ~/.git-credentials
    chmod 600 ~/.git-credentials
    
    export GITHUB_TOKEN
    echo "✓ Git credentials configured"
fi

echo ""
echo -e "${BLUE}Step 2: Repository Setup${NC}"
echo "-------------------------------------"

# Get repo name
read -p "Repository name [battery-rd-pipeline]: " REPO_NAME
REPO_NAME=${REPO_NAME:-"battery-rd-pipeline"}

echo "Creating repository: ${GITHUB_USER}/${REPO_NAME}..."

# Create repo using gh or curl
if command -v gh &> /dev/null; then
    gh repo create "$REPO_NAME" --public --description "Continuous R&D Pipeline for Battery RUL Estimation" --source=. --remote=origin --push
else
    # Use curl API
    curl -X POST "https://api.github.com/user/repos" \
        -H "Authorization: token $GITHUB_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -d "{
            \"name\": \"$REPO_NAME\",
            \"description\": \"Continuous R&D Pipeline for Battery RUL Estimation\",
            \"public\": true,
            \"auto_init\": true
        }"
    
    # Add remote
    git init
    git remote add origin "https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
fi

echo "✓ Repository created: https://github.com/${GITHUB_USER}/${REPO_NAME}"

echo ""
echo -e "${BLUE}Step 3: PostgreSQL Configuration${NC}"
echo "-------------------------------------------"

echo "Enter your PostgreSQL connection details:"
read -p "Database host [localhost]: " DB_HOST
DB_HOST=${DB_HOST:-"localhost"}

read -p "Database port [5432]: " DB_PORT
DB_PORT=${DB_PORT:-"5432"}

read -p "Database name: " DB_NAME

read -p "Database username: " DB_USER

read -sp "Database password: " DB_PASS
echo ""

# Create .env file for the project
cat > .env << EOF
# Battery R&D Pipeline - Environment Configuration

# PostgreSQL Connection
DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@${DB_HOST}:${DB_PORT}/${DB_NAME}
DB_HOST=${DB_HOST}
DB_PORT=${DB_PORT}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASS=${DB_PASS}

# GitHub Token (for API access)
GITHUB_TOKEN=${GITHUB_TOKEN:-""}

# OpenRouter API (for LLM calls)
OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-""}

# Weights & Biases (for experiment tracking)
WANDB_API_KEY=${WANDB_API_KEY:-""}
WANDB_PROJECT=${REPO_NAME}
EOF

chmod 600 .env
echo "✓ Database configuration saved to .env"

echo ""
echo -e "${BLUE}Step 4: Create Project Structure${NC}"
echo "------------------------------------------"

# Create directory structure
mkdir -p {src/{research,development,evaluation,deployment,basket},tests,data,scripts,docs,config}

# Create README
cat > README.md << 'EOF'
# Battery R&D Pipeline

Continuous R&D system for Battery Remaining Useful Life (RUL) estimation using ML & RL.

## 🎯 Vision

A living system that continuously evolves with the state of the art — automatically monitoring research, testing new methods, and maintaining a "basket" of proven approaches.

## 🔄 R&D Cycle

```
Research (Continuous) → Development (Quarterly) → Evaluation → Deployment → Archive
       ↑                                                                                │
       └────────────────────────────────────────────────────────────────────────────────┘
```

## 📁 Structure

- `src/research/` - Research monitoring, paper extraction, method cataloging
- `src/development/` - Method implementation, testing, documentation
- `src/evaluation/` - Benchmarking, comparison, statistical validation
- `src/deployment/` - Shadow mode, production deployment, monitoring
- `src/basket/` - Method registry and archived methods
- `tests/` - Unit and integration tests
- `scripts/` - Automation and cron job scripts
- `config/` - Configuration files
- `data/` - Local data cache (PostgreSQL is primary)

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Run research monitor
python src/research/monitor.py

# Run evaluation
python src/evaluation/benchmark.py
```

## 🤖 Persistent Agents

This project uses persistent sub-agents for each R&D phase:
- Research Agent - Monitors arXiv, journals, GitHub, PDFs
- Development Agent - Implements and tests new methods
- Evaluation Agent - Benchmarks and compares methods
- Deployment Agent - Manages shadow mode and production

## 📊 Method Basket

All proven methods are preserved in the basket:
- Active methods (production)
- Shadow methods (testing)
- Archived methods (hall of fame)

## 📝 License

MIT
EOF

# Create requirements.txt
cat > requirements.txt << 'EOF'
# Core
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
scikit-learn>=1.3.0

# Deep Learning
torch>=2.0.0
transformers>=4.30.0

# Battery Data
matplotlib>=3.7.0
seaborn>=0.12.0

# Database
psycopg2-binary>=2.9.0
sqlalchemy>=2.0.0

# API & Monitoring
requests>=2.31.0
feedparser>=6.0.0  # RSS feeds

# Experiment Tracking
wandb>=0.15.0

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0

# Utilities
pyyaml>=6.0.0
python-dotenv>=1.0.0
tqdm>=4.65.0
EOF

# Create .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.egg-info/
dist/
build/

# Environment
.env
*.env
!.env.example

# Data
data/*.csv
data/*.pkl
data/*.pt
*.h5

# Models
models/
checkpoints/
*.pth
*.pt

# Logs
*.log
wandb/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
EOF

echo "✓ Project structure created"

echo ""
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. cd ~/.hermes/projects/battery-rd"
echo "  2. pip install -r requirements.txt"
echo "  3. python -m pytest tests/  # Verify setup"
echo ""
echo "Repository: https://github.com/${GITHUB_USER}/${REPO_NAME}"
echo ""

# Push to GitHub
echo -e "${BLUE}Pushing to GitHub...${NC}"
git add .
git commit -m "Initial commit: Battery R&D Pipeline framework"
git push -u origin main

echo "✓ Code pushed to GitHub"
