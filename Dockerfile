# PayRoute AI — Intelligent Customer Payment Shield & Routing Platform
# Production Multi-Process Docker Image

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app:/app/payroute-ai:${PYTHONPATH}" \
    PAYROUTE_API_URL="http://localhost:8000" \
    PORT=8501

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt* payroute-ai/requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f "requirements.txt" ]; then pip install --no-cache-dir -r requirements.txt; \
    elif [ -f "payroute-ai/requirements.txt" ]; then pip install --no-cache-dir -r payroute-ai/requirements.txt; fi

# Copy application source code
COPY . .

# Ensure start script has Linux line endings and execute permissions
RUN sed -i 's/\r$//' start.sh 2>/dev/null || true
RUN chmod +x start.sh 2>/dev/null || true
RUN if [ -f "payroute-ai/start.sh" ]; then sed -i 's/\r$//' payroute-ai/start.sh 2>/dev/null || true && chmod +x payroute-ai/start.sh 2>/dev/null || true; fi

# Expose ports: 8000 (FastAPI Backend), 8501 (Streamlit Frontend)
EXPOSE 8000 8501 10000

# Healthcheck for FastAPI backend
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command: launch both backend and frontend via start.sh
CMD ["./start.sh"]
