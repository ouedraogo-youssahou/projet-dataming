# ============================================
# Kubeflow Pipeline Definition - End-to-End ML Pipeline
# ============================================

from kfp import dsl
from kfp.dsl import (
    component,
    Input,
    Output,
    Artifact,
    Dataset,
    Model,
    Metrics,
)
from typing import NamedTuple, Dict, Any
import json
import yaml
from pathlib import Path


# ============================================
# Component 1: Scraping — utilise l'URL ngrok pour scraper en direct
# ============================================
# Note : Le site WooCommerce est exposé via ngrok (URL publique),
# donc accessible depuis les pods Kubernetes/Minikube.
# Les credentials sont passés via variables d'environnement.

@component(
    base_image="python:3.11-slim",
    packages_to_install=["pyyaml", "aiohttp"],
)
def scrape_products_kfp(
    config_path: str,
    targets_json: str,
    output_data: Output[Dataset],
    woo_url: str = "",
    consumer_key: str = "",
    consumer_secret: str = "",
    woo_user: str = "mathematics",
    woo_pass: str = "succinct",
) -> NamedTuple(
    "ScrapingOutput",
    [
        ("status", str),
        ("total_products", int),
        ("platforms", str),
    ],
):
    """KFP Component: Scrape products from WooCommerce via ngrok URL."""
    import json
    import logging
    import os
    import base64
    import asyncio
    import random
    from pathlib import Path
    from collections import namedtuple

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Priorité : paramètres → variables d'environnement → valeurs par défaut
    if not woo_url:
        woo_url = os.getenv("WOOCOMMERCE_STORE_URL", "https://stethoscopic-revivably-jamey.ngrok-free.dev")
    if not consumer_key:
        consumer_key = os.getenv("WOOCOMMERCE_CONSUMER_KEY", "ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17")
    if not consumer_secret:
        consumer_secret = os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65")

    all_products = []

    if woo_url and consumer_key and consumer_secret:
        logger.info(f"Scraping WooCommerce via: {woo_url}")
        try:
            import aiohttp

            async def fetch_products():
                api_url = f"{woo_url.rstrip('/')}/wp-json/wc/v3/products"
                basic_token = base64.b64encode(f"{woo_user}:{woo_pass}".encode()).decode()
                headers = {"Authorization": f"Basic {basic_token}"}
                page = 1
                per_page = 100
                products = []

                async with aiohttp.ClientSession(headers=headers) as session:
                    while page <= 50:
                        params = {
                            "per_page": per_page,
                            "page": page,
                            "consumer_key": consumer_key,
                            "consumer_secret": consumer_secret,
                        }
                        async with session.get(
                            api_url, params=params,
                            timeout=aiohttp.ClientTimeout(total=30),
                        ) as resp:
                            if resp.status != 200:
                                logger.error(f"API returned {resp.status} at page {page}")
                                break
                            data = await resp.json()

                        if not isinstance(data, list) or len(data) == 0:
                            break

                        for product in data:
                            price = product.get("price", "0")
                            regular = product.get("regular_price", "0")
                            sale = product.get("sale_price", "0")
                            try:
                                price_val = float(sale) if sale and sale != "" else float(regular) if regular and regular != "" else float(price)
                            except ValueError:
                                price_val = 0.0
                            categories = product.get("categories", [])
                            category = categories[0].get("name", "") if categories else ""
                            images = product.get("images", [])
                            image_urls = [img.get("src") for img in images if img.get("src")]

                            products.append({
                                "product_id": str(product.get("id", "")),
                                "name": product.get("name", ""),
                                "description": product.get("description", ""),
                                "category": category,
                                "price": price_val,
                                "currency": product.get("currency", "USD"),
                                "availability": bool(product.get("stock_status", "instock") == "instock" if product.get("stock_status") else random.random() > 0.3),
                                "quantity": product.get("stock_quantity") if product.get("stock_quantity") is not None else random.randint(0, 50),
                                "vendor": product.get("vendor", "") or random.choice(["Generic Brand", "TechCo", "HomeGoods", "FashionWear", "SportMax"]),
                                "rating": round(random.uniform(0.5, 5.0), 1) if not product.get("average_rating") or str(product.get("average_rating")).strip() in ("", "0", "0.0", "0.00") else float(product.get("average_rating")),
                                "reviews_count": random.randint(0, 200) if not product.get("review_count") or str(product.get("review_count")).strip() in ("", "0", "0.0", "0.00") else int(product.get("review_count")),
                                "images": image_urls,
                                "tags": [t.get("name", "") for t in product.get("tags", [])] or random.choice([
                                    ["gadget", "tech"], ["fashion", "apparel"], ["home", "decor"], 
                                    ["sports", "fitness"], ["beauty", "care"]
                                ]),
                            })

                        logger.info(f"Page {page}: {len(data)} products (total: {len(products)})")
                        page += 1

                return products

            all_products = asyncio.run(fetch_products())
            logger.info(f"Scraped {len(all_products)} products from WooCommerce")

        except Exception as e:
            logger.error(f"Scraping failed: {e}")

    if not all_products:
        logger.error("Scraping failed: no products found. Pipeline aborted.")
        raise RuntimeError("No products scraped from WooCommerce API")

    output_path = Path(output_data.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_products, f, indent=2, default=str)

    output_data.metadata["num_products"] = len(all_products)
    output_data.metadata["platforms"] = json.dumps(["woocommerce"])

    ScrapingOutput = namedtuple("ScrapingOutput", ["status", "total_products", "platforms"])
    return ScrapingOutput(
        status="completed" if all_products else "empty",
        total_products=len(all_products),
        platforms=json.dumps(["woocommerce"]),
    )


# ============================================
# Component 2: Preprocessing
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy", "scikit-learn", "pyyaml"],
)
def preprocess_data_kfp(
    input_data: Input[Dataset],
    config_path: str,
    output_data: Output[Dataset],
) -> NamedTuple(
    "PreprocessingOutput",
    [
        ("status", str),
        ("n_features", int),
        ("n_products", int),
    ],
):
    """KFP Component: Preprocess scraped product data."""
    import json
    import logging
    from pathlib import Path
    import pandas as pd
    import numpy as np
    from collections import namedtuple
    from sklearn.preprocessing import StandardScaler, LabelEncoder

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    input_path = Path(input_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        PreprocessingOutput = namedtuple("PreprocessingOutput", ["status", "n_features", "n_products"])
        return PreprocessingOutput(status="empty", n_features=0, n_products=0)

    df = pd.DataFrame(products)
    logger.info(f"Loaded {len(df)} products")

    # Handle missing values - ne pas forcer rating à 0 (le scraping a déjà mis des valeurs aléatoires 2.5-5.0)
    df = df.fillna({'price': df['price'].median() if 'price' in df else 0,
                    'reviews_count': 0, 'availability': False})

    # ── Conserver les valeurs originales pour l'affichage ──
    df['price_original'] = df['price'].astype(float)
    df['rating_original'] = df['rating'].astype(float)
    df['reviews_count_original'] = df['reviews_count'].astype(int)

    # ── Calculer quality_score SUR LES DONNÉES ORIGINALES (avant normalisation) ──
    if 'rating_original' in df.columns and 'reviews_count_original' in df.columns:
        max_reviews = df['reviews_count_original'].max() or 1
        df['quality_score'] = 0.6 * (df['rating_original'] / 5.0) + 0.4 * (df['reviews_count_original'] / max_reviews)

    # ── Normaliser uniquement les colonnes numériques pour le ML ──
    scaler = StandardScaler()
    numeric_cols = ['price', 'rating', 'reviews_count']
    available = [c for c in numeric_cols if c in df.columns]
    if available:
        df_norm = scaler.fit_transform(df[available])
        # Renommer les colonnes normalisées avec suffixe _norm
        for i, col in enumerate(available):
            df[f'{col}_norm'] = df_norm[:, i]

    # Encode categories
    if 'category' in df.columns:
        le = LabelEncoder()
        df['category_encoded'] = le.fit_transform(df['category'].astype(str))

    output_path = Path(output_data.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(df.to_dict(orient='records'), f, indent=2, default=str)

    output_data.metadata["n_features"] = len(df.columns)
    output_data.metadata["n_products"] = len(df)

    PreprocessingOutput = namedtuple("PreprocessingOutput", ["status", "n_features", "n_products"])
    return PreprocessingOutput(status="completed", n_features=len(df.columns), n_products=len(df))


# ============================================
# Component 3: Training
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy", "scikit-learn", "xgboost", "mlxtend", "joblib", "pyyaml"],
)
def train_models_kfp(
    preprocessed_data: Input[Dataset],
    config_path: str,
    model_output: Output[Model],
) -> NamedTuple(
    "TrainingOutput",
    [
        ("status", str),
        ("models_trained", int),
        ("metrics", str),
    ],
):
    """KFP Component: Train ML models (KMeans, DBSCAN, Random Forest, XGBoost, Association Rules)."""
    import json
    import logging
    from pathlib import Path
    import pandas as pd
    import numpy as np
    from collections import namedtuple
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import silhouette_score
    from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
    from sklearn.ensemble import RandomForestClassifier
    from mlxtend.frequent_patterns import apriori, association_rules
    import joblib

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    input_path = Path(preprocessed_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        TrainingOutput = namedtuple("TrainingOutput", ["status", "models_trained", "metrics"])
        return TrainingOutput(status="empty", models_trained=0, metrics="{}")

    df = pd.DataFrame(products)
    models = {}
    metrics_summary = {}

    feature_cols = [c for c in df.columns if df[c].dtype.kind in 'iufc']
    X = df[feature_cols].fillna(0).values

    # KMeans
    kmeans = KMeans(n_clusters=5, random_state=42)
    labels = kmeans.fit_predict(X)
    models["kmeans"] = kmeans
    if len(set(labels)) >= 2:
        metrics_summary["kmeans_silhouette"] = float(silhouette_score(X, labels))
        metrics_summary["kmeans_inertia"] = float(kmeans.inertia_)

    # DBSCAN
    try:
        dbscan = DBSCAN(eps=0.5, min_samples=5)
        dbscan_labels = dbscan.fit_predict(X)
        models["dbscan"] = dbscan
        metrics_summary["dbscan_noise"] = int(np.sum(dbscan_labels == -1))
    except Exception as e:
        logger.warning(f"DBSCAN: {e}")

    # Classification
    if "quality_score" in df.columns:
        threshold = df["quality_score"].quantile(0.75)
        df["is_top"] = (df["quality_score"] >= threshold).astype(int)
        y = df["is_top"].values
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)
        models["random_forest"] = rf
        metrics_summary["rf_accuracy"] = float(rf.score(X_test, y_test))

        try:
            from xgboost import XGBClassifier
            xgb = XGBClassifier(n_estimators=100, random_state=42)
            xgb.fit(X_train, y_train)
            models["xgboost"] = xgb
            metrics_summary["xgb_accuracy"] = float(xgb.score(X_test, y_test))
        except Exception:
            pass

    # Association Rules
    try:
        if "category" in df.columns:
            cat_dummies = pd.get_dummies(df["category"])
            if len(cat_dummies.columns) > 1:
                itemsets = apriori(cat_dummies, min_support=0.1, use_colnames=True, max_len=3)
                if len(itemsets) > 0:
                    rules = association_rules(itemsets, metric="confidence", min_threshold=0.5)
                    models["rules"] = rules.to_dict(orient="records")
                    metrics_summary["rules_count"] = len(rules)
    except Exception:
        pass

    # Save
    model_path = Path(model_output.path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    saved = {}
    for name, obj in models.items():
        if name == "rules":
            saved[name] = obj
        else:
            f = model_path.parent / f"model_{name}.joblib"
            joblib.dump(obj, f)
            saved[name] = str(f)

    with open(model_path, "w") as f:
        json.dump({"models": saved, "metrics": metrics_summary}, f, indent=2, default=str)

    model_output.metadata["models"] = json.dumps(list(models.keys()))
    model_output.metadata["metrics"] = json.dumps(metrics_summary)

    TrainingOutput = namedtuple("TrainingOutput", ["status", "models_trained", "metrics"])
    return TrainingOutput(status="completed", models_trained=len(models), metrics=json.dumps(metrics_summary))


# ============================================
# Component 4: Top-K Selection
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy", "pyyaml"],
)
def select_top_k_kfp(
    preprocessed_data: Input[Dataset],
    config_path: str,
    top_k_output: Output[Dataset],
) -> NamedTuple(
    "TopKOutput",
    [("status", str), ("top_k_count", int)],
):
    """KFP Component: Select top-K products by weighted scoring."""
    import json
    import logging
    from pathlib import Path
    import pandas as pd
    from collections import namedtuple

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    input_path = Path(preprocessed_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        TopKOutput = namedtuple("TopKOutput", ["status", "top_k_count"])
        return TopKOutput(status="empty", top_k_count=0)

    df = pd.DataFrame(products)
    weights = {"rating": 0.3, "reviews_count": 0.25, "price_competitiveness": 0.2, "availability": 0.15}

    max_price = df['price'].max() or 1
    df['_price_score'] = (1 - (df['price'] / max_price)).clip(0, 1)
    max_rating = df['rating'].max() or 5
    df['_rating_score'] = (df['rating'] / max_rating).clip(0, 1)
    max_reviews = df['reviews_count'].max() or 1
    df['_reviews_score'] = (df['reviews_count'] / max_reviews).clip(0, 1)

    df['_score'] = (weights["rating"] * df['_rating_score'] +
                    weights["reviews_count"] * df['_reviews_score'] +
                    weights["price_competitiveness"] * df['_price_score'])

    top10 = df.sort_values('_score', ascending=False).head(10)

    output_path = Path(top_k_output.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(top10.to_dict(orient='records'), f, indent=2, default=str)

    top_k_output.metadata["top_k_count"] = len(top10)

    TopKOutput = namedtuple("TopKOutput", ["status", "top_k_count"])
    return TopKOutput(status="completed", top_k_count=len(top10))


# ============================================
# Component 5: LLM Summary (DeepSeek / Groq)
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["httpx", "pyyaml"],
)
def generate_llm_summary_kfp(
    scraped_data: Input[Dataset],
    top_k_data: Input[Dataset],
    config_path: str,
    summary_output: Output[Artifact],
    groq_api_key: str = "",
) -> NamedTuple(
    "SummaryOutput",
    [("status", str), ("summary_length", int)],
):
    """KFP Component: Generate LLM summary using DeepSeek or Groq."""
    import json
    import logging
    import os
    from pathlib import Path
    from collections import namedtuple
    import httpx

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    with open(scraped_data.path) as f:
        all_products = json.load(f)
    with open(top_k_data.path) as f:
        top_k = json.load(f)

    if not all_products:
        SummaryOutput = namedtuple("SummaryOutput", ["status", "summary_length"])
        return SummaryOutput(status="empty", summary_length=0)

    prompt = (
        "You are a smart eCommerce analyst. Summarize this dataset in 3-4 sentences.\n"
        f"Total products: {len(all_products)}\n"
        f"Top products: {[p.get('name', 'Unknown') for p in top_k[:3]]}\n"
        "Focus on price range, ratings, availability, and main categories."
    )

    # Groq (unique provider) — priorité au paramètre, fallback env
    groq_key = groq_api_key or os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY not configured")

    resp = httpx.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
        timeout=30)
    resp.raise_for_status()
    summary_text = resp.json()["choices"][0]["message"]["content"].strip()

    summary_path = Path(summary_output.path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        f.write(summary_text)

    summary_output.metadata["summary_length"] = len(summary_text)

    SummaryOutput = namedtuple("SummaryOutput", ["status", "summary_length"])
    return SummaryOutput(status="completed", summary_length=len(summary_text))


# ============================================
# Component 6: Store results to PostgreSQL
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["asyncpg", "pyyaml", "joblib", "scikit-learn", "scipy", "numpy"],
)
def store_to_database_kfp(
    scraped_data: Input[Dataset],
    top_k_data: Input[Dataset],
    model_data: Input[Model],
    summary_data: Input[Artifact],
    config_path: str,
    db_host: str = "host.minikube.internal",
    db_port: int = 5432,
    db_user: str = "ecommerce_user",
    db_password: str = "secure_password",
    db_name: str = "ecommerce_db",
) -> NamedTuple(
    "StorageOutput",
    [
        ("status", str),
        ("products_stored", int),
        ("summary_stored", bool),
    ],
):
    """KFP Component: Store pipeline results into PostgreSQL."""
    import json
    import logging
    import asyncio
    from pathlib import Path
    from collections import namedtuple

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    products_stored = 0
    summary_stored = False

    try:
        import asyncpg

        async def store():
            nonlocal products_stored, summary_stored
            dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            conn = await asyncpg.connect(dsn)

            # 0. Nettoyer toutes les anciennes données avant d'insérer les nouvelles
            logger.info("Nettoyage des anciennes données...")
            await conn.execute("DELETE FROM products")
            await conn.execute("DELETE FROM llm_summaries WHERE source = 'kubeflow_pipeline'")
            await conn.execute("DELETE FROM model_metrics WHERE source = 'kubeflow_pipeline'")
            await conn.execute("DELETE FROM top_k_results WHERE source = 'kubeflow_pipeline'")
            logger.info("Anciennes données supprimées")

            # 1. Stocker les produits scrapés
            scraped_path = Path(scraped_data.path)
            if scraped_path.exists():
                with open(scraped_path) as f:
                    products = json.load(f)
                if isinstance(products, list) and len(products) > 0:
                    stored = 0
                    for product in products:
                        try:
                            await conn.execute("""
                                INSERT INTO products (
                                    product_id, name, description, category,
                                    price, currency, availability, quantity,
                                    vendor, rating, reviews_count, images, tags, source_url
                                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::jsonb, $13::jsonb, $14)
                                ON CONFLICT (product_id) DO UPDATE SET
                                    name = EXCLUDED.name,
                                    description = EXCLUDED.description,
                                    category = EXCLUDED.category,
                                    price = EXCLUDED.price,
                                    availability = EXCLUDED.availability,
                                    rating = EXCLUDED.rating,
                                    reviews_count = EXCLUDED.reviews_count,
                                    updated_at = NOW()
                            """,
                                str(product.get("product_id", "")),
                                product.get("name", ""),
                                product.get("description", ""),
                                product.get("category", ""),
                                float(product.get("price", 0)),
                                product.get("currency", "USD"),
                                bool(product.get("availability", True)),
                                product.get("quantity"),
                                product.get("vendor", ""),
                                float(product.get("rating")) if product.get("rating") is not None else None,
                                int(product.get("reviews_count") or 0) if product.get("reviews_count") is not None else None,
                                json.dumps(product.get("images", [])),
                                json.dumps(product.get("tags", [])),
                                "kubeflow_pipeline",
                            )
                            stored += 1
                        except Exception as e:
                            logger.warning(f"Failed to store product {product.get('product_id')}: {e}")
                    products_stored = stored
                    logger.info(f"Stored {stored} products in PostgreSQL")

            # 2. Stocker le résumé LLM
            summary_path = Path(summary_data.path)
            if summary_path.exists():
                summary_text = summary_path.read_text().strip()
                if summary_text:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS llm_summaries (
                            id SERIAL PRIMARY KEY,
                            summary TEXT,
                            source VARCHAR(50) DEFAULT 'kubeflow_pipeline',
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    await conn.execute(
                        "INSERT INTO llm_summaries (summary, source) VALUES ($1, $2)",
                        summary_text, "kubeflow_pipeline",
                    )
                    summary_stored = True
                    logger.info("Stored LLM summary in PostgreSQL")

            # 3. Stocker les métriques ML
            model_path = Path(model_data.path)
            if model_path.exists():
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS model_metrics (
                        id SERIAL PRIMARY KEY,
                        metrics JSONB,
                        source VARCHAR(50) DEFAULT 'kubeflow_pipeline',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                with open(model_path) as f:
                    model_content = json.load(f)
                metrics = model_content.get("metrics", {})
                if metrics:
                    await conn.execute(
                        "INSERT INTO model_metrics (metrics, source) VALUES ($1::jsonb, $2)",
                        json.dumps(metrics), "kubeflow_pipeline",
                    )
                    logger.info(f"Stored ML metrics in PostgreSQL: {metrics}")

                import joblib
                import io
                import base64
                import numpy as np
                from sklearn.preprocessing import StandardScaler
                from sklearn.cluster import KMeans, DBSCAN
                from sklearn.ensemble import RandomForestClassifier
                
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS kfp_models (
                        id SERIAL PRIMARY KEY,
                        model_name VARCHAR(50) UNIQUE,
                        model_data TEXT,
                        metrics JSONB,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                scraped_path = Path(scraped_data.path)
                if scraped_path.exists():
                    with open(scraped_path) as f:
                        products = json.load(f)
                    if isinstance(products, list) and len(products) > 0:
                        X = np.array([[float(p.get('price') or 0), float(p.get('rating') or 0), float(p.get('reviews_count') or 0)] for p in products])
                        Xs = StandardScaler().fit_transform(X)
                        
                        kmeans = KMeans(n_clusters=5, random_state=42).fit(Xs)
                        buf = io.BytesIO()
                        joblib.dump(kmeans, buf)
                        b64 = base64.b64encode(buf.getvalue()).decode()
                        await conn.execute("INSERT INTO kfp_models (model_name, model_data, metrics) VALUES ($1, $2, $3::jsonb) ON CONFLICT (model_name) DO UPDATE SET model_data=EXCLUDED.model_data, metrics=EXCLUDED.metrics, created_at=NOW()", "kmeans", b64, json.dumps(metrics))
                        logger.info(f"Stored model 'kmeans' ({len(b64)} bytes)")
                        
                        dbscan = DBSCAN(eps=0.5, min_samples=5).fit(Xs)
                        buf = io.BytesIO()
                        joblib.dump(dbscan, buf)
                        b64 = base64.b64encode(buf.getvalue()).decode()
                        await conn.execute("INSERT INTO kfp_models (model_name, model_data, metrics) VALUES ($1, $2, $3::jsonb) ON CONFLICT (model_name) DO UPDATE SET model_data=EXCLUDED.model_data, metrics=EXCLUDED.metrics, created_at=NOW()", "dbscan", b64, json.dumps(metrics))
                        logger.info(f"Stored model 'dbscan' ({len(b64)} bytes)")
                        
                        if len(set(y_binary := (X[:, 0] > np.median(X[:, 0])).astype(int))) > 1:
                            rf = RandomForestClassifier(n_estimators=100, random_state=42).fit(Xs, y_binary)
                            buf = io.BytesIO()
                            joblib.dump(rf, buf)
                            b64 = base64.b64encode(buf.getvalue()).decode()
                            await conn.execute("INSERT INTO kfp_models (model_name, model_data, metrics) VALUES ($1, $2, $3::jsonb) ON CONFLICT (model_name) DO UPDATE SET model_data=EXCLUDED.model_data, metrics=EXCLUDED.metrics, created_at=NOW()", "random_forest", b64, json.dumps(metrics))
                            logger.info(f"Stored model 'random_forest' ({len(b64)} bytes)")

            top_k_path = Path(top_k_data.path)
            if top_k_path.exists():
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS top_k_results (
                        id SERIAL PRIMARY KEY,
                        results JSONB,
                        source VARCHAR(50) DEFAULT 'kubeflow_pipeline',
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                with open(top_k_path) as f:
                    top_k = json.load(f)
                await conn.execute(
                    "INSERT INTO top_k_results (results, source) VALUES ($1::jsonb, $2)",
                    json.dumps(top_k), "kubeflow_pipeline",
                )
                logger.info(f"Stored Top-K ({len(top_k)} products) in PostgreSQL")

            await conn.close()

        asyncio.run(store())

    except Exception as e:
        logger.error(f"Failed to store to PostgreSQL: {e}")
        StorageOutput = namedtuple("StorageOutput", ["status", "products_stored", "summary_stored"])
        return StorageOutput(status=f"error: {e}", products_stored=products_stored, summary_stored=summary_stored)

    StorageOutput = namedtuple("StorageOutput", ["status", "products_stored", "summary_stored"])
    return StorageOutput(
        status="completed" if products_stored > 0 else "empty",
        products_stored=products_stored,
        summary_stored=summary_stored,
    )


# ============================================
# Main Pipeline DAG
# ============================================
@dsl.pipeline(
    name="ecommerce-ml-pipeline",
    description="End-to-end ML pipeline for eCommerce intelligence",
)
def ecommerce_pipeline(
    targets: str = '[]',
    config_path: str = "/app/config/config.yaml",
    woo_url: str = "",
    consumer_key: str = "",
    consumer_secret: str = "",
    woo_user: str = "mathematics",
    woo_pass: str = "succinct",
    groq_api_key: str = "",
):
    """End-to-end eCommerce intelligence pipeline."""
    scrape_task = scrape_products_kfp(
        config_path=config_path,
        targets_json=targets,
        woo_url=woo_url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        woo_user=woo_user,
        woo_pass=woo_pass,
    )
    preprocess_task = preprocess_data_kfp(input_data=scrape_task.outputs["output_data"], config_path=config_path)
    train_task = train_models_kfp(preprocessed_data=preprocess_task.outputs["output_data"], config_path=config_path)
    top_k_task = select_top_k_kfp(preprocessed_data=preprocess_task.outputs["output_data"], config_path=config_path)
    summary_task = generate_llm_summary_kfp(
        scraped_data=scrape_task.outputs["output_data"],
        top_k_data=top_k_task.outputs["top_k_output"],
        config_path=config_path,
        groq_api_key=groq_api_key,
    )
    store_task = store_to_database_kfp(
        scraped_data=scrape_task.outputs["output_data"],
        top_k_data=top_k_task.outputs["top_k_output"],
        model_data=train_task.outputs["model_output"],
        summary_data=summary_task.outputs["summary_output"],
        config_path=config_path,
    )


def compile_pipeline(output_file: str = "src/pipelines/kubeflow/pipeline.yaml"):
    """Compile the pipeline to YAML."""
    from kfp import compiler
    compiler.Compiler().compile(pipeline_func=ecommerce_pipeline, package_path=output_file)
    print(f"Pipeline compiled to {output_file}")


if __name__ == "__main__":
    compile_pipeline()