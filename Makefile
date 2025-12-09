# Makefile for Optimus Development and Deployment

.PHONY: help install build test clean deploy-dev deploy-prod backup restore logs start stop restart

# Default environment
ENV ?= dev
DOCKER_REGISTRY ?= ghcr.io/optimus
VERSION ?= latest

# Colors for output
BLUE = \033[0;34m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

# Help target
help: ## Show this help message
	@echo "$(BLUE)Optimus Development Makefile$(NC)"
	@echo "$(BLUE)==============================$(NC)"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "Environment variables:"
	@echo "  $(YELLOW)ENV$(NC)             Environment (dev, staging, prod) [default: dev]"
	@echo "  $(YELLOW)DOCKER_REGISTRY$(NC) Docker registry [default: ghcr.io/optimus]"
	@echo "  $(YELLOW)VERSION$(NC)         Version tag [default: latest]"

# Installation and Setup
install: ## Install all dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	@if command -v python3 >/dev/null 2>&1; then \
		python3 -m venv venv; \
		. venv/bin/activate && pip install -r requirements.txt; \
		echo "$(GREEN)✓ Python dependencies installed$(NC)"; \
	else \
		echo "$(RED)✗ Python3 not found$(NC)"; exit 1; \
	fi
	@if command -v npm >/dev/null 2>&1; then \
		cd frontend && npm install; \
		echo "$(GREEN)✓ Frontend dependencies installed$(NC)"; \
	else \
		echo "$(RED)✗ NPM not found$(NC)"; exit 1; \
	fi

setup: ## Setup development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)✓ Environment file created$(NC)"; \
	fi
	@docker network create optimus-network 2>/dev/null || true
	@echo "$(GREEN)✓ Docker network created$(NC)"
	@make install

# Build targets
build: ## Build all Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	@docker build -t $(DOCKER_REGISTRY)/backend:$(VERSION) .
	@docker build -t $(DOCKER_REGISTRY)/frontend:$(VERSION) -f frontend/Dockerfile .
	@echo "$(GREEN)✓ Images built successfully$(NC)"

build-backend: ## Build backend Docker image
	@echo "$(BLUE)Building backend image...$(NC)"
	@docker build -t $(DOCKER_REGISTRY)/backend:$(VERSION) .
	@echo "$(GREEN)✓ Backend image built$(NC)"

build-frontend: ## Build frontend Docker image
	@echo "$(BLUE)Building frontend image...$(NC)"
	@docker build -t $(DOCKER_REGISTRY)/frontend:$(VERSION) -f frontend/Dockerfile .
	@echo "$(GREEN)✓ Frontend image built$(NC)"

push: build ## Build and push images to registry
	@echo "$(BLUE)Pushing images to registry...$(NC)"
	@docker push $(DOCKER_REGISTRY)/backend:$(VERSION)
	@docker push $(DOCKER_REGISTRY)/frontend:$(VERSION)
	@echo "$(GREEN)✓ Images pushed successfully$(NC)"

# Development targets
dev: ## Start development environment
	@echo "$(BLUE)Starting development environment...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "$(GREEN)✓ Development environment started$(NC)"
	@echo "Frontend: http://localhost:3000"
	@echo "Backend: http://localhost:8000"
	@echo "Database Admin: http://localhost:8080"
	@echo "Redis Admin: http://localhost:8081"

dev-build: ## Build and start development environment
	@echo "$(BLUE)Building and starting development environment...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
	@echo "$(GREEN)✓ Development environment started$(NC)"

dev-logs: ## Show development logs
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

dev-stop: ## Stop development environment
	@echo "$(BLUE)Stopping development environment...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
	@echo "$(GREEN)✓ Development environment stopped$(NC)"

dev-clean: ## Clean development environment
	@echo "$(BLUE)Cleaning development environment...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml down -v --remove-orphans
	@docker system prune -f
	@echo "$(GREEN)✓ Development environment cleaned$(NC)"

# Testing targets
test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	@. venv/bin/activate && pytest tests/ -v --tb=short
	@cd frontend && npm test
	@echo "$(GREEN)✓ All tests passed$(NC)"

test-backend: ## Run backend tests
	@echo "$(BLUE)Running backend tests...$(NC)"
	@. venv/bin/activate && pytest tests/ -v --cov=src --cov-report=html
	@echo "$(GREEN)✓ Backend tests completed$(NC)"

test-frontend: ## Run frontend tests
	@echo "$(BLUE)Running frontend tests...$(NC)"
	@cd frontend && npm test -- --coverage --watchAll=false
	@echo "$(GREEN)✓ Frontend tests completed$(NC)"

test-integration: ## Run integration tests
	@echo "$(BLUE)Running integration tests...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@sleep 30
	@. venv/bin/activate && pytest tests/integration/ -v
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
	@echo "$(GREEN)✓ Integration tests completed$(NC)"

test-e2e: ## Run end-to-end tests
	@echo "$(BLUE)Running end-to-end tests...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@sleep 60
	@cd frontend && npm run test:e2e
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
	@echo "$(GREEN)✓ End-to-end tests completed$(NC)"

# Code Quality
lint: ## Run code linting
	@echo "$(BLUE)Running linting...$(NC)"
	@. venv/bin/activate && black --check src/ tests/
	@. venv/bin/activate && ruff check src/ tests/
	@. venv/bin/activate && mypy src/
	@cd frontend && npm run lint
	@echo "$(GREEN)✓ Linting completed$(NC)"

format: ## Format code
	@echo "$(BLUE)Formatting code...$(NC)"
	@. venv/bin/activate && black src/ tests/
	@. venv/bin/activate && ruff check --fix src/ tests/
	@cd frontend && npm run format
	@echo "$(GREEN)✓ Code formatted$(NC)"

security-scan: ## Run security scans
	@echo "$(BLUE)Running security scans...$(NC)"
	@. venv/bin/activate && bandit -r src/
	@cd frontend && npm audit
	@docker run --rm -v $(PWD):/src aquasec/trivy fs --security-checks vuln /src
	@echo "$(GREEN)✓ Security scan completed$(NC)"

# Production deployment
deploy-prod: ## Deploy to production
	@echo "$(BLUE)Deploying to production...$(NC)"
	@if [ "$(ENV)" != "prod" ]; then \
		echo "$(RED)✗ ENV must be set to 'prod' for production deployment$(NC)"; \
		exit 1; \
	fi
	@docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
	@echo "$(GREEN)✓ Production deployment completed$(NC)"

deploy-k8s: ## Deploy to Kubernetes
	@echo "$(BLUE)Deploying to Kubernetes...$(NC)"
	@kubectl apply -k k8s/overlays/$(ENV)/
	@kubectl rollout status deployment/optimus-backend -n optimus-$(ENV)
	@kubectl rollout status deployment/optimus-frontend -n optimus-$(ENV)
	@echo "$(GREEN)✓ Kubernetes deployment completed$(NC)"

# Infrastructure
infra-plan: ## Plan Terraform infrastructure
	@echo "$(BLUE)Planning Terraform infrastructure...$(NC)"
	@cd infrastructure/terraform && terraform plan -var="environment=$(ENV)"

infra-apply: ## Apply Terraform infrastructure
	@echo "$(BLUE)Applying Terraform infrastructure...$(NC)"
	@cd infrastructure/terraform && terraform apply -var="environment=$(ENV)"
	@echo "$(GREEN)✓ Infrastructure deployed$(NC)"

infra-destroy: ## Destroy Terraform infrastructure
	@echo "$(YELLOW)⚠️  This will destroy all infrastructure for $(ENV)$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd infrastructure/terraform && terraform destroy -var="environment=$(ENV)"; \
	fi

# Database operations
db-migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	@docker-compose exec optimus-backend alembic upgrade head
	@echo "$(GREEN)✓ Database migrations completed$(NC)"

db-seed: ## Seed database with test data
	@echo "$(BLUE)Seeding database...$(NC)"
	@docker-compose exec optimus-backend python scripts/seed_database.py
	@echo "$(GREEN)✓ Database seeded$(NC)"

db-reset: ## Reset database
	@echo "$(BLUE)Resetting database...$(NC)"
	@docker-compose exec optimus-backend alembic downgrade base
	@docker-compose exec optimus-backend alembic upgrade head
	@echo "$(GREEN)✓ Database reset$(NC)"

# Backup and restore
backup: ## Backup application data
	@echo "$(BLUE)Creating backup...$(NC)"
	@./scripts/backup.sh $(ENV)
	@echo "$(GREEN)✓ Backup completed$(NC)"

restore: ## Restore application data
	@echo "$(BLUE)Restoring from backup...$(NC)"
	@./scripts/restore.sh $(ENV) $(BACKUP_FILE)
	@echo "$(GREEN)✓ Restore completed$(NC)"

# Monitoring and logs
logs: ## Show application logs
	@docker-compose logs -f --tail=100

logs-backend: ## Show backend logs
	@docker-compose logs -f --tail=100 optimus-backend

logs-frontend: ## Show frontend logs
	@docker-compose logs -f --tail=100 optimus-frontend

logs-db: ## Show database logs
	@docker-compose logs -f --tail=100 postgres

monitor: ## Open monitoring dashboard
	@echo "Opening monitoring dashboard..."
	@open http://localhost:3000  # Grafana

# Utility targets
clean: ## Clean up Docker resources
	@echo "$(BLUE)Cleaning up Docker resources...$(NC)"
	@docker-compose down -v --remove-orphans
	@docker system prune -f
	@docker volume prune -f
	@echo "$(GREEN)✓ Cleanup completed$(NC)"

reset: clean setup ## Reset entire development environment
	@echo "$(GREEN)✓ Environment reset completed$(NC)"

status: ## Show service status
	@echo "$(BLUE)Service Status:$(NC)"
	@docker-compose ps

health: ## Check service health
	@echo "$(BLUE)Health Check:$(NC)"
	@curl -f http://localhost:8000/health 2>/dev/null && echo "$(GREEN)✓ Backend healthy$(NC)" || echo "$(RED)✗ Backend unhealthy$(NC)"
	@curl -f http://localhost:3000/health 2>/dev/null && echo "$(GREEN)✓ Frontend healthy$(NC)" || echo "$(RED)✗ Frontend unhealthy$(NC)"

# Quick start
start: dev ## Alias for dev (start development environment)
stop: dev-stop ## Stop development environment
restart: dev-stop dev ## Restart development environment

# Default target
.DEFAULT_GOAL := help