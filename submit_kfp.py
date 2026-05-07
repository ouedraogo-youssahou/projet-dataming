#!/usr/bin/env python
"""
Submit pipeline to Kubeflow.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from kfp import Client
except ImportError:
    print("❌ KFP not installed. Run: pip install kfp==2.0.0")
    sys.exit(1)

def main():
    # Connect to Kubeflow
    # Try multiple common ports for minikube tunnel
    ports_to_try = [60427, 8888, 80]
    client = None
    
    for port in ports_to_try:
        try:
            client = Client(host=f"http://localhost:{port}")
            print(f"✅ Connected to Kubeflow on port {port}")
            break
        except Exception as e:
            print(f"⚠️  Port {port} failed: {e}")
            continue
    
    if client is None:
        print("❌ Could not connect to Kubeflow.")
        print("   Make sure minikube tunnel is running:")
        print("   minikube service -n kubeflow ml-pipeline-ui --url")
        sys.exit(1)

    # Get or create experiment
    experiment_name = "ecommerce-demo"
    try:
        exp = client.get_experiment(experiment_name=experiment_name)
        print(f"✅ Using experiment: {experiment_name} (id: {exp.id})")
    except Exception:
        exp = client.create_experiment(name=experiment_name)
        print(f"✅ Created experiment: {experiment_name} (id: {exp.id})")

    # Submit pipeline
    pipeline_file = Path("src/pipelines/kubeflow/pipeline_fixed.yaml")
    if not pipeline_file.exists():
        print(f"❌ Pipeline file not found: {pipeline_file}")
        print("   Run: python generate_valid_pipeline.py")
        sys.exit(1)

    print(f"\n📤 Submitting pipeline...")
    print(f"   File: {pipeline_file}")
    print(f"   Experiment: {experiment_name}")

    run = client.run_pipeline(
        experiment_id=exp.id,
        job_name=f"ecommerce-run-{int(Path().stat().st_mtime)}",
        pipeline_package_path=str(pipeline_file),
        params={
            "targets": json.dumps([
                {
                    "platform": "shopify",
                    "url": "https://storefront-demo.myshopify.com"
                }
            ]),
            "config_path": "/app/config/config.yaml"
        }
    )

    print(f"\n✅ Pipeline submitted successfully!")
    print(f"   Run ID: {run.run_id}")
    print(f"   URL: http://localhost:60427/#/runs/details/{run.run_id}")
    print("\n📊 Monitor the run in Kubeflow UI or:")
    print(f"   kubectl get pods -n kubeflow -l pipeline-run-id={run.run_id}")
    print(f"   kubectl logs -n kubeflow <pod-name>")

if __name__ == "__main__":
    main()
