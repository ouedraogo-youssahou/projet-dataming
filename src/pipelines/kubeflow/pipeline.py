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
# Component 1: Scraping
# ============================================
@component(
    base_image="datamining-ml-training:latest",
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
    """
    KFP Component: Scrape products from e-commerce platforms.
    """
    import json
    import logging
    import asyncio
    from pathlib import Path
    import yaml

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    targets = json.loads(targets_json) if targets_json else [
        {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
        {"platform": "woocommerce", "url": "https://example-woo.com"},
    ]

    logger.info(f"Scraping {len(targets)} targets")

    from src.__main__ import SmartECommerceIntelligence
    engine = SmartECommerceIntelligence(config)
    scrape_results = asyncio.run(engine.scrape_all(targets))

    all_products = []
    for r in scrape_results:
        if r.get("status") == "ok" and "data" in r:
            data = r["data"]
            if isinstance(data, list):
                all_products.extend(data)
            elif isinstance(data, dict):
                all_products.append(data)

    logger.info(f"Scraped {len(all_products)} products")

    output_path = Path(output_data.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_products, f, indent=2, default=str)

    platforms = list(set(r.get("platform") for r in scrape_results))
    output_data.metadata["num_products"] = len(all_products)
    output_data.metadata["platforms"] = json.dumps(platforms)

    from collections import namedtuple
    ScrapingOutput = namedtuple("ScrapingOutput", ["status", "total_products", "platforms"])
    return ScrapingOutput(
        status="completed",
        total_products=len(all_products),
        platforms=json.dumps(platforms),
    )


# ============================================
# Component 2: Preprocessing
# ============================================
@component(
    base_image="datamining-ml-training:latest",
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
    import yaml
    from sklearn.preprocessing import StandardScaler, LabelEncoder

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    preproc_cfg = config.get("components", {}).get("preprocessing", {})
    missing_threshold = preproc_cfg.get("missing_threshold", 0.3)
    do_normalize = preproc_cfg.get("normalize", True)

    input_path = Path(input_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        logger.warning("No products to preprocess")
        output_data.metadata["status"] = "empty"
        PreprocessingOutput = namedtuple("PreprocessingOutput", ["status", "n_features", "n_products"])
        return PreprocessingOutput(status="empty", n_features=0, n_products=0)

    df = pd.DataFrame(products)
    logger.info(f"Loaded {len(df)} products with {len(df.columns)} columns")

    steps = []

    # 1. Handle missing values
    before = len(df)
    threshold = missing_threshold
    min_count = int(len(df) * (1 - threshold))
    df = df.dropna(axis=1, thresh=min_count)
    steps.append(f"Dropped columns with >{threshold*100:.0f}% missing")

    df = df.fillna({
        'price': df['price'].median() if 'price' in df else 0,
        'rating': 0,
        'reviews_count': 0,
        'quantity': 0,
        'availability': False,
    })
    steps.append("Filled missing values")

    # 2. Ensure numeric
    numeric_cols = ['price', 'rating', 'reviews_count', 'quantity']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    steps.append("Converted numeric columns")

    # 3. Normalize
    if do_normalize:
        scaler = StandardScaler()
        available_numeric = [c for c in numeric_cols if c in df.columns]
        if available_numeric:
            scaled_values = scaler.fit_transform(df[available_numeric])
            for i, col in enumerate(available_numeric):
                df[f"{col}_normalized"] = scaled_values[:, i]
            steps.append(f"Normalized {len(available_numeric)} features")

    # 4. Encode categoricals
    cat_cols = ['category', 'vendor']
    for col in cat_cols:
        if col in df.columns:
            le = LabelEncoder()
            df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
            steps.append(f"Label encoded '{col}'")

    # 5. Price categories
    if 'price' in df.columns:
        df['price_category'] = pd.cut(
            df['price'],
            bins=[0, 20, 50, 100, float('inf')],
            labels=['budget', 'mid_range', 'premium', 'luxury'],
        )
        steps.append("Created price categories")

    # 6. Quality score
    if 'rating' in df.columns and 'reviews_count' in df.columns:
        max_reviews = df['reviews_count'].max() or 1
        df['quality_score'] = (
            0.6 * (df['rating'] / 5.0) +
            0.4 * (df['reviews_count'] / max_reviews)
        )
        steps.append("Computed quality_score")

    output_path = Path(output_data.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    processed = df.to_dict(orient='records')
    with open(output_path, "w") as f:
        json.dump(processed, f, indent=2, default=str)

    logger.info(f"Saved {len(processed)} preprocessed products")

    output_data.metadata["n_features"] = len(df.columns)
    output_data.metadata["n_products"] = len(processed)
    output_data.metadata["features"] = json.dumps(list(df.columns))

    PreprocessingOutput = namedtuple("PreprocessingOutput", ["status", "n_features", "n_products"])
    return PreprocessingOutput(
        status="completed",
        n_features=len(df.columns),
        n_products=len(processed),
    )


# ============================================
# Component 3: Training
# ============================================
@component(
    base_image="datamining-ml-training:latest",
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
    """KFP Component: Train ML models."""
    import json
    import logging
    from pathlib import Path
    import pandas as pd
    import numpy as np
    import yaml
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import silhouette_score
    from sklearn.cluster import KMeans
    import joblib

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    ml_cfg = config.get("data_analysis", {}).get("models", {})
    eval_cfg = config.get("data_analysis", {}).get("evaluation", {})

    input_path = Path(preprocessed_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        logger.warning("No products for training")
        TrainingOutput = namedtuple("TrainingOutput", ["status", "models_trained", "metrics"])
        return TrainingOutput(status="empty", models_trained=0, metrics="{}")

    df = pd.DataFrame(products)
    logger.info(f"Training on {len(df)} products")

    models = {}
    metrics_summary = {}

    # Clustering features
    feature_cols = [c for c in df.columns if df[c].dtype.kind in 'iufc']
    X = df[feature_cols].fillna(0).values

    # KMeans
    kmeans_cfg = ml_cfg.get("kmeans", {})
    n_clusters = kmeans_cfg.get("n_clusters", 5)
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans_labels = kmeans.fit_predict(X)
    models["kmeans"] = kmeans

    if len(set(kmeans_labels)) >= 2:
        try:
            sil_score = silhouette_score(X, kmeans_labels)
            metrics_summary["kmeans_silhouette"] = float(sil_score)
            metrics_summary["kmeans_inertia"] = float(kmeans.inertia_)
        except Exception as e:
            logger.warning(f"Clustering metrics error: {e}")

    # DBSCAN
    try:
        from sklearn.cluster import DBSCAN
        dbscan = DBSCAN(eps=0.5, min_samples=5)
        dbscan_labels = dbscan.fit_predict(X)
        models["dbscan"] = dbscan
        metrics_summary["dbscan_noise_points"] = int(np.sum(dbscan_labels == -1))
    except Exception as e:
        logger.warning(f"DBSCAN failed: {e}")

    # Hierarchical
    try:
        from sklearn.cluster import AgglomerativeClustering
        hierarchical = AgglomerativeClustering(n_clusters=n_clusters)
        models["hierarchical"] = hierarchical
    except Exception as e:
        logger.warning(f"Hierarchical failed: {e}")

    # Classification
    if "quality_score" in df.columns:
        threshold = df["quality_score"].quantile(0.75)
        df["is_high_quality"] = (df["quality_score"] >= threshold).astype(int)
        y = df["is_high_quality"].values
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        from sklearn.ensemble import RandomForestClassifier
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)
        models["random_forest"] = rf
        metrics_summary["random_forest_accuracy"] = float(rf.score(X_test, y_test))

        try:
            from xgboost import XGBClassifier
            xgb = XGBClassifier(n_estimators=100, random_state=42)
            xgb.fit(X_train, y_train)
            models["xgboost"] = xgb
            metrics_summary["xgboost_accuracy"] = float(xgb.score(X_test, y_test))
        except Exception:
            pass

    # Association Rules
    try:
        from mlxtend.frequent_patterns import apriori, association_rules
        if "category" in df.columns:
            cat_dummies = pd.get_dummies(df["category"])
            if len(cat_dummies.columns) > 1:
                itemsets = apriori(cat_dummies, min_support=0.1, use_colnames=True, max_len=3)
                if len(itemsets) > 0:
                    rules = association_rules(itemsets, metric="confidence", min_threshold=0.5)
                    models["association_rules"] = rules.to_dict(orient="records")
                    metrics_summary["association_rules_count"] = len(rules)
    except Exception:
        pass

    # Save models
    model_path = Path(model_output.path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    saved_models = {}
    for name, model_obj in models.items():
        if name == "association_rules":
            saved_models[name] = model_obj
        else:
            model_file = model_path.parent / f"model_{name}.joblib"
            joblib.dump(model_obj, model_file)
            saved_models[name] = str(model_file)

    with open(model_path, "w") as f:
        json.dump({"models": saved_models, "metrics": metrics_summary, "feature_names": feature_cols},
                  f, indent=2, default=str)

    model_output.metadata["models"] = json.dumps(list(models.keys()))
    model_output.metadata["metrics"] = json.dumps(metrics_summary)

    TrainingOutput = namedtuple("TrainingOutput", ["status", "models_trained", "metrics"])
    return TrainingOutput(status="completed", models_trained=len(models), metrics=json.dumps(metrics_summary))


# ============================================
# Component 4: Top-K Selection
# ============================================
@component(
    base_image="datamining-ml-training:latest",
)
def select_top_k_kfp(
    preprocessed_data: Input[Dataset],
    config_path: str,
    top_k_output: Output[Dataset],
) -> NamedTuple(
    "TopKOutput",
    [("status", str), ("top_k_count", int)],
):
    """KFP Component: Select top-K products."""
    import json
    import logging
    from pathlib import Path
    import pandas as pd

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    top_k_cfg = config.get("data_analysis", {}).get("top_k", {})
    default_k = top_k_cfg.get("default_k", 10)
    weights = top_k_cfg.get("scoring_weights", {
        "rating": 0.3, "reviews_count": 0.25, "price_competitiveness": 0.2,
        "availability": 0.15, "recency": 0.1,
    })

    input_path = Path(preprocessed_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        TopKOutput = namedtuple("TopKOutput", ["status", "top_k_count"])
        return TopKOutput(status="empty", top_k_count=0)

    df = pd.DataFrame(products)
    max_price = df['price'].max() or 1
    df['_price_score'] = (1 - (df['price'] / max_price)).clip(0, 1)
    max_rating = df['rating'].max() or 5
    df['_rating_score'] = (df['rating'] / max_rating).clip(0, 1)
    max_reviews = df['reviews_count'].max() or 1
    df['_reviews_score'] = (df['reviews_count'] / max_reviews).clip(0, 1)
    df['_availability_score'] = df['availability'].astype(float)

    df['_score'] = (
        weights.get("rating", 0) * df['_rating_score'] +
        weights.get("reviews_count", 0) * df['_reviews_score'] +
        weights.get("price_competitiveness", 0) * df['_price_score'] +
        weights.get("availability", 0) * df['_availability_score']
    )

    df_sorted = df.sort_values('_score', ascending=False).head(default_k)

    output_path = Path(top_k_output.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(df_sorted.to_dict(orient='records'), f, indent=2, default=str)

    top_k_output.metadata["top_k_count"] = len(df_sorted)

    TopKOutput = namedtuple("TopKOutput", ["status", "top_k_count"])
    return TopKOutput(status="completed", top_k_count=len(df_sorted))


# ============================================
# Component 5: LLM Summary (DeepSeek / Groq uniquement)
# ============================================
@component(
    base_image="datamining-ml-training:latest",
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
    """KFP Component: Generate LLM-powered summary using DeepSeek/Groq."""
    import json
    import logging
    from pathlib import Path
    import yaml
    import httpx

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    llm_cfg = config.get("llm", {})

    with open(scraped_data.path) as f:
        all_products = json.load(f)
    with open(top_k_data.path) as f:
        top_k = json.load(f)

    if not all_products:
        SummaryOutput = namedtuple("SummaryOutput", ["status", "summary_length"])
        return SummaryOutput(status="empty", summary_length=0)

    prompt = (
        "You are a smart eCommerce analyst. Summarize this product dataset and top-K selection.\n"
        f"Total products: {len(all_products)}\n"
        f"Top products: {[p.get('name', 'Unknown') for p in top_k[:3]]}\n"
        "Focus on price range, ratings, availability, and main categories.\n"
        "Provide 3-4 concise sentences."
    )

    summary_text = None

    # Try DeepSeek first
    deepseek_key = llm_cfg.get("deepseek", {}).get("api_key")
    if deepseek_key:
        try:
            resp = httpx.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"},
                json={"model": "deepseek-chat", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
                timeout=60,
            )
            resp.raise_for_status()
            summary_text = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"DeepSeek summary failed: {e}")

    # Try Groq as fallback
    if not summary_text:
        groq_key = llm_cfg.get("groq", {}).get("api_key")
        if groq_key:
            try:
                resp = httpx.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"model": "mixtral-8x7b-32768", "messages": [{"role": "user", "content": prompt}], "max_tokens": 500},
                    timeout=60,
                )
                resp.raise_for_status()
                summary_text = resp.json()["choices"][0]["message"]["content"].strip()
            except Exception as e:
                logger.error(f"Groq summary failed: {e}")

    if not summary_text:
        summary_text = f"LLM summary unavailable. Dataset has {len(all_products)} products, {len(top_k)} in top-K."

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


# ============================================
# Pipeline Compilation Helper
# ============================================
def compile_pipeline(output_file: str = "src/pipelines/kubeflow/pipeline.yaml"):
    """Compile the pipeline to YAML for Kubeflow deployment."""
    import kfp
    from kfp import compiler
    pipeline_func = ecommerce_pipeline
    compiler.Compiler().compile(pipeline_func=pipeline_func, package_path=output_file)
    print(f"Pipeline compiled to {output_file}")


if __name__ == "__main__":
    compile_pipeline()