import logging
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score
from src.data_analysis.ml_models.clustering import ClusteringEngine
from src.data_analysis.ml_models.classification import ClassificationEngine
from src.data_analysis.ml_models.association import AssociationEngine

logger = logging.getLogger(__name__)


def evaluate_clustering(X, labels) -> Dict[str, Any]:
    """Compute clustering quality metrics."""
    metrics = {}
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    metrics["n_clusters"] = n_clusters
    metrics["n_noise"] = int(np.sum(labels == -1)) if -1 in labels else 0

    # Require at least 2 clusters and enough samples
    if n_clusters >= 2 and X.shape[0] > n_clusters:
        try:
            metrics["silhouette"] = silhouette_score(X, labels)
        except Exception:
            metrics["silhouette"] = None
        try:
            metrics["calinski_harabasz"] = calinski_harabasz_score(X, labels)
        except Exception:
            metrics["calinski_harabasz"] = None
        try:
            metrics["davies_bouldin"] = davies_bouldin_score(X, labels)
        except Exception:
            metrics["davies_bouldin"] = None
    else:
        metrics["silhouette"] = None
        metrics["calinski_harabasz"] = None
        metrics["davies_bouldin"] = None

    return metrics


def evaluate_classification(y_true, y_pred, y_proba=None, average='weighted'):
    """Return classification metrics."""
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, average=average, zero_division=0)
    rec = recall_score(y_true, y_pred, average=average, zero_division=0)
    f1 = f1_score(y_true, y_pred, average=average, zero_division=0)
    metrics = {"accuracy": acc, "precision": prec, "recall": rec, "f1": f1}
    if y_proba is not None:
        try:
            roc = roc_auc_score(y_true, y_proba, multi_class='ovr')
            metrics["roc_auc"] = roc
        except Exception:
            metrics["roc_auc"] = None
    return metrics


def evaluate_association(rules_df, min_lift=1.0):
    """Summarize association rules."""
    if rules_df.empty:
        return {"n_rules": 0, "mean_confidence": 0, "mean_lift": 0}
    filtered = rules_df[rules_df['lift'] >= min_lift]
    return {
        "n_rules": len(filtered),
        "mean_confidence": filtered['confidence'].mean(),
        "mean_lift": filtered['lift'].mean(),
        "max_lift": filtered['lift'].max(),
    }


def product_features_to_df(products: List[Dict[str, Any]], feature_cols: Optional[List[str]] = None):
    """Convert product list to DataFrame for analysis."""
    if not products:
        return pd.DataFrame()
    df = pd.DataFrame(products)
    # Ensure numeric cols are numeric
    if feature_cols is None:
        feature_cols = [c for c in df.columns if df[c].dtype.kind in 'iufc']
    for c in feature_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
    return df
