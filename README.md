# Smart eCommerce Intelligence avec ML&DM Pipelines, Agents A2A, et LLMs

---

## 📋 Présentation du projet

Système intelligent et automatisé capable de :
- **Scraper** des données produits sur WooCommerce via API REST (agents A2A)
- **Analyser** les produits et identifier les meilleurs (Top-K, clustering, classification, règles d'association)
- **Orchestrer** les étapes ML avec Kubeflow
- **Visualiser** les résultats dans un dashboard BI (Streamlit)
- **Enrichir** l'analyse avec des LLMs (DeepSeek / Groq)
- **Exposer** un serveur MCP (Model Context Protocol)

---

## 🗂️ Structure du projet

```
DATA MINING/
├── Dockerfile                   # Multi-stage optimisé (8 stages)
├── docker-compose.yml           # Orchestration multi-conteneurs
├── .env                         # Variables d'environnement (clés API, credentials)
├── requirements-*.txt           # Dépendances séparées par service
│
├── src/
│   ├── __init__.py              # Package principal (exports conditionnels)
│   ├── __main__.py              # Point d'entrée principal (orchestration complète)
│   ├── scraping/                # Module de web scraping (agents A2A)
│   │   ├── main.py              # Point d'entrée scraper autonome
│   │   ├── shopify_scraper.py   # Scraper Shopify (GraphQL + HTML)
│   │   ├── woocommerce_scraper.py  # Scraper WooCommerce avec pagination + HTML crawl
│   │   ├── selenium_scraper.py  # Scraper Selenium (JS)
│   │   ├── playwright_scraper.py # Scraper Playwright (JS)
│   │   ├── storage.py           # PostgreSQL storage
│   │   └── agents/              # Architecture A2A complète
│   ├── data_analysis/           # Analyse de données et ML
│   │   ├── evaluation.py        # Métriques d'évaluation (silhouette, Calinski-Harabasz, ROC-AUC...)
│   │   └── ml_models/           # KMeans, DBSCAN, Random Forest, XGBoost, Apriori
│   ├── pipelines/               # Pipelines ML (Kubeflow)
│   │   └── kubeflow/pipeline.py # Pipeline DAG 5 composants
│   ├── dashboard/               # Dashboard BI Streamlit
│   │   └── app.py               # Dashboard avec mode démo + data réelles
│   ├── llm/                     # Module LLM (DeepSeek & Groq)
│   │   └── wrapper.py           # Wrapper httpx (OpenAI/Anthropic retirés)
│   ├── mcp/                     # Serveur MCP (FastAPI)
│   │   └── server.py            # API REST + outils scraping/analyse/LLM
│   ├── scheduler/               # Planificateur de tâches
│   │   └── main.py              # Jobs cron scraping + ML retrain (import circulaire corrigé)
│   └── monitoring/              # Métriques Prometheus
│       └── prometheus_exporter.py
│
├── config/config.yaml           # Configuration complète
├── data/raw/products.json       # 74 produits scrapés (WooCommerce réel)
├── tests/test_agents.py         # 660 lignes de tests A2A
└── scripts/                     # Utilitaires de test et déploiement
```

---

## 🐳 Guide d'installation et d'exécution (nouvelle machine)

### Prérequis système

| Logiciel | Version minimale | Téléchargement |
|----------|-----------------|----------------|
| **Docker Engine** | 20.10+ | [docs.docker.com/get-docker](https://docs.docker.com/get-docker/) |
| **Docker Compose** | 2.20+ | Inclus avec Docker Desktop |
| **Git** | 2.30+ | [git-scm.com](https://git-scm.com/) |
| **Espace disque** | 15 GB libre | Pour les images Docker + dépendances |

Vérifier l'installation :
```bash
docker --version       # Doit afficher 20.10+
docker compose version # Doit afficher 2.20+
git --version          # Doit afficher 2.30+
```

### Étape 1 : Cloner le projet

```bash
git clone https://github.com/ouedraogo-youssahou/projet-dataming.git
cd projet-dataming
```

> ⚠️ Si vous n'avez pas les droits, téléchargez le ZIP depuis GitHub et extrayez-le.

### Étape 2 : Configurer les variables d'environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env
```

Ouvrir le fichier `.env` et renseigner au minimum les clés suivantes :

```ini
# 🔑 CLÉS API OBLIGATOIRES POUR LE SCRAPING WOOCOMMERCE
WOOCOMMERCE_CONSUMER_KEY=ck_votre_cle_ici
WOOCOMMERCE_CONSUMER_SECRET=cs_votre_secret_ici
WOOCOMMERCE_STORE_URL=https://votre-store.localsite.io

# (Optionnel) Clés DeepSeek pour les résumés LLM
DEEPSEEK_API_KEY=sk-votre_cle_deepseek
GROQ_API_KEY=gsk_votre_cle_groq
```

> 💡 **Pour le scraping du site de démonstration :**
> - Store : `https://famous-breath.localsite.io`
> - Consumer Key : `ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17`
> - Consumer Secret : `cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65`
> - Auth Basic : username `mathematics`, password `succinct`
> - Ces identifiants sont déjà pré-remplis dans le fichier `.env.example`

### Étape 3 : Lancer les services Docker

#### Option A : Tout lancer (recommandé)

```bash
# Construire toutes les images (première fois seulement, ~15-30 min)
docker compose build

# Démarrer tous les services
docker compose up -d

# Vérifier que tout est healthy
docker compose ps
```

Résultat attendu :
```
NAME                   IMAGE                          STATUS          PORTS
ecommerce-dashboard    datamining-dashboard:latest    Up (healthy)    0.0.0.0:8501->8501
ecommerce-scraper      datamining-scraper:latest      Up (healthy)    
ecommerce-mcp-server   datamining-mcp-server:latest   Up (healthy)    0.0.0.0:8000->8000
ecommerce-ml-training  datamining-ml-training:latest  Up (running)    
ecommerce-postgres     postgres:15-alpine             Up (healthy)    0.0.0.0:5432->5432
ecommerce-redis        redis:7-alpine                 Up (healthy)    0.0.0.0:6379->6379
```

#### Option B : Lancer uniquement les services essentiels

```bash
# Minimum pour le scraping + ML + MCP
docker compose up -d postgres redis mcp-server dashboard scraper ml-training
```

### Étape 4 : Scraper des données produits

Le scraper démarre automatiquement et va crawler le store WooCommerce configuré dans `.env` :

```bash
# Voir les logs du scraper en direct
docker logs -f ecommerce-scraper
```

Logs attendus :
```
INFO:__main__:Scraper démarré avec 4 agents et 1 cibles
INFO:...:Starting API crawl: https://.../wp-json/wc/v3/products
INFO:...:Page 1: 74 products (total: 74)
INFO:...:API crawl complete: 74 products
```

Les produits scrapés sont stockés dans `data/raw/products.json`.

### Étape 5 : Accéder aux services

| Service | URL | Identifiants |
|---------|-----|--------------|
| **Dashboard Streamlit** | [http://localhost:8501](http://localhost:8501) | Aucun |
| **MCP Server API** | [http://localhost:8000](http://localhost:8000) | API key : `mcp_api_key` |
| **MCP Health** | [http://localhost:8000/health](http://localhost:8000/health) | — |
| **PostgreSQL** | `localhost:5432` | user `ecommerce_user`, password `secure_password` |
| **Redis** | `localhost:6379` | password `redis_password` |
| **pgAdmin** (dev) | [http://localhost:5050](http://localhost:5050) | admin@example.com / pgadmin_password |
| **Jupyter** (dev) | [http://localhost:8888](http://localhost:8888) | token : `jupyter_token` |

> Pour lancer pgAdmin et Jupyter : `docker compose --profile dev up -d`

### Commandes utiles au quotidien

```bash
# Voir les logs d'un service
docker compose logs -f scraper          # Logs du scraper
docker compose logs -f dashboard        # Logs du dashboard
docker compose logs -f mcp-server       # Logs du serveur MCP

# Redémarrer un service après modification du code
docker compose restart scraper

# Reconstruire un service après modification du Dockerfile
docker compose build scraper --no-cache
docker compose up -d scraper

# Arrêter tous les services
docker compose down

# Arrêter et supprimer les volumes (perte des données PostgreSQL)
docker compose down -v

# Exécuter une commande dans un conteneur
docker exec -it ecommerce-scraper python -c "print('hello from scraper')"
```

### Résolution des problèmes courants

#### Problème : "Port already in use"
```bash
# Le port 8501 ou 8000 est déjà utilisé sur la machine
# Modifier le port dans docker-compose.yml :
#   "8501:8501" → "8502:8501"  (dashboard sur le port 8502)
```

#### Problème : "PostgreSQL init failed"
```bash
# Les credentials PostgreSQL ne sont pas dans .env
# Vérifier que POSTGRES_USER et POSTGRES_PASSWORD sont définis
cat .env | grep POSTGRES
```

#### Problème : "docker compose build trop lent"
```bash
# Utiliser le cache Docker (ne pas mettre --no-cache)
docker compose build

# Pour un service spécifique uniquement
docker compose build scraper
```

#### Problème : "API returned 401"
```bash
# Les clés WooCommerce ou l'auth Basic sont incorrectes
# Vérifier le .env :
#   WOOCOMMERCE_CONSUMER_KEY
#   WOOCOMMERCE_CONSUMER_SECRET
#   WOOCOMMERCE_USERNAME / WOOCOMMERCE_PASSWORD (si auth Basic requise)
```

### Services Docker disponibles

| Service | Image | Port | Taille | Profil |
|---------|-------|------|--------|--------|
| **Dashboard** | `datamining-dashboard` | 8501 | ~1.5 GB | default |
| **Scraper** | `datamining-scraper` | — | ~3 GB | default |
| **ML Training** | `datamining-ml-training` | — | ~3.7 GB | default |
| **MCP Server** | `datamining-mcp-server` | 8000 | ~1 GB | default |
| **PostgreSQL** | `postgres:15-alpine` | 5432 | — | default |
| **Redis** | `redis:7-alpine` | 6379 | — | default |
| **Jupyter** (dev) | `datamining-jupyter` | 8888 | ~3.5 GB | `dev` |
| **pgAdmin** (dev) | `dpage/pgadmin4` | 5050 | — | `dev` |

---

## 🚀 Modules détaillés

### 1. Web Scraping avec agents A2A
- **Architecture A2A complète** : Protocol, MessageBus (in-memory + Redis), AgentRegistry, BaseAgent, Orchestrator
- **Agents spécialisés** : ShopifyAgent, WooCommerceAgent, GenericScraperAgent, DataCollectorAgent
- **Scrapers** : Shopify (GraphQL + HTML fallback), WooCommerce (REST API + HTML crawl), Selenium, Playwright
- **Crawling réel** : 74 produits scrapés depuis `famous-breath.localsite.io` via WooCommerce REST API avec Basic Auth + clés API
- **Tests** : 660 lignes couvrant protocol, bus, agents, orchestrateur

### 2. Analyse ML et Data Mining
- **Top-K Selection** : Scoring multi-critères pondéré (rating, reviews, price, availability)
- **Clustering** : KMeans, DBSCAN, clustering hiérarchique (dans `ClusteringEngine`)
- **Classification** : Random Forest, XGBoost (dans `ClassificationEngine`)
- **Règles d'association** : Apriori, métriques support/confidence/lift (dans `AssociationEngine`)
- **Évaluation** : Silhouette, Calinski-Harabasz, Davies-Bouldin, ROC-AUC, F1-score
- ⚠️ **PCA** : Non implémenté (prévu mais pas encore codé)

### 3. Kubeflow Pipelines
- **5 composants KFP** : scraping → preprocessing → training → top-k → LLM summary
- **761 lignes** de pipeline défini avec `@component` decorators
- **Base image** : `datamining-ml-training:latest` (corrigé, était `ecommerce-kfp:latest` inexistant)
- **Composant LLM** : DeepSeek/Groq (OpenAI/Anthropic retirés)
- ⚠️ **Jamais exécuté** sur un vrai cluster Kubernetes/Kubeflow

### 4. Dashboard BI (Streamlit)
- KPIs : total produits, prix moyen, note moyenne
- Graphiques : distribution des prix (Plotly), top catégories
- Tableau Top-K interactif avec filtres
- Mode démo + données scrapées réelles (74 produits WooCommerce)

### 5. LLM (DeepSeek & Groq)
- **Wrapper httpx** (pas de dépendance OpenAI/Anthropic)
- Méthodes : `complete()`, `summarize()`, `extract_entities()`
- **Auto-fallback** : DeepSeek → Groq si clé DeepSeek absente
- Utilisé dans : MCP Server, pipeline KFP

### 6. Serveur MCP (Model Context Protocol)
- FastAPI avec endpoints : `/health`, `/ready`, `/tools`, `/resources`
- **5 outils** exposés : scrape_shopify, scrape_woocommerce, analyze_top_k, generate_summary, list_resources
- Authentification par API key
- Logging des requêtes/réponses

### 7. Scheduler
- Jobs automatiques : scraping daily (3h), ML retrain weekly (dimanche 4h), health check (5min)
- ⚠️ Ne tourne qu'avec le profil `production`

### 8. Prometheus Metrics
- Métriques : scrape_requests_total, scrape_duration_seconds, agent_tasks_total
- ⚠️ Service avec profil `monitoring` seulement

---

## 🛠️ Technologies utilisées (dans le code)

| Domaine | Outils |
|---------|--------|
| Scraping | Selenium, Playwright, BeautifulSoup, aiohttp |
| ML/DM | Scikit-learn, XGBoost, LightGBM, PyTorch (CPU) |
| Pipelines | Kubeflow (kfp SDK), Docker |
| BI | Streamlit, Plotly, Seaborn |
| LLMs | DeepSeek, Groq (httpx) |
| Infra | Docker Compose, PostgreSQL, Redis |
| CI/CD | GitHub Actions (à configurer) |

---

## 📝 License

Projet développé dans le cadre du cours de Data Mining & Machine Learning.
