FROM python:3.14-slim

# Prevent Python from writing .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# Install curl to fetch uv (fast Python package manager)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh -s -- --yes
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app

# Copy project metadata and lockfile first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies using the locked versions; no dev deps
RUN uv sync --frozen --no-editable --no-dev

# Copy application source
COPY app ./app

# Fly.io expects the app to listen on PORT. We'll use 8080 internally.
ENV PORT=8080
EXPOSE 8080

# Start Uvicorn without reload in production
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
