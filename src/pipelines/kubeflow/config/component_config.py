# ============================================
# Kubeflow Component Configuration Loader
# ============================================

import yaml
from pathlib import Path
from typing import Any, Dict, Optional


def load_pipeline_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """Load pipeline configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "pipeline_config.yaml"

    with open(config_path) as f:
        config = yaml.safe_load(f)

    return config


def get_component_config(config: Dict[str, Any], component_name: str) -> Dict[str, Any]:
    """Get configuration for a specific component."""
    return config.get("components", {}).get(component_name, {})


def get_pipeline_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get top-level pipeline configuration."""
    return config.get("pipeline", {})


def get_data_paths(config: Dict[str, Any]) -> Dict[str, str]:
    """Get data paths configuration."""
    return config.get("data", {})


def get_kubernetes_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Get Kubernetes configuration."""
    return config.get("kubernetes", {})