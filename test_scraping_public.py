#!/usr/bin/env python3
"""
Test script: Scrape public demo eCommerce stores and store raw data in PostgreSQL.
Uses publicly available demo stores (no API keys required).
"""

import asyncio
import logging
import yaml
from pathlib import Path

from src.__main__ import SmartECommerceIntelligence

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Public demo stores that can be scraped without authentication
# These are real public demo stores used for testing
PUBLIC_TARGETS = [
    # Shopify demo store (publicly accessible product page)
    {
        "platform": "shopify",
        "url": "https://row.gymshark.com",
        "note": "Gymshark demo store (public)"
    },
    # WooCommerce demo store
    {
        "platform": "woocommerce",
        "url": "https://woocommerce-496176-1697635.cloudwaysapps.com",
        "note": "WooCommerce public demo store"
    },
    # Another public Shopify store
    {
        "platform": "shopify",
        "url": "https://allbirds.com",
        "note": "Allbirds - public Shopify store"
    },
]

# Fallback: Use generic scraping for sites without structured APIs
GENERIC_TARGETS = [
    {
        "platform": "generic",
        "url": "https://example.com",
        "note": "Generic HTML fallback test"
    },
]


async def test_and_store():
    """Load config, run scraping pipeline, and store in PostgreSQL."""
    
    # Load configuration
    config_path = Path(__file__).parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # Override database settings to use Docker PostgreSQL
    config["database"]["postgresql"]["host"] = "localhost"
    config["database"]["postgresql"]["port"] = 5432
    config["database"]["postgresql"]["user"] = "postgres"
    config["database"]["postgresql"]["password"] = "postgres"
    
    # Disable LLM and MCP for testing (no keys needed)
    config["llm"]["openai"]["api_key"] = None
    config["llm"]["anthropic"]["api_key"] = None
    config["mcp"]["security"]["api_key"] = None
    
    logger.info("=" * 70)
    logger.info("TEST SCRAPING + POSTGRESQL STORAGE")
    logger.info("=" * 70)
    
    # Initialize engine
    engine = SmartECommerceIntelligence(config)
    
    # Initialize storage
    try:
        logger.info("Initializing PostgreSQL storage...")
        await engine.storage.initialize()
        logger.info("✓ PostgreSQL connected and tables ready")
    except Exception as e:
        logger.error(f"Failed to initialize storage: {e}")
        return
    
    # Test 1: Run scraping pipeline on public targets
    logger.info("\n" + "=" * 70)
    logger.info("TEST 1: Scraping public demo stores")
    logger.info("=" * 70)
    
    # Use only a few targets for quick testing
    test_targets = PUBLIC_TARGETS[:1]  # Just one for quick test
    
    logger.info(f"Scraping {len(test_targets)} public stores...")
    scrape_results = await engine.scrape_all(test_targets)
    
    logger.info(f"\nScrape results summary:")
    for r in scrape_results:
        status = r.get("status", "unknown")
        platform = r.get("platform", "unknown")
        url = r.get("url", "unknown")
        note = r.get("note", "")
        logger.info(f"  [{status.upper():6s}] {platform:12s} | {url}")
        if note:
            logger.info(f"            Note: {note}")
    
    # Collect all scraped products
    all_products = []
    for r in scrape_results:
        if r.get("status") == "ok" and "data" in r:
            data = r["data"]
            if isinstance(data, list):
                all_products.extend(data)
            elif isinstance(data, dict):
                all_products.append(data)
    
    logger.info(f"\nTotal products scraped: {len(all_products)}")
    
    if all_products:
        # Show sample of scraped data
        logger.info("\nSample scraped product:")
        sample = all_products[0]
        for key, val in list(sample.items())[:10]:
            logger.info(f"  {key}: {val}")
    
    # Test 2: Store in PostgreSQL
    logger.info("\n" + "=" * 70)
    logger.info("TEST 2: Storing raw data in PostgreSQL")
    logger.info("=" * 70)
    
    if all_products:
        stored_count = await engine.store_results(all_products, source="public_demo_test")
        logger.info(f"✓ Stored {stored_count} products in PostgreSQL")
        
        # Verify storage
        fetched = await engine.storage.fetch_all(limit=10)
        logger.info(f"✓ Verified: {len(fetched)} total products in database")
        
        # Show what's in the database
        if fetched:
            logger.info("\nSample from database:")
            for p in fetched[:3]:
                logger.info(f"  - {p.get('name', 'N/A')[:40]:40s} | ${p.get('price', 0):8.2f} | {p.get('category', 'N/A')[:20]}")
    else:
        logger.warning("No products to store. Creating synthetic test data...")
        
        # Create synthetic test products for storage test
        synthetic_products = [
            {
                "product_id": "TEST-001",
                "name": "Test Wireless Headphones",
                "description": "High-quality wireless headphones for testing",
                "category": "Electronics",
                "price": 79.99,
                "currency": "USD",
                "availability": True,
                "quantity": 50,
                "vendor": "TestVendor",
                "rating": 4.5,
                "reviews_count": 234,
                "images": [],
                "tags": ["test", "wireless", "audio"],
                "source_url": "synthetic_test",
            },
            {
                "product_id": "TEST-002",
                "name": "Running Shoes Pro",
                "description": "Professional running shoes for athletes",
                "category": "Sport",
                "price": 129.99,
                "currency": "USD",
                "availability": True,
                "quantity": 30,
                "vendor": "TestVendor",
                "rating": 4.8,
                "reviews_count": 567,
                "images": [],
                "tags": ["test", "sport", "running"],
                "source_url": "synthetic_test",
            },
        ]
        
        stored_count = await engine.store_results(synthetic_products, source="synthetic_test")
        logger.info(f"✓ Stored {stored_count} synthetic test products in PostgreSQL")
        
        # Verify
        fetched = await engine.storage.fetch_all(limit=10)
        logger.info(f"✓ Total products in database: {len(fetched)}")
    
    # Test 3: Run Top-K analysis on stored data
    logger.info("\n" + "=" * 70)
    logger.info("TEST 3: Top-K analysis on stored products")
    logger.info("=" * 70)
    
    if all_products or synthetic_products:
        source_products = all_products if all_products else synthetic_products
        top_k = engine.analyze_top_k(source_products, k=5)
        logger.info(f"\nTop 5 products by score:")
        for i, p in enumerate(top_k, 1):
            logger.info(f"  {i}. {p.get('name', 'N/A')[:35]:35s} | Score: {p.get('_score', 0):.4f} | ${p.get('price', 0):.2f}")
    
    # Cleanup
    await engine.storage.close()
    logger.info("\n" + "=" * 70)
    logger.info("TESTS COMPLETE")
    logger.info("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_and_store())
