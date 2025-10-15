# PPB PharmTech License Verification - Production Container
FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install curl for healthchecks
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Build stage - install dependencies
FROM base AS builder

RUN pip install --upgrade pip

# Copy only requirements first for better caching
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Final stage - minimal runtime
FROM base

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser

# Install wheels from builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl --fail --silent --show-error --max-time 5 http://localhost:5001/health || exit 1

# Run with gunicorn
CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.app:app"]
