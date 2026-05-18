# AI Quality Gate

A production-grade GitHub App that detects AI-generated issues and pull requests, scores contribution quality, and helps maintainers manage the flood of low-quality automated contributions.

## Features

- **AI Detection** — 40+ fingerprint patterns detecting vocabulary, phrasing, structural, and hallucination signals
- **Quality Scoring** — 15+ checks for issues (repro steps, env info, code snippets) and PRs (linked issues, tests, diff analysis)
- **GitHub Checks** — A `success` / `neutral` / `failure` check run is posted on **every** pull request (visible in the Checks tab and usable as a branch-protection requirement)
- **Auto-Labeling** — `ai-generated`, `ai-suspected`, `low-quality`, `high-quality` (labels are auto-created if missing)
- **Configurable Actions** — Comment, label, request changes, or auto-close
- **Per-Repo Config** — `.github/ai-gate.yml` customization
- **Interactive Dashboard** — Live demo analyzer
- **ML-Ready** — Extensible detector architecture for future ML models

## How it works

When GitHub delivers a webhook event the app:

1. **Acknowledges immediately** (returns `200 OK` inside GitHub's 10 s delivery window) and schedules the analysis on a background task — so slow detectors or a cold container never cause a delivery to be marked failed.
2. **Posts a check run** on the PR's head commit as the very first action. Conclusion follows the configured thresholds:
   - `success` — AI score < `ai.warn` and quality score ≥ `quality.minimum`
   - `neutral` — AI score ≥ `ai.warn` but below `ai.fail`, and quality is acceptable
   - `failure` — AI score ≥ `ai.fail` **or** quality score < `quality.minimum`
3. **Applies labels, posts a comment, and optionally requests changes or closes** the contribution. Each of these is wrapped in its own logged try/except so a transient GitHub API failure on one call (e.g. a rate-limited label create) does not silence the rest.

### Webhook events handled

| Event | Actions that trigger analysis |
|-------|-------------------------------|
| `pull_request` | `opened`, `edited`, `reopened`, `synchronize`, `ready_for_review` |
| `issues` | `opened`, `edited`, `reopened` |

## Architecture

Built with **Clean Architecture** principles:

```
API Layer         →  FastAPI routes, middleware, error handling
Application Layer →  Orchestrator, webhook handler, action dispatcher
Domain Layer      →  Detectors, scorers, entities, patterns (pure logic)
Infrastructure    →  GitHub client, config loader, JWT auth
```

**Design Patterns**: Strategy (detectors/scorers), Registry (patterns), Chain of Responsibility (actions), Factory (config), Dependency Injection (container)

**SOLID**: Single Responsibility, Open/Closed (extensible detectors), Liskov Substitution, Interface Segregation, Dependency Inversion

## Tech Stack

Python 3.12+ | FastAPI | Pydantic v2 | httpx | PyJWT | pytest | Docker

## Quick Start

```bash
# Clone and install
git clone https://github.com/AbdullahBakir97/ai-quality-gate.git
cd ai-quality-gate
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your GitHub App credentials

# Run
python -m src.main

# Test
pytest
```

## Configuration

Add `.github/ai-gate.yml` to any repository:

```yaml
ai:
  warn: 50
  fail: 80
  action: comment

quality:
  minimum: 30
  action: comment

exempt:
  users: [dependabot]
  bots: true
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook` | POST | GitHub webhook receiver |
| `/api/v1/analyze` | POST | Analyze text (demo API) |
| `/health` | GET | Health check |
| `/metrics` | GET | App metrics |
| `/dashboard` | GET | Interactive demo |

## Deployment

```bash
# Docker
docker build -t ai-quality-gate .
docker run -p 8000:8000 --env-file .env ai-quality-gate

# Render
# Uses render.yaml — connect repo and deploy
```

## License

MIT
