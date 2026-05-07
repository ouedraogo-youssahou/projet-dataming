# Smart eCommerce Intelligence with ML&DM Pipelines, A2A Agents, and LLMs

---

## 📋 Présentation du projet

Ce projet vise à développer un système intelligent et automatisé capable de :
- **Scraper** des données produits sur des sites Shopify et WooCommerce
- **Analyser** les produits et identifier les meilleurs (Top-K)
- **Orchestrer** les étapes ML avec Kubeflow
- **Visualiser** les résultats dans un dashboard BI
- **Enrichir** l'analyse avec des LLMs
- **Respecter** les principes du Model Context Protocol (MCP)

---

## 🐳 Démarrage avec Docker

### Prérequis
- Docker Engine 20.10+
- Docker Compose 2.20+

### 1. Configuration

Copiez le fichier d'environnement d'exemple et renseignez vos valeurs :

```bash
cp .env.example .env
# Éditez .env avec vos clés API et mots de passe
```

### 2. Construction et lancement (production)

```bash
# Construire les images
docker compose build

# Démarrer les services essentiels (sans Jupyter/pgadmin)
docker compose up -d

# Vérifier l'état des conteneurs
docker compose ps
```

### 3. Développement (avec Jupyter et pgAdmin)

```bash
# Démarrer tous les services y compris ceux de développement
docker compose --profile dev up -d

# Accéder aux services :
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

# Arrêter et supprimer volumes (nettoyage complet)
docker compose down -v

# Reconstruire un service spécifique
docker compose build [service]

# Lancer les tests et lint
make test
make lint
make format

# Lancer les tests dans Docker
make test-docker

# Compiler le pipeline Kubeflow
make pipeline

# Lancer le cluster d'agents A2A (production)
make agents-start

# Lancer le scheduler (tâches planifiées)
make scheduler-start

# Lancer l'exporteur de métriques Prometheus
make metrics-start

# Accéder aux services :
# - Dashboard Streamlit : http://localhost:8501
# - Jupyter Notebook    : http://localhost:8888
# - pgAdmin (PostgreSQL): http://localhost:5050
# - MCP Server          : http://localhost:8000
# - Prometheus Metrics  : http://localhost:9090/metrics
```

---

## 📦 Déploiement sur une autre machine

1. Cloner le dépôt :
   ```bash
   git clone https://github.com/ouedraogo-youssahou/projet-dataming.git
   cd projet-dataming
   ```



3. Configuration :
   ```bash
   cp .env.example .env
   # Renseigner les variables (API keys, etc.)
   ```

4. Construire et lancer :
   ```bash
   docker compose build
   docker compose up -d
   ```

5. Vérifier :
   - Dashboard : http://localhost:8501
   - MCP health : http://localhost:8000/health
   - PostgreSQL : localhost:5432
   - Redis : localhost:6379

---

## 🗂️ Structure du projet

```
DATA MINING/
├── .dockerignore              # Exclusions des builds Docker
├── .env.example               # Template des variables d'environnement
├── .gitignore                 # Ignore .agents/ et fichiers sensibles
├── Dockerfile                 # Multi-stage builds (base, dev, prod, scraper, ml, mcp)
├── docker-compose.yml         # Orchestration multi-conteneurs
├── Makefile                   # Commandes make courantes
├── requirements.txt           # Dépendances Python
├── src/                       # Code source principal
│   ├── __main__.py            # Point d'entrée principal (orchestration)
│   ├── scraping/              # Module de web scraping (agents A2A)
│   ├── data_analysis/         # Analyse de données et ML
│   ├── pipelines/             # Pipelines ML (Kubeflow)
│   ├── dashboard/             # Dashboard BI (Streamlit)
│   ├── llm/                   # Module LLM pour enrichissement
│   └── mcp/                   # Architecture MCP
├── config/                    # Fichiers de configuration
│   └── config.yaml           # Configuration complète
├── data/                      # Données
│   ├── raw/                   # Données brutes (scraping)
│   ├── processed/             # Données nettoyées
│   └── models/                # Modèles entraînés
├── tests/                     # Tests automatisés
├── docs/                      # Documentation
├── cahierdeCharge.md          # Cahier des charges
└── README.md                  # Ce fichier
```

---

## 🚀 Modules du projet

### 1. Web Scraping avec agents A2A
- Extraction de données depuis Shopify et WooCommerce
- Utilisation de Selenium, Playwright, Scrapy
- Agents autonomes pour le scraping distribué
- **Orchestrateur** pour distribution de tâches et équilibrage de charge

### 2. Analyse ML et Data Mining
- **Top-K Selection** : Sélection des meilleurs produits
- **Clustering** : KMeans, DBSCAN, clustering hiérarchique
- **Classification** : Random Forest, XGBoost
- **Règles d'association** : Analyse du panier
- **PCA** : Réduction dimensionnelle pour visualisation

### 3. Kubeflow Pipelines ( maintenant COMPLET! )
- Pipeline DAG complet: scraping → preprocessing → training → top-k → LLM summary
- 5 composants Kubeflow définis
- Compilation YAML automatique
- Orchestration ML en production
- **Fichiers:** `src/pipelines/kubeflow/pipeline.py`, `run_pipeline.py`

### 4. Dashboard BI
- Visualisation interactive avec Streamlit
- KPIs et graphiques Plotly/Seaborn
- Tableaux de bord décisionnels
- Mode démo inclus

### 5. LLM pour enrichissement
- Génération de synthèses automatiques
- Analyse concurrentielle augmentée
- Recommandations stratégiques
- Support multi-provider (OpenAI, Anthropic, DeepSeek, Groq)

### 6. Architecture MCP
- Model Context Protocol d'Anthropic
- Agents responsables et sécurisés
- Journalisation et permissions
- API REST FastAPI

### 7. Services additionnels (optionnels)
- **Scheduler** : Tâches périodiques (scraping daily, retrain weekly)
- **Prometheus Exporter** : Métriques temps réel
- **Agent Cluster** : Lancement distribué des agents A2A

---

## 🛠️ Technologies utilisées

| Domaine | Outils |
|---------|-------|
| Scraping | Selenium, Playwright, Scrapy, BeautifulSoup |
| ML/DM | Scikit-learn, XGBoost, Pandas, NumPy |
| Pipelines | Kubeflow, Docker, Kubernetes |
| BI | Streamlit, Plotly, Power BI |
| LLMs | OpenAI GPT, Claude, LLaMA, LangChain |
| CI/CD | GitHub Actions |

---

## 📝 License

Ce projet est développé à des fins éducatives.

---

*Projet développé dans le cadre du cours de Data Mining & Machine Learning*