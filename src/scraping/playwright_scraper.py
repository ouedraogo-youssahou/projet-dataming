import asyncio
import logging
from typing import Any, Dict, Optional

from playwright.async_api import async_playwright

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PlaywrightScraper(BaseScraper):
    """Generic scraper using Playwright (headless browser)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.browser = self.config.get("browser", "chromium")
        self.headless = self.config.get("headless", True)
        self.slow_mo = self.config.get("slow_mo", 0)
        self.timeout = self.config.get("timeout", 30000)

    async def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape using Playwright."""
        await self._throttle()
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=self.headless)
                page = await browser.new_page()
                await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                # Small wait for dynamic content
                await asyncio.sleep(1.5)

                title = await page.title()
                price = await self._extract_price(page)
                desc = await self._extract_desc(page)

                await browser.close()

                raw = {
                    "title": title or "",
                    "price": price,
                    "description": desc or "",
                }
                return self.normalize_product(raw)
        except Exception as e:
            logger.error(f"Playwright scrape error for {url}: {e}")
            return self.normalize_product({"title": url, "error": str(e)})

    async def _extract_price(self, page) -> Optional[float]:
        """Try to extract price from page."""
        selectors = [
            "[class*='price'] >> text=/[\\d.,]+/",
            ".price >> text=/[\\d.,]+/",
            "#price >> text=/[\\d.,]+/",
            "meta[property='product:price:amount']",
        ]
        for selector in selectors:
            try:
                if "meta" in selector:
                    content = await page.get_attribute(selector, "content")
                    if content:
                        return self._parse_price(content)
                else:
                    # Try text content
                    elements = await page.query_selector_all(selector.split(">>")[0].strip())
                    for el in elements:
                        text = await el.text_content()
                        if text and any(c.isdigit() for c in text):
                            return self._parse_price(text)
            except Exception:
                continue
        return None

    async def _extract_desc(self, page) -> str:
        """Try to extract description."""
        selectors = [
            "[class*='description']",
            ".description",
            "#description",
            "meta[name='description']",
        ]
        for selector in selectors:
            try:
                if "meta" in selector:
                    content = await page.get_attribute(selector, "content")
                    if content:
                        return content
                else:
                    text = await page.text_content(selector)
                    if text and len(text.strip()) > 20:
                        return text.strip()
            except Exception:
                continue
        return ""
