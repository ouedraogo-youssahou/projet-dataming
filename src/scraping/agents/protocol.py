# ============================================
# A2A Protocol - Message types, Task definitions, Agent capabilities
# ============================================

import uuid
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


class A2AMessageType:
    """All message types for A2A communication between agents."""
    # Task lifecycle
    TASK_ASSIGN = "task_assign"          # Orchestrator → Agent : new task
    TASK_ACCEPT = "task_accept"          # Agent → Orchestrator : accept task
    TASK_REJECT = "task_reject"          # Agent → Orchestrator : reject task
    TASK_PROGRESS = "task_progress"      # Agent → Orchestrator : progress update
    TASK_COMPLETE = "task_complete"      # Agent → Orchestrator : task done
    TASK_FAILED = "task_failed"          # Agent → Orchestrator : task failed

    # Agent lifecycle
    AGENT_HEARTBEAT = "agent_heartbeat"  # Agent → Registry : I'm alive
    AGENT_REGISTER = "agent_register"    # Agent → Registry : register me
    AGENT_UNREGISTER = "agent_unregister" # Agent → Registry : unregister me
    AGENT_DISCOVER = "agent_discover"    # Orchestrator → Registry : find agents
    AGENT_LIST = "agent_list"            # Registry → Orchestrator : agent list

    # Data transfer
    DATA_TRANSFER = "data_transfer"      # Agent → DataCollector : scraped data
    DATA_ACK = "data_ack"                # DataCollector → Agent : data received

    # Orchestrator commands
    ORCHESTRATOR_SHUTDOWN = "orchestrator_shutdown"  # Graceful shutdown
    ORCHESTRATOR_STATUS = "orchestrator_status"      # Status request
    ORCHESTRATOR_PAUSE = "orchestrator_pause"        # Pause all agents


class TaskStatus:
    """Possible states of a task in its lifecycle."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class AgentStatus:
    """Possible states of an agent."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"
    STARTING = "starting"
    SHUTDOWN = "shutdown"


@dataclass
class AgentCapability:
    """Describes what an agent can do."""
    platform: str                          # shopify, woocommerce, generic
    max_concurrent_tasks: int = 5
    supports_js: bool = False
    supports_api: bool = False
    rate_limit: float = 2.0               # requests per second
    supported_features: List[str] = field(default_factory=lambda: ["scrape"])

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    agent_id: str
    agent_type: str
    status: str = AgentStatus.STARTING
    capabilities: AgentCapability = field(default_factory=lambda: AgentCapability(platform="generic"))
    current_load: int = 0                  # number of active tasks
    max_load: int = 5
    last_heartbeat: float = 0.0
    registered_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status,
            "capabilities": self.capabilities.to_dict(),
            "current_load": self.current_load,
            "max_load": self.max_load,
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at,
            "metadata": self.metadata,
        }


@dataclass
class Task:
    """A scraping task to be executed by an agent.
    Note: platform and url must come FIRST (no defaults) before any field with a default.
    """
    platform: str                          # shopify, woocommerce, generic
    url: str
    task_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    status: str = TaskStatus.PENDING
    assigned_to: str = ""
    created_at: float = 0.0
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    max_retries: int = 3
    retry_count: int = 0
    error: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.task_id:
            self.task_id = f"task_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


@dataclass
class A2AMessage:
    """A message exchanged between A2A components."""
    msg_id: str
    msg_type: str
    sender_id: str
    target_id: str                       # "" means broadcast
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    ttl: int = 60                        # seconds before message expires

    def __post_init__(self):
        if not self.msg_id:
            self.msg_id = f"msg_{uuid.uuid4().hex[:12]}"
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def create(cls, msg_type: str, sender_id: str, target_id: str = "",
               payload: Optional[Dict[str, Any]] = None, ttl: int = 60) -> "A2AMessage":
        return cls(
            msg_id=f"msg_{uuid.uuid4().hex[:12]}",
            msg_type=msg_type,
            sender_id=sender_id,
            target_id=target_id,
            payload=payload or {},
            timestamp=time.time(),
            ttl=ttl,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        return cls(
            msg_id=data.get("msg_id", ""),
            msg_type=data.get("msg_type", ""),
            sender_id=data.get("sender_id", ""),
            target_id=data.get("target_id", ""),
            payload=data.get("payload", {}),
            timestamp=data.get("timestamp", time.time()),
            ttl=data.get("ttl", 60),
        )