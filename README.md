# Smart eCommerce Intelligence with ML&DM Pipelines, A2A Agents, and LLMs

---

## 📋 Présentation du projet

Ce projet vise à développer un système intelligent et automatisé capable de :
- **Scraper** des données produits sur des sites Shopify et WooCommerce (via agents A2A)
- **Analyser** les produits et identifier les meilleurs (Top-K, clustering, classification)
- **Orchestrer** les étapes ML avec Kubeflow
- **Visualiser** les résultats dans un dashboard BI (Streamlit)
- **Enrichir** l'analyse avec des LLMs (OpenAI, Anthropic, DeepSeek, Groq)
- **Respecter** les principes du Model Context Protocol (MCP)

---

## 🗂️ Structure du projet

```
DATA MINING/
├── Dockerfile                   # Multi-stage optimisé (8 stages)
├── docker-compose.yml           # Orchestration multi-conteneurs
├── requirements-base.txt        # Dépendances communes (tous les services)
├── requirements-scraping.txt    # Dépendances scraping (Selenium, Playwright)
├── requirements-ml.txt          # Dépendances ML (torch, sklearn, xgboost)
├── requirements-dashboard.txt   # Dépendances dashboard (Streamlit, Plotly)
├── requirements-llm.txt         # Dépendances LLM (OpenAI, Anthropic)
├── requirements.txt             # Dépendances complètes (référence)
├── Makefile                     # Commandes make courantes
│
├── src/
│   ├── __init__.py              # Package principal
│   ├── __main__.py              # Point d'entrée principal (orchestration complète)
│   ├── scraping/                # Module de web scraping (agents A2A)
│   │   ├── main.py              # Point d'entrée scraper autonome (agents A2A)
│   │   ├── shopify_scraper.py   # Scraper Shopify (GraphQL + HTML)
│   │   ├── woocommerce_scraper.py
│   │   ├── selenium_scraper.py
│   │   ├── playwright_scraper.py
│   │   ├── storage.py           # PostgreSQL storage
│   │   └── agents/              # Architecture A2A (message bus, orchestrateur, etc.)
│   ├── data_analysis/           # Analyse de données et ML
│   │   ├── evaluation.py
│   │   └── ml_models/           # Clustering, Classification, Association
│   ├── pipelines/               # Pipelines ML (Kubeflow)
│   │   └── kubeflow/            # Pipeline DAG compilé
│   ├── dashboard/               # Dashboard BI (Streamlit)
│   │   └── app.py               # Dashboard avec mode démo
│   ├── llm/                     # Module LLM
│   │   └── wrapper.py           # Wrapper multi-provider
│   └── mcp/                     # Serveur MCP (FastAPI)
│       └── server.py            # API REST + endpoints LLM
│
├── config/
│   └── config.yaml              # Configuration complète
├── data/                        # Données (raw, processed, models)
├── tests/                       # Tests automatisés
│   └── test_agents.py           # Tests A2A complets
└── docs/                        # Documentation
```

---

## 🐳 Démarrage avec Docker (Optimisé)

Les images Docker utilisent des **requirements séparés** pour minimiser la taille : chaque service n'installe QUE les dépendances dont il a besoin.

| Service | Stage Docker | Taille | Dépendances |
|---------|-------------|--------|-------------|
| **Dashboard** | `dashboard` | **~1.5 GB** | streamlit, plotly, seaborn |
| **Scraper** | `scraper` | **~3 GB** | selenium, playwright, chrome |
| **ML Training** | `ml-training` | **~3.7 GB** | torch, sklearn, xgboost |
| **MCP Server** | `mcp-server` | **~1 GB** | openai, anthropic, fastapi |
| **Jupyter** (dev) | `jupyter` | **~3.5 GB** | tout inclus + jupyter |

### Prérequis
- Docker Engine 20.10+
- Docker Compose 2.20+

### 1. Configuration

```bash
cp .env.example .env
# Éditez .env avec vos clés API et mots de passe
```

### 2. Construction et lancement (production)

```bash
# Construire les images optimisées
docker compose build

# Démarrer les services essentiels
docker compose up -d

# Vérifier l'état
docker compose ps
```

### 3. Développement (avec Jupyter et pgAdmin)

```bash
# Démarrer tous les services y compris ceux de développement
docker compose --profile dev up -d

# Accès :
# - Dashboard Streamlit : http://localhost:8501
# - Jupyter Notebook    : http://localhost:8888
# - pgAdmin (PostgreSQL): http://localhost:5050
# - MCP Server          : http://localhost:8000
```

### 4. Commandes utiles

```bash
# Voir les logs
docker compose logs -f [service]

# Redémarrer un service
docker compose restart [service]

# Arrêter tous les services
docker compose down

# Reconstruire un service spécifique
docker compose build [service]

# Lancer les tests
make test
make lint
make format

# Compiler le pipeline Kubeflow
make pipeline

# Lancer le cluster d'agents A2A
make agents-start

# Lancer le scheduler
make scheduler-start
```

---

## 🚀 Modules du projet

### 1. Web Scraping avec agents A2A
- Extraction de données depuis Shopify et WooCommerce
- Utilisation de Selenium, Playwright, Scrapy
- **Architecture A2A complète** :
  - Protocol messages (task_assign, task_complete, heartbeat, etc.)
  - Message Bus (in-memory ou Redis Pub/Sub)
  - Agent Registry (découverte, heartbeat timeout)
  - BaseAgent (cycle de vie, accept/reject, retry, backoff)
  - Agents spécialisés : ShopifyAgent, WooCommerceAgent, GenericScraperAgent
  - DataCollectorAgent (bufferisation + flush PostgreSQL)
  - Orchestrator (distribution de tâches, failover, équilibrage de charge)

### 2. Analyse ML et Data Mining
- **Top-K Selection** : Scoring multi-critères pondéré
- **Clustering** : KMeans, DBSCAN, clustering hiérarchique
- **Classification** : Random Forest, XGBoost
- **Règles d'association** : Apriori
- **PCA** : Réduction dimensionnelle pour visualisation
- **Évaluation** : Silhouette, Calinski-Harabasz, Davies-Bouldin, ROC-AUC

### 3. Kubeflow Pipelines
- Pipeline DAG complet: scraping → preprocessing → training → top-k → LLM summary
- 5 composants Kubeflow définis
- Compilation YAML automatique

### 4. Dashboard BI
- Visualisation interactive avec Streamlit
- KPIs et graphiques Plotly/Seaborn
- Mode démo inclus (données sample)
- Filtres par catégorie, prix, Top-K

### 5. LLM pour enrichissement
- Génération de synthèses automatiques
- Analyse concurrentielle augmentée
- Support multi-provider (OpenAI, Anthropic, DeepSeek, Groq)
- Auto-fallback entre providers

### 6. Architecture MCP
- Model Context Protocol d'Anthropic
- API REST FastAPI avec authentification
- Endpoints : `/health`, `/tools/*`, `/mcp.json`

### 7. Services additionnels (optionnels)
- **Scheduler** : Tâches périodiques (scraping daily, retrain weekly)
- **Prometheus Exporter** : Métriques temps réel
- **Agent Cluster** : Lancement distribué des agents A2A

---

## 🛠️ Technologies utilisées

| Domaine | Outils |
|---------|-------|
| Scraping | Selenium, Playwright, Scrapy, BeautifulSoup |
| ML/DM | Scikit-learn, XGBoost, LightGBM, PyTorch |
| Pipelines | Kubeflow, Docker, Kubernetes |
| BI | Streamlit, Plotly, Power BI |
| LLMs | OpenAI GPT, Anthropic Claude, DeepSeek, Groq |
| CI/CD | GitHub Actions |

---

## 📝 License

Ce projet est développé à des fins éducatives.

---

*Projet développé dans le cadre du cours de Data Mining & Machine Learning*