#!/usr/bin/env python
# ============================================
# Scheduler - Periodic task scheduler for scraping & ML retraining
# ============================================

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.config import expand_config_vars

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Schedules periodic scraping and ML retraining tasks."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "config.yaml"
        self.config = self._load_config()
        self.scheduler = AsyncIOScheduler()
        # Éviter les imports lourds dans __init__
        self._scraping_engine = None
        self._setup_jobs()

    def _load_config(self) -> dict:
        """Load configuration."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f)
        return expand_config_vars(config)

    def _get_engine(self):
        """Lazy-init du moteur principal (évite l'import lourd au démarrage)."""
        if self._scraping_engine is None:
            from src.scraping.shopify_scraper import ShopifyScraper
            from src.scraping.woocommerce_scraper import WooCommerceScraper
            from src.scraping.storage import PostgreSQLStorage
            from src.llm.wrapper import LLMWrapper

            # Mini-engine pour le scraping programmé (sans dépendre de __main__)
            class _ScheduledEngine:
                def __init__(self, config):
                    self.config = config
                    scrap_cfg = config.get("scraping", {})
                    self.shopify = ShopifyScraper(scrap_cfg.get("shopify", {}))
                    self.woocommerce = WooCommerceScraper(scrap_cfg.get("woocommerce", {}))
                    db_cfg = config.get("database", {})
                    self.storage = PostgreSQLStorage(db_cfg)

                async def scrape_target(self, target: dict) -> dict:
                    platform = target.get("platform")
                    url = target.get("url")
                    if platform == "shopify":
                        data = await self.shopify.scrape(url)
                    else:
                        data = await self.woocommerce.scrape(url)
                    return {"platform": platform, "url": url, "data": data}

                async def store(self, products, source: str = "scheduled"):
                    await self.storage.initialize()
                    return await self.storage.store(products, source_url=source)

            self._scraping_engine = _ScheduledEngine(self.config)
        return self._scraping_engine

    def _setup_jobs(self):
        """Configure scheduled jobs from config."""
        scraping_schedule = os.getenv("SCRAPING_SCHEDULE", "0 3 * * *")
        ml_retrain_schedule = os.getenv("ML_RETRAIN_SCHEDULE", "0 4 * * 0")

        # Job 1: Daily scraping
        self.scheduler.add_job(
            self.run_scraping_pipeline,
            CronTrigger.from_crontab(scraping_schedule),
            id="daily_scraping",
            name="Daily e-commerce scraping",
            replace_existing=True,
        )
        logger.info(f"Scheduled daily scraping: {scraping_schedule}")

        # Job 2: Weekly ML retraining
        self.scheduler.add_job(
            self.run_ml_retraining,
            CronTrigger.from_crontab(ml_retrain_schedule),
            id="weekly_retrain",
            name="Weekly ML model retraining",
            replace_existing=True,
        )
        logger.info(f"Scheduled weekly retraining: {ml_retrain_schedule}")

        # Job 3: Health check (every 5 minutes)
        self.scheduler.add_job(
            self.health_check,
            "interval",
            minutes=5,
            id="health_check",
            name="Service health check",
        )
        logger.info("Scheduled health check: every 5 minutes")

    async def run_scraping_pipeline(self):
        """Execute the full scraping pipeline (sans dépendre de __main__)."""
        logger.info("=" * 60)
        logger.info("Starting scheduled scraping pipeline")
        logger.info("=" * 60)

        try:
            engine = self._get_engine()

            targets = self.config.get("scraping", {}).get("scheduled_targets", [
                {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
                {"platform": "woocommerce", "url": "https://example-woo.com"},
            ])

            all_products = []
            for target in targets:
                result = await engine.scrape_target(target)
                data = result.get("data", [])
                if isinstance(data, list):
                    all_products.extend(data)
                elif isinstance(data, dict):
                    all_products.append(data)

            await engine.store(all_products, source="scheduled_scrape")
            logger.info(f"Scheduled scraping complete: {len(all_products)} products")

        except Exception as e:
            logger.error(f"Scraping pipeline failed: {e}", exc_info=True)

    async def run_ml_retraining(self):
        """Retrain ML models on latest data (Kubeflow pipeline)."""
        logger.info("=" * 60)
        logger.info("Starting scheduled ML retraining")
        logger.info("=" * 60)

        try:
            # Vérifier si le pipeline KFP est disponible
            try:
                from src.pipelines.kubeflow.pipeline import ecommerce_ml_pipeline
                from kfp import compiler
                compiler.Compiler().compile(ecommerce_ml_pipeline, '/tmp/pipeline.yaml')
                logger.info("KFP pipeline compiled successfully (pending submission)")
            except ImportError:
                logger.info("Kubeflow pipeline module not available; skipping retraining")

        except Exception as e:
            logger.error(f"ML retraining failed: {e}", exc_info=True)

    async def health_check(self):
        """Check health of all services."""
        try:
            # Check database connection (config.database.postgresql)
            db_cfg = self.config.get("database", {})
            from src.scraping.storage import PostgreSQLStorage
            storage = PostgreSQLStorage(db_cfg)
            await storage.initialize()
            await storage.close()
            logger.debug("Health check: PostgreSQL OK")

            # Check Redis connection
            import redis
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                password=os.getenv("REDIS_PASSWORD", ""),
                decode_responses=True,
            )
            r.ping()
            logger.debug("Health check: Redis OK")

        except Exception as e:
            logger.warning(f"Health check failed: {e}")

    def start(self):
        """Start the scheduler."""
        logger.info("Starting Task Scheduler...")
        self.scheduler.start()
        logger.info("Scheduler started")

    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping Task Scheduler...")
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")


async def main():
    """Main entry point."""
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    scheduler = TaskScheduler()
    scheduler.start()

    logger.info("Scheduler running. Press Ctrl+C to stop.")

    try:
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
