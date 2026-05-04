import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.responses import JSONResponse
import uvicorn

from src.llm.wrapper import LLMWrapper
from src.scraping.shopify_scraper import ShopifyScraper
from src.scraping.woocommerce_scraper import WooCommerceScraper

logger = logging.getLogger(__name__)


class MCPServer:
    """Model Context Protocol server exposing tools for LLM use."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get("security", {}).get("api_key", "")
        self._app = FastAPI(
            title=config.get("server", {}).get("name", "Ecommerce MCP Server"),
            version=config.get("server", {}).get("version", "1.0.0"),
        )
        self.llm = LLMWrapper(
            openai_key=config.get("llm_integration", {}).get("openai_key"),
            anthropic_key=config.get("llm_integration", {}).get("anthropic_key"),
        )
        self.shopify_scraper = ShopifyScraper(config.get("scraping", {}).get("shopify", {}))
        self.woocommerce_scraper = WooCommerceScraper(config.get("scraping", {}).get("woocommerce", {}))
        self._setup_routes()

    @property
    def app(self):
        """Expose FastAPI app for ASGI servers."""
        return self._app

    def _verify_api_key(self, x_api_key: Optional[str] = Header(None)) -> bool:
        if not self.api_key:
            # If no API key configured, allow all (dev mode)
            return True
        return x_api_key == self.api_key

    def _auth_dependency(self, x_api_key: Optional[str] = Header(None)):
        if not self._verify_api_key(x_api_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return True

    def _setup_routes(self):
        @self.app.get("/health")
        async def health():
            return {"status": "ok", "service": "ecommerce-mcp-server"}

        @self.app.get("/ready")
        async def ready(_auth=Depends(self._auth_dependency)):
            # Simple readiness check: can we reach LLM? (optional, skip if no key)
            return {"status": "ready", "mcp": True}

        @self.app.get("/.well-known/mcp")
        async def mcp_capabilities():
            return {
                "mcpVersion": "2025-03-26",
                "capabilities": {
                    "tools": {
                        "listChanged": True,
                    },
                    "logging": {},
                },
            }

        @self.app.get("/tools")
        async def list_tools(_auth=Depends(self._auth_dependency)):
            return {
                "tools": [
                    {
                        "name": "scrape_shopify",
                        "description": "Scrape product data from a Shopify store using Storefront API or HTML fallback.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string", "description": "Shopify product or store URL"},
                            },
                            "required": ["url"],
                        },
                    },
                    {
                        "name": "scrape_woocommerce",
                        "description": "Scrape product data from a WooCommerce store using REST API.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "url": {"type": "string", "description": "WooCommerce product or store URL"},
                            },
                            "required": ["url"],
                        },
                    },
                    {
                        "name": "analyze_top_k",
                        "description": "Analyze a list of products and return top-K by scoring criteria.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "products": {
                                    "type": "array",
                                    "items": {"type": "object"},
                                    "description": "List of product objects with price, rating, etc.",
                                },
                                "k": {"type": "integer", "minimum": 1, "description": "Number of top products to return", "default": 10},
                                "weights": {
                                    "type": "object",
                                    "description": "Scoring weights (rating, reviews_count, price_competitiveness, availability)",
                                },
                            },
                            "required": ["products"],
                        },
                    },
                    {
                        "name": "generate_summary",
                        "description": "Generate a natural language summary of products and top-K results using LLM.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "products": {"type": "array", "items": {"type": "object"}, "description": "Product list"},
                                "top_k": {"type": "array", "items": {"type": "object"}, "description": "Top-K products"},
                                "prompt": {"type": "string", "description": "Custom prompt (optional)", "default": ""},
                            },
                            "required": ["products"],
                        },
                    },
                    {
                        "name": "list_resources",
                        "description": "List available resources (MCP).",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                        },
                    },
                ]
            }

        @self.app.post("/tools/scrape_shopify")
        async def tool_scrape_shopify(payload: Dict[str, Any], _auth=Depends(self._auth_dependency)):
            url = payload.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="Missing url")
            try:
                logger.info(f"MCP tool scrape_shopify: {url}")
                result = await self.shopify_scraper.scrape(url)
                return {"content": [{"type": "text", "text": str(result)}]}
            except Exception as e:
                logger.error(f"Scrape error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/tools/scrape_woocommerce")
        async def tool_scrape_woocommerce(payload: Dict[str, Any], _auth=Depends(self._auth_dependency)):
            url = payload.get("url")
            if not url:
                raise HTTPException(status_code=400, detail="Missing url")
            try:
                logger.info(f"MCP tool scrape_woocommerce: {url}")
                result = await self.woocommerce_scraper.scrape(url)
                return {"content": [{"type": "text", "text": str(result)}]}
            except Exception as e:
                logger.error(f"Scrape error: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/tools/analyze_top_k")
        async def tool_analyze_top_k(payload: Dict[str, Any], _auth=Depends(self._auth_dependency)):
            products = payload.get("products", [])
            k = payload.get("k", 10)
            weights = payload.get("weights", None)

            from src.__main__ import SmartECommerceIntelligence
            import yaml
            from pathlib import Path
            cfg_path = Path(__file__).parent.parent / "config" / "config.yaml"
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            engine = SmartECommerceIntelligence(cfg)
            top_k = engine.analyze_top_k(products, k=k, weights=weights)
            logger.info(f"MCP analyze_top_k: {len(products)} products -> top {k}")
            return {"content": [{"type": "text", "text": str(top_k)}]}

        @self.app.post("/tools/generate_summary")
        async def tool_generate_summary(payload: Dict[str, Any], _auth=Depends(self._auth_dependency)):
            products = payload.get("products", [])
            top_k = payload.get("top_k", [])
            custom_prompt = payload.get("prompt", "")

            from src.__main__ import SmartECommerceIntelligence
            import yaml
            from pathlib import Path
            cfg_path = Path(__file__).parent.parent / "config" / "config.yaml"
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f)
            engine = SmartECommerceIntelligence(cfg)
            if custom_prompt:
                summary = engine.llm.complete(custom_prompt, max_tokens=500)
            else:
                summary = engine.generate_summary(products, top_k)
            logger.info(f"MCP generate_summary: {len(products)} products summarized")
            return {"content": [{"type": "text", "text": summary}]}

        @self.app.get("/resources")
        async def list_resources(_auth=Depends(self._auth_dependency)):
            return {
                "resources": [
                    {
                        "uri": "data://products/sample",
                        "name": "Sample products resource",
                        "description": "A sample list of products for testing",
                        "mimeType": "application/json",
                    }
                ]
            }

        @self.app.get("/resources/data://products/sample")
        async def get_sample_products(_auth=Depends(self._auth_dependency)):
            sample = [
                {"product_id": "1", "name": "Wireless Earbuds", "price": 59.0, "rating": 4.6, "reviews_count": 1200, "availability": True, "category": "Electronics"},
                {"product_id": "2", "name": "Fitness Tracker", "price": 49.0, "rating": 4.2, "reviews_count": 340, "availability": True, "category": "Sport"},
            ]
            return {"uri": "data://products/sample", "mimeType": "application/json", "text": str(sample)}

    def run(self, host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
        """Run the MCP server."""
        uvicorn.run(self.app, host=host, port=port, reload=reload)


# Module-level app instance for ASGI/WSGI servers
app = MCPServer({"server": {"name": "Ecommerce MCP Server", "version": "1.0.0"}}).app

# Keep for backward compatibility / direct usage
if __name__ == "__main__":
    import yaml
    from pathlib import Path

    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    server = MCPServer(config.get("mcp", {}))
    server.run(host=config.get("mcp", {}).get("server", {}).get("host", "0.0.0.0"), port=config.get("mcp", {}).get("server", {}).get("port", 8000))
