# ============================================
# Data Collector Agent - Aggregates and stores scraped data
# ============================================

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from .base_agent import BaseAgent
from .protocol import (
    A2AMessage, A2AMessageType, Task, AgentCapability, AgentStatus,
)
from .message_bus import A2AMessageBus, AgentRegistry
from ..storage import PostgreSQLStorage

logger = logging.getLogger(__name__)


class DataCollectorAgent(BaseAgent):
    """
    Specialized A2A Agent that collects scraped data from other agents
    and stores it in PostgreSQL (or other storage backends).
    
    Acts as the central data aggregation point in the A2A architecture.
    """

    def __init__(
        self,
        agent_id: str = "data_collector",
        config: Optional[Dict[str, Any]] = None,
        message_bus: Optional[A2AMessageBus] = None,
        registry: Optional[AgentRegistry] = None,
    ):
        capabilities = AgentCapability(
            platform="storage",
            max_concurrent_tasks=10,
            supports_js=False,
            supports_api=False,
            rate_limit=0,  # no rate limit for storage
            supported_features=["collect", "store", "aggregate", "query"],
        )
        super().__init__(
            agent_id=agent_id,
            agent_type="data_collector",
            capabilities=capabilities,
            message_bus=message_bus,
            registry=registry,
        )
        self.config = config or {}

        # Storage backend
        db_config = self.config.get("database", {}).get("postgresql", {})
        self.storage = PostgreSQLStorage({"postgresql": db_config})

        # Collected data buffers
        self._data_buffer: List[Dict[str, Any]] = []
        self._buffer_lock = asyncio.Lock()
        self._buffer_max_size = self.config.get("buffer_size", 50)
        self._flush_interval = self.config.get("flush_interval", 30)  # seconds

        # Statistics
        self.products_collected: int = 0
        self.products_stored: int = 0
        self.storage_errors: int = 0
        self._flush_task: Optional[asyncio.Task] = None
        self._storage_initialized = False

        self.metadata["data_collector"] = True

    async def initialize(self):
        """Initialize data collector: connect storage, start flush loop."""
        await super().initialize()

        # Initialize PostgreSQL storage
        try:
            await self.storage.initialize()
            self._storage_initialized = True
            logger.info("DataCollector: PostgreSQL storage initialized")
        except Exception as e:
            logger.warning(f"DataCollector: PostgreSQL init failed, using memory only: {e}")
            self._storage_initialized = False

        # Start periodic flush
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info("DataCollector agent initialized")

    async def shutdown(self):
        """Shutdown: flush remaining data, close storage."""
        # Flush remaining buffer
        await self.flush_buffer()

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Close storage
        if self._storage_initialized:
            await self.storage.close()

        await super().shutdown()

    async def scrape(self, task: Task) -> Any:
        """
        DataCollector doesn't scrape URLs directly.
        It collects data from other agents.
        """
        logger.warning(f"DataCollector received scrape task {task.task_id} - ignoring")
        return {"status": "data_collector_does_not_scrape"}

    async def handle_message(self, message: A2AMessage) -> None:
        """Override to handle DATA_TRANSFER messages."""
        if message.msg_type == A2AMessageType.DATA_TRANSFER:
            await self._handle_data_transfer(message)
        else:
            await super().handle_message(message)

    async def _handle_data_transfer(self, message: A2AMessage):
        """
        Receive scraped data from another agent.
        Buffers and periodically flushes to storage.
        """
        payload = message.payload
        data = payload.get("data", {})
        task_id = payload.get("task_id", "")
        platform = payload.get("platform", "unknown")
        url = payload.get("url", "")

        # Normalize data (handle both single dict and list)
        products = []
        if isinstance(data, dict):
            if "name" in data or "title" in data:
                products.append(data)
            elif "products" in data and isinstance(data["products"], list):
                products.extend(data["products"])
        elif isinstance(data, list):
            products.extend(data)

        if not products:
            logger.warning(f"DataCollector: no valid products in data from {message.sender_id}")
            # Send ACK anyway
            await self._send_ack(message)
            return

        # Add metadata to each product
        for product in products:
            product["_source_agent"] = message.sender_id
            product["_source_platform"] = platform
            product["_source_url"] = url
            product["_collected_at"] = time.time()

        # Add to buffer
        async with self._buffer_lock:
            self._data_buffer.extend(products)
            self.products_collected += len(products)

        logger.info(f"DataCollector: collected {len(products)} products from '{message.sender_id}' "
                     f"(buffer: {len(self._data_buffer)})")

        # Flush if buffer is full
        if len(self._data_buffer) >= self._buffer_max_size:
            asyncio.create_task(self.flush_buffer())

        # Send ACK
        await self._send_ack(message, {"products_received": len(products)})

    async def _send_ack(self, message: A2AMessage, extra: Optional[Dict] = None):
        """Send acknowledgment for received data."""
        if self.message_bus:
            ack = A2AMessage.create(
                msg_type=A2AMessageType.DATA_ACK,
                sender_id=self.agent_id,
                target_id=message.sender_id,
                payload={
                    "original_msg_id": message.msg_id,
                    "status": "received",
                    **(extra or {}),
                },
            )
            await self.message_bus.publish(message.sender_id, ack)

    async def flush_buffer(self):
        """Flush buffered data to PostgreSQL storage."""
        async with self._buffer_lock:
            if not self._data_buffer:
                return

            batch = self._data_buffer[:]
            self._data_buffer = []

        if not batch:
            return

        logger.info(f"DataCollector: flushing {len(batch)} products to storage")

        if self._storage_initialized:
            try:
                stored = await self.storage.store(batch)
                self.products_stored += stored
                logger.info(f"DataCollector: stored {stored} products in PostgreSQL")
            except Exception as e:
                self.storage_errors += 1
                logger.error(f"DataCollector: storage error: {e}")
                # Re-buffer for retry
                async with self._buffer_lock:
                    self._data_buffer.extend(batch)
        else:
            logger.info(f"DataCollector: storage not available, data kept in memory "
                         f"(total in memory: {self.products_collected})")

    async def _periodic_flush(self):
        """Periodically flush buffer to storage."""
        try:
            while self._running:
                await asyncio.sleep(self._flush_interval)
                await self.flush_buffer()
        except asyncio.CancelledError:
            pass

    async def get_statistics(self) -> Dict[str, Any]:
        """Get data collector statistics."""
        return {
            "products_collected": self.products_collected,
            "products_stored": self.products_stored,
            "storage_errors": self.storage_errors,
            "buffer_size": len(self._data_buffer),
            "storage_available": self._storage_initialized,
            **self.get_stats(),
        }

    async def query_products(self, limit: int = 100, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query stored products from PostgreSQL."""
        if not self._storage_initialized:
            logger.warning("DataCollector: storage not available for query")
            return []

        try:
            products = await self.storage.fetch_all(limit=limit)
            if category:
                products = [p for p in products if p.get("category") == category]
            return products
        except Exception as e:
            logger.error(f"DataCollector: query error: {e}")
            return []