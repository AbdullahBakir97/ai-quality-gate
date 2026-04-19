# AI Quality Gate - System Design Document

## 1. Overview

**AI Quality Gate** is a production-grade GitHub App that detects AI-generated issues and pull requests, scores contribution quality, and gives maintainers automated tools to manage low-quality contributions at scale.

### Problem Statement
Open-source repositories are flooded with AI-generated issues and PRs that waste maintainer time. No existing tool detects, scores, and acts on these contributions automatically.

### Solution
A GitHub App that hooks into repository events, analyzes every new issue/PR through an AI detection pipeline and quality scoring engine, then takes configurable actions (label, comment, request changes, or close).

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|------------|----------|
| FR-1 | Detect AI-generated text using heuristic patterns | P0 |
| FR-2 | Score issue quality (0-100) based on completeness | P0 |
| FR-3 | Score PR quality (0-100) based on description, tests, diff | P0 |
| FR-4 | Post analysis results as GitHub comments | P0 |
| FR-5 | Apply labels based on detection results | P0 |
| FR-6 | Create GitHub Check runs on PRs | P0 |
| FR-7 | Support per-repo configuration via `.github/ai-gate.yml` | P0 |
| FR-8 | Exempt specific users, bots, and labeled contributions | P1 |
| FR-9 | Request changes or auto-close based on thresholds | P1 |
| FR-10 | Interactive demo dashboard | P1 |
| FR-11 | ML-based AI detection (extensible) | P2 |
| FR-12 | Analytics and reporting | P2 |
| FR-13 | Webhook retry and idempotency | P2 |

### 2.2 Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Webhook response time | < 200ms (async processing) |
| Analysis latency | < 5s per contribution |
| Availability | 99.5% uptime |
| Scalability | Handle 1000+ webhook events/hour |
| Security | Webhook signature verification, JWT auth |
| Observability | Structured logging, health checks |
| Testability | > 80% code coverage |

### 2.3 Constraints

- Team: Solo developer (Python background)
- Timeline: MVP in current session
- Stack: Python 3.14, FastAPI, Pydantic v2
- Deployment: Render free tier initially
- Budget: $0 (open source, free hosting)

---

## 3. Architecture

### 3.1 Architectural Style: Clean Architecture (Hexagonal)

```
                    +------------------------------------------+
                    |              External World               |
                    |  GitHub API | Webhook Events | Dashboard  |
                    +------------------+-----+-----------------+
                                       |     |
                    +------------------v-----v-----------------+
                    |           Infrastructure Layer            |
                    |  FastAPI Routes | GitHub Client | Config  |
                    +------------------+-----+-----------------+
                                       |     |
                    +------------------v-----v-----------------+
                    |            Application Layer              |
                    |  Webhook Handler | Analysis Orchestrator  |
                    |  Action Dispatcher | Event Publisher       |
                    +------------------+-----+-----------------+
                                       |     |
                    +------------------v-----v-----------------+
                    |              Domain Layer                 |
                    |  AI Detector | Quality Scorer | Patterns  |
                    |  Entities | Value Objects | Interfaces    |
                    +------------------------------------------+
```

**Dependency Rule**: Inner layers never depend on outer layers. All dependencies point inward through interfaces (Dependency Inversion).

### 3.2 Layer Responsibilities

#### Domain Layer (src/domain/)
- Pure business logic, zero external dependencies
- Entities: `AnalysisResult`, `Signal`, `QualityCheck`, `QualityReport`
- Value Objects: `Score`, `Confidence`, `Grade`
- Interfaces: `IDetector`, `IScorer`, `IGitHubClient`, `IConfigLoader`
- Pattern definitions and detection algorithms

#### Application Layer (src/application/)
- Orchestrates domain objects to fulfill use cases
- `AnalysisOrchestrator` — coordinates detection + scoring
- `WebhookHandler` — routes events to appropriate handlers
- `ActionDispatcher` — decides and executes actions based on results + config

#### Infrastructure Layer (src/infrastructure/)
- Implements interfaces defined in domain layer
- `GitHubClient` — Octokit-equivalent using httpx
- `GitHubConfigLoader` — loads `.github/ai-gate.yml`
- `WebhookAuthenticator` — signature verification, JWT generation

#### API Layer (src/api/)
- FastAPI routes, middleware, error handlers
- Webhook endpoint
- Health/metrics endpoints
- Dashboard static file serving

### 3.3 Component Diagram

```
+------------------------------------------------------------------+
|                        FastAPI Application                         |
|                                                                    |
|  +------------------+  +-------------------+  +-----------------+ |
|  |   API Layer      |  |  Middleware        |  |  Dashboard      | |
|  |  /webhook        |  |  - Auth            |  |  /dashboard     | |
|  |  /health         |  |  - Logging         |  |  /api/analyze   | |
|  |  /api/analyze    |  |  - Error Handler   |  |  (static HTML)  | |
|  |  /metrics        |  |  - Rate Limiter    |  |                 | |
|  +--------+---------+  +--------+----------+  +-----------------+ |
|           |                      |                                 |
|  +--------v----------------------v-----------+                     |
|  |          Application Layer                 |                    |
|  |                                            |                    |
|  |  +------------------+  +----------------+ |                    |
|  |  | WebhookHandler   |  | ActionDispatch | |                    |
|  |  | - handle_issue() |  | - comment()    | |                    |
|  |  | - handle_pr()    |  | - label()      | |                    |
|  |  | - handle_edit()  |  | - close()      | |                    |
|  |  +--------+---------+  +-------+--------+ |                    |
|  |           |                     |          |                    |
|  |  +--------v---------------------v--------+ |                    |
|  |  |      AnalysisOrchestrator             | |                    |
|  |  |  - analyze(context) -> AnalysisResult | |                    |
|  |  +--------+-------------------+----------+ |                    |
|  +-----------|-------------------|------------+                    |
|              |                   |                                 |
|  +-----------v-----------+  +----v-------------------+             |
|  |    Domain Layer       |  |  Infrastructure Layer  |             |
|  |                       |  |                        |             |
|  |  +----------------+  |  |  +------------------+  |             |
|  |  | AIDetector     |  |  |  | GitHubClient     |  |             |
|  |  | - PatternDet.  |  |  |  | - post_comment() |  |             |
|  |  | - StructureDet.|  |  |  | - add_labels()   |  |             |
|  |  | - HallucinDet. |  |  |  | - create_check() |  |             |
|  |  | - CodeDet.     |  |  |  +------------------+  |             |
|  |  +----------------+  |  |                        |             |
|  |  +----------------+  |  |  +------------------+  |             |
|  |  | QualityScorer  |  |  |  | ConfigLoader     |  |             |
|  |  | - IssueScorer  |  |  |  | - load_yaml()    |  |             |
|  |  | - PRScorer     |  |  |  | - merge_defaults |  |             |
|  |  +----------------+  |  |  +------------------+  |             |
|  |  +----------------+  |  |                        |             |
|  |  | PatternRegistry|  |  |  +------------------+  |             |
|  |  | - vocabulary   |  |  |  | JWTAuthenticator |  |             |
|  |  | - phrasing     |  |  |  | - generate_jwt() |  |             |
|  |  | - structural   |  |  |  | - verify_sig()   |  |             |
|  |  +----------------+  |  |  +------------------+  |             |
|  +-----------------------+  +------------------------+             |
+------------------------------------------------------------------+
```

---

## 4. Data Flow

### 4.1 Webhook Event Flow

```
GitHub Event (issue.opened)
    |
    v
[FastAPI /webhook endpoint]
    |
    +-- Verify webhook signature (middleware)
    +-- Parse event type + payload
    +-- Return 200 immediately (async processing)
    |
    v
[WebhookHandler.handle_issue()]
    |
    +-- Load per-repo config (.github/ai-gate.yml)
    +-- Check exemptions (user, bot, labels)
    +-- Build ContributionContext
    |
    v
[AnalysisOrchestrator.analyze()]
    |
    +-- Run AIDetector pipeline
    |   +-- PatternDetector.detect()
    |   +-- StructureDetector.detect()
    |   +-- HallucinationDetector.detect()
    |   +-- (future: MLDetector.detect())
    |   +-- Aggregate signals -> AI score
    |
    +-- Run QualityScorer
    |   +-- IssueScorer.score() or PRScorer.score()
    |   +-- Run individual quality checks
    |   +-- Aggregate -> QualityReport
    |
    +-- Combine -> AnalysisResult
    |
    v
[ActionDispatcher.dispatch()]
    |
    +-- Determine action based on thresholds + config
    +-- GitHubClient.add_labels()
    +-- GitHubClient.post_comment()
    +-- GitHubClient.create_check_run() (for PRs)
    +-- (optional) GitHubClient.request_changes()
    +-- (optional) GitHubClient.close()
```

### 4.2 Demo API Flow

```
User pastes text on dashboard
    |
    v
[POST /api/analyze] (JSON: {text, type})
    |
    v
[AnalysisOrchestrator.analyze()] (no GitHub auth needed)
    |
    v
Return JSON {ai_score, quality_score, signals, checks}
```

---

## 5. Domain Model

### 5.1 Core Entities

```
Signal
  - type: SignalType (enum)
  - pattern: str
  - description: str
  - weight: float (0.0-1.0)
  - occurrences: int
  - contribution: float (calculated)

QualityCheck
  - name: str
  - score: int
  - max_score: int
  - detail: str
  - passed: bool (property)

QualityReport
  - score: int (0-100 normalized)
  - grade: Grade (A-F)
  - checks: list[QualityCheck]
  - passed: list[QualityCheck] (property)
  - failed: list[QualityCheck] (property)

AnalysisResult
  - ai_score: int (0-100)
  - ai_confidence: Confidence
  - ai_signals: list[Signal]
  - is_likely_ai: bool
  - quality_report: QualityReport
  - contribution_type: ContributionType
  - analyzed_at: datetime

ContributionContext
  - title: str
  - body: str
  - author: str
  - labels: list[str]
  - is_bot: bool
  - contribution_type: ContributionType
  - diff: str | None (for PRs)
  - number: int
  - repo_owner: str
  - repo_name: str
```

### 5.2 Enumerations

```python
class SignalType(str, Enum):
    AI_VOCABULARY = "ai-vocabulary"
    AI_PHRASING = "ai-phrasing"
    STRUCTURAL = "structural"
    CODE = "code"
    HALLUCINATION = "hallucination"
    META = "meta"

class Confidence(str, Enum):
    NONE = "none"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class Grade(str, Enum):
    A = "A"  # 80-100
    B = "B"  # 60-79
    C = "C"  # 40-59
    D = "D"  # 20-39
    F = "F"  # 0-19

class ActionType(str, Enum):
    COMMENT = "comment"
    LABEL = "label"
    REQUEST_CHANGES = "request-changes"
    CLOSE = "close"

class ContributionType(str, Enum):
    ISSUE = "issue"
    PULL_REQUEST = "pull_request"
```

---

## 6. Design Patterns

### 6.1 Strategy Pattern — Detectors

Multiple detection strategies implement the same `IDetector` interface. The `AIDetector` aggregates results from all strategies:

```
IDetector (interface)
  +-- PatternDetector    (vocabulary + phrasing regex)
  +-- StructureDetector  (paragraph uniformity, list patterns)
  +-- HallucinationDetector (fake APIs, version refs)
  +-- CodeDetector       (diff analysis)
  +-- MLDetector         (future: transformer-based)
```

### 6.2 Strategy Pattern — Scorers

```
IScorer (interface)
  +-- IssueScorer (title, body, repro steps, env info)
  +-- PRScorer    (description, linked issues, tests, diff)
```

### 6.3 Chain of Responsibility — Action Handlers

```
IActionHandler (interface)
  +-- LabelHandler     (always runs first)
  +-- CommentHandler   (posts analysis comment)
  +-- ReviewHandler    (requests changes on PRs)
  +-- CloseHandler     (auto-closes if configured)
```

### 6.4 Factory Pattern — Config Loading

```
ConfigLoaderFactory
  +-- creates GitHubConfigLoader (production)
  +-- creates FileConfigLoader   (testing)
  +-- creates DefaultConfigLoader (fallback)
```

### 6.5 Registry Pattern — Pattern Management

```
PatternRegistry (singleton)
  +-- register(pattern)
  +-- get_by_type(signal_type) -> list[Pattern]
  +-- get_all() -> list[Pattern]
```

### 6.6 Observer Pattern — Event Publishing

```
EventPublisher
  +-- subscribe(event_type, handler)
  +-- publish(event)

Events:
  - AnalysisCompleted
  - ActionTaken
  - WebhookReceived
  - ConfigLoaded
```

---

## 7. API Design

### 7.1 Webhook Endpoint

```
POST /webhook
Headers:
  X-GitHub-Event: issues | pull_request
  X-GitHub-Delivery: <uuid>
  X-Hub-Signature-256: sha256=<hmac>
Body: GitHub webhook payload (JSON)
Response: 200 {"received": true}
```

### 7.2 Analysis API (for dashboard)

```
POST /api/v1/analyze
Body: {
  "text": "string",
  "title": "string (optional)",
  "type": "issue | pull_request"
}
Response: {
  "ai_detection": {
    "score": 71,
    "confidence": "high",
    "is_likely_ai": true,
    "signals": [...]
  },
  "quality": {
    "score": 56,
    "grade": "C",
    "checks": [...]
  }
}
```

### 7.3 Health & Metrics

```
GET /health
Response: {"status": "ok", "uptime": 3600, "version": "1.0.0"}

GET /metrics
Response: {
  "events_received": 150,
  "analyses_completed": 142,
  "ai_detected": 23,
  "avg_analysis_ms": 450
}
```

---

## 8. Configuration

### 8.1 Environment Variables (Settings)

```
APP_ID=3359121                    # GitHub App ID
PRIVATE_KEY=-----BEGIN RSA...     # Private key (or PRIVATE_KEY_PATH)
WEBHOOK_SECRET=abc123             # Webhook signature secret
PORT=8000                         # Server port
ENV=production                    # Environment
LOG_LEVEL=INFO                    # Logging level
ALLOWED_ORIGINS=*                 # CORS origins
```

### 8.2 Per-Repo Config (.github/ai-gate.yml)

```yaml
enabled: true

ai:
  warn: 50
  fail: 80
  action: comment    # comment | label | request-changes | close

quality:
  minimum: 30
  action: comment

analyze:
  issues: true
  pull_requests: true

labels:
  ai_detected: "ai-generated"
  ai_warning: "ai-suspected"
  low_quality: "low-quality"
  high_quality: "high-quality"

exempt:
  users: []
  labels: ["bot"]
  bots: true
```

---

## 9. Project Structure

```
ai-quality-gate-py/
|
+-- src/
|   +-- __init__.py
|   |
|   +-- domain/                     # Pure business logic (no dependencies)
|   |   +-- __init__.py
|   |   +-- entities.py             # AnalysisResult, Signal, QualityCheck, etc.
|   |   +-- enums.py                # SignalType, Confidence, Grade, etc.
|   |   +-- interfaces.py           # IDetector, IScorer, IGitHubClient, etc.
|   |   +-- exceptions.py           # Custom exception hierarchy
|   |   +-- value_objects.py        # Score, Threshold immutable objects
|   |
|   +-- analyzers/                  # Detection & scoring implementations
|   |   +-- __init__.py
|   |   +-- detectors/
|   |   |   +-- __init__.py
|   |   |   +-- base.py             # BaseDetector with shared logic
|   |   |   +-- pattern_detector.py # Vocabulary + phrasing patterns
|   |   |   +-- structure_detector.py # Structural analysis
|   |   |   +-- hallucination_detector.py
|   |   |   +-- code_detector.py    # Diff/code analysis
|   |   +-- scorers/
|   |   |   +-- __init__.py
|   |   |   +-- base.py             # BaseScorer with shared checks
|   |   |   +-- issue_scorer.py     # Issue-specific quality checks
|   |   |   +-- pr_scorer.py        # PR-specific quality checks
|   |   +-- patterns/
|   |   |   +-- __init__.py
|   |   |   +-- registry.py         # PatternRegistry singleton
|   |   |   +-- vocabulary.py       # AI vocabulary patterns
|   |   |   +-- phrasing.py         # AI phrasing patterns
|   |   |   +-- structural.py       # Structural patterns
|   |   |   +-- code_patterns.py    # Code-specific patterns
|   |   |   +-- hallucination.py    # Hallucination patterns
|   |   +-- aggregator.py           # Combines detector results into AI score
|   |
|   +-- application/                # Use cases / orchestration
|   |   +-- __init__.py
|   |   +-- orchestrator.py         # AnalysisOrchestrator
|   |   +-- webhook_handler.py      # Routes webhook events
|   |   +-- action_dispatcher.py    # Decides and executes actions
|   |   +-- event_publisher.py      # Internal event system
|   |
|   +-- infrastructure/             # External integrations
|   |   +-- __init__.py
|   |   +-- github/
|   |   |   +-- __init__.py
|   |   |   +-- client.py           # GitHubClient (httpx-based)
|   |   |   +-- auth.py             # JWT generation, token management
|   |   |   +-- webhook.py          # Signature verification
|   |   |   +-- models.py           # GitHub API response models
|   |   +-- config/
|   |   |   +-- __init__.py
|   |   |   +-- loader.py           # GitHubConfigLoader
|   |   |   +-- defaults.py         # Default config factory
|   |   |   +-- schema.py           # Pydantic config models
|   |
|   +-- api/                        # FastAPI application
|   |   +-- __init__.py
|   |   +-- app.py                  # FastAPI app factory
|   |   +-- routes/
|   |   |   +-- __init__.py
|   |   |   +-- webhook.py          # POST /webhook
|   |   |   +-- analyze.py          # POST /api/v1/analyze
|   |   |   +-- health.py           # GET /health, /metrics
|   |   +-- middleware/
|   |   |   +-- __init__.py
|   |   |   +-- logging.py          # Request/response logging
|   |   |   +-- error_handler.py    # Global exception handler
|   |   |   +-- rate_limiter.py     # Rate limiting
|   |   +-- dependencies.py         # FastAPI dependency injection
|   |   +-- schemas.py              # Request/response Pydantic models
|   |
|   +-- config/                     # App configuration
|   |   +-- __init__.py
|   |   +-- settings.py             # Environment-based settings
|   |   +-- logging.py              # Logging configuration
|   |
|   +-- container.py                # Dependency injection container
|   +-- main.py                     # Entry point
|
+-- tests/
|   +-- __init__.py
|   +-- conftest.py                 # Shared fixtures
|   +-- unit/
|   |   +-- __init__.py
|   |   +-- test_pattern_detector.py
|   |   +-- test_structure_detector.py
|   |   +-- test_issue_scorer.py
|   |   +-- test_pr_scorer.py
|   |   +-- test_aggregator.py
|   |   +-- test_orchestrator.py
|   |   +-- test_config_loader.py
|   +-- integration/
|   |   +-- __init__.py
|   |   +-- test_webhook_endpoint.py
|   |   +-- test_analyze_endpoint.py
|
+-- dashboard/
|   +-- index.html                  # Landing page + live demo
|   +-- assets/
|       +-- styles.css
|       +-- app.js
|
+-- docs/
|   +-- ARCHITECTURE.md             # This document
|   +-- API.md                      # API documentation
|   +-- CONFIGURATION.md            # Config reference
|
+-- .github/
|   +-- workflows/
|       +-- ci.yml                  # Test + lint on push
|       +-- deploy.yml              # Deploy on main merge
|
+-- pyproject.toml                  # Project config, dependencies
+-- Dockerfile                      # Production container
+-- docker-compose.yml              # Local development
+-- render.yaml                     # Render deployment config
+-- .env.example                    # Environment template
+-- .gitignore
+-- LICENSE
+-- README.md
```

---

## 10. SOLID Principles Application

### Single Responsibility (SRP)
- Each detector handles ONE type of detection
- Each scorer handles ONE type of contribution
- `WebhookHandler` only routes events
- `ActionDispatcher` only executes actions
- `GitHubClient` only communicates with GitHub API

### Open/Closed (OCP)
- New detectors added by implementing `IDetector` — no existing code changes
- New scorers added by implementing `IScorer`
- New action handlers added by implementing `IActionHandler`
- Pattern registry allows runtime pattern registration

### Liskov Substitution (LSP)
- Any `IDetector` implementation can replace another
- `MLDetector` substitutes for `PatternDetector` without breaking contracts
- `FileConfigLoader` substitutes for `GitHubConfigLoader` in tests

### Interface Segregation (ISP)
- `IDetector` only has `detect()` — not mixed with scoring
- `IScorer` only has `score()` — not mixed with detection
- `IGitHubClient` split into focused method groups

### Dependency Inversion (DIP)
- Application layer depends on interfaces, not implementations
- `AnalysisOrchestrator` receives `IDetector[]` and `IScorer` via injection
- `ActionDispatcher` receives `IGitHubClient` via injection
- `container.py` wires everything together

---

## 11. Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Runtime | Python 3.14 | User's primary language, ML ecosystem |
| Web Framework | FastAPI | Async, fast, auto-docs, Pydantic native |
| HTTP Client | httpx | Async support, connection pooling |
| Validation | Pydantic v2 | Fast, type-safe, schema generation |
| Config | pydantic-settings | Env var loading with validation |
| YAML | PyYAML | Parse .github/ai-gate.yml |
| JWT | PyJWT + cryptography | GitHub App authentication |
| Testing | pytest + pytest-asyncio | Async test support |
| Linting | ruff | Fast, replaces flake8+isort+black |
| Type Checking | mypy | Static type analysis |
| Containerization | Docker | Consistent deployment |
| CI/CD | GitHub Actions | Native integration |
| Hosting | Render | Free tier, Docker support |

---

## 12. Deployment Architecture

```
+-------------------+        +-------------------+
|    GitHub.com      |        |    Render.com     |
|                    |        |                   |
|  Webhook Events -------->  |  FastAPI Server   |
|                    |  HTTPS |  (Docker)         |
|  API (REST) <------------- |                   |
|                    |        |  Port 8000        |
+-------------------+        +-------------------+
```

### Render Configuration
- **Service type**: Web Service
- **Runtime**: Docker
- **Build command**: `docker build -t ai-quality-gate .`
- **Start command**: handled by Dockerfile CMD
- **Health check**: GET /health
- **Environment**: Production env vars set in Render dashboard

### Scaling Strategy (Future)
- Phase 1: Single Render instance (current)
- Phase 2: Add Redis for webhook deduplication
- Phase 3: Background worker (Celery/RQ) for async analysis
- Phase 4: Multiple instances behind load balancer

---

## 13. Security

| Concern | Mitigation |
|---------|-----------|
| Webhook authenticity | HMAC-SHA256 signature verification |
| GitHub auth | JWT + installation access tokens (short-lived) |
| Secret management | Environment variables, never in code |
| Rate limiting | FastAPI middleware, per-IP limits |
| Input validation | Pydantic models for all inputs |
| Dependency security | GitHub Dependabot, pip audit |
| CORS | Restricted origins in production |

---

## 14. Observability

### Logging
- Structured JSON logging (structlog or python-json-logger)
- Request ID propagation through async context
- Log levels: DEBUG (dev), INFO (prod), ERROR (always)

### Health Checks
- `/health` — basic liveness check
- `/health/ready` — checks GitHub API connectivity

### Metrics (in-memory for MVP, Prometheus later)
- `events_received` — total webhook events
- `analyses_completed` — successful analyses
- `ai_detected_count` — issues flagged as AI
- `avg_analysis_duration_ms` — performance tracking
- `errors_count` — error rate

---

## 15. Trade-off Analysis

| Decision | Alternative | Trade-off |
|----------|------------|-----------|
| Heuristic detection first | ML model from day 1 | Faster to ship, less accurate, but extensible |
| FastAPI over Flask | Flask is simpler | FastAPI gives async, auto-docs, Pydantic native |
| httpx over requests | requests is more common | httpx has async support, needed for FastAPI |
| In-process analysis | Queue-based workers | Simpler deployment, but limits throughput |
| Per-repo YAML config | Database config | Zero infrastructure, but no UI config editor |
| Single container | Microservices | Simpler ops for solo dev, refactor later if needed |

---

## 16. Implementation Phases

### Phase 1: Core MVP (Current)
- [ ] Domain entities and interfaces
- [ ] Pattern-based AI detector (4 detector types)
- [ ] Issue and PR quality scorers
- [ ] GitHub client (comments, labels, checks)
- [ ] Webhook handler with signature verification
- [ ] FastAPI app with /webhook, /health, /api/v1/analyze
- [ ] Per-repo config loading
- [ ] Dashboard with live demo
- [ ] Docker + Render deployment
- [ ] Unit tests for detectors and scorers

### Phase 2: Hardening
- [ ] Webhook idempotency (prevent duplicate processing)
- [ ] Rate limiting middleware
- [ ] Structured logging
- [ ] Metrics endpoint
- [ ] Integration tests
- [ ] GitHub Marketplace listing

### Phase 3: ML Enhancement
- [ ] Train text classifier on labeled AI vs human text
- [ ] MLDetector implementation
- [ ] A/B testing heuristic vs ML
- [ ] Confidence calibration

### Phase 4: Scale
- [ ] Redis for caching and deduplication
- [ ] Background worker for analysis
- [ ] Analytics dashboard
- [ ] Multi-tenant SaaS features

---

## 17. Dependency Injection Container

```python
class Container:
    """Wires all dependencies together following DIP."""

    def __init__(self, settings: Settings):
        self.settings = settings

        # Infrastructure
        self.github_auth = GitHubAuthenticator(settings)
        self.github_client = GitHubClient(self.github_auth)
        self.config_loader = GitHubConfigLoader(self.github_client)

        # Domain - Detectors
        self.pattern_registry = PatternRegistry()
        self.pattern_registry.register_defaults()

        self.detectors: list[IDetector] = [
            PatternDetector(self.pattern_registry),
            StructureDetector(),
            HallucinationDetector(),
            CodeDetector(),
        ]

        # Domain - Scorers
        self.issue_scorer = IssueScorer()
        self.pr_scorer = PRScorer()

        # Application
        self.aggregator = SignalAggregator()
        self.orchestrator = AnalysisOrchestrator(
            detectors=self.detectors,
            issue_scorer=self.issue_scorer,
            pr_scorer=self.pr_scorer,
            aggregator=self.aggregator,
        )
        self.action_dispatcher = ActionDispatcher(self.github_client)
        self.webhook_handler = WebhookHandler(
            orchestrator=self.orchestrator,
            action_dispatcher=self.action_dispatcher,
            config_loader=self.config_loader,
        )
```

---

*This document is the source of truth for the AI Quality Gate architecture. All implementation decisions should trace back to the principles and patterns defined here.*
