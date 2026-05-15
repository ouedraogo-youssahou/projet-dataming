import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    import asyncpg
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

logger = logging.getLogger(__name__)


class PostgreSQLStorage:
    """Storage service for scraped product data in PostgreSQL."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.pool: Optional[asyncpg.Pool] = None
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize database connection pool."""
        if not POSTGRES_AVAILABLE:
            raise ImportError("asyncpg not installed. Run: pip install asyncpg")

        dsn = self._build_dsn()
        self.pool = await asyncpg.create_pool(
            dsn,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        await self._create_tables()
        self._initialized = True
        logger.info("PostgreSQL storage initialized")

    def _build_dsn(self) -> str:
        """Build PostgreSQL DSN from config."""
        db = self.config.get("postgresql", {})
        return (
            f"postgresql://{db.get('user', 'postgres')}:"
            f"{db.get('password', '')}@"
            f"{db.get('host', 'localhost')}:"
            f"{db.get('port', 5432)}/"
            f"{db.get('database', 'ecommerce_db')}"
        )

    async def _create_tables(self) -> None:
        """Create tables if not exist."""
        if not self.pool:
            raise RuntimeError("Pool not initialized")

        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    product_id VARCHAR(255) UNIQUE,
                    name TEXT,
                    description TEXT,
                    category VARCHAR(255),
                    price NUMERIC(10, 2),
                    currency VARCHAR(10) DEFAULT 'USD',
                    availability BOOLEAN,
                    quantity INTEGER,
                    vendor VARCHAR(255),
                    rating NUMERIC(3, 2),
                    reviews_count INTEGER,
                    images JSONB,
                    tags JSONB,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
                CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating DESC);
                CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);
                CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_url);
            """)

    async def store(self, products: List[Dict[str, Any]], source_url: Optional[str] = None) -> int:
        """Store products in database."""
        if not self._initialized:
            await self.initialize()

        if not products:
            return 0

        stored = 0
        async with self.pool.acquire() as conn:
            for product in products:
                p = dict(product)
                p["source_url"] = p.get("source_url") or source_url
                p["updated_at"] = datetime.utcnow()
                # Serialize JSON fields explicitly for asyncpg JSONB
                p["images"] = json.dumps(p.get("images", []))
                p["tags"] = json.dumps(p.get("tags", []))

                await conn.execute("""
                    INSERT INTO products (
                        product_id, name, description, category,
                        price, currency, availability, quantity,
                        vendor, rating, reviews_count, images, tags, source_url
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (product_id) DO UPDATE SET
                        name = EXCLUDED.name,
                        description = EXCLUDED.description,
                        category = EXCLUDED.category,
                        price = EXCLUDED.price,
                        availability = EXCLUDED.availability,
                        quantity = EXCLUDED.quantity,
                        rating = EXCLUDED.rating,
                        reviews_count = EXCLUDED.reviews_count,
                        images = EXCLUDED.images,
                        tags = EXCLUDED.tags,
                        updated_at = NOW()
                """,
                    p.get("product_id", ""),
                    p.get("name", ""),
                    p.get("description", ""),
                    p.get("category", ""),
                    p.get("price", 0),
                    p.get("currency", "USD"),
                    p.get("availability", True),
                    p.get("quantity"),
                    p.get("vendor", ""),
                    p.get("rating"),
                    p.get("reviews_count"),
                    p["images"],
                    p["tags"],
                    p.get("source_url"),
                )
                stored += 1

        logger.info(f"Stored {stored} products in PostgreSQL")
        return stored

    async def fetch_all(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Fetch all products from database."""
        if not self._initialized:
            await self.initialize()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(f"""
                SELECT * FROM products ORDER BY created_at DESC LIMIT {limit}
            """)
            return [dict(r) for r in rows]

    async def close(self) -> None:
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL connection closed")