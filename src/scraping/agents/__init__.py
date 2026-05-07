# ============================================
# Smart eCommerce Intelligence - A2A Agents Module
# ============================================

from .protocol import A2AMessage, A2AMessageType, Task, TaskStatus, AgentCapability, AgentInfo
from .base_agent import BaseAgent
from .message_bus import A2AMessageBus, AgentRegistry
from .orchestrator import AgentOrchestrator
from .specialized_agents import ShopifyAgent, WooCommerceAgent, GenericScraperAgent
from .data_collector import DataCollectorAgent

__all__ = [
    "A2AMessage",
    "A2AMessageType",
    "Task",
    "TaskStatus",
    "AgentCapability",
    "AgentInfo",
    "BaseAgent",
    "A2AMessageBus",
    "AgentRegistry",
    "AgentOrchestrator",
    "ShopifyAgent",
    "WooCommerceAgent",
    "GenericScraperAgent",
    "DataCollectorAgent",
]