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
# Component 1: Scraping — utilise les données déjà scrapées (data/raw/products.json)
# ============================================
# Note : Le site WooCommerce famous-breath.localsite.io est un site LocalWP
# accessible uniquement depuis la machine hôte. Le scraping depuis les pods
# Kubernetes/Minikube ne fonctionne pas (DNS pointe vers IP publique).
# On utilise donc les 74 produits déjà scrapés.

@component(
    base_image="python:3.11-slim",
    packages_to_install=["pyyaml"],
)
def scrape_products_kfp(
    config_path: str,
    targets_json: str,
    output_data: Output[Dataset],
) -> NamedTuple(
    "ScrapingOutput",
    [
        ("status", str),
        ("total_products", int),
        ("platforms", str),
    ],
):
    """KFP Component: Charge les 74 produits déjà scrapés depuis data/raw/products.json."""
    import json
    import logging
    from pathlib import Path
    from collections import namedtuple

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    logger.info("Chargement des produits déjà scrapés...")

    # Chercher le fichier à plusieurs endroits possibles
    search_paths = [
        Path("/app/data/raw/products.json"),
        Path("/data/raw/products.json"),
        Path("data/raw/products.json"),
    ]

    all_products = []
    for sp in search_paths:
        if sp.exists():
            with open(sp) as f:
                all_products = json.load(f)
            logger.info(f"Fichier trouvé: {sp} — {len(all_products)} produits chargés")
            break

    if not all_products:
        # Fallback : 3 produits de démonstration
        logger.warning("Aucun fichier trouvé, utilisation des données de démo")
        all_products = [
            {"product_id": "1", "name": "Odomos Naturals Mosquito Repellent", "category": "Uncategorized", "price": 56.0, "rating": 0.0, "reviews_count": 0, "availability": True},
            {"product_id": "2", "name": "Priyagold Magic Cake Fruit (150 g)", "category": "Uncategorized", "price": 29.0, "rating": 0.0, "reviews_count": 0, "availability": True},
            {"product_id": "3", "name": "Patanjali Kesh Kanti Shikakai Hair Cleanser (200 ml)", "category": "Uncategorized", "price": 95.0, "rating": 0.0, "reviews_count": 0, "availability": True},
        ]

    # Sauvegarde
    output_path = Path(output_data.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_products, f, indent=2, default=str)

    output_data.metadata["num_products"] = len(all_products)
    output_data.metadata["platforms"] = json.dumps(["woocommerce"])

    from collections import namedtuple
    ScrapingOutput = namedtuple("ScrapingOutput", ["status", "total_products", "platforms"])
    return ScrapingOutput(
        status="completed",
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

    # Handle missing values
    df = df.fillna({'price': df['price'].median() if 'price' in df else 0,
                    'rating': 0, 'reviews_count': 0, 'availability': False})

    # Normalize numeric
    scaler = StandardScaler()
    numeric_cols = ['price', 'rating', 'reviews_count']
    available = [c for c in numeric_cols if c in df.columns]
    if available:
        df[available] = scaler.fit_transform(df[available])

    # Encode categories
    if 'category' in df.columns:
        le = LabelEncoder()
        df['category_encoded'] = le.fit_transform(df['category'].astype(str))

    # Quality score
    if 'rating' in df.columns and 'reviews_count' in df.columns:
        max_reviews = df['reviews_count'].max() or 1
        df['quality_score'] = 0.6 * (df['rating'] / 5.0) + 0.4 * (df['reviews_count'] / max_reviews)

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
) -> NamedTuple(
    "SummaryOutput",
    [("status", str), ("summary_length", int)],
):
    """KFP Component: Generate LLM summary using DeepSeek or Groq."""
    import json
    import logging
    from pathlib import Path
    from collections import namedtuple
    import yaml
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

    summary_text = None

    # DeepSeek
    deepseek_key = "sk-73e4d05b6a5848afa79614910d604f4f"
    try:
        resp = httpx.post("https://api.deepseek.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
            json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
            timeout=30)
        resp.raise_for_status()
        summary_text = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"DeepSeek failed: {e}")

    if not summary_text:
        summary_text = f"Dataset: {len(all_products)} products. Top picks: {[p.get('name','?') for p in top_k[:3]]}."

    summary_path = Path(summary_output.path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        f.write(summary_text)

    summary_output.metadata["summary_length"] = len(summary_text)

    SummaryOutput = namedtuple("SummaryOutput", ["status", "summary_length"])
    return SummaryOutput(status="completed" if summary_text else "fallback", summary_length=len(summary_text))


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
):
    """End-to-end eCommerce intelligence pipeline."""
    scrape_task = scrape_products_kfp(config_path=config_path, targets_json=targets)
    preprocess_task = preprocess_data_kfp(input_data=scrape_task.outputs["output_data"], config_path=config_path)
    train_task = train_models_kfp(preprocessed_data=preprocess_task.outputs["output_data"], config_path=config_path)
    top_k_task = select_top_k_kfp(preprocessed_data=preprocess_task.outputs["output_data"], config_path=config_path)
    summary_task = generate_llm_summary_kfp(
        scraped_data=scrape_task.outputs["output_data"],
        top_k_data=top_k_task.outputs["top_k_output"],
        config_path=config_path,
    )


def compile_pipeline(output_file: str = "src/pipelines/kubeflow/pipeline.yaml"):
    """Compile the pipeline to YAML."""
    from kfp import compiler
    compiler.Compiler().compile(pipeline_func=ecommerce_pipeline, package_path=output_file)
    print(f"Pipeline compiled to {output_file}")


if __name__ == "__main__":
    compile_pipeline()