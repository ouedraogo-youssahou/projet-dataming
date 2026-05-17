# Point d'entrée pour le service scraper : soumet la pipeline Kubeflow
# Au lieu de scraper directement (redondant avec le composant 1 de KFP),
# ce script compile et soumet la pipeline complète à Kubeflow sur Minikube.
# La pipeline se charge du scraping, du ML, du LLM, et du stockage en PostgreSQL.
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Soumet la pipeline Kubeflow complète : scraping → ML → LLM → PostgreSQL."""
    from kfp import client, compiler

    # Déterminer l'hôte Kubeflow (depuis env ou host.docker.internal pour l'accès conteneur→hôte)
    kfp_host = os.getenv("KFP_HOST", "http://host.docker.internal:61567")
    pipeline_yaml = str(Path(__file__).parent.parent.parent / "src/pipelines/kubeflow/pipeline.yaml")

    # Compiler la pipeline
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.pipelines.kubeflow.pipeline import ecommerce_pipeline

    logger.info(f"Compilation de la pipeline vers {pipeline_yaml}")
    compiler.Compiler().compile(pipeline_func=ecommerce_pipeline, package_path=pipeline_yaml)

    # Récupérer les credentials WooCommerce depuis l'environnement
    woo_url = os.getenv("WOOCOMMERCE_STORE_URL", "")
    consumer_key = os.getenv("WOOCOMMERCE_CONSUMER_KEY", "")
    consumer_secret = os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "")
    groq_key = os.getenv("GROQ_API_KEY", "")

    if not woo_url or not consumer_key or not consumer_secret:
        logger.error("WOOCOMMERCE_STORE_URL, WOOCOMMERCE_CONSUMER_KEY, WOOCOMMERCE_CONSUMER_SECRET requis dans .env")
        sys.exit(1)

    logger.info(f"Connexion à Kubeflow: {kfp_host}")
    c = client.Client(host=kfp_host)

    # Uploader la pipeline
    run_id_str = datetime.now().strftime("%Y%m%d-%H%M%S")
    pipeline_name = f"ecommerce-ml-pipeline-{run_id_str}"
    result = c.upload_pipeline(pipeline_package_path=pipeline_yaml, pipeline_name=pipeline_name)
    pid = result.pipeline_id if hasattr(result, 'pipeline_id') else result.id
    logger.info(f"Pipeline uploadée: {pid} ({pipeline_name})")

    # Paramètres à passer à la pipeline
    params = {
        "woo_url": woo_url,
        "consumer_key": consumer_key,
        "consumer_secret": consumer_secret,
        "groq_api_key": groq_key,
        "targets": "[]",
    }

    # Soumettre un run
    job_name = f"ecommerce-run-{run_id_str}"
    logger.info(f"Soumission du run: {job_name}")
    run = c.run_pipeline(
        experiment_id=os.getenv("KFP_EXPERIMENT_ID", "2ddcd9a8-8a77-43bc-a239-41874f7f7918"),
        job_name=job_name,
        pipeline_package_path=pipeline_yaml,
        params=params,
    )
    rid = run.run_id if hasattr(run, 'run_id') else run.id
    logger.info(f"Run soumis: {rid}")
    logger.info(f"URL: {kfp_host}/#/runs/details/{rid}")


if __name__ == "__main__":
    main()