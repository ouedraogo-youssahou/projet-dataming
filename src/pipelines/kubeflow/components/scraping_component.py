# ============================================
# Kubeflow Component: Web Scraping
# ============================================

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


def scrape_products(
    config_path: str,
    output_path: str,
    targets_json: Optional[str] = None,
) -> str:
    """
    Kubeflow component: Scrape products from e-commerce platforms.
    
    Args:
        config_path: Path to pipeline configuration file
        output_path: Path to save scraped products (JSON)
        targets_json: Optional JSON string of targets to scrape
        
    Returns:
        JSON string with scraping results summary
    """
    logger.info(f"=== Scraping Component Started ===")
    logger.info(f"Config: {config_path}")
    logger.info(f"Output: {output_path}")

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    scraping_cfg = config.get("components", {}).get("scraping", {})
    data_cfg = config.get("data", {})

    # Parse targets
    if targets_json:
        targets = json.loads(targets_json)
    else:
        # Default targets for demo
        targets = [
            {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
            {"platform": "woocommerce", "url": "https://example-woo.com"},
        ]

    logger.info(f"Targets to scrape: {len(targets)}")

    # Import scraper only when needed (lazy import for container compatibility)
    from src.__main__ import SmartECommerceIntelligence

    engine = SmartECommerceIntelligence(config)

    # Run scraping
    import asyncio
    scrape_results = asyncio.run(engine.scrape_all(targets))

    # Collect all products
    all_products = []
    for r in scrape_results:
        if r.get("status") == "ok" and "data" in r:
            data = r["data"]
            if isinstance(data, list):
                all_products.extend(data)
            elif isinstance(data, dict):
                all_products.append(data)

    logger.info(f"Total products scraped: {len(all_products)}")

    # Save to output file
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(all_products, f, indent=2, default=str)

    logger.info(f"Products saved to {output_path}")

    # Return summary as JSON string
    summary = {
        "status": "completed",
        "total_targets": len(targets),
        "total_products": len(all_products),
        "output_file": output_path,
        "platforms": list(set(r.get("platform") for r in scrape_results)),
    }

    return json.dumps(summary)


def scrape_products_with_agents(
    config_path: str,
    output_path: str,
    targets_json: Optional[str] = None,
) -> str:
    """
    Kubeflow component: Scrape products using A2A agents (distributed).
    
    Uses the AgentOrchestrator for parallel, resilient scraping.
    """
    logger.info(f"=== Scraping with A2A Agents Component Started ===")

    from src.scraping.agents import (
        A2AMessageBus, AgentRegistry, AgentOrchestrator,
        ShopifyAgent, WooCommerceAgent, GenericScraperAgent,
        DataCollectorAgent,
    )

    # Load config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Parse targets
    if targets_json:
        targets = json.loads(targets_json)
    else:
        targets = [
            {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
            {"platform": "woocommerce", "url": "https://example-woo.com"},
        ]

    # Setup A2A system
    import asyncio

    async def run_agents():
        # Create message bus and registry
        bus = A2AMessageBus()
        registry = AgentRegistry(heartbeat_timeout=90.0)

        # Create and register agents
        shopify_agent = ShopifyAgent(
            agent_id="kubeflow_shopify",
            config=config,
            message_bus=bus,
            registry=registry,
        )
        woo_agent = WooCommerceAgent(
            agent_id="kubeflow_woo",
            config=config,
            message_bus=bus,
            registry=registry,
        )
        generic_agent = GenericScraperAgent(
            agent_id="kubeflow_generic",
            config=config,
            message_bus=bus,
            registry=registry,
        )
        collector = DataCollectorAgent(
            agent_id="kubeflow_collector",
            config=config,
            message_bus=bus,
            registry=registry,
        )

        # Create orchestrator
        orchestrator = AgentOrchestrator(bus, registry, config)

        # Register all agents
        await orchestrator.register_agent(shopify_agent)
        await orchestrator.register_agent(woo_agent)
        await orchestrator.register_agent(generic_agent)
        await orchestrator.register_agent(collector)

        # Run pipeline
        result = await orchestrator.run_all(targets)

        # Get results from collector
        products = collector._data_buffer

        # Cleanup
        await orchestrator.stop()
        await bus.close()

        return result, products

    # Run async
    result, products = asyncio.run(run_agents())

    # Save to output
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(products, f, indent=2, default=str)

    logger.info(f"A2A scraping complete: {len(products)} products")

    summary = {
        "status": "completed",
        "method": "a2a_agents",
        "total_products": len(products),
        "task_summary": result.get("summary", {}),
        "output_file": output_path,
    }

    return json.dumps(summary)


if __name__ == "__main__":
    # Local test
    import sys
    config = sys.argv[1] if len(sys.argv) > 1 else "src/pipelines/kubeflow/config/pipeline_config.yaml"
    output = sys.argv[2] if len(sys.argv) > 2 else "data/raw/scraped_products.json"
    result = scrape_products(config, output)
    print(result)