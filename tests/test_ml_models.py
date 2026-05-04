import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.data_analysis.ml_models.clustering import ClusteringEngine
from src.data_analysis.ml_models.classification import ClassificationEngine
from src.data_analysis.ml_models.association import AssociationEngine

import numpy as np


def test_clustering_kmeans():
    engine = ClusteringEngine()
    X = np.random.randn(100, 3)
    labels = engine.kmeans(X, n_clusters=3)
    assert len(labels) == 100
    assert len(set(labels)) == 3

def test_clustering_dbscan():
    engine = ClusteringEngine()
    X = np.random.randn(50, 2)
    labels = engine.dbscan(X, eps=0.5, min_samples=2)
    assert len(labels) == 50

def test_classification_fit():
    engine = ClassificationEngine()
    X = np.random.randn(100, 4)
    y = np.random.randint(0, 2, 100)
    result = engine.train_classifier(X, y, model_type="random_forest", test_size=0.3)
    assert "accuracy" in result
    assert 0 <= result["accuracy"] <= 1

def test_association_rules():
    engine = AssociationEngine()
    transactions = [["milk", "bread"], ["milk", "diapers"], ["bread", "diapers"], ["milk", "bread", "diapers"]]
    out = engine.find_rules(transactions, min_support=0.1, min_confidence=0.5)
    assert "rules" in out
    assert "summary" in out

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
