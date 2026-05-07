# ============================================
# Smart eCommerce Intelligence - Scraping Module
# ============================================
# Imports conditionnels pour éviter les erreurs si selenium/playwright ne sont pas installés
# (ex: image mcp-server qui n'a que bs4+lxml)

from .base_scraper import BaseScraper
from .shopify_scraper import ShopifyScraper
from .woocommerce_scraper import WooCommerceScraper

try:
    from .selenium_scraper import SeleniumScraper
except ImportError:
    SeleniumScraper = None

try:
    from .playwright_scraper import PlaywrightScraper
except ImportError:
    PlaywrightScraper = None

from .storage import PostgreSQLStorage

# A2A Agents
try:
    from .agents import (
        A2AMessage, A2AMessageType, Task, AgentCapability, AgentInfo,
        BaseAgent,
        A2AMessageBus, AgentRegistry,
        AgentOrchestrator,
        ShopifyAgent, WooCommerceAgent, GenericScraperAgent,
        DataCollectorAgent,
    )
except ImportError:
    A2AMessage = A2AMessageType = Task = AgentCapability = AgentInfo = None
    BaseAgent = None
    A2AMessageBus = AgentRegistry = None
    AgentOrchestrator = None
    ShopifyAgent = WooCommerceAgent = GenericScraperAgent = DataCollectorAgent = None

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
