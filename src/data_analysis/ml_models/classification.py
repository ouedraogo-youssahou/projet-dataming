import logging
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    mean_squared_error,
    r2_score,
)
from sklearn.preprocessing import LabelEncoder, StandardScaler

logger = logging.getLogger(__name__)


class ClassificationEngine:
    """Classification and regression models for product success prediction."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.models = {}
        self.label_encoders = {}
        self.scaler = StandardScaler()

    def prepare_features(
        self,
        products: List[Dict[str, Any]],
        feature_cols: Optional[List[str]] = None,
        target_col: Optional[str] = None,
    ):
        """Convert list of product dicts to X, y numpy arrays."""
        if not products:
            return None, None, []

        default_features = ["price", "rating", "reviews_count", "quantity"]
        feature_cols = feature_cols or default_features

        X_rows = []
        y_vals = []
        used_features = []

        # Build feature list from available keys
        for p in products:
            row = []
            ok = True
            for f in feature_cols:
                if f in p:
                    val = p[f]
                    if val is None:
                        val = 0
                    try:
                        row.append(float(val))
                    except (ValueError, TypeError):
                        # Try encode categorical
                        if f not in self.label_encoders:
                            self.label_encoders[f] = LabelEncoder()
                            # collect all possible values first - simplified: use 0
                            row.append(0.0)
                        else:
                            try:
                                le = self.label_encoders[f]
                                row.append(float(le.transform([str(val)])[0]))
                            except Exception:
                                row.append(0.0)
                else:
                    # feature missing
                    row.append(0.0)
            X_rows.append(row)
            used_features = feature_cols

            if target_col and target_col in p:
                y = p[target_col]
                if isinstance(y, (int, float)):
                    y_vals.append(float(y))
                else:
                    y_vals.append(y)
            elif target_col:
                y_vals.append(None)

        X = np.array(X_rows)
        y = np.array(y_vals) if y_vals else None

        if y is not None and len(y) == len(X):
            # remove rows where y is None
            mask = np.array([yi is not None for yi in y])
            X = X[mask]
            y = y[mask]

        return X, y, used_features

    def train_classifier(
        self,
        X,
        y,
        model_type: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
    ):
        """Train a classification model and return metrics."""
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y if len(np.unique(y)) < 50 else None
        )

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        if model_type == "random_forest":
            model = RandomForestClassifier(n_estimators=100, max_depth=10, min_samples_split=5, random_state=random_state)
        elif model_type == "xgboost":
            model = XGBClassifier(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=random_state, use_label_encoder=False, eval_metric='logloss')
        elif model_type == "logistic":
            model = LogisticRegression(random_state=random_state, max_iter=1000)
        elif model_type == "gradient_boosting":
            model = GradientBoostingClassifier(n_estimators=100, random_state=random_state)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)

        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, average='weighted', zero_division=0)
        rec = recall_score(y_test, y_pred, average='weighted', zero_division=0)
        f1 = f1_score(y_test, y_pred, average='weighted', zero_division=0)

        try:
            roc = roc_auc_score(y_test, model.predict_proba(X_test_scaled), multi_class='ovr')
        except Exception:
            roc = None

        self.models[model_type] = model

        return {
            "model_type": model_type,
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1": f1,
            "roc_auc": roc,
            "n_train": len(X_train),
            "n_test": len(X_test),
        }

    def train_regressor(
        self,
        X,
        y,
        model_type: str = "random_forest",
        test_size: float = 0.2,
        random_state: int = 42,
    ):
        """Train a regression model and return metrics."""
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        if model_type == "random_forest":
            model = RandomForestRegressor(n_estimators=100, max_depth=10, min_samples_split=5, random_state=random_state)
        elif model_type == "xgboost":
            model = XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=random_state)
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)

        mse = mean_squared_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        self.models[model_type] = model

        return {
            "model_type": model_type,
            "mse": mse,
            "rmse": np.sqrt(mse),
            "r2": r2,
            "n_train": len(X_train),
            "n_test": len(X_test),
        }

    def predict(self, X, model_type="random_forest"):
        model = self.models.get(model_type)
        if model is None:
            raise ValueError(f"Model {model_type} not trained")
        X_scaled = self.scaler.transform(X)
        return model.predict(X_scaled)
