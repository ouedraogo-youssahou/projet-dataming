# ============================================
# Kubeflow Pipeline Runner - CLI to submit pipeline
# ============================================

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml") -> dict:
    """Load pipeline configuration."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def prepare_targets(targets_file: str = None, targets_list: str = None) -> str:
    """
    Prepare targets JSON for pipeline.

    Args:
        targets_file: Path to JSON file with targets
        targets_list: JSON string of targets

    Returns:
        JSON string of targets
    """
    if targets_file:
        with open(targets_file) as f:
            targets = json.load(f)
    elif targets_list:
        targets = json.loads(targets_list)
    else:
        # Default demo targets
        targets = [
            {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
            {"platform": "woocommerce", "url": "https://example-woo.com"},
        ]
    return json.dumps(targets)


def compile_pipeline(output_path: str = "src/pipelines/kubeflow/pipeline.yaml"):
    """Compile the pipeline to YAML."""
    from kfp import compiler
    from src.pipelines.kubeflow.pipeline import ecommerce_pipeline

    compiler.Compiler().compile(
        pipeline_func=ecommerce_pipeline,
        package_path=output_path,
    )
    logger.info(f"Pipeline compiled to {output_path}")


def run_pipeline_kfp(
    pipeline_yaml: str,
    targets: str,
    config_path: str,
    experiment_name: str = "ecommerce-default",
    run_name: str = None,
):
    """
    Submit and run the pipeline using KFP client.

    Args:
        pipeline_yaml: Path to compiled pipeline YAML
        targets: JSON string of scraping targets
        config_path: Path to config YAML
        experiment_name: KFP experiment name
        run_name: Optional custom run name
    """
    import kfp
    from kfp import Client
    import datetime

    # Connect to KFP endpoint
    # Incluster: use in-cluster config
    # Local: use localhost port
    try:
        client = Client()
    except Exception:
        # Fallback to localhost
        client = Client(host="http://localhost:8888")

    # Create or get experiment
    try:
        experiment = client.get_experiment(experiment_name=experiment_name)
    except Exception:
        experiment = client.create_experiment(name=experiment_name)

    # Generate run name if not provided
    if run_name is None:
        run_name = f"ecommerce-run-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Submit pipeline run
    logger.info(f"Submitting pipeline run '{run_name}' to experiment '{experiment_name}'")

    run = client.run_pipeline(
        experiment_id=experiment.id,
        job_name=run_name,
        pipeline_package_path=pipeline_yaml,
        params={
            "targets": targets,
            "config_path": config_path,
        },
    )

    logger.info(f"Pipeline run submitted: {run.run_id}")
    logger.info(f"View at: {run.pipeline_url}")

    return run


def run_pipeline_local(
    pipeline_func,
    targets: str,
    config_path: str,
    output_dir: str = "data/pipeline_runs",
):
    """
    Run the pipeline locally using KFP's LocalExecutor (for testing).

    Args:
        pipeline_func: The pipeline function object
        targets: JSON string of scraping targets
        config_path: Path to config YAML
        output_dir: Directory to store run outputs
    """
    from kfp.dsl import LocalCollector
    import kfp.local

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Running pipeline locally, outputs to {output_dir}")

    # Directly invoke pipeline components in order
    # This bypasses KFP orchestration for local testing
    from src.pipelines.kubeflow.pipeline import (
        scrape_products_kfp,
        preprocess_data_kfp,
        train_models_kfp,
        select_top_k_kfp,
        generate_llm_summary_kfp,
    )

    # Execute step-by-step locally (simulating KFP)
    # You would normally use kfp.local.run but it's still experimental
    # Instead, we directly call component functions with proper I/O handling

    logger.info("Local execution not yet implemented - use Kubeflow CLI or submit to KFP server")
    logger.info("Recommended: Use 'kfp run submit' with compiled YAML")


def main():
    parser = argparse.ArgumentParser(
        description="Run the eCommerce ML pipeline with Kubeflow"
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Only compile the pipeline to YAML, don't run it",
    )
    parser.add_argument(
        "--pipeline-yaml",
        default="src/pipelines/kubeflow/pipeline.yaml",
        help="Path to compiled pipeline YAML",
    )
    parser.add_argument(
        "--targets-file",
        help="JSON file with scraping targets list",
    )
    parser.add_argument(
        "--targets",
        help="JSON string of scraping targets",
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Path to config YAML",
    )
    parser.add_argument(
        "--experiment",
        default="ecommerce-default",
        help="Kubeflow experiment name",
    )
    parser.add_argument(
        "--run-name",
        help="Custom run name (auto-generated if not provided)",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="Run locally (for testing, requires kfp local mode)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/pipeline_runs",
        help="Local output directory for local runs",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # Prepare targets
    try:
        targets_json = prepare_targets(args.targets_file, args.targets)
        logger.info(f"Prepared {len(json.loads(targets_json))} targets")
    except Exception as e:
        logger.error(f"Failed to parse targets: {e}")
        sys.exit(1)

    # Compile pipeline
    logger.info(f"Compiling pipeline to {args.pipeline_yaml}")
    compile_pipeline(args.pipeline_yaml)

    if args.compile_only:
        logger.info("Compilation complete. Use kubeflow CLI to submit.")
        return

    # Run pipeline
    if args.local:
        logger.info("Local execution selected (experimental)")
        from src.pipelines.kubeflow.pipeline import ecommerce_pipeline
        run_pipeline_local(
            pipeline_func=ecommerce_pipeline,
            targets=targets_json,
            config_path=args.config,
            output_dir=args.output_dir,
        )
    else:
        # Submit to KFP server
        run = run_pipeline_kfp(
            pipeline_yaml=args.pipeline_yaml,
            targets=targets_json,
            config_path=args.config,
            experiment_name=args.experiment,
            run_name=args.run_name,
        )
        logger.info(f"Pipeline run submitted successfully: {run.run_id}")


if __name__ == "__main__":
    main()
