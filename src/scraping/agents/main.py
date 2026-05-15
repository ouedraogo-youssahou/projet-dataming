#!/usr/bin/env python
# ============================================
# Agent Launcher - Starts A2A Agent Cluster
# ============================================

import asyncio
import json
import logging
import os
import signal
import sys
from pathlib import Path

import yaml
from src.config import expand_config_vars

from src.scraping.agents import (
    A2AMessageBus,
    AgentRegistry,
    AgentOrchestrator,
    ShopifyAgent,
    WooCommerceAgent,
    GenericScraperAgent,
    DataCollectorAgent,
)

logger = logging.getLogger(__name__)


async def load_targets(targets_file=None, targets_list=None):
    """Load scraping targets from config or defaults."""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    config = expand_config_vars(config)

    # Check for targets in config
    targets_from_config = config.get("scraping", {}).get("targets", [])
    if targets_from_config:
        return targets_from_config

    # Fallback to provided file/list
    if targets_file:
        with open(targets_file) as f:
            return json.load(f)
    if targets_list:
        return json.loads(targets_list)

    # Default demo targets
    return [
        {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
        {"platform": "woocommerce", "url": "https://example-woo.com"},
    ]


async def main():
    """Main entry point for agent cluster."""
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("=== Starting A2A Agent Cluster ===")

    # Load config
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    config = expand_config_vars(config)

    # Get Redis config
    use_redis = config.get("agents", {}).get("a2a", {}).get("use_redis", False)
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_password = os.getenv("REDIS_PASSWORD", "")

    # Create message bus
    if use_redis:
        logger.info(f"Using Redis-backed message bus at {redis_host}")
        from src.scraping.agents.redis_bus import RedisA2AMessageBus
        bus = RedisA2AMessageBus(
            host=redis_host,
            password=redis_password,
        )
    else:
        logger.info("Using in-memory message bus (development mode)")
        bus = A2AMessageBus()

    # Create registry
    registry = AgentRegistry(
        heartbeat_timeout=config.get("agents", {}).get("a2a", {}).get("heartbeat_interval", 30) * 3
    )

    # Create agents
    agents_config = config.get("agents", {}).get("defaults", {})

    shopify_agent = ShopifyAgent(
        agent_id="shopify_agent_1",
        config=config,
        message_bus=bus,
        registry=registry,
    )

    woo_agent = WooCommerceAgent(
        agent_id="woocommerce_agent_1",
        config=config,
        message_bus=bus,
        registry=registry,
    )

    generic_agent = GenericScraperAgent(
        agent_id="generic_agent_1",
        config=config,
        message_bus=bus,
        registry=registry,
    )

    collector_agent = DataCollectorAgent(
        agent_id="collector_agent_1",
        config=config,
        message_bus=bus,
        registry=registry,
    )

    agents = [shopify_agent, woo_agent, generic_agent, collector_agent]

    # Create orchestrator
    orchestrator = AgentOrchestrator(bus, registry, config)

    # Register all agents
    logger.info("Registering agents with orchestrator...")
    for agent in agents:
        await orchestrator.register_agent(agent)
        logger.info(f"  ✓ Registered: {agent.agent_id} ({agent.agent_type})")

    # Start orchestrator
    await orchestrator.start()
    logger.info("Orchestrator started")

    # Setup signal handlers for graceful shutdown
    loop = asyncio.get_event_loop()

    shutdown_event = asyncio.Event()

    def signal_handler():
        logger.info("Shutdown signal received")
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    # Load and run targets if provided
    targets = await load_targets(
        targets_file=os.getenv("TARGETS_FILE"),
        targets_list=os.getenv("TARGETS_JSON"),
    )

    if targets:
        logger.info(f"Running {len(targets)} scraping targets...")
        result = await orchestrator.run_all(targets)

        # Print summary
        summary = result.get("summary", {})
        logger.info("=" * 60)
        logger.info("Pipeline Complete")
        logger.info(f"  Total tasks: {summary.get('total_tasks', 0)}")
        logger.info(f"  Completed: {summary.get('completed', 0)}")
        logger.info(f"  Failed: {summary.get('failed', 0)}")
        logger.info(f"  Retried: {summary.get('retried', 0)}")
        logger.info("=" * 60)

        # Wait for collector to flush to database
        await asyncio.sleep(2)

    # Keep running until shutdown signal
    logger.info("Agent cluster running. Press Ctrl+C to stop.")
    await shutdown_event.wait()

    # Graceful shutdown
    logger.info("Shutting down...")
    await orchestrator.stop()
    await bus.close()
    logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
