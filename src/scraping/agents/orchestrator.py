# ============================================
# Agent Orchestrator - Distributes tasks, manages agents, collects results
# ============================================

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from .protocol import (
    A2AMessage, A2AMessageType,
    Task, TaskStatus, AgentStatus, AgentCapability, AgentInfo,
)
from .message_bus import A2AMessageBus, AgentRegistry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Central orchestrator for A2A agents.
    
    Responsibilities:
    - Register and manage agents
    - Distribute scraping tasks to the most suitable agents
    - Handle failures with retry and failover
    - Collect and aggregate results
    - Provide real-time status of all agents and tasks
    """

    def __init__(
        self,
        message_bus: A2AMessageBus,
        registry: AgentRegistry,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.message_bus = message_bus
        self.registry = registry
        self.config = config or {}

        # Task management
        self.task_queue: asyncio.Queue[Task] = asyncio.Queue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.failed_tasks: Dict[str, Task] = {}

        # Agent management
        self._registered_agents: Dict[str, Any] = {}  # agent_id → agent instance
        self._running = False
        self._orchestrator_task: Optional[asyncio.Task] = None

        # Statistics
        self.tasks_dispatched: int = 0
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0
        self.tasks_retried: int = 0
        self.start_time: float = 0.0

    async def register_agent(self, agent: Any) -> bool:
        """
        Register an agent with the orchestrator.
        Also registers with the agent registry for discovery.
        """
        agent_id = agent.agent_id
        self._registered_agents[agent_id] = agent

        # Register with message bus
        await self.message_bus.subscribe(agent_id)

        # Initialize agent if not already
        if hasattr(agent, 'initialize') and agent._running is False:
            await agent.initialize()

        logger.info(f"Orchestrator: Agent '{agent_id}' registered and ready")
        return True

    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent."""
        if agent_id in self._registered_agents:
            agent = self._registered_agents[agent_id]
            if hasattr(agent, 'shutdown'):
                await agent.shutdown()
            del self._registered_agents[agent_id]
            await self.message_bus.unsubscribe(agent_id)
            logger.info(f"Orchestrator: Agent '{agent_id}' unregistered")
            return True
        return False

    async def start(self):
        """Start the orchestrator: begin processing task queue."""
        self._running = True
        self.start_time = time.time()
        self._orchestrator_task = asyncio.create_task(self._process_task_queue())
        logger.info("Orchestrator started")

    async def stop(self):
        """Stop the orchestrator gracefully."""
        self._running = False

        # Send shutdown signal to all agents
        for agent_id in self._registered_agents:
            msg = A2AMessage.create(
                msg_type=A2AMessageType.ORCHESTRATOR_SHUTDOWN,
                sender_id="orchestrator",
                target_id=agent_id,
            )
            await self.message_bus.publish(agent_id, msg)

        # Cancel orchestrator task
        if self._orchestrator_task:
            self._orchestrator_task.cancel()
            try:
                await self._orchestrator_task
            except asyncio.CancelledError:
                pass

        logger.info("Orchestrator stopped")

    async def run_all(self, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run the complete A2A scraping pipeline.
        
        Args:
            targets: List of dicts with keys:
                - url (str): URL to scrape
                - platform (str): shopify, woocommerce, or generic
                - params (dict, optional): additional parameters
                
        Returns:
            Dict with keys:
                - tasks (List[Dict]): all task results
                - summary (Dict): execution summary
                - agent_stats (Dict): per-agent statistics
        """
        logger.info(f"Orchestrator: Starting pipeline with {len(targets)} targets")

        # Create tasks from targets
        tasks = []
        for target in targets:
            task = Task(
                task_id=f"task_{uuid.uuid4().hex[:12]}",
                platform=target.get("platform", "generic"),
                url=target.get("url", ""),
                params=target.get("params", {}),
                priority=target.get("priority", 0),
                max_retries=target.get("max_retries", 3),
            )
            tasks.append(task)
            await self.task_queue.put(task)

        # Start processing if not already
        if not self._running:
            await self.start()

        # Wait for all tasks to complete
        await self._wait_for_completion(tasks)

        # Collect results
        results = []
        for task in tasks:
            if task.task_id in self.completed_tasks:
                completed = self.completed_tasks[task.task_id]
                results.append({
                    "task_id": completed.task_id,
                    "url": completed.url,
                    "platform": completed.platform,
                    "status": "completed",
                    "duration": completed.duration,
                    "data": completed.result,
                    "agent": completed.assigned_to,
                })
            elif task.task_id in self.failed_tasks:
                failed = self.failed_tasks[task.task_id]
                results.append({
                    "task_id": failed.task_id,
                    "url": failed.url,
                    "platform": failed.platform,
                    "status": "failed",
                    "error": failed.error,
                    "agent": failed.assigned_to,
                })
            else:
                results.append({
                    "task_id": task.task_id,
                    "url": task.url,
                    "platform": task.platform,
                    "status": task.status,
                })

        return {
            "tasks": results,
            "summary": self.get_summary(),
            "agent_stats": await self.get_agent_stats(),
        }

    async def _process_task_queue(self):
        """Main loop: pick tasks from queue and assign to agents."""
        try:
            while self._running:
                try:
                    # Get next task from queue (wait up to 5 seconds)
                    task = await asyncio.wait_for(self.task_queue.get(), timeout=5.0)
                    await self._dispatch_task(task)
                except asyncio.TimeoutError:
                    # No tasks in queue, check if we should stop
                    continue
                except Exception as e:
                    logger.error(f"Orchestrator queue processing error: {e}")
        except asyncio.CancelledError:
            pass

    async def _dispatch_task(self, task: Task) -> bool:
        """Assign a task to the best available agent."""
        # Find the best agent for this task
        agent_info = await self._select_best_agent(task)

        if agent_info is None:
            logger.warning(f"No available agent for task {task.task_id} ({task.platform}: {task.url})")
            task.status = TaskStatus.FAILED
            task.error = "No suitable agent available"
            self.failed_tasks[task.task_id] = task
            self.tasks_failed += 1
            return False

        # Update task status
        task.status = TaskStatus.ASSIGNED
        task.assigned_to = agent_info.agent_id
        self.active_tasks[task.task_id] = task
        self.tasks_dispatched += 1

        logger.info(f"Dispatching task {task.task_id} ({task.platform}) → agent '{agent_info.agent_id}'")

        # Send task assignment message
        msg = A2AMessage.create(
            msg_type=A2AMessageType.TASK_ASSIGN,
            sender_id="orchestrator",
            target_id=agent_info.agent_id,
            payload={"task": task.to_dict()},
        )
        await self.message_bus.publish(agent_info.agent_id, msg)
        return True

    async def _select_best_agent(self, task: Task) -> Optional[AgentInfo]:
        """
        Select the best agent for a given task.
        
        Strategy:
        1. Filter by platform (shopify → ShopifyAgent, etc.)
        2. Prefer agents with low load
        3. Fallback to generic agents if no platform-specific agent available
        """
        # First try: platform-specific agents
        available = await self.registry.discover(platform=task.platform)

        if not available:
            # Second try: generic agents (fallback)
            available = await self.registry.discover(platform="generic")

        if not available:
            return None

        # Sort by load (prefer least loaded)
        available.sort(key=lambda a: (a.current_load / max(a.max_load, 1)))

        return available[0] if available else None

    async def handle_task_complete(self, message: A2AMessage):
        """Handle task completion message from an agent."""
        payload = message.payload
        task_id = payload.get("task_id", "")

        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.result = payload.get("result_summary", {})
            self.completed_tasks[task_id] = task
            self.tasks_completed += 1
            logger.info(f"Task {task_id} completed by '{message.sender_id}' in {task.duration:.2f}s")

    async def handle_task_failed(self, message: A2AMessage):
        """Handle task failure message from an agent."""
        payload = message.payload
        task_id = payload.get("task_id", "")
        error = payload.get("error", "Unknown error")

        if task_id in self.active_tasks:
            task = self.active_tasks.pop(task_id)
            task.status = TaskStatus.FAILED
            task.error = error
            task.completed_at = time.time()

            # Retry logic
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                self.tasks_retried += 1
                logger.info(f"Retrying task {task_id} (attempt {task.retry_count}/{task.max_retries})")
                # Re-queue with backoff
                await asyncio.sleep(2 ** task.retry_count)
                await self._dispatch_task(task)
            else:
                self.failed_tasks[task_id] = task
                self.tasks_failed += 1
                logger.error(f"Task {task_id} failed after {task.max_retries} retries: {error}")

    async def handle_task_progress(self, message: A2AMessage):
        """Handle progress update from an agent."""
        payload = message.payload
        task_id = payload.get("task_id", "")
        progress = payload.get("progress", 0)
        msg = payload.get("message", "")

        if task_id in self.active_tasks:
            logger.debug(f"Task {task_id}: {progress:.0%} - {msg}")

    async def handle_data_transfer(self, message: A2AMessage):
        """Handle data transfer from an agent (forward to DataCollector)."""
        # This is handled by the DataCollector agent directly
        # Just log receipt
        payload = message.payload
        task_id = payload.get("task_id", "")
        logger.info(f"Data received for task {task_id} from '{message.sender_id}'")

    async def _wait_for_completion(self, tasks: List[Task], timeout: float = 300.0):
        """Wait for all tasks to complete or fail."""
        start = time.time()
        remaining = set(t.task_id for t in tasks)

        while remaining and (time.time() - start) < timeout:
            await asyncio.sleep(1.0)
            for task_id in list(remaining):
                if task_id in self.completed_tasks or task_id in self.failed_tasks:
                    remaining.remove(task_id)

        # Check for timeout
        if remaining:
            logger.warning(f"Timeout: {len(remaining)} tasks did not complete")
            for task_id in remaining:
                if task_id in self.active_tasks:
                    task = self.active_tasks.pop(task_id)
                    task.status = TaskStatus.TIMEOUT
                    self.failed_tasks[task_id] = task

    def get_summary(self) -> Dict[str, Any]:
        """Get execution summary."""
        return {
            "total_tasks": self.tasks_dispatched,
            "completed": self.tasks_completed,
            "failed": self.tasks_failed,
            "retried": self.tasks_retried,
            "active": len(self.active_tasks),
            "active_agents": len(self._registered_agents),
            "uptime": time.time() - self.start_time if self.start_time else 0,
            "status": "running" if self._running else "stopped",
        }

    async def get_agent_stats(self) -> Dict[str, Any]:
        """Get per-agent statistics."""
        agent_stats = {}
        for agent_id, agent in self._registered_agents.items():
            if hasattr(agent, 'get_stats'):
                agent_stats[agent_id] = agent.get_stats()
        return agent_stats

    async def get_status(self) -> Dict[str, Any]:
        """Get full orchestrator status."""
        return {
            "orchestrator": self.get_summary(),
            "agents": await self.registry.get_statistics(),
            "bus": self.message_bus.get_statistics(),
        }