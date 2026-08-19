#!/bin/bash
set -e

MODEL_DIR="/app/backend/data/models"
DB_FILE="/app/backend/data/beautyrec.db"

# First run: seed data and train models
if [ ! -f "$DB_FILE" ] || [ ! -f "$MODEL_DIR/cf_model.pkl" ]; then
    echo "=== First run: seeding data and training models ==="

    # Create data directories
    mkdir -p /app/backend/data/raw /app/backend/data/processed /app/backend/data/evaluation

    # Check if ml-25m dataset is available
    if [ ! -d "/app/backend/data/raw/ml-25m" ]; then
        echo "=== Downloading MovieLens 25M dataset ==="
        cd /app/backend/data/raw
        curl -sL https://files.grouplens.org/datasets/movielens/ml-25m.zip -o ml-25m.zip
        unzip -q ml-25m.zip
        rm ml-25m.zip
        cd /app/backend
    fi

    # Seed data (100K ratings)
    echo "=== Seeding database ==="
    PYTHONPATH=. python seed_data.py --sample

    # Train models
    echo "=== Training models ==="
    PYTHONPATH=. python evaluate.py

    echo "=== Setup complete ==="
fi

# Start the server
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
