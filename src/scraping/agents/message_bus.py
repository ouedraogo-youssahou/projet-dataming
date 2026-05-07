# ============================================
# A2A Message Bus & Agent Registry
# Inter-agent communication layer
# ============================================

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

from .protocol import (
    A2AMessage, A2AMessageType, AgentInfo, AgentStatus, AgentCapability,
)

logger = logging.getLogger(__name__)


class A2AMessageBus:
    """
    Message bus for A2A communication between agents.
    
    In development mode: uses in-memory asyncio.Queues (no external dependency).
    In production mode: can be backed by Redis Pub/Sub for distributed agents.
    
    Each agent has its own queue identified by its agent_id.
    Channels allow broadcast communication (e.g., "orchestrator", "agents", "data_collector").
    """

    def __init__(self, use_redis: bool = False, redis_config: Optional[Dict[str, Any]] = None):
        self.use_redis = use_redis
        self.redis_config = redis_config or {}

        # In-memory queues (development mode)
        self._queues: Dict[str, asyncio.Queue] = defaultdict(lambda: asyncio.Queue())
        self._channels: Dict[str, Set[str]] = defaultdict(set)  # channel → set of agent_ids

        # Redis client (production mode)
        self._redis = None
        if use_redis:
            self._init_redis()

        # Statistics
        self.messages_sent: int = 0
        self.messages_received: int = 0
        self.start_time: float = time.time()

    def _init_redis(self):
        """Initialize Redis connection (production mode)."""
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.Redis(
                host=self.redis_config.get("host", "localhost"),
                port=self.redis_config.get("port", 6379),
                db=self.redis_config.get("db", 0),
                password=self.redis_config.get("password", None),
                decode_responses=True,
            )
            logger.info("A2AMessageBus: Redis initialized for distributed messaging")
        except ImportError:
            logger.warning("redis.asyncio not available, falling back to in-memory queues")
            self.use_redis = False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, falling back to in-memory queues")
            self.use_redis = False

    async def publish(self, channel: str, message: A2AMessage) -> bool:
        """
        Publish a message to a channel.
        All agents subscribed to this channel will receive the message.
        """
        try:
            if self.use_redis and self._redis:
                await self._redis.publish(channel, message.to_dict())
            else:
                # In-memory: deliver to queue subscribers
                subscribers = self._channels.get(channel, set())
                if not subscribers and channel != "broadcast":
                    # Try as direct agent_id
                    if channel in self._queues:
                        await self._queues[channel].put(message)
                        self.messages_sent += 1
                        return True
                for agent_id in subscribers:
                    if agent_id in self._queues:
                        await self._queues[agent_id].put(message)
                        self.messages_sent += 1

            self.messages_sent += 1
            return True
        except Exception as e:
            logger.error(f"Failed to publish message to {channel}: {e}")
            return False

    async def subscribe(self, agent_id: str, channel: str = "") -> bool:
        """
        Subscribe an agent to receive messages.
        If channel is specified, subscribes to that channel.
        Otherwise creates a direct queue for the agent.
        """
        try:
            # Always ensure a direct queue exists for the agent
            if agent_id not in self._queues:
                self._queues[agent_id] = asyncio.Queue()

            if channel:
                self._channels[channel].add(agent_id)
                logger.debug(f"Agent {agent_id} subscribed to channel '{channel}'")
            else:
                logger.debug(f"Agent {agent_id} has direct message queue")

            if self.use_redis and self._redis:
                pubsub = self._redis.pubsub()
                if channel:
                    await pubsub.subscribe(channel)
                # Note: Redis pubsub is managed separately in production

            return True
        except Exception as e:
            logger.error(f"Failed to subscribe agent {agent_id}: {e}")
            return False

    async def unsubscribe(self, agent_id: str, channel: str = ""):
        """Unsubscribe an agent from a channel."""
        if channel:
            self._channels[channel].discard(agent_id)
        else:
            self._queues.pop(agent_id, None)

    async def consume(self, agent_id: str, timeout: float = 5.0) -> Optional[A2AMessage]:
        """
        Consume the next message for an agent.
        Blocks until a message is available or timeout.
        """
        try:
            queue = self._queues.get(agent_id)
            if queue is None:
                return None

            message = await asyncio.wait_for(queue.get(), timeout=timeout)
            self.messages_received += 1
            return message
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logger.error(f"Error consuming message for {agent_id}: {e}")
            return None

    async def request_response(self, target_id: str, message: A2AMessage,
                               timeout: float = 30.0) -> Optional[A2AMessage]:
        """
        Send a request and wait for a response.
        Creates a temporary response queue for the sender.
        """
        response_queue: asyncio.Queue = asyncio.Queue()
        temp_queue_id = f"_response_{message.msg_id}"

        # Register temporary response queue
        self._queues[temp_queue_id] = response_queue
        message.payload["_response_queue"] = temp_queue_id

        # Send message
        await self.publish(target_id, message)

        try:
            response = await asyncio.wait_for(response_queue.get(), timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request to {target_id} timed out after {timeout}s")
            return None
        finally:
            # Clean up temporary queue
            self._queues.pop(temp_queue_id, None)

    def get_statistics(self) -> Dict[str, Any]:
        """Get message bus statistics."""
        return {
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "active_queues": len(self._queues),
            "active_channels": {ch: len(subs) for ch, subs in self._channels.items()},
            "uptime": time.time() - self.start_time,
            "mode": "redis" if self.use_redis else "in_memory",
        }

    async def close(self):
        """Clean up resources."""
        if self._redis:
            await self._redis.close()
        self._queues.clear()
        self._channels.clear()


class AgentRegistry:
    """
    Registry of all available agents.
    Agents register here so the orchestrator can discover them.
    """

    def __init__(self, heartbeat_timeout: float = 90.0):
        self._agents: Dict[str, AgentInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout  # seconds before marking as offline
        self.start_time = time.time()

    async def register(self, agent_info: AgentInfo) -> bool:
        """Register an agent."""
        agent_info.last_heartbeat = time.time()
        if not agent_info.registered_at:
            agent_info.registered_at = time.time()
        self._agents[agent_info.agent_id] = agent_info
        logger.info(f"Registry: Agent '{agent_info.agent_id}' registered ({agent_info.agent_type})")
        return True

    async def unregister(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].status = AgentStatus.OFFLINE
            del self._agents[agent_id]
            logger.info(f"Registry: Agent '{agent_id}' unregistered")
            return True
        return False

    async def heartbeat(self, agent_id: str) -> bool:
        """Update agent's last heartbeat time."""
        if agent_id in self._agents:
            self._agents[agent_id].last_heartbeat = time.time()
            if self._agents[agent_id].status == AgentStatus.OFFLINE:
                self._agents[agent_id].status = AgentStatus.IDLE
            return True
        return False

    async def discover(self, platform: Optional[str] = None) -> List[AgentInfo]:
        """
        Discover agents, optionally filtered by platform capability.
        Returns only agents that appear alive (recent heartbeat).
        """
        now = time.time()
        available = []

        for agent_info in self._agents.values():
            # Check if agent is alive
            if now - agent_info.last_heartbeat > self._heartbeat_timeout:
                agent_info.status = AgentStatus.OFFLINE
                continue

            # Filter by platform if specified
            if platform and agent_info.capabilities.platform != platform:
                if agent_info.capabilities.platform != "generic":
                    continue

            available.append(agent_info)

        return available

    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent."""
        return self._agents.get(agent_id)

    async def list_agents(self) -> List[AgentInfo]:
        """List all registered agents (including offline)."""
        return list(self._agents.values())

    async def health_check_all(self) -> Dict[str, str]:
        """
        Check health of all agents.
        Returns dict of agent_id → status.
        """
        now = time.time()
        health = {}

        for agent_id, agent_info in self._agents.items():
            if now - agent_info.last_heartbeat > self._heartbeat_timeout:
                agent_info.status = AgentStatus.OFFLINE
                health[agent_id] = AgentStatus.OFFLINE
            else:
                health[agent_id] = agent_info.status

        return health

    async def count_by_type(self) -> Dict[str, int]:
        """Count agents by type."""
        counts: Dict[str, int] = {}
        for agent_info in self._agents.values():
            counts[agent_info.agent_type] = counts.get(agent_info.agent_type, 0) + 1
        return counts

    async def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        health = await self.health_check_all()
        online = sum(1 for s in health.values() if s != AgentStatus.OFFLINE)
        return {
            "total_agents": len(self._agents),
            "online_agents": online,
            "offline_agents": len(self._agents) - online,
            "by_type": await self.count_by_type(),
            "uptime": time.time() - self.start_time,
        }