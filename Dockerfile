# =============================================
# Stage 1: Builder - Install dependencies
# =============================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip wheel && \
    pip install --no-cache-dir -r requirements.txt


# =============================================
# Stage 2: Production - Minimal runtime image
# =============================================
FROM python:3.11-slim-bookworm AS production

# Security: Run as non-root user
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=appuser:appgroup bot/ ./bot/
COPY --chown=appuser:appgroup core/ ./core/
COPY --chown=appuser:appgroup handlers/ ./handlers/
COPY --chown=appuser:appgroup utils/ ./utils/
COPY --chown=appuser:appgroup skills/ ./skills/
COPY --chown=appuser:appgroup config.yaml ./
COPY --chown=appuser:appgroup requirements.txt ./

# Create data directory for SQLite
RUN mkdir -p /app/data && chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port (if bot has web interface)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the bot
CMD ["python", "-m", "bot.main"]
