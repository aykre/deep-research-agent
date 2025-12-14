FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --no-dev

# Install Playwright browsers
RUN uv run playwright install --with-deps chromium

# Copy application code
COPY server/ ./server/

# Expose port
EXPOSE 8000

# Run the server
CMD ["uv", "run", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
