#!/usr/bin/env python3
"""
Test scraping + PostgreSQL storage directly via raw asyncpg.
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


async def test_db():
    logger.info("Testing PostgreSQL connection directly with asyncpg...")
    
    # Try different connection strings
    configs = [
        'postgresql://postgres:postgres@172.18.0.2:5432/ecommerce_db',
        'postgresql://postgres:postgres@postgres:5432/ecommerce_db',
    ]
    
    pool = None
    for dsn in configs:
        try:
            logger.info(f"Trying: {dsn}")
            pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5, command_timeout=60)
            logger.info(f"✓ Connected!")
            break
        except Exception as e:
            logger.warning(f"  Failed: {e}")
    
    if not pool:
        logger.error("Could not connect to PostgreSQL")
        return
    
    # Check existing data
    async with pool.acquire() as conn:
        count = await conn.fetchval('SELECT COUNT(*) FROM products')
        logger.info(f"Products in DB: {count}")
        
        # Insert test products
        test_products = [
            ('TEST-001', 'Test Wireless Earbuds', 'Test earbuds', 'Electronics', 49.99, 'USD', True, 100, 'TestVendor', 4.5, 500, '[]', '[]', 'synthetic_test'),
            ('TEST-002', 'Fitness Tracker Pro', 'Fitness tracker', 'Sport', 79.99, 'USD', True, 50, 'FitTech', 4.7, 1200, '[]', '[]', 'synthetic_test'),
            ('TEST-003', 'LED Desk Lamp', 'Smart lamp', 'Home', 34.99, 'USD', True, 200, 'BrightHome', 4.8, 980, '[]', '[]', 'synthetic_test'),
        ]
        
        for p in test_products:
            await conn.execute("""
                INSERT INTO products (product_id, name, description, category, price, currency, availability, quantity, vendor, rating, reviews_count, images, tags, source_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                ON CONFLICT (product_id) DO UPDATE SET
                    name = EXCLUDED.name, price = EXCLUDED.price, updated_at = NOW()
            """, *p)
        
        logger.info(f"✓ Inserted {len(test_products)} test products")
        
        # Verify
        rows = await conn.fetch('SELECT name, price, category FROM products ORDER BY created_at DESC LIMIT 5')
        logger.info("\nProducts in database:")
        for r in rows:
            logger.info(f"  - {r['name'][:35]:35s} | ${r['price']:8.2f} | {r['category']}")
    
    await pool.close()
    logger.info("\n✓ Database test complete")


if __name__ == '__main__':
    asyncio.run(test_db())
