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
# Component 1: Scraping (already exists as function)
# We'll wrap it as KFP component
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["asyncpg", "aiohttp", "selenium", "playwright", "scrapy", "beautifulsoup4", "psycopg2-binary", "pyyaml"],
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

    Args:
        config_path: Path to pipeline configuration YAML
        targets_json: JSON string of scraping targets
        output_data: Output artifact for scraped products

    Returns:
        NamedTuple with status, count, and platforms
    """
    import json
    import logging
    import asyncio
    from pathlib import Path
    import yaml

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Parse targets
    targets = json.loads(targets_json) if targets_json else [
        {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
        {"platform": "woocommerce", "url": "https://example-woo.com"},
    ]

    logger.info(f"Scraping {len(targets)} targets")

    # Import engine
    from src.__main__ import SmartECommerceIntelligence

    engine = SmartECommerceIntelligence(config)

    # Run scraping
    scrape_results = asyncio.run(engine.scrape_all(targets))

    # Collect products
    all_products = []
    for r in scrape_results:
        if r.get("status") == "ok" and "data" in r:
            data = r["data"]
            if isinstance(data, list):
                all_products.extend(data)
            elif isinstance(data, dict):
                all_products.append(data)

    logger.info(f"Scraped {len(all_products)} products")

    # Write to output artifact
    output_path = Path(output_data.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(all_products, f, indent=2, default=str)

    # Metadata
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
# Component 2: Preprocessing (already exists)
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
    import yaml
    from sklearn.preprocessing import StandardScaler, LabelEncoder

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    preproc_cfg = config.get("components", {}).get("preprocessing", {})
    missing_threshold = preproc_cfg.get("missing_threshold", 0.3)
    do_normalize = preproc_cfg.get("normalize", True)

    # Load input
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

    # Save output
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
# Component 3: Training (NEW - was missing!)
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy", "scikit-learn", "xgboost", "lightgbm", "mlxtend", "joblib"],
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
    """
    KFP Component: Train ML models on preprocessed data.

    Trains:
    - Clustering: KMeans, DBSCAN, Hierarchical
    - Classification: Random Forest, XGBoost (if labels available)
    - Association Rules (if sufficient transactions)
    """
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

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    ml_cfg = config.get("data_analysis", {}).get("models", {})
    eval_cfg = config.get("data_analysis", {}).get("evaluation", {})

    # Load preprocessed data
    input_path = Path(preprocessed_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        logger.warning("No products for training")
        TrainingOutput = namedtuple("TrainingOutput", ["status", "models_trained", "metrics"])
        return TrainingOutput(status="empty", models_trained=0, metrics="{}")

    df = pd.DataFrame(products)
    logger.info(f"Training on {len(df)} products with {len(df.columns)} features")

    models = {}
    metrics_summary = {}

    # ========================================
    # 1. CLUSTERING
    # ========================================
    logger.info("Training clustering models...")

    # Features for clustering
    feature_cols = [c for c in df.columns if df[c].dtype.kind in 'iufc']
    X = df[feature_cols].fillna(0).values

    # KMeans
    kmeans_cfg = ml_cfg.get("kmeans", {})
    n_clusters = kmeans_cfg.get("n_clusters", 5)

    kmeans = KMeans(
        n_clusters=n_clusters,
        init=kmeans_cfg.get("init", "k-means++"),
        n_init=kmeans_cfg.get("n_init", 10),
        max_iter=kmeans_cfg.get("max_iter", 300),
        random_state=42,
    )
    kmeans_labels = kmeans.fit_predict(X)
    models["kmeans"] = kmeans

    # Clustering metrics
    if len(set(kmeans_labels)) >= 2:
        try:
            sil_score = silhouette_score(X, kmeans_labels)
            metrics_summary["kmeans_silhouette"] = float(sil_score)
            metrics_summary["kmeans_inertia"] = float(kmeans.inertia_)
        except Exception as e:
            logger.warning(f"Could not compute clustering metrics: {e}")

    logger.info(f"KMeans trained: {n_clusters} clusters, inertia={kmeans.inertia_:.2f}")

    # DBSCAN (optional, may fail on some data)
    try:
        dbscan_cfg = ml_cfg.get("dbscan", {})
        from sklearn.cluster import DBSCAN
        dbscan = DBSCAN(
            eps=dbscan_cfg.get("eps", 0.5),
            min_samples=dbscan_cfg.get("min_samples", 5),
        )
        dbscan_labels = dbscan.fit_predict(X)
        models["dbscan"] = dbscan
        n_noise = int(np.sum(dbscan_labels == -1))
        metrics_summary["dbscan_noise_points"] = n_noise
        logger.info(f"DBSCAN trained: {len(set(dbscan_labels))} clusters, {n_noise} noise points")
    except Exception as e:
        logger.warning(f"DBSCAN training failed: {e}")

    # Hierarchical (sklearn AgglomerativeClustering)
    try:
        hier_cfg = ml_cfg.get("hierarchical", {})
        from sklearn.cluster import AgglomerativeClustering
        hierarchical = AgglomerativeClustering(
            n_clusters=n_clusters,
            linkage=hier_cfg.get("linkage", "ward"),
        )
        hier_labels = hierarchical.fit_predict(X)
        models["hierarchical"] = hierarchical
        logger.info(f"Hierarchical clustering trained: {n_clusters} clusters")
    except Exception as e:
        logger.warning(f"Hierarchical clustering failed: {e}")

    # ========================================
    # 2. CLASSIFICATION (if we can create labels)
    # ========================================
    logger.info("Training classification models...")

    # Create synthetic labels from clustering for supervised training
    # In production, you'd have real labels (e.g., high-performing vs not)
    if "quality_score" in df.columns:
        # Binary classification: high quality (top 25%) vs low quality
        threshold = df["quality_score"].quantile(0.75)
        df["is_high_quality"] = (df["quality_score"] >= threshold).astype(int)

        y = df["is_high_quality"].values
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=eval_cfg.get("test_size", 0.2), random_state=42
        )

        # Random Forest
        from sklearn.ensemble import RandomForestClassifier
        rf_cfg = ml_cfg.get("random_forest", {})
        rf = RandomForestClassifier(
            n_estimators=rf_cfg.get("n_estimators", 100),
            max_depth=rf_cfg.get("max_depth", 10),
            min_samples_split=rf_cfg.get("min_samples_split", 5),
            random_state=42,
        )
        rf.fit(X_train, y_train)
        models["random_forest"] = rf
        rf_score = rf.score(X_test, y_test)
        metrics_summary["random_forest_accuracy"] = float(rf_score)
        logger.info(f"Random Forest trained: accuracy={rf_score:.3f}")

        # XGBoost
        try:
            from xgboost import XGBClassifier
            xgb_cfg = ml_cfg.get("xgboost", {})
            xgb = XGBClassifier(
                n_estimators=xgb_cfg.get("n_estimators", 100),
                max_depth=xgb_cfg.get("max_depth", 6),
                learning_rate=xgb_cfg.get("learning_rate", 0.1),
                objective=xgb_cfg.get("objective", "binary:logistic"),
                random_state=42,
            )
            xgb.fit(X_train, y_train)
            models["xgboost"] = xgb
            xgb_score = xgb.score(X_test, y_test)
            metrics_summary["xgboost_accuracy"] = float(xgb_score)
            logger.info(f"XGBoost trained: accuracy={xgb_score:.3f}")
        except Exception as e:
            logger.warning(f"XGBoost training failed: {e}")

    # ========================================
    # 3. ASSOCIATION RULES (if categorical columns exist)
    # ========================================
    logger.info("Mining association rules...")

    try:
        from mlxtend.frequent_patterns import apriori, association_rules

        # Create transaction-like data: categories per product
        if "category" in df.columns:
            # One-hot encode categories
            categories_dummies = pd.get_dummies(df["category"])
            if len(categories_dummies.columns) > 1:
                frequent_itemsets = apriori(
                    categories_dummies,
                    min_support=0.1,
                    use_colnames=True,
                    max_len=3,
                )
                if len(frequent_itemsets) > 0:
                    rules = association_rules(
                        frequent_itemsets,
                        metric="confidence",
                        min_threshold=0.5,
                    )
                    models["association_rules"] = rules.to_dict(orient="records")
                    metrics_summary["association_rules_count"] = len(rules)
                    logger.info(f"Association rules mined: {len(rules)} rules")
                else:
                    logger.info("No frequent itemsets found for association rules")
            else:
                logger.info("Not enough categorical diversity for association rules")
    except Exception as e:
        logger.warning(f"Association rule mining failed: {e}")

    # ========================================
    # Save Models
    # ========================================
    model_output.metadata["models"] = json.dumps(list(models.keys()))
    model_output.metadata["metrics"] = json.dumps(metrics_summary)

    model_path = Path(model_output.path)
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # Save all models using joblib
    saved_models = {}
    for name, model_obj in models.items():
        if name == "association_rules":
            saved_models[name] = model_obj  # keep as dict
        else:
            model_file = model_path.parent / f"model_{name}.joblib"
            joblib.dump(model_obj, model_file)
            saved_models[name] = str(model_file)

    # Save models bundle
    with open(model_path, "w") as f:
        json.dump({
            "models": saved_models,
            "metrics": metrics_summary,
            "feature_names": feature_cols,
        }, f, indent=2, default=str)

    logger.info(f"Saved {len(models)} models to {model_path}")

    TrainingOutput = namedtuple("TrainingOutput", ["status", "models_trained", "metrics"])
    return TrainingOutput(
        status="completed",
        models_trained=len(models),
        metrics=json.dumps(metrics_summary),
    )


# ============================================
# Component 4: Top-K Selection (already in __main__)
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy"],
)
def select_top_k_kfp(
    preprocessed_data: Input[Dataset],
    config_path: str,
    top_k_output: Output[Dataset],
) -> NamedTuple(
    "TopKOutput",
    [("status", str), ("top_k_count", int)],
):
    """KFP Component: Select top-K products by scoring."""
    import json
    import logging
    from pathlib import Path
    import pandas as pd

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    top_k_cfg = config.get("data_analysis", {}).get("top_k", {})
    default_k = top_k_cfg.get("default_k", 10)
    weights = top_k_cfg.get("scoring_weights", {
        "rating": 0.3,
        "reviews_count": 0.25,
        "price_competitiveness": 0.2,
        "availability": 0.15,
        "recency": 0.1,
    })

    # Load preprocessed data
    input_path = Path(preprocessed_data.path)
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        logger.warning("No products for Top-K selection")
        TopKOutput = namedtuple("TopKOutput", ["status", "top_k_count"])
        return TopKOutput(status="empty", top_k_count=0)

    df = pd.DataFrame(products)
    logger.info(f"Selecting Top-{default_k} from {len(df)} products")

    # Compute scores
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

    # Save top-k
    output_path = Path(top_k_output.path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    top_k_records = df_sorted.to_dict(orient='records')
    with open(output_path, "w") as f:
        json.dump(top_k_records, f, indent=2, default=str)

    logger.info(f"Saved {len(top_k_records)} top-K products")

    top_k_output.metadata["top_k_count"] = len(top_k_records)
    top_k_output.metadata["threshold_score"] = float(df_sorted['_score'].min())

    TopKOutput = namedtuple("TopKOutput", ["status", "top_k_count"])
    return TopKOutput(
        status="completed",
        top_k_count=len(top_k_records),
    )


# ============================================
# Component 5: LLM Summary (NEW)
# ============================================
@component(
    base_image="python:3.11-slim",
    packages_to_install=["openai>=1.0.0", "anthropic", "httpx"],
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
    """KFP Component: Generate LLM-powered summary."""
    import json
    import logging
    from pathlib import Path
    import os

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    llm_cfg = config.get("llm", {})

    # Load data
    with open(scraped_data.path) as f:
        all_products = json.load(f)
    with open(top_k_data.path) as f:
        top_k = json.load(f)

    if not all_products:
        logger.warning("No products to summarize")
        SummaryOutput = namedtuple("SummaryOutput", ["status", "summary_length"])
        return SummaryOutput(status="empty", summary_length=0)

    # Select LLM provider
    openai_key = llm_cfg.get("openai", {}).get("api_key")
    anthropic_key = llm_cfg.get("anthropic", {}).get("api_key")

    prompt = (
        "You are a smart eCommerce analyst. Summarize this product dataset and top-K selection.\n"
        f"Total products: {len(all_products)}\n"
        f"Top products: {[p.get('name', 'Unknown') for p in top_k[:3]]}\n"
        "Focus on price range, ratings, availability, and main categories.\n"
        "Provide 3-4 concise sentences."
    )

    summary_text = None

    # Try OpenAI first
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.chat.completions.create(
                model=llm_cfg.get("openai", {}).get("model", "gpt-3.5-turbo"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.7,
            )
            summary_text = response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI summary failed: {e}")

    # Try Anthropic as fallback
    if not summary_text and anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            message = client.messages.create(
                model=llm_cfg.get("anthropic", {}).get("model", "claude-3-opus-20240229"),
                max_tokens=500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )
            summary_text = message.content[0].text.strip()
        except Exception as e:
            logger.error(f"Anthropic summary failed: {e}")

    if not summary_text:
        summary_text = f"LLM summary unavailable. Dataset has {len(all_products)} products, {len(top_k)} in top-K."

    # Save summary
    summary_path = Path(summary_output.path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, "w") as f:
        f.write(summary_text)

    summary_output.metadata["summary_length"] = len(summary_text)

    SummaryOutput = namedtuple("SummaryOutput", ["status", "summary_length"])
    return SummaryOutput(
        status="completed" if summary_text else "fallback",
        summary_length=len(summary_text),
    )


# ============================================
# Main Pipeline DAG
# ============================================
@dsl.pipeline(
    name="ecommerce-ml-pipeline",
    description="End-to-end ML pipeline for eCommerce intelligence: scraping, preprocessing, training, top-K selection, LLM summary",
)
def ecommerce_pipeline(
    targets: str = '[]',
    config_path: str = "/app/config/config.yaml",
):
    """
    End-to-end eCommerce intelligence pipeline.

    Args:
        targets: JSON array of scraping targets
        config_path: Path to configuration YAML
    """
    # Step 1: Scraping
    scrape_task = scrape_products_kfp(
        config_path=config_path,
        targets_json=targets,
    )

    # Step 2: Preprocessing
    preprocess_task = preprocess_data_kfp(
        input_data=scrape_task.outputs["output_data"],
        config_path=config_path,
    )

    # Step 3: Training (ML models)
    train_task = train_models_kfp(
        preprocessed_data=preprocess_task.outputs["output_data"],
        config_path=config_path,
    )

    # Step 4: Top-K Selection
    top_k_task = select_top_k_kfp(
        preprocessed_data=preprocess_task.outputs["output_data"],
        config_path=config_path,
    )

    # Step 5: LLM Summary
    summary_task = generate_llm_summary_kfp(
        scraped_data=scrape_task.outputs["output_data"],
        top_k_data=top_k_task.outputs["top_k_output"],
        config_path=config_path,
    )

    # Dependency chain: scrape -> preprocess -> [train, top-k] -> summary
    # DAG structure enforces order
    pass


# ============================================
# Pipeline Compilation Helper
# ============================================
def compile_pipeline(output_file: str = "src/pipelines/kubeflow/pipeline.yaml"):
    """
    Compile the pipeline to YAML for Kubeflow deployment.

    Args:
        output_file: Path to save compiled pipeline YAML
    """
    import kfp
    from kfp import compiler

    pipeline_func = ecommerce_pipeline
    compiler.Compiler().compile(
        pipeline_func=pipeline_func,
        package_path=output_file,
    )
    print(f"Pipeline compiled to {output_file}")


if __name__ == "__main__":
    compile_pipeline()
