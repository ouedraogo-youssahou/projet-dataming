#!/usr/bin/env python
"""
Build and submit Kubeflow pipeline - Complete workflow.
"""

import json
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd, desc):
    """Run shell command and check result."""
    print(f"\n{'='*60}")
    print(f"📦 {desc}")
    print(f"{'='*60}")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if result.returncode != 0:
        print(f"❌ Failed: {desc}")
        sys.exit(1)
    print(f"✅ Success: {desc}")

def main():
    print("\n" + "="*60)
    print("  eCommerce Intelligence - Kubeflow Pipeline Deploy")
    print("="*60)

    project_root = Path(__file__).parent

    # Step 1: Build Docker image
    run_cmd(
        "docker build -t ecommerce-kfp:latest -f Dockerfile --target=kfp-components .",
        "Building ecommerce-kfp:latest image"
    )

    # Step 2: Load into Minikube
    run_cmd(
        "minikube image load ecommerce-kfp:latest",
        "Loading image into Minikube"
    )

    # Step 3: Install KFP (if not already)
    try:
        import kfp
        print("✅ KFP already installed")
    except ImportError:
        run_cmd("pip install kfp==2.0.0", "Installing KFP SDK")

    # Step 4: Compile pipeline
    print("\n" + "="*60)
    print("📦 Compiling Kubeflow pipeline")
    print("="*60)
    
    sys.path.insert(0, str(project_root))
    from kfp import compiler
    from src.pipelines.kubeflow.pipeline import ecommerce_pipeline
    
    output_path = project_root / "src/pipelines/kubeflow/pipeline_fixed.yaml"
    compiler.Compiler().compile(
        pipeline_func=ecommerce_pipeline,
        package_path=str(output_path)
    )
    print(f"✅ Pipeline compiled: {output_path}")

    # Step 5: Check Kubeflow UI
    print("\n" + "="*60)
    print("📡 Kubeflow Access")
    print("="*60)
    
    # Get minikube service URL
    try:
        result = subprocess.run(
            ["minikube", "service", "-n", "kubeflow", "ml-pipeline-ui", "--url"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            url = result.stdout.strip()
            print(f"✅ Kubeflow UI: {url}")
            print(f"   Open in browser: {url}")
        else:
            print("⚠️  Could not get Kubeflow URL. Try manually:")
            print("   kubectl port-forward -n kubeflow svc/ml-pipeline-ui 8888:80")
            print("   Then open: http://localhost:8888")
    except Exception as e:
        print(f"⚠️  Error getting service URL: {e}")

    # Step 6: Instructions for submission
    print("\n" + "="*60)
    print("✅ ALL SET! Next steps:")
    print("="*60)
    print()
    print("Option A: Upload via Kubeflow UI")
    print("  1. Open Kubeflow UI (URL above)")
    print("  2. Go to 'Pipelines' → 'Upload pipeline'")
    print(f"  3. Select file: {output_path}")
    print("  4. Name: ecommerce-intelligence")
    print("  5. Click Upload")
    print()
    print("Option B: Submit via Python CLI")
    print("  python submit_kfp.py")
    print()
    print("Option C: Manual Python script")
    print("""
from kfp import Client
import json

client = Client(host="http://localhost:60427")  # adjust port
exp = client.create_experiment(name="ecommerce-demo")
run = client.run_pipeline(
    experiment_id=exp.id,
    job_name="ecommerce-run-001",
    pipeline_package_path="src/pipelines/kubeflow/pipeline_fixed.yaml",
    params={
        "targets": json.dumps([
            {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"}
        ])
    }
)
print(f"Run: {run.run_id}")
""")

if __name__ == "__main__":
    main()
