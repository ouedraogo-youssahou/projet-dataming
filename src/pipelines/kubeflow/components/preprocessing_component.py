# ============================================
# Kubeflow Component: Data Preprocessing
# ============================================

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def preprocess_data(
    input_path: str,
    config_path: str,
    output_path: str,
) -> str:
    """
    Kubeflow component: Preprocess scraped product data.
    
    - Clean missing values
    - Normalize numerical features
    - Encode categorical variables
    - Detect and handle outliers
    
    Args:
        input_path: Path to raw scraped products JSON
        config_path: Path to pipeline configuration YAML
        output_path: Path to save preprocessed data (JSON)
        
    Returns:
        JSON string with preprocessing summary
    """
    logger.info(f"=== Preprocessing Component Started ===")
    logger.info(f"Input: {input_path}")
    logger.info(f"Output: {output_path}")

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    preproc_cfg = config.get("components", {}).get("preprocessing", {})
    missing_threshold = preproc_cfg.get("missing_threshold", 0.3)
    do_normalize = preproc_cfg.get("normalize", True)
    encoding = preproc_cfg.get("encoding", "label")

    # Load input data
    with open(input_path) as f:
        products = json.load(f)

    if not products:
        logger.warning("No products to preprocess")
        return json.dumps({
            "status": "empty",
            "message": "No products provided",
            "n_products": 0,
        })

    df = pd.DataFrame(products)
    logger.info(f"Loaded {len(df)} products with {len(df.columns)} columns")

    # Track preprocessing steps
    steps = []

    # 1. Handle missing values
    before = len(df)
    threshold = missing_threshold
    min_count = int(len(df) * (1 - threshold))
    df = df.dropna(axis=1, thresh=min_count)
    steps.append(f"Dropped columns with >{threshold*100:.0f}% missing values")

    df = df.fillna({
        'price': df['price'].median() if 'price' in df else 0,
        'rating': 0,
        'reviews_count': 0,
        'quantity': 0,
        'availability': False,
    })
    steps.append("Filled remaining missing values")

    # 2. Ensure numeric columns
    numeric_cols = ['price', 'rating', 'reviews_count', 'quantity']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    steps.append("Converted numeric columns")

    # 3. Normalize numerical features
    if do_normalize:
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        available_numeric = [c for c in numeric_cols if c in df.columns]
        if available_numeric:
            scaled_values = scaler.fit_transform(df[available_numeric])
            for i, col in enumerate(available_numeric):
                df[f"{col}_normalized"] = scaled_values[:, i]
            steps.append(f"Normalized {len(available_numeric)} numeric features")
            # Keep original values + normalized versions

    # 4. Encode categorical variables
    if encoding == "label":
        from sklearn.preprocessing import LabelEncoder
        cat_cols = ['category', 'vendor']
        for col in cat_cols:
            if col in df.columns:
                le = LabelEncoder()
                df[f"{col}_encoded"] = le.fit_transform(df[col].astype(str))
                steps.append(f"Label encoded '{col}' ({len(le.classes_)} categories)")

    # 5. Create price categories
    if 'price' in df.columns:
        df['price_category'] = pd.cut(
            df['price'],
            bins=[0, 20, 50, 100, float('inf')],
            labels=['budget', 'mid_range', 'premium', 'luxury'],
        )
        steps.append("Created price categories (budget/mid/premium/luxury)")

    # 6. Create quality score (composite)
    if 'rating' in df.columns and 'reviews_count' in df.columns:
        max_reviews = df['reviews_count'].max() or 1
        df['quality_score'] = (
            0.6 * (df['rating'] / 5.0) +
            0.4 * (df['reviews_count'] / max_reviews)
        )
        steps.append("Computed quality_score from rating + reviews")

    # Save preprocessed data
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert DataFrame to records for JSON serialization
    processed = df.to_dict(orient='records')
    with open(output_path, "w") as f:
        json.dump(processed, f, indent=2, default=str)

    logger.info(f"Saved {len(processed)} preprocessed products to {output_path}")

    summary = {
        "status": "completed",
        "n_products_input": len(products),
        "n_products_output": len(processed),
        "n_features": len(df.columns),
        "features": list(df.columns),
        "steps": steps,
        "output_file": output_path,
    }

    return json.dumps(summary)


if __name__ == "__main__":
    import sys
    input_f = sys.argv[1] if len(sys.argv) > 1 else "data/raw/scraped_products.json"
    config_f = sys.argv[2] if len(sys.argv) > 2 else "src/pipelines/kubeflow/config/pipeline_config.yaml"
    output_f = sys.argv[3] if len(sys.argv) > 3 else "data/processed/preprocessed_products.json"
    result = preprocess_data(input_f, config_f, output_f)
    print(result)