import asyncio
import logging
import aiohttp
from typing import Any, Dict, List, Optional

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ShopifyScraper(BaseScraper):
    """Shopify Storefront API scraper (no HTML fallback)."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.api_version = self.config.get("api_version", "2024-01")
        self.access_token = self.config.get("access_token", "")

    async def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Scrape a Shopify product via Storefront GraphQL API only.
        No HTML fallback – requires valid access_token and .myshopify.com domain.
        """
        await self._throttle()
        if not self.access_token:
            raise ValueError("ShopifyScraper: access_token required, no fallback available")
        if ".myshopify.com" not in url:
            raise ValueError(f"ShopifyScraper: invalid Shopify URL: {url}")

        return await self._scrape_graphql(url)

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

