#!/usr/bin/env python
"""Import products from products.json into PostgreSQL - direct asyncpg."""
import json
import os
import asyncio
from pathlib import Path

async def main():
    # Chercher le fichier products.json
    search = [Path("data/raw/products.json"), Path("/app/data/raw/products.json")]
    products = []
    for s in search:
        if s.exists():
            with open(s) as f:
                products = json.load(f)
            print(f"Chargement de {len(products)} produits depuis {s}")
            break
    if not products:
        print("Aucun produit trouvé")
        return

    # Connexion directe à PostgreSQL (sans storage.py)
    import asyncpg
    host = os.getenv("POSTGRES_HOST", "postgres")
    user = os.getenv("POSTGRES_USER", "ecommerce_user")
    password = os.getenv("POSTGRES_PASSWORD", "secure_password")
    
    conn = await asyncpg.connect(
        host=host, port=5432, database="ecommerce_db",
        user=user, password=password
    )

    count = 0
    for p in products:
        try:
            pid = str(p.get("product_id", p.get("id", "")))
            name = (p.get("name", "") or "")[:500]
            desc = (p.get("description", "") or "")[:1000]
            cat = (p.get("category", "Uncategorized") or "Uncategorized")[:200]
            price = float(p.get("price", 0) or 0)
            currency = p.get("currency", "USD") or "USD"
            avail = bool(p.get("availability", True))
            qty = p.get("quantity")
            rating = float(p.get("rating", 0) or 0)
            reviews = int(p.get("reviews_count", 0) or 0)
            images = p.get("images", []) or []
            tags = p.get("tags", []) or []

            await conn.execute("""
                INSERT INTO products (product_id, name, description, category, price,
                    currency, availability, quantity, rating, reviews_count, images, tags)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
                ON CONFLICT (product_id) DO UPDATE SET
                    name=EXCLUDED.name, price=EXCLUDED.price, rating=EXCLUDED.rating,
                    reviews_count=EXCLUDED.reviews_count, availability=EXCLUDED.availability,
                    updated_at=NOW()
            """, pid, name, desc, cat, price, currency, avail, qty, rating, reviews, images, tags)
            count += 1
        except Exception as e:
            print(f"Erreur: {p.get('name','?')}: {e}")

    await conn.close()
    print(f"{count}/{len(products)} produits importés dans PostgreSQL ✅")

if __name__ == "__main__":
    asyncio.run(main())