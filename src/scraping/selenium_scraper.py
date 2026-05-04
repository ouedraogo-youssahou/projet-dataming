import asyncio
import logging
from typing import Any, Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SeleniumScraper(BaseScraper):
    """Generic scraper using Selenium (for JS-heavy sites)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.headless = self.config.get("headless", True)
        self.browser = self.config.get("browser", "chrome")
        self.window_size = self.config.get("window_size", "1920,1080")

    async def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape using Selenium."""
        await self._throttle()
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._scrape_sync, url)
            return result
        except Exception as e:
            logger.error(f"Selenium scrape error for {url}: {e}")
            return self.normalize_product({"title": url, "error": str(e)})

    def _scrape_sync(self, url: str) -> Dict[str, Any]:
        """Synchronous Selenium scrape."""
        options = Options()
        if self.headless:
            options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--window-size={self.window_size}")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # In the Docker scraper stage we installed google-chrome-stable and chromedriver should be available
        driver = None
        try:
            # Try to use available chrome/chromedriver
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(self.timeout)
            driver.get(url)

            # Wait for some basic element or just get page source after a small delay
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except Exception:
                pass

            title = driver.title or ""
            # Try to find price-like elements
            price = self._extract_price_from_driver(driver)
            desc = self._extract_desc_from_driver(driver)

            raw = {
                "title": title,
                "price": price,
                "description": desc,
            }
            return self.normalize_product(raw)
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _extract_price_from_driver(self, driver) -> Optional[float]:
        """Try to find price on page."""
        candidates = [
            "[class*='price']",
            "[class*='Price']",
            "meta[property='product:price:amount']",
            ".price",
            ".Price",
            "#price",
            "#Price",
        ]
        for selector in candidates:
            try:
                if selector.startswith("meta"):
                    els = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        content = el.get_attribute("content")
                        if content:
                            return self._parse_price(content)
                else:
                    els = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        text = el.text.strip()
                        if text:
                            return self._parse_price(text)
            except Exception:
                continue
        return None

    def _extract_desc_from_driver(self, driver) -> str:
        """Try to find description."""
        selectors = ["[class*='description']", ".description", "#description", "meta[name='description']"]
        for selector in selectors:
            try:
                if selector.startswith("meta"):
                    els = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        c = el.get_attribute("content")
                        if c:
                            return c
                else:
                    els = driver.find_elements(By.CSS_SELECTOR, selector)
                    for el in els:
                        t = el.text.strip()
                        if t:
                            return t
            except Exception:
                continue
        return ""
