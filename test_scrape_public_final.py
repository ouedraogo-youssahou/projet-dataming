#!/usr/bin/env python3
"""
Test scraping + PostgreSQL storage.
"""

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, '/app')

import asyncpg
import yaml

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Public demo stores
PUBLIC_TARGETS = [
    {"platform": "shopify", "url": "https://row.gymshark.com", "note": "Gymshark public store"},
]


async def main():
    logger.info("=" * 70)
    logger.info("TEST: Scrape public store + Store in PostgreSQL")
    logger.info("=" * 70)
    
    # Load config
    config_path = Path('/app/config/config.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # PostgreSQL connection
    db_dsn = 'postgresql://ecommerce_user:secure_password@postgres:5432/ecommerce_db'
    
    logger.info("Initializing PostgreSQL connection...")
    try:
        pool = await asyncpg.create_pool(db_dsn, min_size=1, max_size=10, command_timeout=60)
        logger.info("✓ PostgreSQL connected")
    except Exception as e:
        logger.error(f"Failed: {e}")
        return
    
    # Scrape public store
    logger.info("\nScraping public store...")
    from src.scraping.shopify_scraper import ShopifyScraper
    
    shopify_cfg = config.get('scraping', {}).get('shopify', {})
    scraper = ShopifyScraper(shopify_cfg)
    
    results = []
    for target in PUBLIC_TARGETS:
        try:
            data = await scraper.scrape(target['url'])
            results.append({'status': 'ok', 'url': target['url'], 'data': data})
            logger.info(f"✓ Scraped: {target['url']}")
        except Exception as e:
            logger.warning(f"✗ Failed {target['url']}: {e}")
            results.append({'status': 'error', 'url': target['url'], 'error': str(e)})
    
    # Collect products
    all_products = []
    for r in results:
        if r.get('status') == 'ok' and 'data' in r:
            d = r['data']
            if isinstance(d, list):
                all_products.extend(d)
            elif isinstance(d, dict):
                all_products.append(d)
    
    logger.info(f"\nProducts scraped: {len(all_products)}")
    
    if not all_products:
        # Synthetic fallback
        all_products = [
            {'product_id': 'TEST-001', 'name': 'Wireless Earbuds Pro', 'description': 'Noise-cancelling earbuds', 'category': 'Electronics', 'price': 49.99, 'currency': 'USD', 'availability': True, 'quantity': 100, 'vendor': 'TestVendor', 'rating': 4.5, 'reviews_count': 500, 'images': [], 'tags': ['test', 'audio']},
            {'product_id': 'TEST-002', 'name': 'Fitness Tracker', 'description': 'GPS fitness tracker', 'category': 'Sport', 'price': 79.99, 'currency': 'USD', 'availability': True, 'quantity': 50, 'vendor': 'FitTech', 'rating': 4.7, 'reviews_count': 1200, 'images': [], 'tags': ['test', 'sport']},
            {'product_id': 'TEST-003', 'name': 'LED Desk Lamp', 'description': 'Smart adjustable lamp', 'category': 'Home', 'price': 34.99, 'currency': 'USD', 'availability': True, 'quantity': 200, 'vendor': 'BrightHome', 'rating': 4.8, 'reviews_count': 980, 'images': [], 'tags': ['test', 'home']},
        ]
        logger.info("Using synthetic test data")
    
    # Store in PostgreSQL
    logger.info("\nStoring in PostgreSQL...")
    stored = 0
    async with pool.acquire() as conn:
        for p in all_products:
            try:
                await conn.execute("""
                    INSERT INTO products (product_id, name, description, category, price, currency, availability, quantity, vendor, rating, reviews_count, images, tags, source_url)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (product_id) DO UPDATE SET
                        name = EXCLUDED.name, price = EXCLUDED.price, availability = EXCLUDED.availability,
                        quantity = EXCLUDED.quantity, rating = EXCLUDED.rating, reviews_count = EXCLUDED.reviews_count, updated_at = NOW()
                """,
                p.get('product_id', ''), p.get('name', ''), p.get('description', ''), p.get('category', ''),
                p.get('price', 0), p.get('currency', 'USD'), p.get('availability', True), p.get('quantity'),
                p.get('vendor', ''), p.get('rating'), p.get('reviews_count'),
                p.get('images', []), p.get('tags', []), 'test_scrape'
                )
                stored += 1
            except Exception as e:
                logger.error(f"Insert failed for {p.get('name')}: {e}")
    
    logger.info(f"✓ Stored {stored} products")
    
    # Verify
    async with pool.acquire() as conn:
        count = await conn.fetchval('SELECT COUNT(*) FROM products')
        logger.info(f"\nTotal products in DB: {count}")
        
        rows = await conn.fetch('SELECT name, price, category, rating FROM products ORDER BY created_at DESC LIMIT 5')
        logger.info("\nProducts from PostgreSQL:")
        for r in rows:
            logger.info(f"  - {r['name'][:35]:35s} | ${r['price']:8.2f} | {r['category']:15s} | rating: {r['rating']}")
    
    # Top-K analysis
    logger.info("\nTop-K analysis:")
    from src.__main__ import SmartECommerceIntelligence
    engine = SmartECommerceIntelligence(config)
    top_k = engine.analyze_top_k(all_products, k=3)
    for i, p in enumerate(top_k, 1):
        logger.info(f"  {i}. {p.get('name', 'N/A')[:35]:35s} | Score: {p.get('_score', 0):.4f}")
    
    await pool.close()
    logger.info("\n" + "=" * 70)
    logger.info("TEST COMPLETE ✓")
    logger.info("=" * 70)


if __name__ == '__main__':
    asyncio.run(main())
