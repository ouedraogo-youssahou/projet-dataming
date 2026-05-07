# Kubeflow Pipelines - eCommerce Intelligence

## 📦 Pipeline Components

The pipeline consists of 5 sequential components:

1. **Scraping** (`scrape_products_kfp`)
   - Uses A2A agents or direct scrapers
   - Input: targets list
   - Output: raw products JSON

2. **Preprocessing** (`preprocess_data_kfp`)
   - Cleaning, normalization, encoding
   - Input: raw products
   - Output: preprocessed features

3. **Training** (`train_models_kfp`)
   - Trains clustering, classification, association rules
   - Input: preprocessed data
   - Output: trained models + metrics

4. **Top-K Selection** (`select_top_k_kfp`)
   - Scores products, selects best K
   - Input: preprocessed data
   - Output: top-K products JSON

5. **LLM Summary** (`generate_llm_summary_kfp`)
   - Generates narrative summary with OpenAI/Anthropic
   - Input: scraped data + top-K results
   - Output: summary text

## 🚀 Quick Start

### 1. Compile the Pipeline

```bash
# Make sure KFP is installed
pip install kfp==2.0.0

# Compile to YAML
python -m src.pipelines.kubeflow.run_pipeline --compile-only
# Output: src/pipelines/kubeflow/pipeline.yaml
```

### 2. Submit to Kubeflow

```bash
# Using KFP CLI (if kfp CLI installed)
kfp run submit \
  --experiment ecommerce-demo \
  --pipeline-file src/pipelines/kubeflow/pipeline.yaml \
  --params targets='[]' \
  --params config_path=/app/config/config.yaml
```

Or using Python SDK directly:

```python
from kfp import Client

client = Client(host="http://localhost:8888")  # or in-cluster
run = client.run_pipeline(
    experiment_id="<experiment-id>",
    job_name="ecommerce-run-20240101",
    pipeline_package_path="src/pipelines/kubeflow/pipeline.yaml",
    params={
        "targets": "[]",
        "config_path": "/app/config/config.yaml",
    }
)
```

## 🐳 Docker/Kubeflow Deployment

### Build Pipeline Image

```bash
# Build the Docker image with all dependencies
docker build \
  --target ml-training \
  -t ecommerce-ml:latest \
  -f Dockerfile .

# Push to registry
docker tag ecommerce-ml:latest myregistry/ecommerce-ml:latest
docker push myregistry/ecommerce-ml:latest
```

### Deploy to Kubeflow

1. Upload the compiled `pipeline.yaml` to Kubeflow UI, or
2. Use `kfp` CLI:
   ```bash
   kfp pipeline upload \
     --pipeline-file src/pipelines/kubeflow/pipeline.yaml \
     --pipeline-name "ecommerce-intelligence"
   ```

## ⚙️ Configuration

Pipeline behavior is controlled via `config/config.yaml`:

```yaml
data_analysis:
  top_k:
    default_k: 10
    scoring_weights:
      rating: 0.3
      reviews_count: 0.25
      price_competitiveness: 0.2
      availability: 0.15
  models:
    kmeans:
      n_clusters: 5
    random_forest:
      n_estimators: 100
```

## 📊 Monitoring

- **KFP UI**: View runs at http://localhost:8888
- **Metrics**: Auto-collected per-component (accuracy, silhouette, etc.)
- **Artifacts**: Models saved to PVC `/app/data/models/`

## 🧪 Local Testing

Test components individually:

```bash
# Test scraping component only
python -c "
from src.pipelines.kubeflow.components.scraping_component import scrape_products
result = scrape_products(
    config_path='config/config.yaml',
    output_path='data/raw/test_scrape.json',
    targets_json='[]'
)
print(result)
"

# Test preprocessing
python -c "
from src.pipelines.kubeflow.components.preprocessing_component import preprocess_data
result = preprocess_data(
    input_path='data/raw/scraped_products.json',
    config_path='config/config.yaml',
    output_path='data/processed/test_preprocessed.json',
)
print(result)
"
```

## 🔄 CI/CD Integration

The pipeline is integrated with GitHub Actions (`.github/workflows/ci-cd.yml`). On PR merge:

1. Docker image built and pushed
2. Pipeline YAML re-compiled
3. (Optional) Integration test run triggered

## 📁 File Structure

```
src/pipelines/kubeflow/
├── __init__.py               # Package init
├── pipeline.py               # Main pipeline DAG definition
├── run_pipeline.py           # CLI for running/submitting pipeline
├── pipeline.yaml             # Compiled pipeline (generated)
├── components/
│   ├── scraping_component.py  # Scraping step
│   ├── preprocessing_component.py  # Preprocessing step
│   └── training_component.py  # ⚠️ MISSING - defined in pipeline.py inline
└── config/
    └── component_config.py    # Config utilities
```

## 🐛 Troubleshooting

### Component Fails
Check logs in KFP UI or:
```bash
kubectl logs -f <pod-name> -n kubeflow
```

### Missing Dependencies
All dependencies are in `requirements.txt`. Rebuild the image:
```bash
docker compose build ml-training
```

### Redis Connection Failed
Set `use_redis: true` in `config/config.yaml` and ensure Redis is reachable from the pipeline pod.

### LLM API Errors
Ensure API keys are set as KFP secrets or in config:
```yaml
llm:
  openai:
    api_key: ${OPENAI_API_KEY}
```

## 📚 References

- [Kubeflow Pipelines SDK](https://www.kubeflow.org/docs/components/pipelines/sdk/)
- [KFP Python DSL](https://kubeflow-pipelines.readthedocs.io/en/latest/source/kfp.dsl.html)
- [Argo Workflows](https://argoproj.github.io/argo-workflows/)
