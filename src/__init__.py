"""Smart eCommerce Intelligence - Main Package."""
# Tous les imports sont conditionnels pour fonctionner même dans des images sans ML

# Scraping (toujours disponible)
try:
    from src.scraping.shopify_scraper import ShopifyScraper
except ImportError:
    ShopifyScraper = None

try:
    from src.scraping.woocommerce_scraper import WooCommerceScraper
except ImportError:
    WooCommerceScraper = None

try:
    from src.scraping.storage import PostgreSQLStorage
except ImportError:
    PostgreSQLStorage = None

# ML Engines (disponible seulement dans ml-training)
try:
    from src.data_analysis.ml_models.clustering import ClusteringEngine
except ImportError:
    ClusteringEngine = None

try:
    from src.data_analysis.ml_models.classification import ClassificationEngine
except ImportError:
    ClassificationEngine = None

try:
    from src.data_analysis.ml_models.association import AssociationEngine
except ImportError:
    AssociationEngine = None

# LLM
try:
    from src.llm.wrapper import LLMWrapper
except ImportError:
    LLMWrapper = None

try:
    from src.llm.competitive_analysis import CompetitiveAnalysis, generate_competitive_insights
except ImportError:
    CompetitiveAnalysis = None
    generate_competitive_insights = None

# MCP Server
try:
    from src.mcp.server import MCPServer
except ImportError:
    MCPServer = None

__all__ = [
    "ShopifyScraper",
    "WooCommerceScraper",
    "PostgreSQLStorage",
    "ClusteringEngine",
    "ClassificationEngine",
    "AssociationEngine",
    "LLMWrapper",
    "CompetitiveAnalysis",
    "generate_competitive_insights",
    "MCPServer",
]
