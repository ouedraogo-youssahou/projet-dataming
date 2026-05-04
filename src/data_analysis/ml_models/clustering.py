import logging
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class ClusteringEngine:
    """Clustering models: KMeans, DBSCAN, Hierarchical."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.last_inertia = None
        self.last_labels = None
        self.scaler = StandardScaler()

    def kmeans(self, X, n_clusters: int = 5, random_state: int = 42):
        """KMeans clustering."""
        X_scaled = self.scaler.fit_transform(X)
        model = KMeans(
            n_clusters=n_clusters,
            init="k-means++",
            n_init=10,
            max_iter=300,
            random_state=random_state,
        )
        labels = model.fit_predict(X_scaled)
        self.last_inertia = model.inertia_
        self.last_labels = labels
        return labels

    def dbscan(self, X, eps: float = 0.5, min_samples: int = 5):
        """DBSCAN clustering."""
        X_scaled = self.scaler.fit_transform(X)
        model = DBSCAN(eps=eps, min_samples=min_samples)
        labels = model.fit_predict(X_scaled)
        self.last_labels = labels
        return labels

    def hierarchical(self, X, n_clusters: int = 5):
        """Agglomerative hierarchical clustering."""
        X_scaled = self.scaler.fit_transform(X)
        model = AgglomerativeClustering(n_clusters=n_clusters)
        labels = model.fit_predict(X_scaled)
        self.last_labels = labels
        return labels

    def pca_transform(self, X, n_components: int = 2):
        """Reduce dimensions with PCA for visualization."""
        X_scaled = self.scaler.fit_transform(X)
        pca = PCA(n_components=n_components)
        return pca.fit_transform(X_scaled)

    def get_cluster_stats(self, labels) -> Dict[str, Any]:
        """Basic cluster statistics."""
        unique, counts = np.unique(labels, return_counts=True)
        return {
            "n_clusters": len(unique),
            "cluster_sizes": dict(zip(unique.astype(int).tolist(), counts.tolist())),
            "noise_points": int(np.sum(labels == -1)) if -1 in unique else 0,
        }
