# Deployment Guide

## Deployment Strategies

### Blue-Green Deployment
- **Blue**: Current production environment
- **Green**: New version being deployed
- **Switch**: Instant cutover via load balancer
- **Rollback**: Instant rollback by switching back

### Canary Deployment
- **Canary**: 5% traffic to new version
- **Monitor**: Watch error rates, latency
- **Gradual**: Increase traffic 5% → 25% → 50% → 100%
- **Rollback**: Reduce traffic to 0% if issues

### Rolling Update
- **Batch 1**: Update 25% of pods
- **Verify**: Health checks pass
- **Batch 2**: Update next 25%
- **Continue**: Until all pods updated

## Kubernetes Deployment

### Prerequisites
```bash
# Install tools
kubectl version --client
helm version
aws eks update-kubeconfig --name beautyrec-prod
```

### Deploy to Kubernetes
```bash
# Apply base manifests
kubectl apply -f infra/kubernetes/base/

# Apply production overlay
kubectl apply -f infra/kubernetes/overlays/prod/

# Check deployment status
kubectl get pods -n beautyrec
kubectl get svc -n beautyrec
kubectl get ingress -n beautyrec
```

### Scaling
```bash
# Manual scaling
kubectl scale deployment beautyrec-backend --replicas=5 -n beautyrec

# Check HPA
kubectl get hpa -n beautyrec
```

## Docker Deployment

### Build Images
```bash
# Backend
docker build -t beautyrec-backend:latest -f Dockerfile.backend .

# Frontend
docker build -t beautyrec-frontend:latest -f Dockerfile.frontend .
```

### Docker Compose
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend

# Stop
docker-compose down
```

## Environment Configuration

### Development
```bash
ENVIRONMENT=development
DATABASE_URL=sqlite:///./beautyrec.db
LOG_LEVEL=debug
```

### Staging
```bash
ENVIRONMENT=staging
DATABASE_URL=postgresql+asyncpg://user:pass@staging-db:5432/beautyrec
LOG_LEVEL=info
```

### Production
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://user:pass@prod-db:5432/beautyrec
LOG_LEVEL=warning
```

## CI/CD Pipeline

### GitHub Actions Workflow
```yaml
name: CI/CD
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -e ".[all]"
      - run: pytest backend/tests/ -v
      - run: ruff check backend/
      - run: mypy backend/app --ignore-missing-imports

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker build -t beautyrec-backend:latest -f Dockerfile.backend .
      - run: docker build -t beautyrec-frontend:latest -f Dockerfile.frontend .

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: kubectl apply -f infra/kubernetes/overlays/prod/
```

## Monitoring Deployment

### Health Checks
```bash
# Backend health
curl https://api.beautyrec.dev/health

# Kubernetes health
kubectl get pods -n beautyrec -o wide
kubectl describe pod <pod-name> -n beautyrec
```

### Logs
```bash
# Kubernetes logs
kubectl logs -f deployment/beautyrec-backend -n beautyrec

# Docker logs
docker-compose logs -f backend
```

### Metrics
- **Prometheus**: http://prometheus:9090
- **Grafana**: http://grafana:3000

## Rollback Procedures

### Kubernetes Rollback
```bash
# Rollback to previous version
kubectl rollout undo deployment/beautyrec-backend -n beautyrec

# Rollback to specific revision
kubectl rollout undo deployment/beautyrec-backend --to-revision=2 -n beautyrec

# Check rollout history
kubectl rollout history deployment/beautyrec-backend -n beautyrec
```

### Docker Rollback
```bash
# Stop current version
docker-compose down

# Start previous version
docker-compose up -d backend=beautyrec-backend:previous
```

## References

- Kubernetes: https://kubernetes.io/docs/
- Docker: https://docs.docker.com/
- GitHub Actions: https://docs.github.com/en/actions
