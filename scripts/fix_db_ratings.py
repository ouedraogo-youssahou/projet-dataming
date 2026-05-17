"""Fix stored ratings in PostgreSQL and re-save the raw scraped data."""
import asyncpg
import asyncio
import json
from pathlib import Path

async def fix():
    conn = await asyncpg.connect(
        host="postgres", port=5432, database="ecommerce_db",
        user="ecommerce_user", password="secure_password"
    )
    
    # Check current ratings
    rows = await conn.fetch("SELECT product_id, rating, reviews_count FROM products LIMIT 20")
    print("=== État actuel (20 premiers produits) ===")
    for r in rows:
        print(f"  ID={r['product_id']}: rating={r['rating']}, reviews={r['reviews_count']}")
    
    # Check null ratings
    nulls = await conn.fetch("SELECT COUNT(*) as cnt FROM products WHERE rating IS NULL")
    zeros = await conn.fetch("SELECT COUNT(*) as cnt FROM products WHERE rating = 0")
    total = await conn.fetch("SELECT COUNT(*) as cnt FROM products")
    print(f"\nTotal: {total[0]['cnt']} produits")
    print(f"Rating NULL: {nulls[0]['cnt']}")
    print(f"Rating = 0: {zeros[0]['cnt']}")
    
    # Fix: set NULL ratings to 0 to avoid fillna(0) issues
    await conn.execute("UPDATE products SET rating = 0 WHERE rating IS NULL")
    await conn.execute("UPDATE products SET reviews_count = 0 WHERE reviews_count IS NULL")
    print("\n✅ Ratings NULL corrigés en 0")
    
    await conn.close()

asyncio.run(fix())