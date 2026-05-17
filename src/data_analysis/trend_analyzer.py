"""
Trend Analysis Module - Version Professionnelle
================================================
Analyse de tendances eCommerce avancée utilisant :
- Prophet (prévision temporelle)
- XGBoost (détection de produits trending)
- LinearRegression (fallback)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# === Imports optionnels ===
try:
    from prophet import Prophet
    HAS_PROPHET = True
except ImportError:
    HAS_PROPHET = False

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


class TrendAnalyzer:
    """Analyseur de tendances eCommerce complet et professionnel."""

    def __init__(self):
        self.scaler = StandardScaler()
        self.trending_model = None
        self.feature_cols = ["price", "rating", "reviews_count"]

    # ============================================================
    # 1. Tendance des Prix par Catégorie (Prophet)
    # ============================================================
    def analyze_price_trend(
        self,
        prices: List[float],
        timestamps: Optional[List[datetime]] = None
    ) -> Dict[str, Any]:
        """Analyse la tendance des prix (growing / stable / declining) + prévision."""
        if len(prices) < 5:
            return {"trend": "insufficient_data", "slope": 0.0}

        prices = np.array(prices[-100:])

        if timestamps is None:
            timestamps = [datetime.now() - timedelta(days=i) for i in range(len(prices)-1, -1, -1)]

        df = pd.DataFrame({"ds": timestamps, "y": prices}).sort_values("ds")

        forecast_data = None
        if HAS_PROPHET:
            try:
                # Option 1: Floor = prix minimum observé + limitation de pente réaliste
                min_price = float(np.min(prices))
                avg_price = float(np.mean(prices))
                
                # Ajouter floor pour éviter les prix négatifs
                df['floor'] = min_price
                df['cap'] = avg_price * 2  # Cap à 2x le prix moyen
                
                model = Prophet(
                    interval_width=0.95,
                    daily_seasonality=False,
                    growth='logistic',
                    changepoint_prior_scale=0.05  # Moins sensible aux changements brusques
                )
                model.fit(df)
                future = model.make_future_dataframe(periods=30)
                future['floor'] = min_price
                future['cap'] = avg_price * 2
                forecast = model.predict(future)
                
                # Calculer la pente
                raw_slope = (forecast['yhat'].iloc[-1] - forecast['yhat'].iloc[0]) / len(prices)
                
                # Limiter la pente maximale de baisse (max -10% du prix moyen par mois)
                max_decline_per_day = -(avg_price * 0.10) / 30  # -10% par mois max
                slope = max(raw_slope, max_decline_per_day)
                
                # Extraire les données de prévision avec floor appliqué
                forecast_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(30)
                forecast_values = [max(min_price, v) for v in forecast_df['yhat'].round(2).tolist()]
                forecast_lower = [max(min_price, v) for v in forecast_df['yhat_lower'].round(2).tolist()]
                forecast_upper = [max(min_price, v) for v in forecast_df['yhat_upper'].round(2).tolist()]
                
                forecast_data = {
                    "dates": forecast_df['ds'].dt.strftime('%Y-%m-%d').tolist(),
                    "values": forecast_values,
                    "lower": forecast_lower,
                    "upper": forecast_upper
                }
            except Exception:
                slope = self._linear_slope(prices)
        else:
            slope = self._linear_slope(prices)

        normalized = slope / (np.mean(prices) + 1e-6)

        if normalized > 0.015:
            trend = "growing"
        elif normalized < -0.015:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "slope": float(slope),
            "normalized_slope": float(normalized),
            "current_price": float(prices[-1]),
            "avg_price": float(np.mean(prices)),
            "forecast_available": HAS_PROPHET and forecast_data is not None,
            "forecast": forecast_data,
            "historical_dates": [ts.strftime('%Y-%m-%d') for ts in timestamps[-30:]],
            "historical_prices": [float(p) for p in prices[-30:].tolist()]
        }

    def analyze_category_price_trends(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse et prédit la tendance des prix par catégorie."""
        from collections import defaultdict
        
        if not products:
            return {"category_trends": {}, "category_forecasts": {}}
        
        # Group products by category
        categories = defaultdict(list)
        for p in products:
            cat = p.get('category', 'Unknown')
            if 'price' in p:
                categories[cat].append(p['price'])
        
        category_trends = {}
        category_forecasts = {}
        
        for cat, prices in categories.items():
            if len(prices) >= 5:
                result = self.analyze_price_trend(prices)
                category_trends[cat] = {
                    "trend": result["trend"],
                    "avg_price": result["avg_price"],
                    "count": len(prices)
                }
                if result.get("forecast"):
                    category_forecasts[cat] = result["forecast"]
        
        return {
            "category_trends": category_trends,
            "category_forecasts": category_forecasts
        }

    def _linear_slope(self, values: np.ndarray) -> float:
        X = np.arange(len(values)).reshape(-1, 1)
        model = LinearRegression().fit(X, values)
        return float(model.coef_[0])

    # ============================================================
    # 2. Tendance de Popularité (Reviews + Rating)
    # ============================================================
    def analyze_popularity_trend(
        self,
        reviews_count: List[int],
        ratings: List[float]
    ) -> Dict[str, Any]:
        """Analyse l'évolution de la popularité."""
        if len(reviews_count) < 5:
            return {"review_trend": "insufficient_data", "rating_trend": "insufficient_data"}

        reviews = np.array(reviews_count)
        ratings_arr = np.array(ratings)

        review_slope = self._linear_slope(reviews)
        rating_slope = self._linear_slope(ratings_arr)

        review_trend = "increasing" if review_slope > 2 else "decreasing" if review_slope < -2 else "stable"
        rating_trend = "improving" if rating_slope > 0.04 else "declining" if rating_slope < -0.04 else "stable"

        return {
            "review_trend": review_trend,
            "rating_trend": rating_trend,
            "review_slope": float(review_slope),
            "rating_slope": float(rating_slope),
            "total_reviews": int(reviews.sum()),
            "avg_rating": float(np.mean(ratings_arr))
        }

    # ============================================================
    # 3. Tendance par Catégorie
    # ============================================================
    def analyze_category_trends(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Identifie les catégories en hausse et en baisse."""
        if not products:
            return {"rising": [], "declining": []}

        df = pd.DataFrame(products)
        if "category" not in df.columns:
            return {"rising": [], "declining": []}

        stats = df.groupby("category").agg({
            "price": ["count", "mean"],
            "rating": "mean",
            "reviews_count": "sum" if "reviews_count" in df.columns else "count"
        }).reset_index()

        stats.columns = ["category", "count", "avg_price", "avg_rating", "total_reviews"]

        mean_count = stats["count"].mean()
        rising = stats[(stats["count"] > mean_count * 1.3) | (stats["avg_rating"] > 4.2)]["category"].tolist()
        declining = stats[(stats["count"] < mean_count * 0.6) & (stats["avg_rating"] < 3.5)]["category"].tolist()

        return {
            "rising": rising[:6],
            "declining": declining[:6]
        }

    # ============================================================
    # 4. Détection de Produits Trending (XGBoost)
    # ============================================================
    def train_trending_model(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Entraîne un modèle XGBoost pour prédire les produits trending."""
        if not HAS_XGBOOST or len(products) < 50:
            return {"status": "skipped", "reason": "XGBoost not available or insufficient data"}

        df = pd.DataFrame(products)
        if not all(col in df.columns for col in self.feature_cols):
            return {"status": "error", "reason": "Missing required columns"}

        X = df[self.feature_cols].fillna(0).values
        y = ((df["rating"] > 4.0) & (df["reviews_count"] > df["reviews_count"].median())).astype(int).values

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1,
            use_label_encoder=False,
            eval_metric="logloss"
        )
        model.fit(X_train, y_train)

        acc = accuracy_score(y_test, model.predict(X_test))
        self.trending_model = model

        return {"status": "trained", "accuracy": round(acc, 3)}

    def predict_trending_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prédit les produits les plus susceptibles de devenir trending."""
        if not self.trending_model:
            return products

        df = pd.DataFrame(products)
        X = df[self.feature_cols].fillna(0).values
        df["trending_score"] = self.trending_model.predict_proba(X)[:, 1]

        return df.sort_values("trending_score", ascending=False).to_dict("records")


# ============================================================
# Fonction utilitaire pour le Dashboard
# ============================================================
def generate_trend_insights(products: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Point d'entrée simple pour le dashboard."""
    analyzer = TrendAnalyzer()
    insights = {
        "generated_at": datetime.now().isoformat(),
        "total_products": len(products),
    }

    if not products:
        return insights

    # Prix par catégorie + Prophet
    category_prices = analyzer.analyze_category_price_trends(products)
    insights["category_price_trends"] = category_prices["category_trends"]
    insights["category_price_forecasts"] = category_prices["category_forecasts"]
    insights["prophet_used"] = HAS_PROPHET and len(category_prices["category_forecasts"]) > 0
    
    # Tendance globale simple (linéaire) pour l'affichage principal
    all_prices = [p.get("price", 0) for p in products]
    insights["price_trend"] = analyzer.analyze_price_trend(all_prices)

    # Popularité
    insights["popularity_trend"] = analyzer.analyze_popularity_trend(
        [p.get("reviews_count", 0) for p in products],
        [p.get("rating", 0) for p in products]
    )

    # Catégories
    insights["category_trend"] = analyzer.analyze_category_trends(products)

    # XGBoost - Produits Trending
    if HAS_XGBOOST and len(products) >= 30:
        train_result = analyzer.train_trending_model(products)
        if train_result.get("status") == "trained":
            trending = analyzer.predict_trending_products(products)[:5]
            insights["trending_products"] = [
                {
                    "name": p.get("name", "Unknown"),
                    "category": p.get("category", ""),
                    "score": round(p.get("trending_score", 0), 3)
                }
                for p in trending
            ]
            insights["xgboost_accuracy"] = train_result.get("accuracy")

    return insights


__all__ = [
    "TrendAnalyzer",
    "generate_trend_insights",
    "analyze_price_trend",
    "analyze_popularity_trend",
    "analyze_category_trends",
]
