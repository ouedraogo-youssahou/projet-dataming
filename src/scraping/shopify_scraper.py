import asyncio
import logging
import aiohttp
from typing import Any, Dict, List, Optional

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ShopifyScraper(BaseScraper):
    """Shopify Storefront API + HTML fallback scraper."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_version = self.config.get("api_version", "2024-01")
        self.access_token = self.config.get("access_token", "")

    async def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """Try Storefront GraphQL first, fall back to HTML parsing."""
        await self._throttle()
        # Try GraphQL if we have token and it's a shopify domain
        if self.access_token and ".myshopify.com" in url:
            try:
                return await self._scrape_graphql(url)
            except Exception as e:
                logger.warning(f"GraphQL scrape failed for {url}: {e}, falling back")

        # HTML fallback
        return await self._scrape_html(url)

    async def _scrape_graphql(self, url: str) -> Dict[str, Any]:
        """Query Storefront API for product data."""
        # Convert store URL to GraphQL endpoint
        if "/products/" in url:
            handle = url.split("/products/")[-1].split("?")[0].strip("/")
        else:
            handle = ""

        shop_domain = url.split("//")[1].split("/")[0].replace(".myshopify.com", "")
        endpoint = f"https://{shop_domain}.myshopify.com/api/{self.api_version}/graphql.json"

        query = """
        query productByHandle($handle: String!) {
          productByHandle(handle: $handle) {
            id
            title
            description
            descriptionHtml
            handle
            productType: productType
            tags
            vendor
            variants(first: 25) {
              edges {
                node {
                  id
                  title
                  price
                  availableForSale
                  inventoryQuantity
                }
              }
            }
            images(first: 10) {
              edges {
                node {
                  originalSrc
                  altText
                }
              }
            }
            rating: metafield(namespace: "reviews", key: "rating") {
              value
            }
            reviewsCount: metafield(namespace: "reviews", key: "count") {
              value
            }
          }
        }
        """

        variables = {"handle": handle} if handle else {}

        headers = {
            "X-Shopify-Storefront-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

        if not handle:
            # If no handle in URL, try to fetch a generic product list (first product)
            query = """
            query {
              products(first: 1) {
                edges {
                  node {
                    id
                    title
                    description
                    handle
                    productType
                    tags
                    vendor
                    variants(first: 1) {
                      edges {
                        node {
                          price
                          availableForSale
                          inventoryQuantity
                        }
                      }
                    }
                    images(first: 3) {
                      edges {
                        node {
                          originalSrc
                        }
                      }
                    }
                  }
                }
              }
            }
            """
            variables = None

        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                data = await resp.json()

        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")

        if handle:
            product = data.get("data", {}).get("productByHandle")
        else:
            edges = data.get("data", {}).get("products", {}).get("edges", [])
            product = edges[0]["node"] if edges else None

        if not product:
            raise RuntimeError("No product found via GraphQL")

        return self._parse_shopify_gql(product)

    def _parse_shopify_gql(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Parse GraphQL product response."""
        variants = product.get("variants", {}).get("edges", [])
        prices = []
        total_qty = 0
        available = False
        for v in variants:
            node = v.get("node", {})
            price = node.get("price", 0)
            prices.append(float(price) if price else 0.0)
            qty = node.get("inventoryQuantity", 0) or 0
            total_qty += qty if qty else 0
            if node.get("availableForSale"):
                available = True

        images = product.get("images", {}).get("edges", [])
        image_urls = [e["node"]["originalSrc"] for e in images if e.get("node", {}).get("originalSrc")]

        # Try to get rating from metafield
        rating_raw = product.get("rating", {}).get("value")
        reviews_raw = product.get("reviewsCount", {}).get("value")

        return {
            "product_id": product.get("id", ""),
            "name": product.get("title", ""),
            "description": product.get("description", "") or product.get("descriptionHtml", ""),
            "category": product.get("productType", ""),
            "price": min(prices) if prices else 0.0,
            "currency": "USD",
            "availability": available,
            "quantity": total_qty,
            "vendor": product.get("vendor", ""),
            "rating": float(rating_raw) if rating_raw else None,
            "reviews_count": int(reviews_raw) if reviews_raw else None,
            "images": image_urls,
            "tags": product.get("tags", []),
        }

    async def _scrape_html(self, url: str) -> Dict[str, Any]:
        """Basic HTML fallback using aiohttp + selectors."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=self.timeout)) as resp:
                html = await resp.text()

        # Very simple heuristics - in practice use BeautifulSoup or parsel
        import re
        # Extract JSON-LD if present
        ld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
        if ld_match:
            import json
            try:
                ld = json.loads(ld_match.group(1))
                if isinstance(ld, list):
                    ld = ld[0]
                if ld.get("@type") == "Product":
                    name = ld.get("name", "")
                    desc = ld.get("description", "")
                    offers = ld.get("offers", {})
                    price = offers.get("price") if isinstance(offers, dict) else 0
                    avail = offers.get("availability", "") if isinstance(offers, dict) else ""
                    return self.normalize_product({
                        "title": name,
                        "description": desc,
                        "price": price,
                        "available": "InStock" in avail or True,
                    })
            except Exception:
                pass

        # Fallback to basic normalization
        return self.normalize_product({"title": url.split("/")[-1].replace("-", " ").title(), "price": 0})
