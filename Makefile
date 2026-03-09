.PHONY: help setup install proxy generate clean

help:
	@echo "Solution Generation Pipeline"
	@echo ""
	@echo "Setup:"
	@echo "  make setup     - Install all dependencies"
	@echo ""
	@echo "Running:"
	@echo "  make proxy     - Start LiteLLM proxy (run in separate terminal)"
	@echo "  make generate  - Generate solution (requires REPO and ISSUE)"
	@echo ""
	@echo "Examples:"
	@echo "  make proxy"
	@echo "  make generate REPO=owner/repo ISSUE=123"
	@echo "  make generate REPO=owner/repo ISSUE=123 MODEL=gpt-4o"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean     - Remove generated data and caches"

# Install all dependencies
setup:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt
	@echo ""
	@echo "Installing OpenCode dependencies..."
	git submodule update --init --recursive
	cd external/opencode && bun install
	@echo ""
	@echo "Creating data directories..."
	mkdir -p data/solutions data/workspaces
	@echo ""
	@echo "Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and add your API keys"
	@echo "  2. Copy configs/opencode.json to ~/.config/opencode/opencode.json"
	@echo "  3. Run 'make proxy' in one terminal"
	@echo "  4. Run 'make generate REPO=... ISSUE=...' in another"

# Start LiteLLM proxy server
proxy:
	@echo "Starting LiteLLM proxy on http://localhost:4000"
	@echo "Press Ctrl+C to stop"
	@echo ""
	litellm --config configs/litellm_config.yaml --port 4000

# Generate solution for an issue
REPO ?=
ISSUE ?=
MODEL ?= gpt-4o-mini

generate:
ifndef REPO
	$(error REPO is required. Usage: make generate REPO=owner/repo ISSUE=123)
endif
ifndef ISSUE
	$(error ISSUE is required. Usage: make generate REPO=owner/repo ISSUE=123)
endif
	python scripts/generate.py --repo $(REPO) --issue $(ISSUE) --model $(MODEL)

# Clean up generated files
clean:
	rm -rf data/solutions/*.json
	rm -rf data/workspaces/*
	rm -rf __pycache__ src/**/__pycache__
	@echo "Cleaned up generated files"
