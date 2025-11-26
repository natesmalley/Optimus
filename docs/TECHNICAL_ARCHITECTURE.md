# Optimus Technical Architecture

## System Overview

Optimus is designed as a modular, event-driven system with a microservices-inspired architecture that can start as a monolith and evolve into distributed services as needed.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Optimus Prime                           │
│                    (Future Voice Interface)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌─────────────────────────────┴────────────────────────────────────┐
│                      Web Dashboard (React)                        │
├────────────────────────────────────────────────────────────────────┤
│                    API Gateway (FastAPI)                          │
├────────────────────────────────────────────────────────────────────┤
│                      Core Services Layer                          │
├──────────────┬──────────────┬──────────────┬────────────────────┤
│   Scanner    │  Analyzer    │  Advisor     │   Orchestrator    │
│   Service    │  Service     │  Service     │   Service         │
├──────────────┴──────────────┴──────────────┴────────────────────┤
│                    Data Layer (PostgreSQL + Redis)               │
├────────────────────────────────────────────────────────────────────┤
│                 File System & Process Monitors                    │
└────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Scanner Service (`src/scanner/`)
**Purpose**: Discovers and monitors all projects

**Components**:
- `project_discovery.py` - Finds all projects in ~/projects
- `runtime_monitor.py` - Tracks running processes/containers
- `git_scanner.py` - Analyzes git repositories
- `dependency_scanner.py` - Maps project dependencies
- `stack_analyzer.py` - Identifies technologies used

**Key Features**:
- Filesystem watching with `watchdog`
- Process monitoring via `psutil`
- Git integration with `GitPython`
- Package analysis (package.json, requirements.txt, Cargo.toml, etc.)

### 2. Analyzer Service (`src/analyzer/`)
**Purpose**: Provides intelligence about projects

**Components**:
- `code_quality.py` - Measures code quality metrics
- `security_scanner.py` - Finds vulnerabilities
- `performance_analyzer.py` - Identifies bottlenecks
- `tech_debt_calculator.py` - Assesses technical debt
- `pattern_recognition.py` - Learns from error patterns

**Key Features**:
- Static code analysis with `ast`, `radon`
- Security scanning with `bandit`, `safety`
- Performance profiling hooks
- ML-based pattern matching with `scikit-learn`

### 3. Advisor Service (`src/advisor/`)
**Purpose**: Monetization and business intelligence

**Components**:
- `monetization_engine.py` - Suggests revenue models
- `market_analyzer.py` - Trends and opportunity analysis
- `roi_calculator.py` - Project investment analysis
- `recommendation_engine.py` - Actionable suggestions
- `troubleshooting_advisor.py` - Solution recommendations

**Key Features**:
- Business model templates
- Market data integration
- Cost tracking and projections
- ML-based recommendations

### 4. Orchestrator Service (`src/orchestrator/`)
**Purpose**: Manages project operations

**Components**:
- `project_launcher.py` - Start/stop projects
- `environment_manager.py` - Handle dev/staging/prod
- `resource_allocator.py` - Optimize resource usage
- `deployment_assistant.py` - Deploy to production
- `backup_coordinator.py` - Manage backups

**Key Features**:
- Process management with `subprocess`, `docker-py`
- Environment variable management
- Resource monitoring and limits
- Automated deployment scripts

### 5. API Gateway (`src/api/`)
**Purpose**: RESTful API for all functionality

**Endpoints Structure**:
```python
/api/v1/
├── /projects
│   ├── GET / - List all projects
│   ├── GET /{id} - Get project details
│   ├── POST /{id}/scan - Trigger project scan
│   └── POST /{id}/analyze - Run analysis
├── /runtime
│   ├── GET /status - Running projects status
│   ├── POST /start/{id} - Start project
│   └── POST /stop/{id} - Stop project
├── /analysis
│   ├── GET /{id}/quality - Code quality report
│   ├── GET /{id}/security - Security report
│   └── GET /{id}/performance - Performance report
├── /monetization
│   ├── GET /{id}/opportunities - Revenue opportunities
│   ├── GET /{id}/roi - ROI analysis
│   └── POST /{id}/recommend - Get recommendations
├── /troubleshooting
│   ├── POST /diagnose - Diagnose issue
│   └── POST /fix - Attempt automated fix
└── /orchestration
    ├── POST /deploy/{id} - Deploy project
    └── POST /backup/{id} - Backup project
```

### 6. Web Dashboard (`src/dashboard/`)
**Purpose**: Visual interface for monitoring

**Components**:
- Project grid view with status indicators
- Real-time monitoring dashboards
- Analytics and trend visualizations
- Monetization opportunity cards
- Troubleshooting console
- Settings and configuration

**Tech Stack**:
- React with TypeScript
- Real-time updates via WebSockets
- D3.js for visualizations
- Material-UI components

## Database Schema

### PostgreSQL Tables

```sql
-- Projects main table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    path TEXT NOT NULL UNIQUE,
    type VARCHAR(50),
    stack JSONB,
    status VARCHAR(20),
    health_score INTEGER,
    monetization_potential DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Project metrics
CREATE TABLE project_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    metric_type VARCHAR(50),
    value JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Runtime status
CREATE TABLE runtime_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    process_id INTEGER,
    port INTEGER,
    status VARCHAR(20),
    started_at TIMESTAMP,
    resources JSONB
);

-- Issues and solutions
CREATE TABLE issues (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    type VARCHAR(50),
    severity VARCHAR(20),
    description TEXT,
    stack_trace TEXT,
    solution JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Monetization opportunities
CREATE TABLE monetization_opportunities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES projects(id),
    type VARCHAR(50),
    potential_revenue DECIMAL(10,2),
    confidence_score DECIMAL(3,2),
    recommendations JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Learning patterns
CREATE TABLE patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pattern_type VARCHAR(50),
    pattern_data JSONB,
    success_rate DECIMAL(3,2),
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Redis Cache Structure

```
optimus:projects:{id}:summary     # Quick project summary
optimus:runtime:status             # Current runtime status
optimus:metrics:{id}:latest        # Latest metrics cache
optimus:recommendations:{id}       # Cached recommendations (TTL: 1 hour)
optimus:patterns:frequent          # Frequently used patterns
```

## Security Architecture

### Authentication & Authorization
- JWT-based authentication for API
- Role-based access control (RBAC)
- API key management for external integrations

### Data Security
- Encryption at rest for sensitive data
- TLS for all API communications
- Secrets management with environment variables
- No storage of credentials or API keys

### Project Isolation
- Sandboxed execution for automated fixes
- Read-only access by default
- Explicit permission for write operations
- Audit logging for all actions

## Deployment Strategy

### Phase 1: Local Development (Current)
```bash
# Docker Compose setup
docker-compose up -d postgres redis
python -m uvicorn src.api.main:app --reload
npm start # Dashboard
```

### Phase 2: Production Deployment
```yaml
# docker-compose.prod.yml
services:
  api:
    build: .
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    ports:
      - "8000:8000"
  
  scanner:
    build: .
    command: python -m src.scanner.main
    volumes:
      - ~/projects:/projects:ro
  
  analyzer:
    build: .
    command: python -m src.analyzer.main
  
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine
```

### Phase 3: Kubernetes (Future)
- Helm charts for deployment
- Horizontal pod autoscaling
- Service mesh for inter-service communication
- Persistent volume claims for data

## Technology Stack Summary

### Backend
- **Language**: Python 3.11+
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Task Queue**: Celery with Redis
- **Testing**: pytest, pytest-asyncio

### Frontend
- **Framework**: React 18 with TypeScript
- **State**: Redux Toolkit
- **UI**: Material-UI
- **Charts**: D3.js, Recharts
- **Testing**: Jest, React Testing Library

### Infrastructure
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Containers**: Docker
- **Orchestration**: Docker Compose → Kubernetes
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack (future)

### AI/ML
- **ML Framework**: scikit-learn
- **NLP**: spaCy, transformers
- **Vector DB**: Pinecone (future)
- **Voice (Future)**: OpenAI Whisper, Coqui TTS

## Development Phases

### Phase 1: Foundation (Months 1-2)
- [ ] Project scanner implementation
- [ ] Basic API endpoints
- [ ] Simple web dashboard
- [ ] PostgreSQL schema setup

### Phase 2: Intelligence (Months 3-4)
- [ ] Code analysis engine
- [ ] Pattern recognition system
- [ ] Troubleshooting knowledge base
- [ ] Basic monetization analysis

### Phase 3: Automation (Months 5-6)
- [ ] Project orchestration
- [ ] Automated fixes
- [ ] Deployment assistance
- [ ] Advanced recommendations

### Phase 4: Voice Preparation (Months 7-12)
- [ ] NLP integration
- [ ] Command parsing
- [ ] Response generation
- [ ] Context management

### Phase 5: Optimus Prime (Year 2+)
- [ ] Voice synthesis
- [ ] Wake word detection
- [ ] Personality implementation
- [ ] Full conversational AI

## Success Metrics

- **Performance**: <100ms API response time
- **Scalability**: Support 100+ projects
- **Accuracy**: >90% issue diagnosis accuracy
- **Uptime**: 99.9% availability
- **User Impact**: 50% reduction in troubleshooting time

## Next Steps

1. Set up development environment
2. Implement project scanner
3. Create basic API structure
4. Build minimal dashboard
5. Deploy first version locally
6. Iterate based on usage feedback