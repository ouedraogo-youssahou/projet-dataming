# ============================================
# Smart eCommerce Intelligence - Dockerfile
# ============================================

# ============================================
# Stage 1: Base Image
# ============================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    wget \
    vim \
    htop \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage 2: Development Image
# ============================================
FROM base as development

# Install additional development tools
RUN pip install --no-cache-dir \
    ipython \
    jupyter \
    jupyterlab \
    debugpy

# Copy source code
COPY . .

# Expose ports
EXPOSE 8501 8888 8000

# Set environment for development
ENV PYTHON_ENV=development

# Health check for development services
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501')" || exit 1

# Default command
CMD ["python", "-m", "streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ============================================
# Stage 3: Production Image
# ============================================
FROM base as production

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Copy only necessary files
COPY --chown=appuser:appuser . .

# Pre-compile Python files
RUN python -m compileall /app

# Expose ports
EXPOSE 8501

# Set environment for production
ENV PYTHON_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501')" || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8501", "--workers", "4", "--timeout", "120", "streamlit.web.cli:main", "run", "src/dashboard/app.py"]

# ============================================
# Stage 4: Scraping Service (Lightweight)
# ============================================
FROM python:3.11-slim as scraper

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for Selenium/Playwright + dumb-init for signal handling
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    dumb-init \
    && rm -rf /var/lib/apt/lists/*

    # Install Chrome/Chromium for Selenium
    RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-archive-keyring.gpg && \
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
        apt-get update && apt-get install -y google-chrome-stable && \
        rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy scraping code
COPY src/scraping/ ./src/scraping/
COPY config/ ./config/

# Create output directory and non-root user
RUN mkdir -p /app/data/raw && \
    useradd --create-home --shell /bin/bash scraper && \
    chown -R scraper:scraper /app

# Switch to non-root user
USER scraper

# Default command for scraping
CMD ["dumb-init", "--", "python", "-m", "src.scraping.main"]

# ============================================
# Stage 5: ML Training Service
# ============================================
FROM base as ml-training

# Install additional ML dependencies
RUN pip install --no-cache-dir \
    optuna \
    wandb

# Copy source code
COPY src/data_analysis/ ./src/data_analysis/
COPY config/ ./config/
COPY data/ ./data/

# Create models directory
RUN mkdir -p /app/data/models

# Default command for training
CMD ["python", "-m", "src.data_analysis.train"]

# ============================================
# Stage 6: MCP Server
# ============================================
FROM base as mcp-server

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy MCP code
COPY src/mcp/ ./src/mcp/
COPY config/ ./config/

# Create non-root user for MCP server
RUN groupadd -r mcpuser && \
    useradd --create-home --shell /bin/bash --gid mcpuser mcpuser && \
    chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose MCP port
EXPOSE 8000

# Default command for MCP server
CMD ["python", "-m", "uvicorn", "src.mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]