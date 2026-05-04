#!/usr/bin/env bash
set -e

echo "== Smart eCommerce Intelligence - Quick Start =="
echo ""
echo "1. Checking Python imports..."
cd /app && python -c "
from src.scraping.shopify_scraper import ShopifyScraper
from src.scraping.woocommerce_scraper import WooCommerceScraper
from src.scraping.selenium_scraper import SeleniumScraper
from src.scraping.playwright_scraper import PlaywrightScraper
from src.data_analysis.ml_models.clustering import ClusteringEngine
from src.data_analysis.ml_models.classification import ClassificationEngine
from src.data_analysis.ml_models.association import AssociationEngine
from src.llm.wrapper import LLMWrapper
from src.mcp.server import MCPServer
from src.dashboard.app import render_header
print('OK: all imports succeeded')
"

echo ""
echo "2. Running minimal pipeline on sample data..."
cd /app && python -m src.__main__

echo ""
echo "== Done. You can now run Docker services. =="
