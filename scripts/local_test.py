#!/usr/bin/env python3
"""Quick local test of core imports and minimal pipeline."""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    from scraping.shopify_scraper import ShopifyScraper
    from scraping.woocommerce_scraper import WooCommerceScraper
    from scraping.selenium_scraper import SeleniumScraper
    from scraping.playwright_scraper import PlaywrightScraper
    from data_analysis.ml_models.clustering import ClusteringEngine
    from data_analysis.ml_models.classification import ClassificationEngine
    from data_analysis.ml_models.association import AssociationEngine
    from llm.wrapper import LLMWrapper
    from mcp.server import MCPServer
    from dashboard.app import render_header
    print("✅ All imports succeeded.")

def test_minimal_pipeline():
    from src.__main__ import SmartECommerceIntelligence
    import yaml
    cfg_path = Path(__file__).parent / "config" / "config.yaml"
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    engine = SmartECommerceIntelligence(cfg)
    # Use empty targets to avoid external calls
    result = engine.run_pipeline([], top_k_count=5)
    print(f"✅ Pipeline completed. Result keys: {list(result.keys())}")
    print(f"   Top-K sample: {result['top_k'][:2] if result['top_k'] else '[]'}")

if __name__ == "__main__":
    test_imports()
    test_minimal_pipeline()
    print("\n🎉 All local checks passed.")
