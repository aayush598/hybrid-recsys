#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
VENV_DIR="$PROJECT_DIR/.venv"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}   BeautyRec - Hybrid Recommendation System${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Check Python venv
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Python venv not found. Run: python -m venv .venv && .venv/bin/pip install -r backend/requirements.txt${NC}"
    exit 1
fi

# Check node_modules
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo -e "${YELLOW}Installing frontend dependencies...${NC}"
    (cd "$FRONTEND_DIR" && npm install)
fi

# Check if DB has data
DB_PATH="$BACKEND_DIR/data/beautyrec.db"
if [ ! -f "$DB_PATH" ]; then
    echo -e "${YELLOW}No database found. Seeding data (first time only, takes ~30s)...${NC}"
    (cd "$BACKEND_DIR" && PYTHONPATH=. "$VENV_DIR/bin/python" seed_data.py --sample)
    echo -e "${YELLOW}Training ML models (first time only, takes ~15s)...${NC}"
    (cd "$BACKEND_DIR" && PYTHONPATH=. "$VENV_DIR/bin/python" evaluate.py)
fi

# Check if models exist
if [ ! -d "$BACKEND_DIR/data/models" ] || [ -z "$(ls -A "$BACKEND_DIR/data/models" 2>/dev/null)" ]; then
    echo -e "${YELLOW}No trained models found. Training now...${NC}"
    (cd "$BACKEND_DIR" && PYTHONPATH=. "$VENV_DIR/bin/python" evaluate.py)
fi

echo ""
echo -e "${GREEN}Starting backend server on http://localhost:8000${NC}"
echo -e "${GREEN}Starting frontend dev server on http://localhost:3000${NC}"
echo ""

# Start backend
(cd "$BACKEND_DIR" && PYTHONPATH=. "$VENV_DIR/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

# Wait for backend to be ready
echo -n "Waiting for backend"
for i in $(seq 1 30); do
    if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e " ${GREEN}ready!${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e " ${RED}failed to start!${NC}"
    cleanup
fi

# Start frontend
(cd "$FRONTEND_DIR" && npm run dev) &
FRONTEND_PID=$!
sleep 2

echo ""
echo -e "${BLUE}============================================${NC}"
echo -e "${GREEN}  BeautyRec is running!${NC}"
echo ""
echo -e "  Frontend:  ${BLUE}http://localhost:3000${NC}"
echo -e "  Backend:   ${BLUE}http://localhost:8000${NC}"
echo -e "  API Docs:  ${BLUE}http://localhost:8000/docs${NC}"
echo -e "  Health:    ${BLUE}http://localhost:8000/api/v1/health${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all services"
echo -e "${BLUE}============================================${NC}"
echo ""

# Wait for either to exit
wait
