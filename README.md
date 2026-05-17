# Smart eCommerce Intelligence

## Système Intelligent de Data Mining & Machine Learning pour l'Analyse Concurrentielle eCommerce

---

## 📋 Présentation

Système complet et automatisé capable de scraper des données produits WooCommerce/Shopify, analyser les données avec des algorithmes de Data Mining (KMeans, DBSCAN, Random Forest, XGBoost, PCA, Apriori), orchestrer les traitements via Kubeflow Pipelines, et visualiser les résultats dans un dashboard Streamlit — le tout enrichi par des LLMs (DeepSeek, Groq) pour des analyses concurrentielles en langage naturel.

---

## 🚀 Guide de Démarrage Rapide

### Prérequis

| Logiciel | Version | Vérification |
|---|---|---|
| **Docker Engine** | 20.10+ | `docker --version` |
| **Docker Compose** | 2.20+ | `docker compose version` |
| **Minikube** (optionnel) | 1.30+ | `minikube version` |
| **Git** | 2.30+ | `git --version` |

### Installation en 5 minutes

```bash
# 1. Cloner le projet
git clone <url-du-depot>
cd DATA MINING

# 2. Copier et configurer le fichier .env
cp .env.example .env
```

### 3. Configurer le fichier `.env`

```ini
# Clés API WooCommerce (obligatoires pour le scraping)
WOOCOMMERCE_CONSUMER_KEY=ck_votre_cle
WOOCOMMERCE_CONSUMER_SECRET=cs_votre_secret
WOOCOMMERCE_STORE_URL=https://votre-store.localsite.io

# Clés LLM (optionnelles, sans le dashboard fonctionne sans)
GROQ_API_KEY=gsk_votre_cle_groq
DEEPSEEK_API_KEY=sk_votre_cle_deepseek

# PostgreSQL (valeurs par défaut)
POSTGRES_USER=ecommerce_user
POSTGRES_PASSWORD=secure_password

# MCP Server
MCP_API_KEY=mcp_api_key
```

> **💡 Identifiants de démonstration (store WooCommerce de test) :**
> - Store : `https://famous-breath.localsite.io`
> - Consumer Key : `ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17`
> - Consumer Secret : `cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65`
> - Basic Auth : utilisateur `mathematics`, mot de passe `succinct`

---

## 🐳 Commandes Docker

### Lancer tous les services

```bash
docker compose up -d
```

### Lancer uniquement les services essentiels

```bash
docker compose up -d postgres redis dashboard mcp-server
```

### Lancer le scraper (une seule exécution)

Le conteneur `scraper` compile et soumet la pipeline Kubeflow, puis s'arrête :

```bash
docker compose up -d scraper
```

Pour relancer le scraping (soumet un nouveau run Kubeflow) :

```bash
docker compose run --rm scraper
```

### Gestion des services

```bash
# Voir les logs d'un service
docker compose logs -f scraper
docker compose logs -f dashboard
docker compose logs -f mcp-server

# Redémarrer un service
docker compose restart dashboard

# Reconstruire et redémarrer
docker compose build scraper --no-cache
docker compose up -d scraper

# Arrêter tous les services
docker compose down

# Arrêter et supprimer les volumes (perte des données PostgreSQL)
docker compose down -v
```

### Profils Docker

| Profil | Commande | Services supplémentaires |
|---|---|---|
| **Développement** | `docker compose --profile dev up -d` | Jupyter (8888), pgAdmin (5050) |
| **Production** | `docker compose --profile production up -d` | Scheduler, agent-cluster, metrics |
| **Monitoring** | `docker compose --profile monitoring up -d` | Prometheus metrics (9090) |

### Services disponibles

| Service | URL | Identifiants |
|---|---|---|
| **Dashboard Streamlit** | [http://localhost:8501](http://localhost:8501) | Aucun |
| **MCP Server API** | [http://localhost:8000](http://localhost:8000) | API key : `mcp_api_key` |
| **MCP Health** | [http://localhost:8000/health](http://localhost:8000/health) | — |
| **PostgreSQL** | `localhost:5432` | user `ecommerce_user`, password `secure_password` |
| **Redis** | `localhost:6379` | password `redis_password` |
| **pgAdmin** (dev) | [http://localhost:5050](http://localhost:5050) | admin@example.com / pgadmin_password |
| **Jupyter** (dev) | [http://localhost:8888](http://localhost:8888) | token : `dev_token_123` |

---

## 📊 Accès au Dashboard

1. Ouvrir [http://localhost:8501](http://localhost:8501)
2. Le dashboard charge les produits depuis :
   - **PostgreSQL** (si des données existent)
   - **Fichier JSON** (`data/raw/products.json`)
   - **Données d'exemple** (3 produits factices en fallback)

### Pages du dashboard

| Page | Fonction |
|---|---|
| **📊 Vue d'ensemble** | KPIs, scatter plot prix/note, répartition catégories |
| **🏷️ Top Produits** | Classement avec filtres (catégorie, k, prix max) |
| **📈 Analyses ML** | Clustering (PCA, KMeans, DBSCAN, RF), prévisions Prophet, tendances XGBoost |
| **🏆 Concurrence** | Analyses concurrentielles via Groq (comparaison, émergents, stratégie) |
| **⚙️ Infrastructure** | Lancement pipeline Kubeflow, endpoints MCP |

---

## 🔧 Commandes avancées

### Tests unitaires

```bash
# Tous les tests
docker compose run --rm scraper python -m pytest tests/

# Tests spécifiques aux agents A2A
docker compose run --rm scraper python -m pytest tests/test_agents.py -v
```

### Pipeline Kubeflow

```bash
# Soumettre la pipeline depuis la machine hôte
python scripts/run_kfp.py --host http://127.0.0.1:61567

# Compiler seulement (sans soumettre)
python scripts/run_kfp.py --compile-only
```

### Lancer le scraping sans Docker

```bash
# Depuis la racine du projet
python -m src.scraping.main
```

### Exécuter le pipeline complet (scraping + ML + LLM)

```bash
python -m src
```

### Console Python dans un conteneur

```bash
docker exec -it ecommerce-scraper python
```

### Vérifier PostgreSQL

```bash
docker exec ecommerce-postgres psql -U ecommerce_user -d ecommerce_db -c "SELECT COUNT(*) FROM products;"
```

### Vérifier les modèles ML stockés

```bash
docker exec ecommerce-postgres psql -U ecommerce_user -d ecommerce_db -c "SELECT model_name, LENGTH(model_data) as size_bytes FROM kfp_models;"
```

---

## 🔍 Architecture des conteneurs

```
┌──────────────────────────────────────────────────────────────────┐
│                         Docker Compose                            │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │ Dashboard│  │  Scraper │  │ML-Training│  │MCP Server│        │
│  │ :8501    │  │ (1 exec) │  │          │  │ :8000    │        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │
│       │              │              │              │             │
│       └──────────────┼──────────────┼──────────────┘             │
│                      ▼              ▼                            │
│               ┌──────────┐  ┌──────────┐                        │
│               │PostgreSQL│  │  Redis   │                        │
│               │ :5432    │  │ :6379    │                        │
│               └──────────┘  └──────────┘                        │
│                                                                  │
│  Profils optionnels :                                            │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Jupyter  │  │ pgAdmin  │  │Scheduler │                      │
│  │ (dev)    │  │ (dev)    │  │(prod)    │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└──────────────────────────────────────────────────────────────────┘
                         │
                         ▼
               ┌──────────────────┐
               │   Minikube       │
               │   Kubeflow       │
               │   :61567         │
               └──────────────────┘
```

---

## 🛠️ Modules

| Module | Description | Technologie |
|---|---|---|
| **Scraping A2A** | Architecture multi-agents distribuée | Protocol, MessageBus (in-memory/Redis), 4 agents spécialisés |
| **ML & Data Mining** | KMeans, DBSCAN, PCA, Random Forest, XGBoost, Apriori | Scikit-learn, XGBoost, mlxtend |
| **Prévisions** | Tendance des prix par catégorie | Prophet (Meta), LinearRegression |
| **LLM** | DeepSeek & Groq avec auto-fallback | httpx, Llama-3.3-70b |
| **Analyse concurrentielle** | 3 analyses : comparaison, émergents, stratégie | Groq, LLMWrapper |
| **Pipeline Kubeflow** | 6 composants en DAG | kfp SDK v2 |
| **Dashboard BI** | 5 pages + assistant IA | Streamlit, Plotly |
| **MCP Server** | API REST compatible MCP | FastAPI |
| **Scheduler** | 3 jobs (daily, weekly, health) | APScheduler |
| **Monitoring** | Métriques Prometheus | prometheus_client |

---

## 📁 Structure du projet

```
DATA MINING/
├── .env                      # Variables d'environnement
├── .env.example              # Modèle du .env
├── Dockerfile                # Build multi-stage (8 stages)
├── docker-compose.yml        # Orchestration (8 services)
├── config/
│   └── config.yaml           # Configuration complète
├── data/
│   ├── raw/products.json     # Produits scrapés (cache)
│   └── models/               # Modèles ML sauvegardés
├── src/
│   ├── __main__.py           # Point d'entrée principal
│   ├── scraping/             # Scraping A2A
│   │   ├── main.py           # Point d'entrée scraper
│   │   ├── agents/           # Architecture A2A (6 fichiers)
│   │   ├── woocommerce_scraper.py
│   │   ├── shopify_scraper.py
│   │   ├── selenium_scraper.py
│   │   ├── playwright_scraper.py
│   │   └── storage.py        # PostgreSQL storage
│   ├── data_analysis/        # ML & Data Mining
│   │   ├── ml_models/        # KMeans, DBSCAN, RF, XGBoost, Apriori
│   │   ├── trend_analyzer.py # Prophet, XGBoost Trending
│   │   └── evaluation.py     # Métriques (silhouette, accuracy, ROC-AUC)
│   ├── llm/                  # Module LLM
│   │   ├── wrapper.py        # DeepSeek & Groq
│   │   └── competitive_analysis.py  # Analyse concurrentielle
│   ├── pipelines/kubeflow/
│   │   └── pipeline.py       # 6 composants KFP
│   ├── dashboard/
│   │   └── app.py            # Dashboard Streamlit
│   ├── mcp/
│   │   └── server.py         # Serveur MCP FastAPI
│   ├── scheduler/
│   │   └── main.py           # Jobs périodiques
│   └── monitoring/
│       └── prometheus_exporter.py
├── scripts/                  # Utilitaires
│   ├── run_kfp.py            # Soumission pipeline KFP
│   ├── setup_db.sql          # Schéma PostgreSQL
│   └── test_*.py             # Scripts de test
└── tests/
    ├── test_agents.py        # 660 lignes de tests A2A
    └── test_ml_models.py     # Tests ML
```

---

## 🧪 Tests

```bash
# Lancer tous les tests
docker compose run --rm scraper python -m pytest

# Tests agents A2A (660 lignes)
docker compose run --rm scraper python -m pytest tests/test_agents.py -v

# Tests ML
docker compose run --rm scraper python -m pytest tests/test_ml_models.py -v
```

---

## ❓ Dépannage

| Problème | Solution |
|---|---|
| **Port déjà utilisé** | Modifier le port dans `docker-compose.yml` (ex: `8501:8501` → `8502:8501`) |
| **Scraper ne démarre pas** | Vérifier que PostgreSQL est healthy : `docker compose ps` |
| **Dashboard sans données** | Lancer le scraping ou la pipeline KFP d'abord |
| **Erreur de build pip** | Relancer le build : `docker compose build --no-cache scraper` |
| **Pipeline KFP inaccessible** | Vérifier Minikube : `minikube status`, puis `kubectl get pods -n kubeflow` |
| **GROQ_API_KEY manquante** | Ajouter la clé dans `.env` et redémarrer le dashboard |
| **Conteneur en restart** | Voir les logs : `docker logs <nom_conteneur> --tail 50` |

---

## 📝 Licence

Projet développé dans le cadre du cours de Data Mining & Machine Learning — Bac+5.