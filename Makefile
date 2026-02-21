.PHONY: help setup install-opencode install-deps clean

# Load .env if it exists
ifneq (,$(wildcard .env))
    include .env
    export
endif

help:
	@echo "Usage:"
	@echo "  make setup"
	@echo "  make clean"

# One command setup
setup: install-opencode install-deps
	@echo ""
	@echo "Setup complete. Next steps:"
	@echo "  1. cp .env.example .env"
	@echo "  2. Fill in your API keys in .env"
	@echo "  3. make proxy"
	@echo "  4. make run PROMPT='your prompt'"

install-opencode:
	git submodule update --init --recursive
	cd external/opencode && bun install

install-deps:
	pip install -r requirements.txt

clean:
	cd external/opencode && rm -rf node_modules
