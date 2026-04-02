# Sandbox environment for mini-swe-agent execution

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
RUN git config --global --add safe.directory '*'
WORKDIR /workspace

# Default command (mini-swe-agent will override this)
CMD ["bash"]
