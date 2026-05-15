# ============================================
# Specialized A2A Agents for each e-commerce platform
# ============================================

import logging
from typing import Any, Dict, Optional

from .base_agent import BaseAgent
from .protocol import Task, AgentCapability
from .message_bus import A2AMessageBus, AgentRegistry
from ..shopify_scraper import ShopifyScraper
from ..woocommerce_scraper import WooCommerceScraper
from ..selenium_scraper import SeleniumScraper
from ..playwright_scraper import PlaywrightScraper

logger = logging.getLogger(__name__)


class ShopifyAgent(BaseAgent):
    """
    A2A Agent specialized in scraping Shopify stores.
    Uses ShopifyScraper (GraphQL API only, no HTML fallback).
    Rate limited to 2 requests/second.
    """

    def __init__(
        self,
        agent_id: str = "shopify_agent_1",
        config: Optional[Dict[str, Any]] = None,
        message_bus: Optional[A2AMessageBus] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        capabilities = AgentCapability(
            platform="shopify",
            max_concurrent_tasks=5,
            supports_js=False,
            supports_api=True,
            rate_limit=2.0,
            supported_features=["scrape", "search_products", "get_product_details"],
        )
        super().__init__(
            agent_id=agent_id,
            agent_type="shopify",
            capabilities=capabilities,
            message_bus=message_bus,
            registry=registry,
        )
        self.config = config or {}
        self.scraper = ShopifyScraper(self.config.get("shopify", {}))
        self.metadata["platform"] = "Shopify"

    async def scrape(self, task: Task) -> Any:
        """
        Scrape a Shopify URL using the Shopify scraper.
        
        Args:
            task: Task with url to scrape
            
        Returns:
            Dict of normalized product data
        """
        url = task.url
        params = task.params

        logger.info(f"ShopifyAgent scraping: {url}")

        # Apply rate limiting
        await self._throttle()

        # Scrape using the existing Shopify scraper
        result = await self.scraper.scrape(url, **params)

        # Add metadata
        if isinstance(result, dict):
            result["_scraped_by"] = self.agent_id
            result["_platform"] = "shopify"

        return result

    async def _throttle(self):
        """Rate limiting for Shopify API (2 req/s)."""
        import asyncio
        rps = self.capabilities.rate_limit
        if rps > 0:
            await asyncio.sleep(1.0 / rps)

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "type": "Shopify",
            "capabilities": {
                "api_support": self.capabilities.supports_api,
                "max_concurrent": self.capabilities.max_concurrent_tasks,
                "rate_limit": f"{self.capabilities.rate_limit} req/s",
            },
            "status": self.status,
        }


class WooCommerceAgent(BaseAgent):
    """
    A2A Agent specialized in scraping WooCommerce stores.
    Uses WooCommerceScraper (REST API only, no HTML fallback).
    Rate limited to 4 requests/second.
    """

    def __init__(
        self,
        agent_id: str = "woocommerce_agent_1",
        config: Optional[Dict[str, Any]] = None,
        message_bus: Optional[A2AMessageBus] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        capabilities = AgentCapability(
            platform="woocommerce",
            max_concurrent_tasks=5,
            supports_js=False,
            supports_api=True,
            rate_limit=4.0,
            supported_features=["scrape", "search_products", "get_product_details"],
        )
        super().__init__(
            agent_id=agent_id,
            agent_type="woocommerce",
            capabilities=capabilities,
            message_bus=message_bus,
            registry=registry,
        )
        self.config = config or {}
        # Injecter les credentials WooCommerce depuis les variables d'environnement
        import os
        woo_cfg = dict(self.config.get("woocommerce", {}))
        env_key = os.getenv("WOOCOMMERCE_CONSUMER_KEY", "")
        env_secret = os.getenv("WOOCOMMERCE_CONSUMER_SECRET", "")
        if env_key:
            woo_cfg["consumer_key"] = env_key
        if env_secret:
            woo_cfg["consumer_secret"] = env_secret
        self.scraper = WooCommerceScraper(woo_cfg)
        self.metadata["platform"] = "WooCommerce"

    async def scrape(self, task: Task) -> Any:
        """
        Scrape a WooCommerce store or product page.
        If URL is a store root (no /product/ in path), crawls ALL products.
        """
        url = task.url
        params = task.params

        logger.info(f"WooCommerceAgent scraping: {url}")

        await self._throttle()

        # Détection : si c'est un store (pas une page produit), crawler tous les produits
        if "/product/" not in url:
            result = await self.scraper.scrape_all(url, max_pages=params.get("max_pages", 50))
        else:
            result = await self.scraper.scrape(url, **params)

        # Ajouter métadonnées
        if isinstance(result, list):
            for item in result:
                if isinstance(item, dict):
                    item["_scraped_by"] = self.agent_id
                    item["_platform"] = "woocommerce"
        elif isinstance(result, dict):
            result["_scraped_by"] = self.agent_id
            result["_platform"] = "woocommerce"

        return result

    async def _throttle(self):
        """Rate limiting for WooCommerce API (4 req/s)."""
        import asyncio
        rps = self.capabilities.rate_limit
        if rps > 0:
            await asyncio.sleep(1.0 / rps)

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "type": "WooCommerce",
            "capabilities": {
                "api_support": self.capabilities.supports_api,
                "max_concurrent": self.capabilities.max_concurrent_tasks,
                "rate_limit": f"{self.capabilities.rate_limit} req/s",
            },
            "status": self.status,
        }


class GenericScraperAgent(BaseAgent):
    """
    Generic A2A Agent for any website.
    Uses Selenium or Playwright for JS-heavy sites.
    Acts as fallback when platform-specific agents fail.
    """

    def __init__(
        self,
        agent_id: str = "generic_agent_1",
        config: Optional[Dict[str, Any]] = None,
        use_playwright: bool = False,
        message_bus: Optional[A2AMessageBus] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        capabilities = AgentCapability(
            platform="generic",
            max_concurrent_tasks=3,
            supports_js=True,
            supports_api=False,
            rate_limit=1.0,
            supported_features=["scrape", "scrape_any"],
        )
        super().__init__(
            agent_id=agent_id,
            agent_type="generic",
            capabilities=capabilities,
            message_bus=message_bus,
            registry=registry,
        )
        self.config = config or {}
        self.use_playwright = use_playwright

        # Initialize both scrapers (can choose at runtime)
        self.selenium_scraper = SeleniumScraper(self.config.get("selenium", {}))
        self.playwright_scraper = PlaywrightScraper(self.config.get("playwright", {}))

        self.metadata["use_playwright"] = use_playwright
        self.metadata["platform"] = "Generic"

    async def scrape(self, task: Task) -> Any:
        """
        Scrape any URL using Selenium or Playwright.
        Can handle JavaScript-heavy sites.
        
        Args:
            task: Task with url to scrape
            
        Returns:
            Dict of normalized product data
        """
        url = task.url
        params = task.params

        logger.info(f"GenericAgent scraping: {url}")

        # Apply rate limiting
        await self._throttle()

        # Choose scraper based on config or task params
        use_playwright = params.get("use_playwright", self.use_playwright)

        try:
            if use_playwright:
                result = await self.playwright_scraper.scrape(url, **params)
            else:
                result = await self.selenium_scraper.scrape(url, **params)

            # Add metadata
            if isinstance(result, dict):
                result["_scraped_by"] = self.agent_id
                result["_platform"] = "generic"
                result["_scraper"] = "playwright" if use_playwright else "selenium"

            return result

        except Exception as e:
            logger.error(f"GenericAgent failed with primary scraper, trying fallback: {e}")

            # Fallback: try the other scraper
            if use_playwright:
                logger.info("Falling back to Selenium...")
                result = await self.selenium_scraper.scrape(url, **params)
            else:
                logger.info("Falling back to Playwright...")
                result = await self.playwright_scraper.scrape(url, **params)

            if isinstance(result, dict):
                result["_scraped_by"] = self.agent_id
                result["_platform"] = "generic"
                result["_scraper"] = "fallback"

            return result

    async def _throttle(self):
        """Rate limiting for generic scraping (1 req/s)."""
        import asyncio
        rps = self.capabilities.rate_limit
        if rps > 0:
            await asyncio.sleep(1.0 / rps)

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "type": "Generic Scraper",
            "capabilities": {
                "js_support": self.capabilities.supports_js,
                "max_concurrent": self.capabilities.max_concurrent_tasks,
                "rate_limit": f"{self.capabilities.rate_limit} req/s",
                "scrapers": ["selenium", "playwright"],
            },
            "status": self.status,
        }