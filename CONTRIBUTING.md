# Contributing to BeautyRec

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Code Style](#code-style)
- [Commit Convention](#commit-convention)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Architecture Decisions](#architecture-decisions)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

We follow the Contributor Covenant Code of Conduct. Be respectful, inclusive, and constructive.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourusername/beautyrec.git`
3. Create a branch: `git checkout -b feature/amazing-feature`
4. Make your changes
5. Run tests: `pytest backend/tests/`
6. Commit: `git commit -m "feat: add amazing feature"`
7. Push: `git push origin feature/amazing-feature`
8. Open a Pull Request

## Development Setup

```bash
# Clone and setup
git clone https://github.com/yourusername/beautyrec.git
cd beautyrec
python -m venv .venv && source .venv/bin/activate
pip install -e ".[all]"

# Frontend
cd frontend && npm install && cd ..

# Seed data
cd backend && python seed_data.py --sample && cd ..

# Run tests
pytest backend/tests/ -v --cov=backend/app

# Lint
ruff check backend/
ruff format backend/
mypy backend/app --ignore-missing-imports
```

## Code Style

### Python (Ruff + MyPy)
- Line length: 100 characters max
- Type hints required on all public functions
- Docstrings required on all public classes and functions
- Follow PEP 8 naming conventions
- Use `from __future__ import annotations` in all files

### TypeScript (ESLint)
- Strict TypeScript mode
- Functional components with hooks
- Props interfaces required
- No `any` types unless justified

### Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add new recommendation algorithm
fix: resolve cold-start fallback issue
docs: update API documentation
style: format code with ruff
refactor: extract feature store into separate module
test: add unit tests for neural CF model
chore: update dependencies
perf: optimize FAISS index building for large datasets
ci: add GitHub Actions workflow
build: update Docker configuration
```

## Pull Request Process

1. **Before submitting:**
   - All tests pass (`pytest`)
   - Linting passes (`ruff check`)
   - Type checking passes (`mypy`)
   - Documentation updated if needed
   - ADR created for architectural changes

2. **PR Description:**
   - What does this PR do?
   - Why is this change needed?
   - How to test it?
   - Any breaking changes?

3. **Review:**
   - At least 1 approval required
   - CI must pass
   - No merge conflicts

## Testing Requirements

| Test Type | Requirement | Command |
|-----------|-------------|---------|
| Unit Tests | 80%+ coverage | `pytest backend/tests/unit/` |
| Integration Tests | All API endpoints | `pytest backend/tests/integration/` |
| Load Tests | <100ms P95 | `locust -f backend/tests/load/locustfile.py` |

## Architecture Decisions

For any significant architectural change, create an ADR in `docs/adr/`:

```bash
# Use the template
cp docs/adr/000-template.md docs/adr/NNN-decision-title.md
```

## Reporting Issues

- Use GitHub Issues
- Include reproduction steps
- Include environment details
- Label appropriately (bug, enhancement, question)

## Questions?

Open a Discussion on GitHub or reach out on Slack.
