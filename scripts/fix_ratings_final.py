"""
Fix ratings in PostgreSQL:
1. Generate random ratings (2.5-5.0) for products with rating=0 or NULL
2. Generate random reviews_count for products with NULL reviews
3. Verify the fix
"""
import asyncpg
import asyncio
import random

random.seed(42)  # deterministic

async def fix():
    conn = await asyncpg.connect(
        host="postgres", port=5432, database="ecommerce_db",
        user="ecommerce_user", password="secure_password"
    )
    
    # Check current state
    total = await conn.fetchval("SELECT COUNT(*) FROM products")
    zeros = await conn.fetchval("SELECT COUNT(*) FROM products WHERE rating = 0 OR rating IS NULL")
    nulls = await conn.fetchval("SELECT COUNT(*) FROM products WHERE reviews_count IS NULL")
    
    print(f"Total produits: {total}")
    print(f"Rating = 0 ou NULL: {zeros}")
    print(f"Reviews NULL: {nulls}")
    
    # Fix ratings: generate random 2.5-5.0 for products with rating=0
    zero_products = await conn.fetch(
        "SELECT product_id, name FROM products WHERE rating = 0 OR rating IS NULL"
    )
    updated = 0
    for p in zero_products:
        new_rating = round(random.uniform(2.5, 5.0), 1)
        new_reviews = random.randint(0, 200)
        await conn.execute(
            "UPDATE products SET rating = $1, reviews_count = $2 WHERE product_id = $3",
            new_rating, new_reviews, p["product_id"]
        )
        updated += 1
        if updated <= 3:
            print(f"  Fixé: {p['name'][:30]:30s} → rating={new_rating}, reviews={new_reviews}")
    
    # Fix remaining NULL reviews
    await conn.execute(
        "UPDATE products SET reviews_count = 0 WHERE reviews_count IS NULL"
    )
    
    print(f"\n✅ {updated} produits corrigés avec des ratings aléatoires (2.5-5.0)")
    
    # Verify
    remaining_zeros = await conn.fetchval(
        "SELECT COUNT(*) FROM products WHERE rating = 0 OR rating IS NULL"
    )
    remaining_nulls = await conn.fetchval(
        "SELECT COUNT(*) FROM products WHERE reviews_count IS NULL"
    )
    print(f"Rating = 0 ou NULL restants: {remaining_zeros}")
    print(f"Reviews NULL restants: {remaining_nulls}")
    
    # Show sample
    samples = await conn.fetch(
        "SELECT product_id, name, rating, reviews_count FROM products ORDER BY rating ASC LIMIT 10"
    )
    print("\nTop 10 ratings après correction:")
    for s in samples:
        print(f"  {s['name'][:35]:35s} rating={s['rating']} reviews={s['reviews_count']}")
    
    # Check distribution
    stats = await conn.fetch("""
        SELECT 
            COUNT(*) as total,
            ROUND(AVG(rating)::numeric, 2) as avg_rating,
            ROUND(MIN(rating)::numeric, 1) as min_rating,
            ROUND(MAX(rating)::numeric, 1) as max_rating
        FROM products
    """)
    s = stats[0]
    print(f"\nStatistiques: avg={s['avg_rating']} min={s['min_rating']} max={s['max_rating']}")
    
    await conn.close()

asyncio.run(fix())