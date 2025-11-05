.PHONY: help build run migrate analyze info shell clean rebuild logs test

# Default target
help:
	@echo "🐳 C to C# Migration System - Docker Commands"
	@echo ""
	@echo "Available commands:"
	@echo "  make build      - Build Docker image"
	@echo "  make run        - Run container (show help)"
	@echo "  make migrate    - Run migration on examples/test_project"
	@echo "  make analyze    - Analyze dependencies"
	@echo "  make info       - Show system information"
	@echo "  make shell      - Open bash shell in container"
	@echo "  make clean      - Remove containers and volumes"
	@echo "  make rebuild    - Rebuild image from scratch"
	@echo "  make logs       - Show container logs"
	@echo "  make test       - Run tests in container"
	@echo ""
	@echo "Custom migration:"
	@echo "  make migrate INPUT=path/to/input OUTPUT=path/to/output"
	@echo ""

# Build Docker image
build:
	@echo "🔨 Building Docker image..."
	docker-compose build

# Run container with default command
run:
	@echo "🚀 Running container..."
	docker-compose run --rm migration-system

# Run migration on test project
migrate:
	@echo "🔄 Running migration..."
	docker-compose run --rm migration-system python3 main.py migrate \
		-i $(or $(INPUT),examples/test_project) \
		-o $(or $(OUTPUT),output/converted) \
		$(if $(VERBOSE),--verbose,) \
		$(if $(DEBUG),--debug,)

# Analyze dependencies
analyze:
	@echo "🔍 Analyzing dependencies..."
	docker-compose run --rm migration-system python3 main.py analyze \
		-i $(or $(INPUT),examples/test_project) \
		--visualize

# Show system info
info:
	@echo "ℹ️  System information..."
	docker-compose run --rm migration-system python3 main.py info

# Open bash shell in container
shell:
	@echo "🐚 Opening shell in container..."
	docker-compose run --rm migration-system bash

# Clean up
clean:
	@echo "🧹 Cleaning up..."
	docker-compose down -v
	@echo "✅ Cleaned up containers and volumes"

# Rebuild from scratch
rebuild:
	@echo "🔄 Rebuilding from scratch..."
	docker-compose build --no-cache

# Show logs
logs:
	@echo "📋 Showing logs..."
	docker-compose logs -f migration-system

# Run tests
test:
	@echo "🧪 Running tests..."
	docker-compose run --rm migration-system pytest tests/ -v

# Quick start example
quickstart:
	@echo "🚀 Quick start example..."
	@echo "1. Building image..."
	@make build
	@echo ""
	@echo "2. Running migration..."
	@make migrate
	@echo ""
	@echo "✅ Done! Check output/converted/ for results"

# Development workflow
dev:
	@echo "💻 Starting development workflow..."
	@make build
	@make shell

