# Multi-stage build for minimal Lambda image
FROM python:3.13-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy dependencies
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies to a target directory
RUN pip install --target /build/deps --no-cache-dir .

# Install Lambda Runtime Interface Client
RUN pip install --target /build/deps --no-cache-dir awslambdaric

# ============================================================
# Final stage - Lambda runtime
# ============================================================

FROM python:3.13-slim

# Set Lambda task root
ENV LAMBDA_TASK_ROOT=/var/task

# Set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy installed packages from builder
COPY --from=builder /build/deps ${LAMBDA_TASK_ROOT}

# Copy application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set Python path
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

# Set the entrypoint to the Lambda Runtime Interface Client
ENTRYPOINT ["python", "-m", "awslambdaric"]

# Set the CMD to your handler
CMD ["src.app.lambda_handler"]
