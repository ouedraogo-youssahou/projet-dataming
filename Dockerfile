# ============================================
# Smart eCommerce Intelligence - Dockerfile Optimisé
# ============================================
# Stratégie : requirements séparés par service pour réduire la taille des images
# Chaque stage n'installe QUE ce dont il a besoin.

# ============================================
# Stage 1: Base Image - Dépendances communes à TOUS les services
# ============================================
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install minimal system dependencies (communes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Mettre à jour pip + installer dépendances de base
COPY requirements-base.txt .
RUN pip install --upgrade pip && pip install -r requirements-base.txt

# ============================================
# Stage 2: Dashboard (streamlit + plots, pas de torch/ML lourd)
# ============================================
FROM base as dashboard

WORKDIR /app

# Copier et installer UNIQUEMENT les dépendances dashboard
COPY requirements-dashboard.txt .
RUN pip install --no-cache-dir -r requirements-dashboard.txt

# Copier les sources nécessaires
COPY src/dashboard/ ./src/dashboard/
COPY src/data_analysis/ ./src/data_analysis/
COPY src/llm/ ./src/llm/
COPY src/__init__.py ./src/
COPY config/ ./config/
COPY data/ ./data/

# Expose port
EXPOSE 8501

# Health check léger
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501')" || exit 1

CMD ["python", "-m", "streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]

# ============================================
# Stage 3: Scraper Service (léger, sans torch/ML/numpy lourd)
# ============================================
FROM python:3.11-slim as scraper

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Chrome/Chromium pour Selenium + dumb-init
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg dumb-init \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-archive-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Mettre à jour pip (correction bug JSON decode) puis installer dépendances
RUN pip install --upgrade pip
COPY requirements-base.txt requirements-scraping.txt ./
RUN pip install --no-cache-dir -r requirements-base.txt -r requirements-scraping.txt

# Installer playwright (navigateur)
RUN playwright install chromium --with-deps

# Copier le code scraping + package src
COPY src/scraping/ ./src/scraping/
COPY src/config/ ./src/config/
COPY src/__init__.py ./src/
COPY config/ ./config/

# Créer répertoire de sortie (pas de user non-root pour éviter les problèmes de volume Windows)
RUN mkdir -p /app/data/raw

CMD ["dumb-init", "--", "python", "-m", "src.scraping.main"]

# ============================================
# Stage 4: ML Training (torch, xgboost, lightgbm - le plus lourd)
# ============================================
FROM base as ml-training

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Installer Torch séparément (CPU wheel pour alléger)
RUN pip install torch==2.1.0 -i https://download.pytorch.org/whl/cpu --retries 10 --timeout 2200

# Tout installer en UNE SEULE commande pip (évite bug hash mismatch)
COPY requirements-ml.txt .
RUN pip install -r requirements-ml.txt --retries 10 --timeout 4200

# Purger le cache pip pour réduire la taille de l'image
RUN pip cache purge

# Copier sources ML uniquement
COPY src/data_analysis/ ./src/data_analysis/
COPY config/ ./config/
COPY data/ ./data/

RUN mkdir -p /app/data/models

CMD ["python", "-c", "from src.data_analysis.ml_models.clustering import ClusteringEngine; from src.data_analysis.ml_models.classification import ClassificationEngine; from src.data_analysis.ml_models.association import AssociationEngine; print('ML Training module ready'); print('Clustering, Classification, Association engines available')"]

# ============================================
# Stage 5: MCP Server (API + scraping léger + LLM)
# ============================================
FROM base as mcp-server

WORKDIR /app

# Installer dépendances spécifiques MCP/LLM
COPY requirements-llm.txt .
RUN pip install --no-cache-dir -r requirements-llm.txt

# Scraping léger (pour les endpoints MCP)
RUN pip install --no-cache-dir beautifulsoup4>=4.12.0 lxml>=4.9.0

# Copier les sources nécessaires
COPY src/mcp/ ./src/mcp/
COPY src/llm/ ./src/llm/
COPY src/scraping/ ./src/scraping/
COPY config/ ./config/

# User non-root
RUN groupadd -r mcpuser && \
    useradd --create-home --shell /bin/bash --gid mcpuser mcpuser && \
    chown -R mcpuser:mcpuser /app

USER mcpuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.mcp.server:app", "--host", "0.0.0.0", "--port", "8000"]

# ============================================
# Stage 6: Jupyter (développement - tout compris)
# ============================================
FROM base as jupyter

WORKDIR /app

# Installer les dépendances de tous les modules
COPY requirements-scraping.txt requirements-ml.txt requirements-dashboard.txt requirements-llm.txt ./
RUN pip install --no-cache-dir -r requirements-scraping.txt \
    -r requirements-ml.txt \
    -r requirements-dashboard.txt \
    -r requirements-llm.txt

# Jupyter + outils dev
RUN pip install --no-cache-dir jupyter jupyterlab ipykernel ipywidgets nbconvert debugpy kfp==2.0.0 apscheduler prometheus-client

# Torch (CPU)
RUN pip install --no-cache-dir torch==2.1.0 -i https://download.pytorch.org/whl/cpu

# Copier tout le code source
COPY . .

EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8888')" || exit 1

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]

# ============================================
# Stage 7: KFP Components (ML + scraping léger)
# ============================================
FROM ml-training as kfp-components

WORKDIR /app

# Ajouter outils KFP
RUN pip install --no-cache-dir kfp==2.0.0 apscheduler prometheus-client

# Copier tout le code source
COPY . .

# User non-root
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

USER appuser

# ============================================
# Stage 8: Agent Orchestrator (basé sur kfp-components)
# ============================================
FROM kfp-components as agent-orchestrator

CMD ["python", "-m", "src.scraping.agents.main"]