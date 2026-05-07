import sys
sys.path.insert(0, 'src')

from kfp import compiler, dsl
from kfp.dsl import component, Input, Output, Dataset, Model  # Add Model import
import json

@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy", "pyyaml"],
)
def scrape_comp(config_path: str, targets: str, output: Output[Dataset]) -> str:
    import json, yaml, asyncio
    from pathlib import Path
    from src.__main__ import SmartECommerceIntelligence
    
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    targets_list = json.loads(targets) if targets else []
    engine = SmartECommerceIntelligence(config)
    results = asyncio.run(engine.scrape_all(targets_list))
    
    all_products = []
    for r in results:
        if r.get("status") == "ok" and "data" in r:
            data = r["data"]
            if isinstance(data, list):
                all_products.extend(data)
            elif isinstance(data, dict):
                all_products.append(data)
    
    out_path = Path(output.path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(all_products, f, indent=2, default=str)
    
    return json.dumps({"count": len(all_products)})

@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy", "scikit-learn"],
)
def preprocess_comp(input_data: Input[Dataset], output: Output[Dataset]) -> str:
    import json, pandas as pd
    from pathlib import Path
    from sklearn.preprocessing import LabelEncoder
    
    in_path = Path(input_data.path)
    with open(in_path) as f:
        products = json.load(f)
    
    if not products:
        return "empty"
    
    df = pd.DataFrame(products)
    df = df.fillna({'price': 0, 'rating': 0, 'reviews_count': 0})
    
    for col in ['category', 'vendor']:
        if col in df.columns:
            le = LabelEncoder()
            df[f"{col}_enc"] = le.fit_transform(df[col].astype(str))
    
    out_path = Path(output.path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(df.to_dict(orient='records'), f, indent=2, default=str)
    
    return "done"

@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy", "scikit-learn", "joblib"],
)
def train_comp(input_data: Input[Dataset], model_out: Output[Model]) -> str:  # Model is now defined
    import json, pandas as pd, joblib
    from pathlib import Path
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    
    in_path = Path(input_data.path)
    with open(in_path) as f:
        products = json.load(f)
    
    if not products:
        return "no_data"
    
    df = pd.DataFrame(products)
    X = df[['price', 'rating', 'reviews_count']].fillna(0).values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    
    model_dir = Path(model_out.path).parent
    model_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(kmeans, model_dir / "kmeans.pkl")
    joblib.dump(scaler, model_dir / "scaler.pkl")
    
    return "trained"

@component(
    base_image="python:3.11-slim",
    packages_to_install=["pandas", "numpy"],
)
def topk_comp(input_data: Input[Dataset], output: Output[Dataset]) -> str:
    import json, pandas as pd
    from pathlib import Path
    
    in_path = Path(input_data.path)
    with open(in_path) as f:
        products = json.load(f)
    
    if not products:
        return "empty"
    
    df = pd.DataFrame(products)
    df['_score'] = (
        0.3 * (df['rating'] / (df['rating'].max() or 5)) +
        0.25 * (df['reviews_count'] / (df['reviews_count'].max() or 1)) +
        0.2 * (1 - (df['price'] / (df['price'].max() or 1))) +
        0.15 * df['availability'].astype(float)
    )
    
    top5 = df.nlargest(5, '_score')
    out_path = Path(output.path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(top5.to_dict(orient='records'), f, indent=2, default=str)
    
    return "done"

@dsl.pipeline(
    name="ecommerce-intelligence",
    description="Scrape → Preprocess → Train → Top-K",
)
def pipeline():
    scrape = scrape_comp(
        config_path="/app/config/config.yaml",
        targets='[{"platform": "shopify", "url": "https://storefront-demo.myshopify.com"}]',
    )
    preprocess = preprocess_comp(input_data=scrape.outputs["output"])
    train = train_comp(input_data=preprocess.outputs["output"])
    topk = topk_comp(input_data=preprocess.outputs["output"])

if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=pipeline,
        package_path="src/pipelines/kubeflow/pipeline_fixed.yaml",
    )
    print("✅ Generated: src/pipelines/kubeflow/pipeline_fixed.yaml")