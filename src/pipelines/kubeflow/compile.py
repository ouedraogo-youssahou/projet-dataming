# ============================================
# Kubeflow Pipeline Compiler - Build YAML Manually
# Alternative to KFP compiler for environments without kfp installed
# ============================================

import yaml
from pathlib import Path
from typing import Dict, Any


def create_kubeflow_pipeline_yAML(
    output_path: str = "src/pipelines/kubeflow/pipeline.yaml",
    base_image: str = "datamining-dashboard:latest",
    config_mount_path: str = "/app/config",
    data_mount_path: str = "/app/data",
) -> str:
    """
    Create a Kubeflow pipeline YAML manifest directly.

    This creates an Argo Workflow-based pipeline compatible with Kubeflow Pipelines.

    Args:
        output_path: Where to save the YAML
        base_image: Docker image to use for all steps
        config_mount_path: Mount point for config volume
        data_mount_path: Mount point for data volume

    Returns:
        Path to created YAML file
    """
    workflow = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "generateName": "ecommerce-pipeline-",
            "annotations": {
                "pipelines.kubeflow.org/pipeline_spec": (
                    '{"description": "End-to-end eCommerce ML pipeline", '
                    '"name": "ecommerce-ml-pipeline", "version": "v1"}'
                )
            }
        },
        "spec": {
            "entrypoint": "ecommerce-pipeline",
            "templates": [
                {
                    "name": "ecommerce-pipeline",
                    "steps": [
                        [
                            {
                                "name": "scrape",
                                "template": "scrape-products",
                                "arguments": {
                                    "artifacts": [
                                        {
                                            "name": "output-data",
                                            "from": "{{tasks.scrape-products.outputs.artifacts.output-data}}"
                                        }
                                    ]
                                }
                            }
                        ],
                        [
                            {
                                "name": "preprocess",
                                "template": "preprocess-data",
                                "dependencies": ["scrape"],
                                "arguments": {
                                    "artifacts": [
                                        {
                                            "name": "input-data",
                                            "from": "{{tasks.scrape-products.outputs.artifacts.output-data}}"
                                        },
                                        {
                                            "name": "output-data",
                                            "from": "{{tasks.preprocess-data.outputs.artifacts.output-data}}"
                                        }
                                    ]
                                }
                            }
                        ],
                        [
                            {
                                "name": "train",
                                "template": "train-models",
                                "dependencies": ["preprocess"],
                                "arguments": {
                                    "artifacts": [
                                        {
                                            "name": "preprocessed-data",
                                            "from": "{{tasks.preprocess-data.outputs.artifacts.output-data}}"
                                        },
                                        {
                                            "name": "model-output",
                                            "from": "{{tasks.train-models.outputs.artifacts.model-output}}"
                                        }
                                    ]
                                }
                            }
                        ],
                        [
                            {
                                "name": "top-k",
                                "template": "select-top-k",
                                "dependencies": ["preprocess"],
                                "arguments": {
                                    "artifacts": [
                                        {
                                            "name": "preprocessed-data",
                                            "from": "{{tasks.preprocess-data.outputs.artifacts.output-data}}"
                                        },
                                        {
                                            "name": "top-k-output",
                                            "from": "{{tasks.select-top-k.outputs.artifacts.top-k-output}}"
                                        }
                                    ]
                                }
                            }
                        ],
                        [
                            {
                                "name": "summary",
                                "template": "generate-summary",
                                "dependencies": ["train", "top-k"],
                                "arguments": {
                                    "artifacts": [
                                        {
                                            "name": "scraped-data",
                                            "from": "{{tasks.scrape-products.outputs.artifacts.output-data}}"
                                        },
                                        {
                                            "name": "top-k-data",
                                            "from": "{{tasks.select-top-k.outputs.artifacts.top-k-output}}"
                                        },
                                        {
                                            "name": "summary-output",
                                            "from": "{{tasks.generate-summary.outputs.artifacts.summary-output}}"
                                        }
                                    ]
                                }
                            }
                        ]
                    ]
                },
                # ========================================
                # Template: Scrape Products
                # ========================================
                {
                    "name": "scrape-products",
                    "container": {
                        "image": base_image,
                        "command": ["python", "-m", "src.pipelines.kubeflow.scraping_component"],
                        "args": [
                            "--config_path", config_mount_path + "/config.yaml",
                            "--output_path", data_mount_path + "/raw/scraped_products.json",
                        ],
                        "env": [
                            {"name": "PYTHON_PATH", "value": "/app"},
                        ],
                        "volumeMounts": [
                            {"name": "config-volume", "mountPath": config_mount_path},
                            {"name": "data-volume", "mountPath": data_mount_path},
                        ]
                    },
                    "outputs": {
                        "artifacts": [
                            {
                                "name": "output-data",
                                "path": data_mount_path + "/raw/scraped_products.json",
                                "type": "dataset"
                            }
                        ]
                    }
                },
                # ========================================
                # Template: Preprocess Data
                # ========================================
                {
                    "name": "preprocess-data",
                    "container": {
                        "image": base_image,
                        "command": ["python", "-m", "src.pipelines.kubeflow.preprocessing_component"],
                        "args": [
                            "--input_path", data_mount_path + "/raw/scraped_products.json",
                            "--config_path", config_mount_path + "/config.yaml",
                            "--output_path", data_mount_path + "/processed/preprocessed_products.json",
                        ],
                        "volumeMounts": [
                            {"name": "config-volume", "mountPath": config_mount_path},
                            {"name": "data-volume", "mountPath": data_mount_path},
                        ]
                    },
                    "inputs": {
                        "artifacts": [
                            {
                                "name": "input-data",
                                "path": data_mount_path + "/raw/scraped_products.json"
                            }
                        ]
                    },
                    "outputs": {
                        "artifacts": [
                            {
                                "name": "output-data",
                                "path": data_mount_path + "/processed/preprocessed_products.json",
                                "type": "dataset"
                            }
                        ]
                    }
                },
                # ========================================
                # Template: Train Models
                # ========================================
                {
                    "name": "train-models",
                    "container": {
                        "image": base_image,
                        "command": ["python", "-c"],
                        "args": [
                            # Inline training script since we defined it in pipeline.py
                            "from src.pipelines.kubeflow.pipeline import train_models_kfp; "
                            "import sys; sys.path.insert(0, '/app'); "
                            "train_models_kfp("
                            "preprocessed_data='/app/data/processed/preprocessed_products.json',"
                            "config_path='/app/config/config.yaml',"
                            "model_output='/app/data/models/model_bundle.json'"
                            ")"
                        ],
                        "volumeMounts": [
                            {"name": "config-volume", "mountPath": config_mount_path},
                            {"name": "data-volume", "mountPath": data_mount_path},
                        ]
                    },
                    "inputs": {
                        "artifacts": [
                            {
                                "name": "preprocessed-data",
                                "path": data_mount_path + "/processed/preprocessed_products.json"
                            }
                        ]
                    },
                    "outputs": {
                        "artifacts": [
                            {
                                "name": "model-output",
                                "path": data_mount_path + "/models/model_bundle.json",
                                "type": "model"
                            }
                        ]
                    }
                },
                # ========================================
                # Template: Select Top-K
                # ========================================
                {
                    "name": "select-top-k",
                    "container": {
                        "image": base_image,
                        "command": ["python", "-c"],
                        "args": [
                            "from src.pipelines.kubeflow.pipeline import select_top_k_kfp; "
                            "import sys; sys.path.insert(0, '/app'); "
                            "select_top_k_kfp("
                            "preprocessed_data='/app/data/processed/preprocessed_products.json',"
                            "config_path='/app/config/config.yaml',"
                            "top_k_output='/app/data/analysis/top_k_products.json'"
                            ")"
                        ],
                        "volumeMounts": [
                            {"name": "config-volume", "mountPath": config_mount_path},
                            {"name": "data-volume", "mountPath": data_mount_path},
                        ]
                    },
                    "inputs": {
                        "artifacts": [
                            {
                                "name": "preprocessed-data",
                                "path": data_mount_path + "/processed/preprocessed_products.json"
                            }
                        ]
                    },
                    "outputs": {
                        "artifacts": [
                            {
                                "name": "top-k-output",
                                "path": data_mount_path + "/analysis/top_k_products.json",
                                "type": "dataset"
                            }
                        ]
                    }
                },
                # ========================================
                # Template: Generate LLM Summary
                # ========================================
                {
                    "name": "generate-summary",
                    "container": {
                        "image": base_image,
                        "command": ["python", "-c"],
                        "args": [
                            "from src.pipelines.kubeflow.pipeline import generate_llm_summary_kfp; "
                            "import sys; sys.path.insert(0, '/app'); "
                            "generate_llm_summary_kfp("
                            "scraped_data='/app/data/raw/scraped_products.json',"
                            "top_k_data='/app/data/analysis/top_k_products.json',"
                            "config_path='/app/config/config.yaml',"
                            "summary_output='/app/data/analysis/summary.txt'"
                            ")"
                        ],
                        "volumeMounts": [
                            {"name": "config-volume", "mountPath": config_mount_path},
                            {"name": "data-volume", "mountPath": data_mount_path},
                        ]
                    },
                    "inputs": {
                        "artifacts": [
                            {
                                "name": "scraped-data",
                                "path": data_mount_path + "/raw/scraped_products.json"
                            },
                            {
                                "name": "top-k-data",
                                "path": data_mount_path + "/analysis/top_k_products.json"
                            }
                        ]
                    },
                    "outputs": {
                        "artifacts": [
                            {
                                "name": "summary-output",
                                "path": data_mount_path + "/analysis/summary.txt",
                                "type": "text"
                            }
                        ]
                    }
                },
                # ========================================
                # Volumes
                # ========================================
                {
                    "name": "config-volume",
                    "persistentVolumeClaim": {
                        "claimName": "config-pvc"
                    }
                },
                {
                    "name": "data-volume",
                    "persistentVolumeClaim": {
                        "claimName": "data-pvc"
                    }
                }
            ],
            # tolerations and affinity for GKE/Azure can be added
        }
    }

    # Write YAML
    output_fp = Path(output_path)
    output_fp.parent.mkdir(parents=True, exist_ok=True)

    with open(output_fp, "w") as f:
        yaml.dump(workflow, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Kubeflow pipeline YAML written to: {output_fp}")
    print(f"   Components: scrape → preprocess → train → top-k → summary")
    print(f"   Image: {base_image}")

    return str(output_fp)


def create_kubeflow_components_yaml(
    output_path: str = "src/pipelines/kubeflow/components.yaml",
):
    """
    Create a separate components YAML for reuse.

    This defines each component as a reusable Kubeflow component.
    """
    components = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {"generateName": "ecommerce-components-"},
        "spec": {
            "entrypoint": "main",
            "templates": [
                {
                    "name": "main",
                    "steps": []  # empty - used as container
                },
                {
                    "name": "scrape-products",
                    "inputs": {
                        "parameters": [
                            {"name": "config_path"},
                            {"name": "targets_json"},
                        ],
                        "artifacts": [
                            {
                                "name": "output-data",
                                "path": "/app/data/output/scraped.json"
                            }
                        ]
                    },
                    "container": {
                        "image": "datamining-dashboard:latest",
                        "command": ["python", "-m", "src.pipelines.kubeflow.components.scraping_component"],
                        "args": [
                            "--config_path", "{{inputs.parameters.config_path}}",
                            "--targets_json", "{{inputs.parameters.targets_json}}",
                            "--output_path", "/app/data/output/scraped.json",
                        ],
                    },
                    "outputs": {
                        "artifacts": [
                            {
                                "name": "output-data",
                                "path": "/app/data/output/scraped.json"
                            }
                        ]
                    }
                },
                # Could define preprocess, train, top-k, summary similarly
            ]
        }
    }

    output_fp = Path(output_path)
    output_fp.parent.mkdir(parents=True, exist_ok=True)

    with open(output_fp, "w") as f:
        yaml.dump(components, f, default_flow_style=False)

    print(f"✅ Components YAML written to: {output_fp}")
    return str(output_fp)


if __name__ == "__main__":
    print("Generating Kubeflow pipeline YAML...")
    yaml_path = create_kubeflow_pipeline_yAML()
    print(f"Pipeline YAML created: {yaml_path}")

    print("\nGenerating components YAML...")
    comp_path = create_kubeflow_components_yaml()
    print(f"Components YAML created: {comp_path}")

    print("\nNext steps:")
    print("1. Validate: kfp pipeline validate --file", yaml_path)
    print("2. Upload to Kubeflow UI or submit via CLI:")
    print("   kfp run submit --pipeline-file", yaml_path)
