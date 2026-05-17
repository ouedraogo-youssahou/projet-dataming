#!/usr/bin/env python
"""Submit a Kubeflow pipeline run via SDK v2.

Usage:
    python scripts/run_kfp.py                    # Submit pipeline
    python scripts/run_kfp.py --compile-only      # Only compile to YAML
    python scripts/run_kfp.py --host <url>        # Specify KFP host manually
"""
import sys
import os
from kfp import client, compiler

DEFAULT_HOST = os.getenv("KFP_HOST", "http://127.0.0.1:61567")
PIPELINE_YAML = "src/pipelines/kubeflow/pipeline.yaml"


def compile_pipeline():
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from src.pipelines.kubeflow.pipeline import ecommerce_pipeline
    compiler.Compiler().compile(pipeline_func=ecommerce_pipeline, package_path=PIPELINE_YAML)
    print(f"✅ Pipeline compiled to {PIPELINE_YAML}")
    return True


def submit_pipeline(host: str):
    print(f"🔗 Connecting to Kubeflow at: {host}")
    c = client.Client(host=host)

    import datetime
    name = f"ecommerce-ml-pipeline-{datetime.datetime.now().strftime('%H%M%S')}"
    result = c.upload_pipeline(pipeline_package_path=PIPELINE_YAML, pipeline_name=name)
    pid = result.pipeline_id if hasattr(result, 'pipeline_id') else result.id
    print(f"✅ Uploaded: {pid} ({name})")

    exp_id = "2ddcd9a8-8a77-43bc-a239-41874f7f7918"

    # Build params with all secrets
    params = {
        "woo_url": os.getenv("WOOCOMMERCE_STORE_URL", "https://stethoscopic-revivably-jamey.ngrok-free.dev"),
        "consumer_key": os.getenv("WOOCOMMERCE_CONSUMER_KEY", "ck_a554b0e6ad8e1e7ea9e8850acefa9525b6224e17"),
        "consumer_secret": os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "cs_7b19931e3375156b6eaa34fb1c6697956fdc8a65"),
        
        "targets": "[]",
    }

    job = f"ecommerce-run-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
    print(f"🚀 Submitting: {job}")

    run = c.run_pipeline(
        experiment_id=exp_id,
        job_name=job,
        pipeline_package_path=PIPELINE_YAML,
        params=params,
    )
    rid = run.run_id if hasattr(run, 'run_id') else run.id
    print(f"   Run ID: {rid}")
    print(f"   URL:    {host}/#/runs/details/{rid}")
    return run


def main():
    compile_only = '--compile-only' in sys.argv
    host = DEFAULT_HOST
    for i, arg in enumerate(sys.argv):
        if arg == '--host' and i + 1 < len(sys.argv):
            host = sys.argv[i + 1]
    if not compile_pipeline():
        sys.exit(1)
    if compile_only:
        print("✅ Compile-only mode.")
        return
    submit_pipeline(host)


if __name__ == "__main__":
    main()