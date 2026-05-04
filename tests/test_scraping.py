import pytest
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.scraping.base_scraper import BaseScraper


@pytest.mark.asyncio
async def test_base_scraper_normalize():
    scraper = BaseScraper()
    raw = {"title": "Test Product", "price": "29.99", "available": True}
    norm = scraper.normalize_product(raw)
    assert norm["name"] == "Test Product"
    assert norm["price"] == 29.99
    assert norm["availability"] is True


@pytest.mark.asyncio
async def test_base_scraper_price_parsing():
    scraper = BaseScraper()
    assert scraper._parse_price("29.99") == 29.99
    assert scraper._parse_price("$29.99") == 29.99
    assert scraper._parse_price(None) == 0.0
    assert scraper._parse_price("invalid") == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
