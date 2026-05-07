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

logger = logging.getLogger(__name__)


class TaskScheduler:
    """Schedules periodic scraping and ML retraining tasks."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or Path(__file__).parent.parent.parent / "config" / "config.yaml"
        self.config = self._load_config()
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _load_config(self) -> dict:
        """Load configuration."""
        with open(self.config_path) as f:
            return yaml.safe_load(f)

    def _setup_jobs(self):
        """Configure scheduled jobs from config."""
        scraping_schedule = os.getenv("SCRAPING_SCHEDULE", self.config.get("scheduling", {}).get("scraping", "0 3 * * *"))
        ml_retrain_schedule = os.getenv("ML_RETRAIN_SCHEDULE", self.config.get("scheduling", {}).get("ml_retrain", "0 4 * * 0"))

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
        """Execute the full scraping pipeline."""
        logger.info("=" * 60)
        logger.info("Starting scheduled scraping pipeline")
        logger.info("=" * 60)

        try:
            from src.__main__ import SmartECommerceIntelligence

            # Load targets from config
            targets = self.config.get("scraping", {}).get("scheduled_targets", [
                {"platform": "shopify", "url": "https://storefront-demo.myshopify.com"},
                {"platform": "woocommerce", "url": "https://example-woo.com"},
            ])

            engine = SmartECommerceIntelligence(self.config)
            result = engine.run_pipeline(targets, top_k_count=10)

            # Store results
            await engine.store_results(result.get("top_k", []), source="scheduled_scrape")

            logger.info(f"Scraping complete: {len(result.get('top_k', []))} top products found")

        except Exception as e:
            logger.error(f"Scraping pipeline failed: {e}", exc_info=True)

    async def run_ml_retraining(self):
        """Retrain ML models on latest data."""
        logger.info("=" * 60)
        logger.info("Starting scheduled ML retraining")
        logger.info("=" * 60)

        try:
            # TODO: Implement full Kubeflow pipeline submission
            # For now, just log that it would run
            logger.info("ML retraining triggered (Kubeflow pipeline integration pending)")

            # When Kubeflow is ready:
            # from src.pipelines.kubeflow.run_pipeline import run_pipeline_kfp
            # run = run_pipeline_kfp(...)

        except Exception as e:
            logger.error(f"ML retraining failed: {e}", exc_info=True)

    async def health_check(self):
        """Check health of all services."""
        try:
            # Check database connection
            from src.scraping.storage import PostgreSQLStorage
            storage = PostgreSQLStorage(self.config.get("database", {}))
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
