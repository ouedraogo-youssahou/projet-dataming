import sys

from src.scraping.shopify_scraper import ShopifyScraper
from src.scraping.woocommerce_scraper import WooCommerceScraper
from src.scraping.selenium_scraper import SeleniumScraper
from src.scraping.playwright_scraper import PlaywrightScraper

def test_scrapers_imports():
    assert ShopifyScraper is not None
    assert WooCommerceScraper is not None
    assert SeleniumScraper is not None
    assert PlaywrightScraper is not None
    print("OK: scrapers imports")

if __name__ == "__main__":
    test_scrapers_imports()
