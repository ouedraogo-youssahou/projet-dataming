# 📊 Rapport d'Avancement du Projet

## Smart eCommerce Intelligence avec ML&DM Pipelines, Agents A2A, et LLMs

**Date :** Mai 2026
**Statut global :** ~70% du projet complet

---


---

## 2. Détail par module

### 2.1 Web Scraping avec agents A2A (85%)

#### Architecture A2A complète

**Fichiers implémentés :**

| Fichier | Rôle | Description technique |
|---------|------|---------------------|
| `src/scraping/agents/protocol.py` | Définition du protocole A2A | Classes `A2AMessage`, `A2AMessageType`, `Task`, `AgentCapability`, `AgentInfo`. Messages : task_assign, task_complete, agent_heartbeat, data_deliver, etc. |
| `src/scraping/agents/message_bus.py` | Bus de messages | `A2AMessageBus` : communication asynchrone entre agents (in-memory via `asyncio.Queue` ou Redis Pub/Sub). `AgentRegistry` : découverte d'agents, heartbeat timeout (30s). |
| `src/scraping/agents/base_agent.py` | Agent de base | `BaseAgent` : cycle de vie (initialized → idle → busy → completed), accept/reject de tâches, retry avec backoff exponentiel, heartbeat automatique toutes les 30s. |
| `src/scraping/agents/orchestrator.py` | Orchestrateur | `AgentOrchestrator` : distribution round-robin des tâches, failover si agent défaillant, équilibrage de charge, collecte et agrégation des résultats. |
| `src/scraping/agents/specialized_agents.py` | Agents spécialisés | `ShopifyAgent` (scraping Shopify GraphQL), `WooCommerceAgent` (scraping REST API + Basic Auth), `GenericScraperAgent` (fallback Selenium/Playwright). |
| `src/scraping/agents/data_collector.py` | Collecteur de données | `DataCollectorAgent` : bufferisation (flush à 30s ou 50 produits), tentative stockage PostgreSQL, fallback mémoire. |

**✅ Avantages de l'architecture A2A :**
- **Scalabilité horizontale** : chaque agent peut être déployé séparément. On peut ajouter des agents Shopify ou WooCommerce sans modifier le code existant. Par exemple, pour scraper 10 boutiques en parallèle, il suffit de créer 10 instances de WooCommerceAgent.
- **Résilience** : si un agent plante (ex: timeout réseau), l'orchestrateur redirige automatiquement la tâche vers un autre agent disponible. Le heartbeat timeout (30s) permet de détecter les agents morts.
- **Découplage** : les agents communiquent via le MessageBus (asynchrone). L'orchestrateur n'a pas besoin de connaître l'implémentation interne des agents. On peut remplacer un agent sans impact sur les autres.
- **Bufferisation** : le DataCollectorAgent accumule les produits en mémoire et les flush par lots (50 produits ou 30s). Cela évite de faire 74 requêtes PostgreSQL individuelles pour 74 produits.
- **Extensibilité** : pour ajouter un nouveau type de plateforme (ex: Magento), il suffit de créer une nouvelle classe qui hérite de `BaseAgent` et l'enregistrer dans l'orchestrateur.

#### Scrapers individuels

| Fichier | Rôle | Technologies |
|---------|------|-------------|
| `src/scraping/shopify_scraper.py` | Scraper Shopify | Storefront GraphQL API + HTML fallback (requests/BeautifulSoup) |
| `src/scraping/woocommerce_scraper.py` | Scraper WooCommerce | REST API paginée + HTML crawl (BeautifulSoup). Support Basic Auth + clés API |
| `src/scraping/selenium_scraper.py` | Scraper Selenium | Chrome headless pour sites JavaScript lourds |
| `src/scraping/playwright_scraper.py` | Scraper Playwright | Chromium headless, fallback automatique si Selenium échoue |
| `src/scraping/storage.py` | Stockage PostgreSQL | Connection pool asyncpg, création automatique des tables |
| `src/scraping/base_scraper.py` | Classe de base | Rate limiting, rotation user-agent, normalisation des champs produits |

**✅ Avantages des scrapers :**
- **Multi-plateforme** : supporte à la fois Shopify (GraphQL), WooCommerce (REST) et sites génériques (HTML). Couvre la majorité des boutiques en ligne.
- **Pagination automatique** : le scraper WooCommerce récupère tous les produits (100 par page) jusqu'à épuisement. Pas besoin de connaître le nombre total de produits à l'avance.
- **HTML fallback** : si l'API REST WooCommerce n'est pas disponible (401, 403), le scraper bascule automatiquement sur le HTML crawl avec BeautifulSoup.
- **Rate limiting** : chaque scraper limite ses requêtes (2 req/s Shopify, 4 req/s WooCommerce) pour ne pas être banni par les serveurs cibles.
- **Authentification flexible** : supporte Basic Auth (pour les sites protégés par .htaccess) ET les clés API WooCommerce en paramètres URL.

#### Scraping réel effectué

- **Site cible** : `https://famous-breath.localsite.io` (WooCommerce)
- **Authentification** : Basic Auth (mathematics:succinct) + clés API WooCommerce
- **74 produits** scrapés sur 1 page (pagination automatique, 100 produits/page)
- **Échantillon de données** : prix de $2.00 à $680.00, 7 catégories
- **Fichier de sortie** : `data/raw/products.json`

**✅ Avantage du scraping réel :**
- **Données authentiques** : contrairement à des données synthétiques, les 74 produits proviennent d'un vrai site WooCommerce avec de vraies catégories, prix et descriptions.
- **Preuve de concept fonctionnelle** : le pipeline complet (A2A → scraper → stockage fichier) a été testé et validé avec un site réel.

#### ⚠️ Ce qui manque

- **Crawling multi-pages** : ne récupère que la page 1 du shop. Pas de navigation sur les pages de catégories, sous-pages ou pages de détail.
- **Shopify réel** : pas de scraping Shopify effectif (clé API non configurée).
- **Stockage PostgreSQL** : le DataCollector ne peut pas stocker en base (credentials PostgreSQL absents du `.env`).
- **Tests d'intégration** : pas de tests avec les vrais scrapers (Selenium, Playwright).

---

### 2.2 Analyse ML & Data Mining (70%)

#### Moteurs ML implémentés

**`ClusteringEngine` (`src/data_analysis/ml_models/clustering.py`) :**

| Méthode | Algorithme | Usage |
|---------|-----------|-------|
| `kmeans(X, n_clusters)` | KMeans (scikit-learn) | Segmentation des produits en groupes (premium, budget, populaires) |
| `dbscan(X, eps, min_samples)` | DBSCAN | Détection des produits atypiques, anomalies de prix |
| `hierarchical(X, n_clusters)` | AgglomerativeClustering | Hiérarchie des catégories de produits |
| `find_optimal_k(X, max_k)` | Méthode du coude + Silhouette | Trouver automatiquement le nombre optimal de clusters |

**✅ Avantages du clustering :**
- **Segmentation marketing** : KMeans permet de grouper les produits par gamme de prix/niveau de popularité. Ex: un cluster "premium" (prix > $200, note > 4.5), un cluster "bon plan" (prix < $50, note > 4.0), etc.
- **Détection d'anomalies** : DBSCAN identifie les produits avec des prix anormalement hauts ou bas par rapport à leur catégorie. Utile pour repérer les erreurs de saisie ou les offres exceptionnelles.
- **Hiérarchie naturelle** : le clustering hiérarchique construit un arbre des catégories. Permet de visualiser comment les produits se regroupent (ex: tous les T-shirts ensemble, puis séparés par prix).
- **Auto-optimisation** : `find_optimal_k()` évite de deviner le nombre de clusters manuellement. Il calcule la meilleure valeur de K avec la méthode du coude + score silhouette.

**`ClassificationEngine` (`src/data_analysis/ml_models/classification.py`) :**

| Méthode | Algorithme | Usage |
|---------|-----------|-------|
| `train_random_forest(X, y)` | Random Forest | Prédire si un produit sera "top" ou "non top" |
| `train_xgboost(X, y)` | XGBoost | Prédiction plus rapide et souvent plus précise |
| `predict(model, X)` | Inférence | Classifier un nouveau produit |
| `evaluate(model, X_test, y_test)` | Évaluation | Accuracy, précision, rappel, F1, ROC-AUC |

**✅ Avantages de la classification :**
- **Prédiction de succès** : en entraînant sur des données historiques (produits qui ont bien marché vs. ceux qui ont échoué), le modèle peut prédire le potentiel d'un nouveau produit.
- **Double modèle** : Random Forest pour l'interprétabilité (on peut voir quels facteurs influencent le plus la prédiction), XGBoost pour la performance pure.
- **Métriques complètes** : au-delà de l'accuracy, les métriques de précision/rappel/F1 permettent d'évaluer la qualité même sur des datasets déséquilibrés (ex: 90% de produits "non top", 10% de "top").

**`AssociationEngine` (`src/data_analysis/ml_models/association.py`) :**

| Méthode | Algorithme | Usage |
|---------|-----------|-------|
| `find_frequent_itemsets(df, min_support)` | Apriori (mlxtend) | Trouver les combinaisons de produits fréquentes |
| `generate_rules(itemsets, metric, min_threshold)` | Association Rules | Générer les règles {A} → {B} avec support/confidence/lift |

**✅ Avantages des règles d'association :**
- **Recommandation cross-sell** : si la règle `{smartphone} → {coque}` a un lift de 3.5, cela signifie qu'un client qui achète un smartphone est 3.5 fois plus susceptible d'acheter une coque. Utile pour le panier moyen.
- **Métrique lift** : contrairement à la simple corrélation, le lift mesure si l'association est significative (>1) ou due au hasard (≈1).
- **Apriori optimisé** : l'algorithme Apriori réduit l'espace de recherche en éliminant les itemsets rares dès les premières itérations.

**`evaluation.py` (`src/data_analysis/evaluation.py`) :**

| Fonction | Usage |
|----------|-------|
| `evaluate_clustering(X, labels)` | Silhouette, Calinski-Harabasz, Davies-Bouldin |
| `evaluate_classification(y_true, y_pred)` | Accuracy, precision, recall, F1, ROC-AUC |
| `evaluate_association(rules_df)` | Support, confidence, lift, nombre de règles |

**✅ Avantages de l'évaluation :**
- **Validité scientifique** : les métriques utilisées sont celles recommandées par le cahier des charges (silhouette, Calinski-Harabasz, Davies-Bouldin, ROC-AUC).
- **Comparaison objective** : permet de comparer KMeans vs DBSCAN sur les mêmes données avec les mêmes métriques.
- **Détection des overfitting** : la séparation train/test (80/20) évite que le modèle apprenne par cœur les données.

#### Top-K Selection

Implémenté dans `src/__main__.py` (méthode `analyze_top_k()`).

**Critères de scoring pondéré :**
| Critère | Poids | Justification |
|---------|-------|---------------|
| Rating | 30% | La note client est le meilleur indicateur de satisfaction |
| Reviews count | 25% | Un produit avec beaucoup d'avis est plus fiable |
| Price competitiveness | 20% | Un prix bas par rapport à la moyenne = meilleur rapport qualité/prix |
| Availability | 15% | Un produit en stock est prioritaire |
| Recency | 10% | Les produits récents sont plus pertinents |

**✅ Avantages du Top-K :**
- **Décision multi-critères** : au lieu d'un simple tri par prix ou par note, le scoring combine 5 facteurs avec leurs poids respectifs.
- **Personnalisable** : les poids peuvent être modifiés dans la config (`config.yaml`). Un site peut favoriser le prix (poids 0.4) plutôt que la note (poids 0.2).
- **Normalisation** : chaque critère est normalisé entre 0 et 1 avant pondération. Un produit à $680 n'écrase pas le score des produits à $50.

#### Volume de données

**74 produits réels** scrapés (`data/raw/products.json`).

**⚠️ Limitation :** le cahier des charges recommande 2000-5000 produits. 74 produits c'est insuffisant pour un apprentissage ML significatif (les modèles risquent l'overfitting).

#### ⚠️ Ce qui manque


- **Pas d'exécution réelle** : les algorithmes sont codés mais jamais exécutés sur les 74 produits.
- **Rapport d'analyse** : aucun document business avec interprétation des résultats.

---

### 2.3 Kubeflow Pipelines (60%)

#### Implémentation

| Fichier | Rôle | Description |
|---------|------|-------------|
| `src/pipelines/kubeflow/pipeline.py` | Définition du pipeline DAG | 5 composants chainés : scrape → preprocess → train → top-k → LLM summary. 761 lignes de code. |
| `src/pipelines/kubeflow/config/` | Configuration | `pipeline_config.yaml`, `component_config.py` |
| `generate_valid_pipeline.py` | Compilation | Script pour générer le YAML Kubeflow |

**Les 5 composants du pipeline :**
1. **scrape_products_kfp** : scrape les produits depuis les plateformes configurées
2. **preprocess_data_kfp** : nettoie, normalise, encode les données (StandardScaler, LabelEncoder)
3. **train_models_kfp** : entraîne KMeans, DBSCAN, Random Forest, XGBoost + règles d'association
4. **select_top_k_kfp** : calcule le score et sélectionne les K meilleurs produits
5. **generate_llm_summary_kfp** : génère un résumé avec DeepSeek/Groq

**✅ Avantages du pipeline Kubeflow :**
- **Reproductibilité** : le pipeline peut être exécuté à l'identique sur n'importe quel cluster Kubeflow. Pas de dépendance à l'environnement local.
- **Orchestration automatique** : les étapes s'exécutent dans l'ordre (scrape → preprocess → train). Si le scraping échoue, l'entraînement n'est pas lancé.
- **Parallélisation** : les composants indépendants (ex: training et top-k qui dépendent tous deux du preprocessing) peuvent s'exécuter en parallèle.
- **Traçabilité** : chaque exécution est loguée avec ses métriques (accuracy, silhouette score, etc.). On peut comparer les runs.
- **Artefacts versionnés** : les datasets, modèles et métriques sont sauvegardés comme artefacts Kubeflow.

#### Correctifs appliqués

| Problème | Correctif |
|----------|-----------|
| Base image `ecommerce-kfp:latest` inexistante | Changée pour `datamining-ml-training:latest` (image Docker réelle) |
| Composant LLM utilisait OpenAI/Anthropic | Migré vers DeepSeek/Groq avec httpx |

#### ⚠️ Ce qui manque

- **Jamais exécuté** : le pipeline est codé mais jamais soumis à Kubeflow (pas de cluster Kubernetes actif).
- **YAML compilé manquant** : le fichier `pipeline.yaml` compilé n'existe pas.
- **CI/CD absent** : pas de workflow GitHub Actions.
- **Fichiers obsolètes** : `components/scraping_component.py` et `preprocessing_component.py` sont des doublons non utilisés.

---

### 2.4 Dashboard BI — Streamlit (80%)

#### Implémentation

**Fichier :** `src/dashboard/app.py`

**Fonctionnalités :**
| Feature | Description | Avantage |
|---------|-------------|----------|
| **KPIs** | Total produits, prix moyen, note moyenne, stock | Vue d'ensemble instantanée de la base produits |
| **Distribution des prix** | Histogramme Plotly interactif | Identifier la gamme de prix dominante |
| **Top catégories** | Bar chart des catégories les plus représentées | Visualiser la composition du catalogue |
| **Nuage de points** | Prix vs Rating (taille = reviews count) | Repérer les outliers : produits chers mal notés |
| **Tableau Top-K** | Top 10 produits avec score, filtres | Sélection rapide des meilleurs produits |
| **Filtres** | Par catégorie, tranche de prix | Analyse ciblée par segment |
| **Mode démo** | Données sample incluses | Fonctionne même sans scraping |

**✅ Avantages du dashboard :**
- **Prise en main immédiate** : accessible via navigateur à http://localhost:8501. Pas besoin de compétences techniques pour visualiser les données.
- **Interactif** : les graphiques Plotly sont zoomables, les filtres permettent de segmenter l'analyse. Un commercial peut filtrer par catégorie "Tshirts" et voir le Top-K.
- **Mode démo** : le dashboard est fonctionnel même sans base de données. Les données sample permettent de tester l'interface.
- **Léger** : image Docker de seulement 1.5 GB (contre 3.7 GB pour ML Training).

#### ⚠️ Ce qui manque

- **Données réelles** : utilise des données sample, pas les 74 produits scrapés.
- **Chatbot LLM** : le cahier des charges demande une interface conversationnelle.
- **Storytelling** : pas de narration visuelle des tendances.

---

### 2.5 LLM — DeepSeek & Groq (75%)

#### Implémentation

**Fichier :** `src/llm/wrapper.py`

**Méthodes :**
| Méthode | Description |
|---------|-------------|
| `complete(prompt, model, provider)` | Appel à l'API DeepSeek ou Groq avec fallback automatique |
| `summarize(text, max_tokens)` | Résumé automatique d'un texte long |
| `extract_entities(text, schema)` | Extraction d'informations structurées en JSON |

**Fonctionnement du fallback :**
1. Si `provider="auto"` et clé DeepSeek disponible → DeepSeek
2. Si `provider="auto"` et clé DeepSeek absente mais Groq disponible → Groq
3. Si aucune clé → erreur explicite

**✅ Avantages du wrapper LLM :**
- **Zéro dépendance lourde** : utilise `httpx` (déjà dans requirements-base.txt) au lieu de `openai` ou `anthropic` (pas besoin d'installer 200MB de SDK).
- **Auto-fallback** : si DeepSeek est down ou non configuré, Groq prend le relais automatiquement. Pas d'interruption de service.
- **Extraction structurée** : la méthode `extract_entities()` retourne du JSON directement exploitable par le dashboard ou la base de données.
- **Gratuit possible** : Groq offre un tier gratuit avec Mixtral 8x7B. Le projet peut fonctionner sans abonnement payant.

**Intégrations :**
- **MCP Server** : outil `generate_summary` utilise LLMWrapper
- **Pipeline KFP** : composant `generate_llm_summary_kfp` utilise httpx avec DeepSeek/Groq

**Ce qui a été retiré :**
- OpenAI et Anthropic retirés de tous les fichiers : wrapper, config, docker-compose, requirements, pipeline KFP.

#### ⚠️ Ce qui manque

- **Analyse concurrentielle** : pas de comparaison automatique entre produits concurrents.
- **Génération de rapports** : pas de "5 produits émergents cette semaine".
- **Chatbot** : pas d'interface conversationnelle dans le dashboard.
- **Prompt Engineering** : pas de Chain of Thought optimisé.

---

### 2.6 Serveur MCP — Model Context Protocol (70%)

#### Implémentation

**Fichier :** `src/mcp/server.py`

**Endpoints exposés :**
| Endpoint | Méthode | Description | Utilité |
|----------|---------|-------------|---------|
| `/health` | GET | Vérification du service | Monitoring |
| `/ready` | GET | Vérification + auth | Health check Kubernetes |
| `/.well-known/mcp` | GET | Capacités MCP | Découverte par clients MCP |
| `/tools` | GET | Liste des outils | Découverte par LLMs |
| `/tools/scrape_shopify` | POST | Scraper Shopify | Intégration LLM → scraping |
| `/tools/scrape_woocommerce` | POST | Scraper WooCommerce | Intégration LLM → scraping |
| `/tools/analyze_top_k` | POST | Analyse Top-K | Scoring automatique |
| `/tools/generate_summary` | POST | Résumé LLM | Synthèse automatique |
| `/resources` | GET | Ressources MCP | Données sample |
| `/resources/data://products/sample` | GET | Produits sample | Test rapide |

**✅ Avantages du serveur MCP :**
- **Standard ouvert** : le serveur implémente le protocole MCP d'Anthropic (`.well-known/mcp`, outils, ressources). Compatible avec les clients MCP (Claude Desktop, etc.).
- **5 outils utilitaires** : un LLM externe (Claude, DeepSeek) peut utiliser ces outils pour scraper, analyser et résumer automatiquement.
- **Authentification** : API key obligatoire pour les endpoints sensibles. Empêche les accès non autorisés.
- **Architecture REST** : chaque outil est un endpoint POST avec son propre schéma d'entrée (inputSchema). Facile à documenter et à tester.

#### ⚠️ Ce qui manque

- **Rapport MCP** : le cahier des charges demande une réflexion écrite sur le protocole MCP. Aucun document produit.
- **Permissions fines** : une seule API key pour tous les outils. Pas de distinction admin/user.
- **MCP Host** : le dashboard Streamlit n'utilise pas le client MCP.

---

### 2.7 Scheduler (75%)

#### Implémentation

**Fichier :** `src/scheduler/main.py`

**Jobs programmés :**
| Job | Déclencheur | Description |
|-----|-------------|-------------|
| **Daily scraping** | Tous les jours à 3h du matin | Scrape les boutiques configurées |
| **ML retraining** | Dimanche à 4h | Ré-entraîne les modèles ML |
| **Health check** | Toutes les 5 minutes | Vérifie PostgreSQL + Redis |

**✅ Avantages du scheduler :**
- **Automatisation complète** : une fois configuré, le système scrape, analyse et retraîne sans intervention humaine.
- **Horaires décalés** : le scraping à 3h du matin évite de surcharger les serveurs cibles pendant les heures de pointe.
- **Health check proactif** : détection précoce des pannes (base de données inaccessible, Redis down).

**Problèmes corrigés :**
- Import circulaire vers `src.__main__` → remplacé par `_ScheduledEngine` local avec lazy-init.
- `PostgreSQLStorage` init corrigé.

#### ⚠️ Ce qui manque

- **Profil production** : pas lancé par défaut (profil `production` dans docker-compose).
- **ML retrain** : marqué `TODO` dans le code.

---

### 2.8 Monitoring / Prometheus (70%)

#### Implémentation

**Fichier :** `src/monitoring/prometheus_exporter.py`

**Métriques exposées :**
| Métrique | Type | Description |
|----------|------|-------------|
| `ecommerce_scrape_requests_total` | Counter | Nombre total de requêtes de scraping |
| `ecommerce_scrape_duration_seconds` | Histogram | Durée des opérations de scraping |
| `ecommerce_agent_tasks_total` | Counter | Tâches traitées par les agents |
| `ecommerce_products_stored_total` | Counter | Produits stockés en base |
| `ecommerce_llm_requests_total` | Counter | Requêtes LLM effectuées |
| `ecommerce_memory_usage_bytes` | Gauge | Mémoire utilisée par le collecteur |

**✅ Avantages du monitoring :**
- **Visibilité temps réel** : chaque scraping, chaque tâche agent, chaque requête LLM est comptabilisée.
- **Histogramme de performance** : `scrape_duration_seconds` avec buckets (0.1s à 60s) permet d'identifier les lenteurs.
- **Format standard Prometheus** : compatible avec Grafana pour des dashboards de visualisation.

#### ⚠️ Ce qui manque

- **Service pas lancé** : profil `monitoring` dans docker-compose.
- **Dashboard Grafana** : pas de dashboard pré-construit pour visualiser les métriques.

---

### 2.9 CI/CD (0%)

#### Non implémenté

- Pas de workflow GitHub Actions.
- Pas de tests automatiques sur push/PR.
- Pas de déploiement automatique.

**✅ Opportunités si implémenté :**
- **Tests automatiques** : `pytest tests/` à chaque push pour détecter les régressions.
- **Build Docker automatique** : reconstruction des images à chaque commit sur `main`.
- **Déploiement continu** : push vers un registre Docker (Docker Hub) automatiquement.

---


---

## 4. Priorité des tâches restantes

### 🔴 Urgent (indispensable avant présentation)

| # | Tâche | Module | Effort | Pourquoi c'est important |
|---|-------|--------|--------|--------------------------|

| 2 | **Exécuter ML sur les 74 produits** | Data Analysis | 2h | Les algorithmes sont codés mais jamais exécutés. Il faut des résultats concrets à présenter. |
| 3 | **Configurer PostgreSQL** | Infra | 15min | Remplir les mots de passe dans `.env` pour que le stockage fonctionne. |
| 4 | **Connecter dashboard aux données** | Dashboard | 1h | Charger `products.json` dans le dashboard au lieu des données sample. |
| 5 | **Rapport business** | Docs | 3h | Interpréter les résultats ML avec des recommandations business concrètes. |

### 🟡 Important

| # | Tâche | Module | Effort |
|---|-------|--------|--------|
| 6 | Exécuter Kubeflow sur Minikube | Pipelines | 3h |
| 7 | Crawling multi-pages (catégories, sous-pages) | Scraping | 2h |
| 8 | Scraper plus de produits (≥500) | Scraping | 2h |
| 9 | Analyse concurrentielle LLM | LLM | 2h |
| 10 | Tests ML sur les données réelles | Tests | 2h |

### 🟢 Optionnel

| # | Tâche | Module | Effort |
|---|-------|--------|--------|
| 11 | Chatbot LLM dans le dashboard | Dashboard | 3h |
| 12 | Rapport MCP (réflexion architecture responsable) | Docs | 2h |
| 13 | Dashboard Grafana pour Prometheus | Monitoring | 2h |
| 14 | CI/CD GitHub Actions | CI/CD | 2h |
| 15 | Compiler pipeline.yaml Kubeflow | Pipelines | 30min |
| 16 | Nettoyer composants KFP obsolètes | Pipelines | 30min |
| 17 | Générer 2000+ produits synthétiques | Data | 1h |

---

## 5. Services Docker — Statut actuel

```
ecommerce-dashboard     Up (healthy)     ✅ http://localhost:8501
ecommerce-scraper       Up (healthy)     ✅ 74 produits scrapés
ecommerce-mcp-server    Up (healthy)     ✅ http://localhost:8000
ecommerce-ml-training   Up (running)     ✅ ML modules chargés
ecommerce-postgres      Up (healthy)     ✅ PostgreSQL
ecommerce-redis         Up (healthy)     ✅ Redis
```

---

## 6. Statistiques du projet

| Métrique | Valeur |
|----------|--------|
| Lignes de code | ~4500+ |
| Fichiers Python | ~35 |
| Tests unitaires | 660 lignes (A2A protocol) |
| Produits scrapés réels | 74 (WooCommerce) |
| Images Docker | 6 services |
| Taille totale des images | ~10 GB |
| Tâches restantes | 17 (5 urgentes, 5 importantes, 7 optionnelles) |