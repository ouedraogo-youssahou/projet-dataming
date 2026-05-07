#!/usr/bin/env python
# ============================================
# Prometheus Metrics Exporter
# ============================================

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, Info, start_http_server

logger = logging.getLogger(__name__)


@dataclass
class MetricLabels:
    """Common metric labels."""
    service: str = "ecommerce"
    platform: str = "none"
    agent_id: str = "none"


class MetricsCollector:
    """Collects and exposes Prometheus metrics for the eCommerce system."""

    def __init__(self, port: int = 9090):
        self.port = port

        # Define metrics
        # ─────────────────────────────────────────────────────────────
        # Scraping metrics
        self.scrape_requests_total = Counter(
            'ecommerce_scrape_requests_total',
            'Total number of scraping requests',
            ['platform', 'status']
        )
        self.scrape_duration_seconds = Histogram(
            'ecommerce_scrape_duration_seconds',
            'Scraping duration in seconds',
            ['platform'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        )

        # Agent metrics
        self.agent_tasks_total = Counter(
            'ecommerce_agent_tasks_total',
            'Total tasks processed by agents',
            ['agent_id', 'agent_type', 'status'],
        )
        self.agent_queue_size = Gauge(
            'ecommerce_agent_queue_size',
            'Current size of agent task queue',
            ['agent_id'],
        )
        self.agent_active_tasks = Gauge(
            'ecommerce_agent_active_tasks',
            'Number of currently active tasks per agent',
            ['agent_id'],
        )

        # Database metrics
        self.db_connections = Gauge(
            'ecommerce_db_connections',
            'Number of active database connections',
            ['host'],
        )
        self.db_operations_total = Counter(
            'ecommerce_db_operations_total',
            'Total database operations',
            ['operation', 'status'],
        )
        self.products_stored = Gauge(
            'ecommerce_products_stored_total',
            'Total number of products stored in database',
        )

        # ML metrics
        self.model_training_duration = Histogram(
            'ecommerce_model_training_seconds',
            'Model training duration',
            ['model_type'],
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
        )
        self.model_accuracy = Gauge(
            'ecommerce_model_accuracy',
            'Model accuracy on test set',
            ['model_type'],
        )
        self.clustering_silhouette = Gauge(
            'ecommerce_clustering_silhouette',
            'Silhouette score for clustering',
        )

        # Top-K metrics
        self.top_k_selections_total = Counter(
            'ecommerce_top_k_selections_total',
            'Total number of Top-K selections',
        )
        self.top_k_average_score = Gauge(
            'ecommerce_top_k_average_score',
            'Average score of selected top-K products',
        )

        # System health
        self.service_health = Gauge(
            'ecommerce_service_health',
            'Health status of services (1=healthy, 0=unhealthy)',
            ['service_name'],
        )
        self.api_requests_total = Counter(
            'ecommerce_api_requests_total',
            'Total API requests to MCP server',
            ['endpoint', 'method', 'status'],
        )

        # System info
        self.info = Info('ecommerce_system', 'eCommerce Intelligence System Info')
        self.info.info({
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('PYTHON_ENV', 'development'),
        })

        logger.info("Metrics collector initialized")

    def start(self):
        """Start the HTTP server to expose metrics."""
        logger.info(f"Starting Prometheus metrics server on port {self.port}")
        start_http_server(self.port)
        logger.info(f"Metrics available at http://localhost:{self.port}/metrics")

    # ─────────────────────────────────────────────────────────────
    # Scraping helpers
    # ─────────────────────────────────────────────────────────────
    def record_scrape_start(self, platform: str):
        """Record start of a scraping operation."""
        return time.time()

    def record_scrape_end(self, platform: str, start_time: float, status: str = "success"):
        """Record completion of a scraping operation."""
        duration = time.time() - start_time
        self.scrape_duration_seconds.labels(platform=platform).observe(duration)
        self.scrape_requests_total.labels(platform=platform, status=status).inc()

    def increment_products_stored(self, count: int):
        """Increment total products stored."""
        self.products_stored.inc(count)

    # ─────────────────────────────────────────────────────────────
    # Agent helpers
    # ─────────────────────────────────────────────────────────────
    def record_agent_task(self, agent_id: str, agent_type: str, status: str):
        """Record an agent task completion."""
        self.agent_tasks_total.labels(agent_id=agent_id, agent_type=agent_type, status=status).inc()

    def update_agent_queue_size(self, agent_id: str, size: int):
        """Update agent queue size gauge."""
        self.agent_queue_size.labels(agent_id=agent_id).set(size)

    def update_agent_active_tasks(self, agent_id: str, count: int):
        """Update active tasks gauge."""
        self.agent_active_tasks.labels(agent_id=agent_id).set(count)

    # ─────────────────────────────────────────────────────────────
    # Database helpers
    # ─────────────────────────────────────────────────────────────
    def update_db_connections(self, host: str, count: int):
        """Update database connection gauge."""
        self.db_connections.labels(host=host).set(count)

    def record_db_operation(self, operation: str, status: str):
        """Record a database operation."""
        self.db_operations_total.labels(operation=operation, status=status).inc()

    # ─────────────────────────────────────────────────────────────
    # ML helpers
    # ─────────────────────────────────────────────────────────────
    def record_model_training(self, model_type: str, duration_seconds: float):
        """Record model training duration."""
        self.model_training_duration.labels(model_type=model_type).observe(duration_seconds)

    def set_model_accuracy(self, model_type: str, accuracy: float):
        """Set model accuracy gauge."""
        self.model_accuracy.labels(model_type=model_type).set(accuracy)

    def set_clustering_silhouette(self, score: float):
        """Set clustering silhouette score."""
        self.clustering_silhouette.set(score)

    # ─────────────────────────────────────────────────────────────
    # Top-K helpers
    # ─────────────────────────────────────────────────────────────
    def record_top_k_selection(self, count: int, avg_score: float):
        """Record a Top-K selection run."""
        self.top_k_selections_total.inc()
        self.top_k_average_score.set(avg_score)

    # ─────────────────────────────────────────────────────────────
    # Service health
    # ─────────────────────────────────────────────────────────────
    def set_service_health(self, service_name: str, healthy: bool):
        """Set service health gauge."""
        self.service_health.labels(service_name=service_name).set(1 if healthy else 0)


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        port = int(os.getenv("PROMETHEUS_PORT", 9090))
        _metrics_collector = MetricsCollector(port=port)
        _metrics_collector.start()
    return _metrics_collector


# Convenience functions for direct use
def record_scrape(platform: str, duration: float, status: str = "success"):
    get_metrics_collector().record_scrape_end(platform, duration, status)


def record_agent_task(agent_id: str, agent_type: str, status: str):
    get_metrics_collector().record_agent_task(agent_id, agent_type, status)


def set_service_health(service: str, healthy: bool):
    get_metrics_collector().set_service_health(service, healthy)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = get_metrics_collector()
    logger.info("Metrics server running on :9090/metrics")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server")
