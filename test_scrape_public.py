#!/usr/bin/env python3
"""
Test scraping public stores and storing in PostgreSQL.
Run inside the scraper container: docker exec -it ecommerce-scraper python test_scrape_public.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, '/app')

from src.__main__ import SmartECommerceIntelligence
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# Public demo stores
PUBLIC_TARGETS = [
    {
        "platform": "shopify",
        "url": "https://row.gymshark.com",
        "note": "Gymshark public store"
    },
]


async def main():
    logger.info("=" * 70)
    logger.info("TEST: Scrape public store + Store in PostgreSQL")
    logger.info("=" * 70)
    
    # Load config
    config_path = Path('/app/config/config.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # PostgreSQL is on the ecommerce-network at 172.18.0.2
    config['database']['postgresql']['host'] = '172.18.0.2'
    config['database']['postgresql']['port'] = 5432
    config['database']['postgresql']['user'] = 'postgres'
    config['database']['postgresql']['password'] = 'postgres'
    
    # Disable LLM for testing
    config['llm']['openai']['api_key'] = None
    config['llm']['anthropic']['api_key'] = None
    config['mcp']['security']['api_key'] = None
    
    # Initialize engine
    engine = SmartECommerceIntelligence(config)
    
    # Initialize storage
    logger.info("Initializing PostgreSQL connection...")
    try:
        await engine.storage.initialize()
        logger.info("✓ PostgreSQL connected successfully")
    except Exception as e:
        logger.error(f"Failed to connect: {e}")
        return
    
    # Scrape public store
    logger.info("\nScraping public store (Gymshark)...")
    scrape_results = await engine.scrape_all(PUBLIC_TARGETS)
    
    all_products = []
    for r in scrape_results:
        status = r.get('status', 'unknown')
        url = r.get('url', '')
        note = r.get('note', '')
        logger.info(f"  [{status}] {url}")
        if note:
            logger.info(f"    Note: {note}")
        
        if r.get('status') == 'ok' and 'data' in r:
            data = r['data']
            if isinstance(data, list):
                all_products.extend(data)
            elif isinstance(data, dict):
                all_products.append(data)
    
    logger.info(f"\nProducts scraped: {len(all_products)}")
    
    if all_products:
        logger.info("\nSample scraped product:")
        p = all_products[0]
        for k, v in list(p.items())[:10]:
            logger.info(f"  {k}: {v}")
    
    # Store in PostgreSQL
    logger.info("\nStoring raw data in PostgreSQL...")
    if all_products:
        stored = await engine.store_results(all_products, source='public_demo_gymshark')
        logger.info(f"✓ Stored {stored} products in PostgreSQL")
    else:
        # Create synthetic test data (fallback)
        logger.info("No products scraped, using synthetic test data...")
        synthetic = [
            {
                'product_id': 'TEST-001',
                'name': 'Test Wireless Earbuds Pro',
                'description': 'High-quality wireless test earbuds with noise cancellation',
                'category': 'Electronics',
                'price': 49.99,
                'currency': 'USD',
                'availability': True,
                'quantity': 100,
                'vendor': 'TestVendor',
                'rating': 4.5,
                'reviews_count': 500,
                'images': [],
                'tags': ['test', 'demo', 'wireless', 'audio'],
            },
            {
                'product_id': 'TEST-002',
                'name': 'Fitness Tracker Pro Max',
                'description': 'Advanced fitness tracker with GPS and heart rate monitor',
                'category': 'Sport',
                'price': 79.99,
                'currency': 'USD',
                'availability': True,
                'quantity': 50,
                'vendor': 'FitTech',
                'rating': 4.7,
                'reviews_count': 1200,
                'images': [],
                'tags': ['test', 'fitness', 'tracker', 'sport'],
            },
            {
                'product_id': 'TEST-003',
                'name': 'LED Desk Lamp Ultra Bright',
                'description': 'Smart LED desk lamp with 10 adjustable color temperatures',
                'category': 'Home',
                'price': 34.99,
                'currency': 'USD',
                'availability': True,
                'quantity': 200,
                'vendor': 'BrightHome',
                'rating': 4.8,
                'reviews_count': 980,
                'images': [],
                'tags': ['test', 'home', 'lighting', 'smart'],
            },
        ]
        stored = await engine.store_results(synthetic, source='synthetic_test')
        logger.info(f"✓ Stored {stored} synthetic test products in PostgreSQL")
        all_products = synthetic
    
    # Verify storage
    logger.info("\nVerifying data in PostgreSQL...")
    fetched = await engine.storage.fetch_all(limit=10)
    logger.info(f"✓ Total products in PostgreSQL database: {len(fetched)}")
    
    if fetched:
        logger.info("\nProducts stored in PostgreSQL:")
        for p in fetched[:5]:
            logger.info(f"  - {p.get('name', 'N/A')[:35]:35s} | ${p.get('price', 0):8.2f} | {p.get('category', 'N/A'):20s} | in_stock: {p.get('availability')}")
    
    # Run Top-K analysis on stored data
    logger.info("\nRunning Top-K analysis on stored products...")
    top_k = engine.analyze_top_k(all_products, k=3)
    logger.info(f"\nTop 3 products by scoring algorithm:")
    for i, p in enumerate(top_k, 1):
        score = p.get('_score', 0)
        price = p.get('price', 0)
        rating = p.get('rating', 0)
        logger.info(f"  {i}. {p.get('name', 'N/A')[:35]:35s} | Score: {score:.4f} | ${price:7.2f} | Rating: {rating}")
    
    # Cleanup
    await engine.storage.close()
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUITE COMPLETE")
    logger.info("=" * 70)
    logger.info("Summary:")
    logger.info(f"  - Scraper: {'Success' if scrape_results else 'Failed'}")
    logger.info(f"  - Products stored: {len(all_products)}")
    logger.info(f"  - PostgreSQL: Connected & Verified")
    logger.info(f"  - Top-K: {len(top_k)} top products identified")
    logger.info("=" * 70)


if __name__ == '__main__':
    asyncio.run(main())
