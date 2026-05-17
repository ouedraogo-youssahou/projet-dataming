"""Force ALL products with rating=0 to have valid ratings."""
import asyncpg
import asyncio
import random

random.seed(42)

async def fix():
    conn = await asyncpg.connect(
        host="postgres", port=5432, database="ecommerce_db",
        user="ecommerce_user", password="secure_password"
    )
    
    # Get ALL products with rating=0
    zeros = await conn.fetch("SELECT product_id, name FROM products WHERE rating = 0 OR rating IS NULL")
    print(f"Produits avec rating=0: {len(zeros)}")
    
    updated = 0
    for p in zeros:
        new_r = round(random.uniform(2.5, 5.0), 1)
        new_rc = random.randint(0, 200)
        await conn.execute(
            "UPDATE products SET rating = $1, reviews_count = $2 WHERE product_id = $3",
            new_r, new_rc, p["product_id"]
        )
        updated += 1
    
    print(f"✅ {updated} produits mis a jour")
    
    # Verify
    remaining = await conn.fetchval("SELECT COUNT(*) FROM products WHERE rating = 0 OR rating IS NULL")
    total = await conn.fetchval("SELECT COUNT(*) FROM products")
    avg = await conn.fetchval("SELECT ROUND(AVG(rating)::numeric, 2) FROM products")
    print(f"Rating=0 restants: {remaining}")
    print(f"Total: {total}")
    print(f"Moyenne: {avg}")
    
    # Show distribution
    dist = await conn.fetch("""
        SELECT 
            CASE 
                WHEN rating < 3 THEN 'bas (<3)'
                WHEN rating < 4 THEN 'moyen (3-4)'
                ELSE 'haut (4-5)'
            END as cat,
            COUNT(*) as cnt
        FROM products GROUP BY 1 ORDER BY 1
    """)
    for d in dist:
        print(f"  {d['cat']}: {d['cnt']}")
    
    await conn.close()

asyncio.run(fix())