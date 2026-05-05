import asyncio
import logging
from typing import Any, Dict, List, Optional

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class WooCommerceScraper(BaseScraper):
    """WooCommerce REST API scraper."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.consumer_key = self.config.get("consumer_key", "")
        self.consumer_secret = self.config.get("consumer_secret", "")
        self.api_version = self.config.get("api_version", "wc/v3")

    async def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape WooCommerce store or product page."""
        await self._throttle()

        # If URL looks like a product page, try to extract id/handle
        # WooCommerce API: /wp-json/wc/v3/products?slug=...
        import aiohttp

        # Try to get base store URL
        base = self._get_base_url(url)
        if not base:
            return self.normalize_product({"title": url})

        api_url = f"{base}/wp-json/{self.api_version}/products"

        # If path contains /product/ try slug
        slug = None
        if "/product/" in url:
            slug = url.split("/product/")[-1].split("?")[0].strip("/")

        params = {"per_page": 1}
        if slug:
            params["slug"] = slug

        auth = None
        if self.consumer_key and self.consumer_secret:
            auth = aiohttp.BasicAuth(self.consumer_key, self.consumer_secret)

        try:
            async with aiohttp.ClientSession(auth=auth) as session:
                async with session.get(
                    api_url,
                    params=params,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    data = await resp.json()

            if isinstance(data, list) and len(data) > 0:
                product = data[0]
                return self._parse_woo_product(product)
            elif isinstance(data, dict) and "id" in data:
                return self._parse_woo_product(data)
            else:
                logger.warning(f"No products found for {url}")
                return self.normalize_product({"title": slug or url})
        except Exception as e:
            logger.error(f"WooCommerce scrape error for {url}: {e}")
            # Fallback basic
            return self.normalize_product({"title": slug or url, "price": 0})

    async def _scrape_html_fallback(self, url: str) -> Dict[str, Any]:
        """HTML fallback for sites without API access."""
        import aiohttp
        import re
        import json

        await self._throttle()
        self.rotate_user_agent()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as resp:
                    html = await resp.text()

            ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
            if ld_match:
                try:
                    ld = json.loads(ld_match.group(1))
                    if isinstance(ld, list):
                        ld = ld[0]
                    if ld.get("@type") == "Product":
                        return self.normalize_product({
                            "title": ld.get("name", ""),
                            "description": ld.get("description", ""),
                            "price": ld.get("offers", {}).get("price", 0),
                            "available": "InStock" in ld.get("offers", {}).get("availability", ""),
                        })
                except Exception:
                    pass
            return self.normalize_product({"title": url.split("/")[-1]})
        except Exception as e:
            logger.error(f"HTML fallback error: {e}")
            return self.normalize_product({"title": url})

    def _get_base_url(self, url: str) -> Optional[str]:
        """Extract base store URL from product URL."""
        # Simple: remove path after domain to get root
        parts = url.split("/")
        if len(parts) >= 3:
            return f"{parts[0]}//{parts[2]}"
        return None

    def _parse_woo_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Parse WooCommerce API product."""
        price = product.get("price", "0")
        regular = product.get("regular_price", "0")
        sale = product.get("sale_price", "0")

        # Determine best price
        try:
            price_val = float(sale) if sale and sale != "" else float(regular) if regular and regular != "" else float(price)
        except ValueError:
            price_val = 0.0

        stock = product.get("stock_quantity")
        if stock is None:
            stock = product.get("stock_status", "") == "instock"

        images = product.get("images", [])
        image_urls = [img.get("src") for img in images if img.get("src")]

        categories = product.get("categories", [])
        category = categories[0].get("name", "") if categories else ""

        return {
            "product_id": product.get("id", ""),
            "name": product.get("name", ""),
            "description": product.get("description", ""),
            "category": category,
            "price": price_val,
            "currency": product.get("currency", "USD"),
            "availability": product.get("stock_status", "instock") == "instock" if product.get("stock_status") else bool(stock),
            "quantity": stock if isinstance(stock, int) else None,
            "vendor": product.get("seller_info", {}).get("name") if isinstance(product.get("seller_info"), dict) else "",
            "rating": product.get("average_rating"),
            "reviews_count": product.get("review_count"),
            "images": image_urls,
            "tags": [t.get("name", "") for t in product.get("tags", [])],
        }
