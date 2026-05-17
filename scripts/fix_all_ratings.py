"""Fix ALL ratings in PostgreSQL using the fresh data from the raw JSON file."""
import asyncpg
import asyncio
import json
from pathlib import Path

RAW_PRODUCTS_PATH = "/app/data/raw/products.json"

async def fix_all():
    # Load raw products
    raw_path = Path(RAW_PRODUCTS_PATH)
    if not raw_path.exists():
        print(f"ERREUR: fichier {RAW_PRODUCTS_PATH} non trouve")
        return
    
    with open(raw_path) as f:
        raw_products = json.load(f)
    
    print(f"Fichier RAW charge: {len(raw_products)} produits")
    
    # Build lookup by product_id
    lookup = {}
    for p in raw_products:
        pid = str(p.get("product_id", ""))
        lookup[pid] = p
    
    print(f"Lookup construit: {len(lookup)} ids")
    
    # Connect to PostgreSQL
    conn = await asyncpg.connect(
        host="postgres", port=5432, database="ecommerce_db",
        user="ecommerce_user", password="secure_password"
    )
    
    # Get all products from DB
    db_products = await conn.fetch("SELECT product_id, rating, reviews_count FROM products")
    print(f"Produits dans DB: {len(db_products)}")
    
    updated = 0
    errors = 0
    skipped = 0
    
    for row in db_products:
        pid = str(row["product_id"])
        
        if pid not in lookup:
            skipped += 1
            continue
        
        raw = lookup[pid]
        raw_rating = raw.get("rating")
        raw_reviews = raw.get("reviews_count")
        
        # Only update if DB has wrong values (null or 0)
        db_rating = row["rating"]
        db_reviews = row["reviews_count"]
        
        if (db_rating is None or db_rating == 0 or db_reviews is None) and raw_rating is not None:
            new_rating = float(raw_rating) if raw_rating else 0.0
            new_reviews = int(raw_reviews) if raw_reviews else 0
            
            await conn.execute(
                "UPDATE products SET rating = $1, reviews_count = $2 WHERE product_id = $3",
                new_rating, new_reviews, pid
            )
            updated += 1
    
    print(f"\nResultats:")
    print(f"  Mis a jour: {updated}")
    print(f"  Non trouves dans RAW: {skipped}")
    print(f"  Erreurs: {errors}")
    
    # Verify
    remaining_zeros = await conn.fetch("SELECT COUNT(*) as cnt FROM products WHERE rating = 0 OR rating IS NULL")
    remaining_nulls = await conn.fetch("SELECT COUNT(*) as cnt FROM products WHERE reviews_count IS NULL")
    print(f"  Rating = 0 ou NULL apres correction: {remaining_zeros[0]['cnt']}")
    print(f"  Reviews NULL apres correction: {remaining_nulls[0]['cnt']}")
    
    # Show sample
    samples = await conn.fetch("SELECT product_id, name, rating, reviews_count FROM products ORDER BY rating DESC LIMIT 5")
    print("\nEchantillon apres correction (top 5 ratings):")
    for s in samples:
        print(f"  {s['name'][:30]:30s} rating={s['rating']} reviews={s['reviews_count']}")
    
    await conn.close()

asyncio.run(fix_all())