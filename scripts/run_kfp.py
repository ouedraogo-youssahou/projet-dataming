#!/usr/bin/env python
"""Submit a Kubeflow pipeline run via SDK v2."""
from kfp import client

c = client.Client(host="http://127.0.0.1:57556")

# Get pipeline versions
pipeline_id = "687d9211-80f1-4172-a2f3-d6c872aab0e3"
versions = c.list_pipeline_versions(pipeline_id=pipeline_id).versions
print("Versions:", [(v.version_id, v.display_name) for v in versions])

if not versions:
    print("No versions found - need to upload properly")
    # Upload pipeline with version
    result = c.upload_pipeline(
        pipeline_package_path="src/pipelines/kubeflow/pipeline.yaml",
        pipeline_name="ecommerce-ml-pipeline",
    )
    print(f"Uploaded pipeline: {result.pipeline_id}, version: {result.version_id}")
    pipeline_id = result.pipeline_id
    version_id = result.version_id
else:
    version_id = versions[0].version_id

# Get or create experiment
exps = c.list_experiments().experiments
exp_id = None
for e in exps:
    if e.display_name == "ecommerce":
        exp_id = e.experiment_id
        break

if not exp_id:
    exp = c.create_experiment(name="ecommerce")
    exp_id = exp.experiment_id
    print(f"Created experiment: {exp_id}")

run = c.run_pipeline(
    experiment_id=exp_id,
    job_name="run-test-1",
    pipeline_id=pipeline_id,
    version_id=version_id,
)

print(f"Run submitted successfully!")
print(f"Run ID: {run.run_id}")