# Build stage
FROM --platform=$TARGETPLATFORM python:3.14-slim AS builder

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH
ARG VERSION

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better layer caching
COPY pyproject.toml setup.py README.md ./
COPY TonieToolbox/ ./TonieToolbox/

# Install Python dependencies with all requirements
RUN pip install --no-cache-dir --user .

# Runtime stage
FROM --platform=$TARGETPLATFORM python:3.14-slim

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS
ARG TARGETARCH
ARG VERSION

LABEL org.opencontainers.image.title="TonieToolbox" \
      org.opencontainers.image.description="Convert audio files to Tonie box compatible format" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.authors="Quentendo64" \
      org.opencontainers.image.url="https://github.com/Quentendo64/TonieToolbox" \
      org.opencontainers.image.source="https://github.com/Quentendo64/TonieToolbox" \
      org.opencontainers.image.licenses="GPL-3.0-or-later" \
      org.opencontainers.image.documentation="https://github.com/Quentendo64/TonieToolbox/blob/main/README.md" \
      maintainer="Quentendo64"

WORKDIR /tonietoolbox

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && echo "Built for platform: ${TARGETPLATFORM}"

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY TonieToolbox/ ./TonieToolbox/
COPY tonietoolbox.py ./

# Update PATH to include user-installed packages
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create output directories with appropriate permissions
RUN mkdir -p /tonietoolbox/output /tonietoolbox/temp \
    && chmod -R 777 /tonietoolbox/output /tonietoolbox/temp \
    && echo "Built TonieToolbox version: ${VERSION:-unknown}" \
    && echo "Built for platform: ${TARGETPLATFORM:-unknown}"

# Declare volumes for input/output
VOLUME ["/tonietoolbox/input", "/tonietoolbox/output", "/tonietoolbox/temp"]

ENTRYPOINT ["python", "-m", "TonieToolbox"]
CMD ["--help"]