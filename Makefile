.PHONY: help setup install test run run-mock dev dev-mock dev-notmux dev-mock-notmux dev-mock-sleek console stop-dev clean

# Use bash for all commands
SHELL := /bin/bash

help:
	@echo "AWX TUI - Available Commands"
	@echo ""
	@echo "Setup & Installation:"
	@echo "  make setup        - Create venv, install package with dev dependencies, copy example config.yaml"
	@echo "  make install      - Install package in development mode (if venv exists)"
	@echo ""
	@echo "Running:"
	@echo "  make run          - Run awx-tui with environment variables (connects to local AWX)"
	@echo "  make run-mock     - Run awx-tui in mock mode (no AWX required)"
	@echo ""
	@echo "Development (with hot reload):"
	@echo "  make dev          - Run in tmux with TUI + console (real AWX, auto-reload)"
	@echo "  make dev-mock     - Run in tmux with TUI + console (mock mode, auto-reload)"
	@echo "  make dev-notmux   - Run with hot reload, no tmux (real AWX)"
	@echo "  make dev-mock-notmux - Run with hot reload, no tmux (mock mode)"
	@echo "  make dev-mock-sleek - Run with hot reload, no tmux (mock + sleek dashboard)"
	@echo "  make console      - Run Textual console in separate terminal"
	@echo "  make dev-mock-debug - Run mock mode with debug logging to file (no hot reload)"
	@echo "  make stop-dev     - Stop the dev tmux session"
	@echo ""
	@echo "Testing:"
	@echo "  make test         - Run all tests"
	@echo "  make test-basic   - Run basic smoke tests"
	@echo "  make coverage     - Run tests with coverage report"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean        - Remove venv and build artifacts"
	@echo "  make clean-config - Remove config.yaml"

# Real file targets (not phony)
# These are named after the files they produce

# Create virtual environment
.venv:
	@echo "Creating virtual environment..."
	python3 -m venv .venv

# Install package and dependencies (produces awx-tui executable)
.venv/bin/awx-tui: .venv requirements.txt requirements-dev.txt
	@echo "Installing package in development mode..."
	.venv/bin/pip install -e .
	@echo "Installing development dependencies..."
	.venv/bin/pip install -r requirements-dev.txt
	@echo "✅ Installation complete!"

# Install pytest (for testing)
.venv/bin/pytest: .venv requirements-dev.txt
	@echo "Installing development dependencies..."
	.venv/bin/pip install -r requirements-dev.txt

# Create config.yaml from template
config.yaml: config.yaml.development
	@echo "Creating config.yaml from config.yaml.development..."
	cp config.yaml.development config.yaml && chmod 600 config.yaml
	@echo "✅ Config created! Please update with your AWX credentials"

# Phony targets (aliases and actions)

setup: .venv/bin/awx-tui config.yaml
	@echo "✅ Setup complete! Please configure the proper password or token in config.yaml and then use 'make run' to start awx-tui"

install: .venv/bin/awx-tui

run: .venv/bin/awx-tui config.yaml
	@echo "Starting AWX TUI (connecting to local AWX)..."
	@source awx-env.sh && .venv/bin/awx-tui

run-mock: .venv/bin/awx-tui
	@echo "Starting AWX TUI in mock mode..."
	@.venv/bin/awx-tui --mock

dev: .venv/bin/awx-tui config.yaml
	@echo "Starting AWX TUI in dev mode with tmux (real AWX + hot reload)..."
	@command -v tmux >/dev/null 2>&1 || { echo "❌ Error: tmux is not installed and is required. Please install tmux... or execute 'make run' instead"; exit 1; }
	@echo "🧹 Cleaning up stale tmux sockets..."
	@rm -rf /private/tmp/tmux-$$(id -u)/awx-tui-dev 2>/dev/null || true
	@if tmux has-session -t awx-tui-dev 2>/dev/null; then \
		echo "📋 Attaching to existing awx-tui-dev session..."; \
		tmux attach-session -t awx-tui-dev; \
	else \
		echo "🚀 Creating new awx-tui-dev tmux session..."; \
		tmux new-session -s awx-tui-dev -d bash; \
		tmux send-keys -t awx-tui-dev:0.0 'cd $(CURDIR) && $(CURDIR)/.venv/bin/textual console' C-m; \
		tmux split-window -v -b -p 92 -t awx-tui-dev; \
		tmux send-keys -t awx-tui-dev:0.0 'cd $(CURDIR) && source $(CURDIR)/awx-env.sh && export AWX_TUI_DEV=true && $(CURDIR)/.venv/bin/watchmedo auto-restart --directory=awx_tui --pattern="*.py" --recursive -- $(CURDIR)/.venv/bin/textual run --dev awx_tui.app:AWXTUIApp' C-m; \
		tmux select-pane -t awx-tui-dev:0.0; \
		tmux attach-session -t awx-tui-dev; \
	fi

dev-mock: .venv/bin/awx-tui
	@echo "Starting AWX TUI in dev mode with tmux (mock mode + hot reload)..."
	@command -v tmux >/dev/null 2>&1 || { echo "❌ Error: tmux is not installed and is required. Please install tmux... or execute 'make run-mock' instead"; exit 1; }
	@echo "🧹 Cleaning up stale tmux sockets..."
	@rm -rf /private/tmp/tmux-$$(id -u)/awx-tui-dev 2>/dev/null || true
	@if tmux has-session -t awx-tui-dev 2>/dev/null; then \
		echo "📋 Attaching to existing awx-tui-dev session..."; \
		tmux attach-session -t awx-tui-dev; \
	else \
		echo "🚀 Creating new awx-tui-dev tmux session..."; \
		tmux new-session -s awx-tui-dev -d bash; \
		tmux send-keys -t awx-tui-dev:0.0 'cd $(CURDIR) && $(CURDIR)/.venv/bin/textual console' C-m; \
		tmux split-window -v -b -p 92 -t awx-tui-dev; \
		tmux send-keys -t awx-tui-dev:0.0 'cd $(CURDIR) && export AWX_TUI_DEV=true && $(CURDIR)/.venv/bin/watchmedo auto-restart --directory=awx_tui --pattern="*.py" --recursive -- $(CURDIR)/.venv/bin/textual run --dev awx_tui.app:AWXTUIApp -- --mock' C-m; \
		tmux select-pane -t awx-tui-dev:0.0; \
		tmux attach-session -t awx-tui-dev; \
	fi

dev-mock-debug: .venv/bin/awx-tui
	@echo "Starting AWX TUI in dev mode with debug logging (mock mode, no hot reload)..."
	@echo "📝 Logs will be written to ~/.cache/awx-tui/awx-tui.log"
	@.venv/bin/awx-tui --mock --debug

dev-notmux: .venv/bin/awx-tui config.yaml
	@$(CURDIR)/run-dev.sh

dev-mock-notmux: .venv/bin/awx-tui
	@echo "Starting AWX TUI with hot reload in mock mode (no tmux)..."
	@echo "💡 Tip: Run 'make console' in another terminal for Textual console"
	@export AWX_TUI_DEV=true && \
		$(CURDIR)/.venv/bin/watchmedo auto-restart \
		--directory=awx_tui \
		--pattern="*.py" \
		--recursive \
		-- $(CURDIR)/.venv/bin/textual run --dev awx_tui.app:AWXTUIApp -- --mock

dev-mock-sleek: .venv/bin/awx-tui
	@echo "Starting AWX TUI with hot reload in mock mode + sleek dashboard (no tmux)..."
	@echo "💡 Tip: Run 'make console' in another terminal for Textual console"
	@export AWX_TUI_DEV=true && \
		$(CURDIR)/.venv/bin/watchmedo auto-restart \
		--directory=awx_tui \
		--pattern="*.py" \
		--recursive \
		-- $(CURDIR)/.venv/bin/textual run --dev awx_tui.app:AWXTUIApp -- --mock --dashboard sleek

console: .venv/bin/awx-tui
	@echo "Starting Textual console (connect from dev app)..."
	@$(CURDIR)/.venv/bin/textual console

stop-dev:
	@echo "Stopping AWX TUI dev session..."
	@if tmux has-session -t awx-tui-dev 2>/dev/null; then \
		tmux kill-session -t awx-tui-dev; \
		echo "✅ Dev session stopped"; \
	else \
		echo "ℹ️  No dev session running"; \
	fi
	@rm -f /tmp/awx-tui-hot-reload-state.json
	@echo "🧹 Cleared hot reload state"

test:
	@echo "Running all tests..."
	@.venv/bin/pytest

test-basic:
	@echo "Running basic smoke tests..."
	@.venv/bin/pytest tests/test_basic.py -v

coverage:
	@echo "Running tests with coverage..."
	@.venv/bin/pytest --cov=awx_tui --cov-report=html --cov-report=term
	@echo ""
	@echo "📊 Coverage report generated in htmlcov/index.html"

# Install formatters and linters
.venv/bin/ruff: .venv requirements-lint.txt
	@echo "Installing linting dependencies..."
	.venv/bin/pip install -r requirements-lint.txt

lint: .venv/bin/ruff
	@echo "Checking Linting and Formatting..."
	@.venv/bin/ruff check awx_tui/ tests/
	@.venv/bin/black --check awx_tui tests/

lint-fix: .venv/bin/ruff
	@echo "Checking and Fixing Linting and Formatting..."
	@.venv/bin/ruff check awx_tui/ tests/ --fix
	@.venv/bin/black awx_tui tests/

clean:
	@echo "Cleaning up..."
	rm -rf .venv
	rm -rf build
	rm -rf dist
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete!"
