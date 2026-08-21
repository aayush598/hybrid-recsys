# Getting Started — BeautyRec Developer Onboarding

Welcome to the BeautyRec recommendation system! This guide gets you from
clone to running app in ~15 minutes.

## Prerequisites

| Tool | Version | Check |
| --- | --- | --- |
| Python | 3.12+ | `python --version` |
| Node.js | 20+ | `node --version` |
| Docker + Compose | recent | `docker compose version` |
| Make / bash | any | — |

Optional for infra work: Terraform ≥ 1.5, kubectl, Helm 3.

## 1. Clone and Set Up the Backend

```bash
git clone <repo-url> && cd recommendation_system

# Python environment (or use your own venv manager)
python -m venv .venv && source .venv/bin/activate
pip install -e "backend[dev]"        # or: pip install -r backend/requirements.txt
```

Configure environment:

```bash
cp .env.example .env                 # defaults work out of the box (SQLite)
```

## 2. Run the Stack Locally

Option A — everything in containers:

```bash
docker compose up --build
```

Option B — native processes with hot reload:

```bash
./start.sh                           # backend on :8000, frontend on :3000
```

Verify:

- Backend health: http://localhost:8000/api/v1/health
- API docs (OpenAPI): http://localhost:8000/docs
- Frontend: http://localhost:3000

## 3. Repository Map

```
backend/
  app/
    api/          REST routers (v1)
    core/         config, logging, security, disaster recovery
    db/           SQLAlchemy models & session management
    ml/           training pipelines, evaluation, tracking
    services/     business logic (recommendation orchestration)
    serving/      model loading & in-process inference (see ADR 005)
frontend/
  src/            React + TypeScript app (Vite)
infra/
  kubernetes/     base manifests, Helm chart, Kustomize overlays
  terraform/      AWS modules (VPC, EKS, RDS, ElastiCache) per environment
docs/
  adr/            architecture decision records — read ADRs 001–005 first!
  runbooks/       operational procedures
```

## 4. Key Concepts (read these ADRs)

1. **ADR 002** — hybrid CF + content + trending algorithm.
2. **ADR 004** — SQLite locally, PostgreSQL in production; never write
   dialect-specific SQL without checking both.
3. **ADR 005** — models are served in-process; artifacts live under
   `backend/data/models/`.

## 5. Testing & Linting

```bash
# Backend tests (SQLite, no services needed)
pytest backend/tests -m "not slow"

# Lint & format
ruff check backend && ruff format --check backend

# Frontend
cd frontend && npm ci && npm run test && npm run lint
```

Pre-commit hooks are available:

```bash
pre-commit install
```

## 6. Making Your First Change

1. Create a branch: `feat/<short-name>` or `fix/<short-name>`.
2. Add/adjust tests alongside your change; keep coverage stable.
3. Run the test suite and linters locally.
4. Open a PR — CI runs unit tests, integration tests, and lint.
5. Migrations: use Alembic (`alembic revision --autogenerate`); ensure they
   apply cleanly to both SQLite and Postgres.

## 7. Deployments (overview)

- **Staging:** merge to `main` → CI builds images → deploys to the staging
  EKS cluster via the Kustomize staging overlay.
- **Production:** tagged releases deploy through the Helm chart
  (`infra/kubernetes/helm/beautyrec`) with HPA and PDB protections enabled.
- Infra changes go through Terraform PRs per environment
  (`infra/terraform/environments/{staging,production}`).

## 8. Where to Get Help

- `#beautyrec-dev` Slack channel for questions.
- Operational incidents → see `docs/runbooks/`.
- Architecture proposals → write an ADR using the template in
  `docs/adr/001-architecture-decision-records.md`.

Happy building!
