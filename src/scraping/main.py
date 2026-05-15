# Point d'entrée pour le service scraper autonome
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Boucle principale du scraper : utilise les agents A2A."""
    import yaml
    from src.config import expand_config_vars

    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)
    config = expand_config_vars(config)

    # Importer les agents A2A (uniquement ce qui est nécessaire pour le scraping)
    from src.scraping.agents.message_bus import A2AMessageBus, AgentRegistry
    from src.scraping.agents.orchestrator import AgentOrchestrator
    from src.scraping.agents.specialized_agents import ShopifyAgent, WooCommerceAgent, GenericScraperAgent
    from src.scraping.agents.data_collector import DataCollectorAgent

    # Initialiser le bus et le registry
    agents_config = config.get("agents", {}).get("a2a", {})
    use_redis = agents_config.get("use_redis", False)
    message_bus = A2AMessageBus(use_redis=use_redis)
    registry = AgentRegistry()

    # Créer les agents
    agents = [
        ShopifyAgent("shopify_agent_1", config=config, message_bus=message_bus, registry=registry),
        WooCommerceAgent("woocommerce_agent_1", config=config, message_bus=message_bus, registry=registry),
        GenericScraperAgent("generic_agent_1", config=config, message_bus=message_bus, registry=registry),
        DataCollectorAgent("data_collector", config=config, message_bus=message_bus, registry=registry),
    ]

    # Créer l'orchestrateur
    orchestrator = AgentOrchestrator(message_bus, registry, config=agents_config)

    # Enregistrer les agents
    for agent in agents:
        await orchestrator.register_agent(agent)

    # Lancer l'orchestrateur
    await orchestrator.start()

    # Définir les cibles : WooCommerce store depuis .env (shopify désactivé pour l'instant)
    import os
    woo_url = os.getenv("WOOCOMMERCE_STORE_URL", "")
    targets = []
    if woo_url:
        targets.append({"platform": "woocommerce", "url": woo_url})
    else:
        # Cible par défaut si aucune URL configurée
        targets = [{"platform": "woocommerce", "url": "https://majestic-cheese.localsite.io"}]

    logger.info(f"Scraper démarré avec {len(agents)} agents et {len(targets)} cibles")

    try:
        # Lancer le pipeline de scraping
        result = await orchestrator.run_all(targets)
        summary = result.get("summary", {})
        logger.info(f"Scraping terminé : {summary.get('completed', 0)} succès, {summary.get('failed', 0)} échecs")
    except KeyboardInterrupt:
        logger.info("Arrêt du scraper...")
    finally:
        await orchestrator.stop()
        for agent in agents:
            await agent.shutdown()
        await message_bus.close()

    logger.info("Scraper terminé")


if __name__ == "__main__":
    asyncio.run(main())