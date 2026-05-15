# ============================================
# Smart eCommerce Intelligence - Pipelines Module
# ============================================

from .kubeflow.pipeline import ecommerce_pipeline as ecommerce_ml_pipeline

__all__ = [
    "ecommerce_ml_pipeline",
]
