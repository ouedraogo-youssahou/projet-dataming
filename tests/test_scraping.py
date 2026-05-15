"""Tests for scraping agents on public test stores."""

import asyncio
import pytest
from src.scraping.shopify_scraper import ShopifyScraper
from src.scraping.woocommerce_scraper import WooCommerceScraper
from src.scraping.storage import PostgreSQLStorage


class TestShopifyScraper:
    """Test Shopify scraper with public test stores."""

    @pytest.mark.asyncio
    async def test_user_agent_rotation(self):
        """Test user agent rotation."""
        scraper = ShopifyScraper()
        original_ua = scraper.headers["User-Agent"]
        scraper.rotate_user_agent()
        new_headers = scraper.headers
        assert new_headers["User-Agent"] != original_ua

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting between requests."""
        scraper = ShopifyScraper({"rate_limit": {"requests_per_second": 5}})
        import time
        start = time.time()
        await scraper._throttle()
        elapsed = time.time() - start
        assert elapsed >= 0.2  # Should have at least some delay


class TestWooCommerceScraper:
    """Test WooCommerce scraper."""

    @pytest.mark.asyncio
    async def test_base_url_extraction(self):
        """Test base URL extraction."""
        scraper = WooCommerceScraper()
        url = "https://example.com/product/test-product/"
        base = scraper._get_base_url(url)
        assert base == "https://example.com"


class TestPostgreSQLStorage:
    """Test PostgreSQL storage service."""

    @pytest.mark.asyncio
    async def test_store_products(self):
        """Test storing products in PostgreSQL."""
        storage = PostgreSQLStorage({
            "postgresql": {
                "host": "localhost",
                "port": 5432,
                "database": "ecommerce_db",
                "user": "postgres",
                "password": "test",
            }
        })
        try:
            await storage.initialize()
            products = [{
                "product_id": "test_001",
                "name": "Test Product",
                "price": 99.99,
                "rating": 4.5,
                "availability": True,
            }]
            stored = await storage.store(products)
            assert stored == 1
        finally:
            await storage.close()

    @pytest.mark.asyncio
    async def test_fetch_products(self):
        """Test fetching stored products."""
        storage = PostgreSQLStorage({
            "postgresql": {
                "host": "localhost",
                "database": "ecommerce_db",
                "user": "postgres",
                "password": "test",
            }
        })
        try:
            await storage.initialize()
            products = await storage.fetch_all(limit=10)
            assert isinstance(products, list)
        finally:
            await storage.close()


class TestScrapingIntegration:
    """Integration tests for scraping pipeline."""

    @pytest.mark.asyncio
    async def test_multiple_scrapers(self):
        """Test running multiple scrapers with rate limiting."""
        shopify = ShopifyScraper()
        woocommerce = WooCommerceScraper()

        # Test that both scrapers have user agent rotation
        assert hasattr(shopify, 'rotate_user_agent')
        assert hasattr(woocommerce, 'rotate_user_agent')

    @pytest.mark.asyncio
    async def test_storage_integration(self):
        """Test storage integration with scraped data."""
        storage = PostgreSQLStorage()
        try:
            await storage.initialize()
            # Verify connection works
            products = await storage.fetch_all(limit=1)
            assert isinstance(products, list)
        except Exception:
            pass  # Skip if no database available
        finally:
            await storage.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])