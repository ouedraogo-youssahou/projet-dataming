# ============================================
# Smart eCommerce Intelligence - Scraping Module
# ============================================

from .shopify_scraper import ShopifyScraper
from .woocommerce_scraper import WooCommerceScraper
from .selenium_scraper import SeleniumScraper
from .playwright_scraper import PlaywrightScraper
from .base_scraper import BaseScraper
from .storage import PostgreSQLStorage

# A2A Agents
from .agents import (
    A2AMessage, A2AMessageType, Task, AgentCapability, AgentInfo,
    BaseAgent,
    A2AMessageBus, AgentRegistry,
    AgentOrchestrator,
    ShopifyAgent, WooCommerceAgent, GenericScraperAgent,
    DataCollectorAgent,
)

__all__ = [
    "ShopifyScraper",
    "WooCommerceScraper",
    "SeleniumScraper",
    "PlaywrightScraper",
    "BaseScraper",
    "PostgreSQLStorage",
    # A2A Agents
    "A2AMessage",
    "A2AMessageType",
    "Task",
    "AgentCapability",
    "AgentInfo",
    "BaseAgent",
    "A2AMessageBus",
    "AgentRegistry",
    "AgentOrchestrator",
    "ShopifyAgent",
    "WooCommerceAgent",
    "GenericScraperAgent",
    "DataCollectorAgent",
]
