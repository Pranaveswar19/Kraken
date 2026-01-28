# Start from Python base image
FROM python:3.13.1

# Set working directory inside container
WORKDIR /app

# Install uv package manager
RUN pip install uv

# Copy project files and source code
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install dependencies (creates .venv/)
RUN uv sync --frozen --no-cache

# Copy application scripts
COPY scripts/ ./scripts/

# Set Python path
ENV PYTHONPATH=/app/src

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import sys; sys.exit(0)"

# Use uv run to activate virtual environment
CMD ["uv", "run", "python", "scripts/run_scheduler.py"]