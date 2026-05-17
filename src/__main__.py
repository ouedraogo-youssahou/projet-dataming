import asyncio
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

# Scraping
from src.scraping.shopify_scraper import ShopifyScraper
from src.scraping.woocommerce_scraper import WooCommerceScraper
from src.scraping.selenium_scraper import SeleniumScraper
from src.scraping.playwright_scraper import PlaywrightScraper
from src.scraping.storage import PostgreSQLStorage

# Data analysis
from src.data_analysis.ml_models.clustering import ClusteringEngine
from src.data_analysis.ml_models.classification import ClassificationEngine
from src.data_analysis.ml_models.association import AssociationEngine

# LLM
from src.llm.wrapper import LLMWrapper
from src.llm.competitive_analysis import CompetitiveAnalysis

# MCP
from src.mcp.server import MCPServer

# Dashboard
from src.dashboard.app import run_dashboard


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Product:
    product_id: str
    name: str
    description: str
    category: str
    price: float
    currency: str = "USD"
    availability: bool = True
    quantity: Optional[int] = None
    vendor: Optional[str] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SmartECommerceIntelligence:
    """
    Main orchestrator for the Smart eCommerce Intelligence system.
    Handles scraping, analysis, LLM enrichment, MCP serving and dashboard.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.products: List[Product] = []

        # Scrapers
        self.shopify_scraper = ShopifyScraper(config.get("scraping", {}).get("shopify", {}))
        self.woocommerce_scraper = WooCommerceScraper(config.get("scraping", {}).get("woocommerce", {}))
        self.selenium_scraper = SeleniumScraper(config.get("scraping", {}).get("selenium", {}))
        self.playwright_scraper = PlaywrightScraper(config.get("scraping", {}).get("playwright", {}))

        # Storage
        self.storage = PostgreSQLStorage(config.get("database", {}).get("postgresql", {}))

        # ML Engines
        self.clustering = ClusteringEngine(config.get("data_analysis", {}).get("models", {}))
        self.classification = ClassificationEngine(config.get("data_analysis", {}).get("models", {}))
        self.association = AssociationEngine(config.get("data_analysis", {}).get("models", {}))

        # LLM (DeepSeek & Groq uniquement)
        llm_cfg = config.get("llm", {})
        self.llm = LLMWrapper(
            deepseek_key=llm_cfg.get("deepseek", {}).get("api_key"),
            groq_key=llm_cfg.get("groq", {}).get("api_key"),
            config=llm_cfg
        )

        # MCP Server
        self.mcp_server = MCPServer(
            mcp_config=config.get("mcp", {}),
            scraping_config=config.get("scraping", {}),
            llm_config=config.get("llm", {})
        )

    async def scrape_all(self, targets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run all scrapers on given targets."""
        results = []
        for target in targets:
            platform = target.get("platform")
            url = target.get("url")
            try:
                if platform == "shopify":
                    data = await self.shopify_scraper.scrape(url)
                elif platform == "woocommerce":
                    data = await self.woocommerce_scraper.scrape(url)
                elif platform == "generic":
                    data = await self.selenium_scraper.scrape(url)
                else:
                    data = await self.playwright_scraper.scrape(url)
                results.append({"platform": platform, "url": url, "data": data, "status": "ok"})
                logger.info(f"Scraped {url} ({platform})")
            except Exception as e:
                logger.error(f"Failed to scrape {url}: {e}")
                results.append({"platform": platform, "url": url, "error": str(e), "status": "error"})
        return results

    def analyze_top_k(self, products: List[Dict[str, Any]], k: int = 10, weights: Optional[Dict[str, float]] = None) -> List[Dict[str, Any]]:
        """Score products and return top-K."""
        if not products:
            return []

        default_weights = {
            "rating": 0.3,
            "reviews_count": 0.25,
            "price_competitiveness": 0.2,
            "availability": 0.15,
            "recency": 0.1,
        }
        weights = weights or default_weights

        # Normalize and score (simplified)
        scored = []
        max_price = max((p.get("price") or 0 for p in products if (p.get("price") or 0) > 0), default=1)
        max_rating = max((p.get("rating") or 0 for p in products), default=5)
        max_reviews = max((p.get("reviews_count") or 0 for p in products), default=1)

        for p in products:
            price = p.get("price") or 0
            rating = p.get("rating") or 0
            reviews = p.get("reviews_count") or 0
            available = 1 if (p.get("availability") or False) else 0
            # price_competitiveness: lower is better -> invert
            price_score = (1 - (price / max_price)) if max_price > 0 else 0
            rating_score = (rating / max_rating) if max_rating > 0 else 0
            reviews_score = (reviews / max_reviews) if max_reviews > 0 else 0

            score = (
                weights.get("rating", 0) * rating_score +
                weights.get("reviews_count", 0) * reviews_score +
                weights.get("price_competitiveness", 0) * price_score +
                weights.get("availability", 0) * available
                # recency omitted for simplicity
            )
            p2 = dict(p)
            p2["_score"] = round(score, 4)
            scored.append(p2)

        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored[:k]

    def cluster_products(self, products: List[Dict[str, Any]], n_clusters: int = 5) -> Dict[str, Any]:
        """Cluster products (features: price, rating, reviews)."""
        import numpy as np
        from sklearn.preprocessing import StandardScaler

        X = []
        for p in products:
            X.append([
                (p.get("price") or 0),
                (p.get("rating") or 0),
                (p.get("reviews_count") or 0),
            ])
        X = np.array(X)
        scaler = StandardScaler()
        Xs = scaler.fit_transform(X)

        labels = self.clustering.kmeans(Xs, n_clusters=n_clusters)
        return {
            "n_clusters": n_clusters,
            "labels": labels.tolist(),
            "inertia": float(self.clustering.last_inertia) if hasattr(self.clustering, "last_inertia") else None,
        }

    def generate_summary(self, products: List[Dict[str, Any]], top_k: List[Dict[str, Any]]) -> str:
        """Use LLM to generate a natural language summary."""
        if not products:
            return "No products to summarize."

        prompt = (
            "You are a smart eCommerce analyst. Summarize this product dataset and top-K selection in 3-4 sentences.\n"
            f"Total products: {len(products)}\n"
            f"Top products: {[p.get('name', 'Unknown') for p in top_k[:3]]}\n"
            "Focus on price range, ratings, availability, and main categories."
        )
        try:
            response = self.llm.complete(prompt, max_tokens=500)
            return response
        except Exception as e:
            logger.warning(f"LLM summary failed: {e}")
            return f"Could not generate LLM summary: {e}"

    def run_pipeline(self, targets: List[Dict[str, Any]], top_k_count: int = 10) -> Dict[str, Any]:
        """End-to-end pipeline."""
        logger.info("Starting end-to-end pipeline")
        # Scrape
        scrape_results = asyncio.run(self.scrape_all(targets))
        all_products = []
        for r in scrape_results:
            if r.get("status") == "ok" and "data" in r:
                # data could be a list or dict
                d = r["data"]
                if isinstance(d, list):
                    all_products.extend(d)
                elif isinstance(d, dict):
                    all_products.append(d)

        # If no products from scraping, return empty result
        if not all_products:
            logger.warning("No products scraped; returning empty result")
            return {
                "scrape_results": scrape_results,
                "top_k": [],
                "clusters": None,
                "summary": "No products scraped.",
            }

        # Top-K
        top_k = self.analyze_top_k(all_products, k=top_k_count)

        # Clustering
        clusters = self.cluster_products(all_products, n_clusters=min(5, len(all_products)))

        # LLM summary
        summary = self.generate_summary(all_products, top_k)

        logger.info("Pipeline completed")
        return {
            "scrape_results": scrape_results,
            "top_k": top_k,
            "clusters": clusters,
            "summary": summary,
        }

    async def store_results(self, products: List[Dict[str, Any]], source: str = "pipeline") -> int:
        """Store scraped products to PostgreSQL."""
        try:
            await self.storage.initialize()
            return await self.storage.store(products, source_url=source)
        except Exception as e:
            logger.error(f"Storage error: {e}")
            return 0


if __name__ == "__main__":
    import yaml
    from pathlib import Path
    from src.config import expand_config_vars

    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    config = expand_config_vars(config)

    engine = SmartECommerceIntelligence(config)

    # Example targets
    example_targets = [
        {"platform": "shopify", "url": "https://example-store.myshopify.com"},
        {"platform": "woocommerce", "url": "https://example-woo.com"},
    ]

    # Run pipeline (if you have real endpoints, they'll be scraped)
    result = engine.run_pipeline([], top_k_count=10)
    print("Top-K (empty if no data):", result["top_k"])
    print("Summary:", result["summary"])
