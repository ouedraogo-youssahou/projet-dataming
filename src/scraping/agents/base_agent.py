# ============================================
# Base Agent - Abstract class for all A2A scraping agents
# ============================================

from __future__ import annotations

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .protocol import (
    A2AMessage, A2AMessageType,
    Task, TaskStatus, AgentStatus, AgentCapability, AgentInfo,
)

if TYPE_CHECKING:
    from .message_bus import A2AMessageBus, AgentRegistry

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all A2A scraping agents.
    
    An agent is an autonomous component that:
    - Registers itself with the AgentRegistry
    - Listens for task assignments via the MessageBus
    - Executes scraping tasks using platform-specific logic
    - Reports progress, completion, or failure
    - Sends scraped data to the DataCollector
    - Sends heartbeats to signal it's alive
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        capabilities: AgentCapability,
        message_bus: Optional["A2AMessageBus"] = None,
        registry: Optional["AgentRegistry"] = None,
    ):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.capabilities = capabilities
        self.status = AgentStatus.STARTING
        self.message_bus = message_bus
        self.registry = registry

        # Task management
        self.active_tasks: Dict[str, Task] = {}
        self._pending_messages: asyncio.Queue[A2AMessage] = asyncio.Queue()
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._message_consumer_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0
        self.total_scraped: int = 0
        self.start_time: float = 0.0
        self.metadata: Dict[str, Any] = {}

    @property
    def info(self) -> AgentInfo:
        return AgentInfo(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            status=self.status,
            capabilities=self.capabilities,
            current_load=len(self.active_tasks),
            max_load=self.capabilities.max_concurrent_tasks,
            last_heartbeat=time.time(),
            registered_at=self.start_time,
            metadata=self.metadata,
        )

    async def initialize(self):
        """Initialize the agent: connect to bus, register, start tasks."""
        self._running = True
        self.start_time = time.time()
        self.status = AgentStatus.STARTING

        if self.message_bus:
            # Subscribe to messages addressed to this agent
            await self.message_bus.subscribe(self.agent_id)
            self._message_consumer_task = asyncio.create_task(self._consume_messages())

        if self.registry:
            await self.registry.register(self.info)
            logger.info(f"Agent {self.agent_id} registered with registry")

        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        self.status = AgentStatus.IDLE
        logger.info(f"Agent {self.agent_id} initialized and ready ({self.agent_type})")

    async def shutdown(self):
        """Graceful shutdown: cancel tasks, unregister."""
        self._running = False
        self.status = AgentStatus.SHUTDOWN

        # Cancel heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Cancel message consumer
        if self._message_consumer_task:
            self._message_consumer_task.cancel()
            try:
                await self._message_consumer_task
            except (asyncio.CancelledError, RuntimeError) as e:
                # RuntimeError can occur if task is not a valid future (already cancelled/done)
                if isinstance(e, RuntimeError) and "wasn't used with future" not in str(e):
                    raise
                pass

        # Cancel all active tasks
        for task_id in list(self.active_tasks.keys()):
            task = self.active_tasks[task_id]
            task.status = TaskStatus.CANCELLED

        self.active_tasks.clear()

        # Unregister
        if self.registry:
            await self.registry.unregister(self.agent_id)

        logger.info(f"Agent {self.agent_id} shutdown complete")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to the registry."""
        try:
            while self._running:
                if self.registry:
                    await self.registry.heartbeat(self.agent_id)
                await asyncio.sleep(30)  # every 30 seconds
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Agent {self.agent_id} heartbeat error: {e}")

    async def _consume_messages(self):
        """Listen for incoming A2A messages and process them."""
        try:
            while self._running:
                if not self.message_bus:
                    await asyncio.sleep(1)
                    continue

                try:
                    message = await self.message_bus.consume(self.agent_id, timeout=5.0)
                    if message:
                        await self.handle_message(message)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Agent {self.agent_id} consume error: {e}")
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def handle_message(self, message: A2AMessage) -> None:
        """Process an incoming A2A message based on its type."""
        logger.debug(f"Agent {self.agent_id} received message: {message.msg_type}")

        if message.msg_type == A2AMessageType.TASK_ASSIGN:
            await self._handle_task_assign(message)
        elif message.msg_type == A2AMessageType.ORCHESTRATOR_SHUTDOWN:
            await self.shutdown()
        elif message.msg_type == A2AMessageType.ORCHESTRATOR_STATUS:
            await self._send_status()
        elif message.msg_type == A2AMessageType.ORCHESTRATOR_PAUSE:
            self.status = AgentStatus.IDLE
        elif message.msg_type == A2AMessageType.DATA_ACK:
            logger.debug(f"Agent {self.agent_id}: data acknowledged by '{message.sender_id}'")
        else:
            logger.warning(f"Agent {self.agent_id} unknown message type: {message.msg_type}")

    async def _handle_task_assign(self, message: A2AMessage) -> None:
        """Evaluate and accept/reject a task assignment."""
        payload = message.payload
        task_dict = payload.get("task", {})
        task = Task(
            task_id=task_dict.get("task_id", ""),
            platform=task_dict.get("platform", ""),
            url=task_dict.get("url", ""),
            params=task_dict.get("params", {}),
            priority=task_dict.get("priority", 0),
            max_retries=task_dict.get("max_retries", 3),
        )

        # Can we accept this task?
        if self.can_accept_task(task):
            if len(self.active_tasks) >= self.capabilities.max_concurrent_tasks:
                await self._reject_task(task, "At max concurrent tasks")
                return

            await self._accept_task(task)
            # Start processing in background
            asyncio.create_task(self._execute_task(task))
        else:
            await self._reject_task(task, "Incompatible platform or missing capability")

    def can_accept_task(self, task: Task) -> bool:
        """Check if this agent can handle the given task."""
        # Check platform compatibility
        if task.platform != self.capabilities.platform and self.capabilities.platform != "generic":
            return False
        if not self._running:
            return False
        return True

    async def _accept_task(self, task: Task) -> None:
        """Accept a task and send confirmation."""
        task.status = TaskStatus.ACCEPTED
        task.assigned_to = self.agent_id
        task.started_at = time.time()
        self.active_tasks[task.task_id] = task
        self.status = AgentStatus.BUSY

        if self.message_bus:
            msg = A2AMessage.create(
                msg_type=A2AMessageType.TASK_ACCEPT,
                sender_id=self.agent_id,
                target_id="orchestrator",
                payload={"task_id": task.task_id, "agent_id": self.agent_id},
            )
            await self.message_bus.publish("orchestrator", msg)

    async def _reject_task(self, task: Task, reason: str) -> None:
        """Reject a task with a reason."""
        if self.message_bus:
            msg = A2AMessage.create(
                msg_type=A2AMessageType.TASK_REJECT,
                sender_id=self.agent_id,
                target_id="orchestrator",
                payload={"task_id": task.task_id, "reason": reason},
            )
            await self.message_bus.publish("orchestrator", msg)

    async def _execute_task(self, task: Task) -> None:
        """Execute a scraping task: scrape URL, send progress, complete."""
        task.status = TaskStatus.IN_PROGRESS
        try:
            # Send progress: started
            await self._send_progress(task, 0.1, "Starting scrape")

            # Platform-specific scraping logic
            result = await self.scrape(task)

            # Send progress: data scraped
            await self._send_progress(task, 0.8, "Data scraped, normalizing")

            # Send data to collector
            if self.message_bus:
                data_msg = A2AMessage.create(
                    msg_type=A2AMessageType.DATA_TRANSFER,
                    sender_id=self.agent_id,
                    target_id="data_collector",
                    payload={
                        "task_id": task.task_id,
                        "data": result,
                        "platform": task.platform,
                        "url": task.url,
                    },
                )
                await self.message_bus.publish("data_collector", data_msg)

            # Mark task as complete
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = result
            self.tasks_completed += 1
            self.total_scraped += 1 if isinstance(result, dict) else len(result) if isinstance(result, list) else 0

            # Send completion message
            if self.message_bus:
                complete_msg = A2AMessage.create(
                    msg_type=A2AMessageType.TASK_COMPLETE,
                    sender_id=self.agent_id,
                    target_id="orchestrator",
                    payload={
                        "task_id": task.task_id,
                        "duration": task.duration,
                        "result_summary": {
                            "product_count": self.total_scraped,
                            "has_data": result is not None and bool(result),
                        },
                    },
                )
                await self.message_bus.publish("orchestrator", complete_msg)

            logger.info(f"Agent {self.agent_id} completed task {task.task_id} ({task.url})")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()
            self.tasks_failed += 1

            logger.error(f"Agent {self.agent_id} failed task {task.task_id}: {e}")

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                logger.info(f"Agent {self.agent_id} retrying task {task.task_id} ({task.retry_count}/{task.max_retries})")
                await asyncio.sleep(2 ** task.retry_count)  # exponential backoff
                await self._execute_task(task)
            else:
                # Send failure message
                if self.message_bus:
                    fail_msg = A2AMessage.create(
                        msg_type=A2AMessageType.TASK_FAILED,
                        sender_id=self.agent_id,
                        target_id="orchestrator",
                        payload={
                            "task_id": task.task_id,
                            "error": str(e),
                        },
                    )
                    await self.message_bus.publish("orchestrator", fail_msg)
        finally:
            # Clean up active task
            self.active_tasks.pop(task.task_id, None)
            if not self.active_tasks:
                self.status = AgentStatus.IDLE

    async def _send_progress(self, task: Task, progress: float, message: str = ""):
        """Send progress update to orchestrator."""
        if self.message_bus:
            msg = A2AMessage.create(
                msg_type=A2AMessageType.TASK_PROGRESS,
                sender_id=self.agent_id,
                target_id="orchestrator",
                payload={
                    "task_id": task.task_id,
                    "progress": progress,
                    "message": message,
                },
            )
            await self.message_bus.publish("orchestrator", msg)

    async def _send_status(self):
        """Send current status to orchestrator."""
        if self.message_bus:
            msg = A2AMessage.create(
                msg_type=A2AMessageType.AGENT_HEARTBEAT,
                sender_id=self.agent_id,
                target_id="orchestrator",
                payload={"info": self.info.to_dict()},
            )
            await self.message_bus.publish("orchestrator", msg)

    @abstractmethod
    async def scrape(self, task: Task) -> Any:
        """
        Platform-specific scraping logic.
        Must be implemented by each specialized agent.
        
        Args:
            task: The task containing URL and params to scrape
            
        Returns:
            Dict or List[Dict] of scraped product data
        """
        raise NotImplementedError

    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "uptime": time.time() - self.start_time,
            "active_tasks": len(self.active_tasks),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_scraped": self.total_scraped,
            "load_percentage": (len(self.active_tasks) / self.capabilities.max_concurrent_tasks) * 100,
        }