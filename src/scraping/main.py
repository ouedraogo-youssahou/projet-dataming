# Point d'entrée pour le service scraper
import asyncio
import sys
import logging


from src.__main__ import SmartECommerceIntelligence

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    import yaml
    from pathlib import Path
    
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    engine = SmartECommerceIntelligence(config)
    
    # Test simple
    targets = [{"platform": "shopify", "url": "https://storefront-demo.myshopify.com"}]
    result = engine.run_pipeline(targets, top_k_count=5)
    print("Pipeline result:", result["top_k"])