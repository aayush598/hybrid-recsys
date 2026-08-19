#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[BeautyRec]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

cd "$PROJECT_ROOT"

case "${1:-help}" in
  setup)
    log "Setting up BeautyRec..."
    python -m venv .venv
    source .venv/bin/activate
    pip install -e ".[all]"
    cd frontend && npm install && cd ..
    success "Setup complete"
    ;;

  seed)
    log "Seeding database with MovieLens data..."
    source .venv/bin/activate
    cd backend
    if [[ "${2:-}" == "--sample" ]]; then
      python seed_data.py --sample
    else
      python seed_data.py
    fi
    cd ..
    success "Database seeded"
    ;;

  train)
    log "Training models..."
    source .venv/bin/activate
    cd backend
    python -c "
import asyncio
from app.db.session import init_db, get_db_context
from app.services.model_manager import model_manager
from ml.pipelines.data_pipeline import FeatureEngineer

async def main():
    await init_db()
    async with get_db_context() as db:
        fe = FeatureEngineer(db)
        await fe.build_content_features()
    await model_manager.initialize()
    print('Models trained successfully')

asyncio.run(main())
"
    cd ..
    success "Models trained"
    ;;

  evaluate)
    log "Running evaluation..."
    source .venv/bin/activate
    cd backend
    python evaluate.py
    cd ..
    ;;

  dev)
    log "Starting development servers..."
    source .venv/bin/activate
    cd backend
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
    BACKEND_PID=$!
    cd ../frontend
    npm run dev &
    FRONTEND_PID=$!
    log "Backend: http://localhost:8000"
    log "Frontend: http://localhost:3000"
    log "Docs: http://localhost:8000/docs"
    trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
    wait
    ;;

  docker-up)
    log "Starting Docker services..."
    docker-compose up -d --build
    success "Services started"
    log "Frontend: http://localhost:3000"
    log "Backend API: http://localhost:8000"
    log "Grafana: http://localhost:3001"
    log "Prometheus: http://localhost:9090"
    ;;

  docker-down)
    log "Stopping Docker services..."
    docker-compose down
    success "Services stopped"
    ;;

  help|*)
    echo "BeautyRec - Recommendation System"
    echo ""
    echo "Usage: ./scripts/setup.sh <command>"
    echo ""
    echo "Commands:"
    echo "  setup        Install dependencies and set up environment"
    echo "  seed         Download MovieLens data and seed database"
    echo "  seed --sample  Seed with a small sample for quick testing"
    echo "  train        Train ML models"
    echo "  evaluate     Run evaluation metrics"
    echo "  dev          Start development servers (backend + frontend)"
    echo "  docker-up    Start all services with Docker Compose"
    echo "  docker-down  Stop all Docker services"
    echo "  help         Show this help message"
    ;;
esac
