.PHONY: help setup patch-mini-swe generate clean clean-all

help:
	@echo "Solution Generation Pipeline"
	@echo ""
	@echo "Setup:"
	@echo "  make setup     - Create venv and install all dependencies"
	@echo ""
	@echo "Running:"
	@echo "  make generate  - Generate solutions (requires DATASET)"
	@echo ""
	@echo "Examples:"
	@echo "  make generate DATASET=org/routing-issues"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean     - Remove generated data and caches"
	@echo "  make clean-all - Also remove virtual environment"

setup: patch-mini-swe
	@echo "Creating virtual environment and installing dependencies..."
	uv sync
	@echo ""
	@echo "Creating data directories..."
	mkdir -p data/solutions data/workspaces
	@echo ""
	@echo "Setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Copy .env.example to .env and add your API keys"
	@echo "  2. Run 'make generate DATASET=org/routing-issues'"

patch-mini-swe:
	@echo "Applying mini-swe-agent patches..."
	@if git -C external/mini-swe-agent apply --check $(CURDIR)/patches/track-exposed-files.patch 2>/dev/null; then \
		git -C external/mini-swe-agent apply $(CURDIR)/patches/track-exposed-files.patch; \
		echo "  Applied: track-exposed-files.patch"; \
	else \
		echo "  Already applied (or conflict): track-exposed-files.patch"; \
	fi

DATASET ?=
MODEL ?= openai/gpt-4o-mini
LIMIT ?=

generate:
ifndef DATASET
	$(error DATASET is required. Usage: make generate DATASET=org/routing-issues)
endif
ifdef LIMIT
	uv run generate --dataset $(DATASET) --model $(MODEL) --limit $(LIMIT)
else
	uv run generate --dataset $(DATASET) --model $(MODEL)
endif

clean:
	rm -rf data/solutions/*.json
	rm -rf data/workspaces/*
	rm -rf __pycache__ src/**/__pycache__
	@echo "Cleaned up generated files"

clean-all: clean
	rm -rf .venv
	@echo "Removed virtual environment"
