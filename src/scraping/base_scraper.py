import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base scraper with common helpers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.rate_limit = self.config.get("rate_limit", {})
        self.timeout = self.config.get("timeout", 30)
        self._user_agents = self.config.get("user_agents", [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ])
        self._ua_index = 0
        self.headers = self._build_headers()

    def _build_headers(self) -> Dict[str, str]:
        """Build headers with rotated user agent."""
        ua = self._user_agents[self._ua_index % len(self._user_agents)]
        return {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        }

    def rotate_user_agent(self) -> Dict[str, str]:
        """Rotate to next user agent and return new headers."""
        self._ua_index += 1
        self.headers = self._build_headers()
        return self.headers

    @abstractmethod
    async def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """Scrape a URL and return normalized product data."""
        raise NotImplementedError

    def normalize_product(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw product dict to common schema."""
        return {
            "product_id": raw.get("id") or raw.get("product_id") or "",
            "name": raw.get("title") or raw.get("name") or raw.get("product_name") or "",
            "description": raw.get("description") or raw.get("body_html") or "",
            "category": raw.get("category") or raw.get("product_type") or "",
            "price": self._parse_price(raw.get("price") or raw.get("variants", [{}])[0].get("price") if raw.get("variants") else None),
            "currency": raw.get("currency") or raw.get("price_currency") or "USD",
            "availability": raw.get("available", True),
            "quantity": raw.get("inventory_quantity"),
            "vendor": raw.get("vendor") or raw.get("seller") or "",
            "rating": raw.get("rating"),
            "reviews_count": raw.get("reviews_count"),
            "images": raw.get("images") or raw.get("image") or [],
            "tags": raw.get("tags") or [],
        }

    def _parse_price(self, val) -> float:
        if val is None:
            return 0.0
        try:
            return float(val)
        except (ValueError, TypeError):
            # try strip non-numeric
            import re
            m = re.search(r"[\d.,]+", str(val))
            if m:
                cleaned = m.group(0).replace(",", "")
                try:
                    return float(cleaned)
                except ValueError:
                    pass
            return 0.0

    async def _throttle(self):
        """Simple rate-limit helper."""
        rps = self.rate_limit.get("requests_per_second", 2)
        if rps and rps > 0:
            await asyncio.sleep(1.0 / rps)
