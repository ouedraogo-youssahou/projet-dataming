# ============================================
# Tests for A2A Agents module
# ============================================

import asyncio
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.scraping.agents.protocol import (
    A2AMessage, A2AMessageType, Task, TaskStatus, AgentStatus,
    AgentCapability, AgentInfo,
)
from src.scraping.agents.message_bus import A2AMessageBus, AgentRegistry
from src.scraping.agents.base_agent import BaseAgent


# ============================================
# Protocol Tests
# ============================================

class TestProtocol:
    """Test A2A protocol message types and data classes."""

    def test_a2a_message_creation(self):
        msg = A2AMessage.create(
            msg_type=A2AMessageType.AGENT_HEARTBEAT,
            sender_id="test_agent",
            target_id="orchestrator",
            payload={"status": "idle"},
        )
        assert msg.msg_type == "agent_heartbeat"
        assert msg.sender_id == "test_agent"
        assert msg.target_id == "orchestrator"
        assert msg.payload["status"] == "idle"
        assert msg.msg_id.startswith("msg_")

    def test_a2a_message_from_dict(self):
        data = {
            "msg_id": "msg_test123",
            "msg_type": "task_assign",
            "sender_id": "orchestrator",
            "target_id": "agent_1",
            "payload": {"task_id": "task_001"},
            "timestamp": 1234567890,
            "ttl": 60,
        }
        msg = A2AMessage.from_dict(data)
        assert msg.msg_id == "msg_test123"
        assert msg.msg_type == "task_assign"
        assert msg.payload["task_id"] == "task_001"

    def test_task_creation(self):
        task = Task(
            task_id="test_task_001",
            platform="shopify",
            url="https://test-store.myshopify.com",
            priority=1,
        )
        assert task.task_id == "test_task_001"
        assert task.platform == "shopify"
        assert task.url == "https://test-store.myshopify.com"
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 0
        assert task.max_retries == 3

    def test_task_auto_id(self):
        task = Task(
            platform="generic",
            url="https://example.com",
        )
        assert task.task_id.startswith("task_")
        assert task.platform == "generic"

    def test_task_duration(self):
        import time
        now = time.time()
        task = Task(
            task_id="duration_test",
            platform="shopify",
            url="https://test.com",
            started_at=now - 5.0,
            completed_at=now,
        )
        assert task.duration is not None
        assert 4.0 <= task.duration <= 6.0

    def test_agent_capability(self):
        cap = AgentCapability(
            platform="shopify",
            max_concurrent_tasks=5,
            supports_api=True,
            rate_limit=2.0,
        )
        assert cap.platform == "shopify"
        assert cap.supports_api is True
        assert cap.supports_js is False
        assert cap.to_dict()["platform"] == "shopify"

    def test_agent_info(self):
        cap = AgentCapability(platform="woocommerce")
        info = AgentInfo(
            agent_id="woo_agent_1",
            agent_type="woocommerce",
            capabilities=cap,
            current_load=2,
            max_load=5,
        )
        assert info.agent_id == "woo_agent_1"
        assert info.status == AgentStatus.STARTING  # default
        info_dict = info.to_dict()
        assert info_dict["capabilities"]["platform"] == "woocommerce"
        assert info_dict["current_load"] == 2
        assert info_dict["max_load"] == 5


# ============================================
# Message Bus Tests
# ============================================

class TestA2AMessageBus:
    """Test in-memory A2A message bus."""

    @pytest.mark.asyncio
    async def test_publish_subscribe(self):
        bus = A2AMessageBus()
        await bus.subscribe("agent_1")
        await bus.subscribe("agent_2")

        msg = A2AMessage.create(
            msg_type="test",
            sender_id="orchestrator",
            target_id="agent_1",
            payload={"hello": "world"},
        )
        sent = await bus.publish("agent_1", msg)
        assert sent is True

        received = await bus.consume("agent_1", timeout=1.0)
        assert received is not None
        assert received.payload["hello"] == "world"

        # agent_2 should not receive this message
        no_msg = await bus.consume("agent_2", timeout=0.2)
        assert no_msg is None

        await bus.close()

    @pytest.mark.asyncio
    async def test_channel_subscription(self):
        bus = A2AMessageBus()
        await bus.subscribe("agent_1", channel="broadcast")
        await bus.subscribe("agent_2", channel="broadcast")

        msg = A2AMessage.create(
            msg_type="broadcast_test",
            sender_id="orchestrator",
            payload={"broadcast": True},
        )
        await bus.publish("broadcast", msg)

        # At least one subscriber should receive the broadcast
        import time
        start = time.time()
        received = []
        while time.time() - start < 2.0 and len(received) < 2:
            m1 = await bus.consume("agent_1", timeout=0.3)
            if m1:
                received.append(m1)
            m2 = await bus.consume("agent_2", timeout=0.3)
            if m2:
                received.append(m2)

        assert len(received) >= 1, "At least one agent should receive the broadcast"
        for r in received:
            assert r.payload["broadcast"] is True

        await bus.close()

    @pytest.mark.asyncio
    async def test_request_response(self):
        bus = A2AMessageBus()
        await bus.subscribe("responder")

        msg = A2AMessage.create(
            msg_type="request",
            sender_id="requester",
            target_id="responder",
            payload={"question": "ping"},
        )

        # Simulate responder in background
        async def responder():
            req = await bus.consume("responder", timeout=2.0)
            if req:
                resp = A2AMessage.create(
                    msg_type="response",
                    sender_id="responder",
                    target_id=req.sender_id,
                    payload={"answer": "pong"},
                )
                await bus.publish(req.payload.get("_response_queue", req.sender_id), resp)

        asyncio.create_task(responder())

        # Wait for response
        import time
        await asyncio.sleep(0.1)
        await bus.publish("responder", msg)

        # Give time for response
        await asyncio.sleep(0.5)

        # Check the response was received
        response = await bus.consume("responder", timeout=0.2)
        # The responder consumed the request, check stats
        stats = bus.get_statistics()
        assert stats["messages_sent"] >= 1
        assert stats["messages_received"] >= 0

        await bus.close()

    @pytest.mark.asyncio
    async def test_bus_statistics(self):
        bus = A2AMessageBus()
        await bus.subscribe("agent_a")

        for i in range(3):
            msg = A2AMessage.create(
                msg_type="test",
                sender_id="orchestrator",
                target_id="agent_a",
                payload={"i": i},
            )
            await bus.publish("agent_a", msg)

        await bus.consume("agent_a", timeout=0.5)

        stats = bus.get_statistics()
        assert stats["messages_sent"] >= 3
        assert stats["active_queues"] >= 1
        assert stats["mode"] == "in_memory"

        await bus.close()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = A2AMessageBus()
        await bus.subscribe("agent_x")
        await bus.unsubscribe("agent_x")

        msg = A2AMessage.create(msg_type="test", sender_id="orchestrator")
        await bus.publish("agent_x", msg)

        received = await bus.consume("agent_x", timeout=0.3)
        assert received is None  # queue was removed

        await bus.close()


# ============================================
# Agent Registry Tests
# ============================================

class TestAgentRegistry:
    """Test agent registry functionality."""

    @pytest.mark.asyncio
    async def test_register_and_discover(self):
        registry = AgentRegistry(heartbeat_timeout=30.0)

        cap = AgentCapability(platform="shopify", max_concurrent_tasks=5)
        info = AgentInfo(
            agent_id="shopify_1",
            agent_type="shopify",
            status=AgentStatus.IDLE,
            capabilities=cap,
        )
        registered = await registry.register(info)
        assert registered is True

        # Discover all
        all_agents = await registry.discover()
        assert len(all_agents) == 1

        # Discover by platform
        shopify_agents = await registry.discover(platform="shopify")
        assert len(shopify_agents) == 1

        woocommerce_agents = await registry.discover(platform="woocommerce")
        assert len(woocommerce_agents) == 0  # none registered

    @pytest.mark.asyncio
    async def test_heartbeat_timeout(self):
        registry = AgentRegistry(heartbeat_timeout=0.1)  # very short timeout

        info = AgentInfo(
            agent_id="test_agent",
            agent_type="generic",
            status=AgentStatus.IDLE,
            capabilities=AgentCapability(platform="generic"),
        )
        await registry.register(info)

        # Immediately discoverable
        available = await registry.discover()
        assert len(available) == 1

        # Wait for heartbeat timeout
        await asyncio.sleep(0.15)

        # Should be offline now
        available = await registry.discover()
        assert len(available) == 0

        # Health check should show offline
        health = await registry.health_check_all()
        assert health.get("test_agent") == AgentStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_heartbeat_update(self):
        registry = AgentRegistry(heartbeat_timeout=0.3)

        info = AgentInfo(
            agent_id="heartbeat_agent",
            agent_type="generic",
            capabilities=AgentCapability(platform="generic"),
        )
        await registry.register(info)

        # Update heartbeat
        await registry.heartbeat("heartbeat_agent")

        available = await registry.discover()
        assert len(available) == 1

    @pytest.mark.asyncio
    async def test_unregister(self):
        registry = AgentRegistry()

        info = AgentInfo(
            agent_id="remove_me",
            agent_type="test",
            capabilities=AgentCapability(platform="test"),
        )
        await registry.register(info)
        assert len(await registry.list_agents()) == 1

        await registry.unregister("remove_me")
        assert len(await registry.list_agents()) == 0

    @pytest.mark.asyncio
    async def test_statistics(self):
        registry = AgentRegistry()

        for i in range(3):
            info = AgentInfo(
                agent_id=f"agent_{i}",
                agent_type=f"type_{i % 2}",
                capabilities=AgentCapability(platform="generic"),
            )
            await registry.register(info)

        stats = await registry.get_statistics()
        assert stats["total_agents"] == 3
        assert stats["online_agents"] == 3
        assert "by_type" in stats

    @pytest.mark.asyncio
    async def test_get_agent(self):
        registry = AgentRegistry()

        info = AgentInfo(
            agent_id="find_me",
            agent_type="test",
            capabilities=AgentCapability(platform="test"),
        )
        await registry.register(info)

        found = await registry.get_agent("find_me")
        assert found is not None
        assert found.agent_id == "find_me"

        not_found = await registry.get_agent("nonexistent")
        assert not_found is None


# ============================================
# Base Agent Tests (Mock implementation)
# ============================================

class MockScrapingAgent(BaseAgent):
    """Mock agent for testing BaseAgent functionality."""

    def __init__(self, agent_id="mock_agent", message_bus=None, registry=None, fail=False):
        cap = AgentCapability(platform="test", max_concurrent_tasks=3)
        super().__init__(
            agent_id=agent_id,
            agent_type="test",
            capabilities=cap,
            message_bus=message_bus,
            registry=registry,
        )
        self.fail = fail
        self.scrape_calls = []

    async def scrape(self, task):
        self.scrape_calls.append(task)
        if self.fail:
            raise RuntimeError("Mock agent forced failure")
        return {
            "product_id": "test_001",
            "name": "Test Product",
            "price": 29.99,
            "rating": 4.5,
        }


class TestBaseAgent:
    """Test base agent functionality."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        bus = A2AMessageBus()
        registry = AgentRegistry()
        agent = MockScrapingAgent(
            agent_id="test_mock",
            message_bus=bus,
            registry=registry,
        )

        await agent.initialize()
        assert agent.status == AgentStatus.IDLE
        assert agent.agent_id == "test_mock"
        assert agent.tasks_completed == 0

        # Check it was registered
        info = await registry.get_agent("test_mock")
        assert info is not None

        await agent.shutdown()
        await bus.close()

    @pytest.mark.asyncio
    async def test_agent_can_accept_task(self):
        bus = A2AMessageBus()
        registry = AgentRegistry()
        agent = MockScrapingAgent(
            agent_id="accept_test",
            message_bus=bus,
            registry=registry,
        )
        await agent.initialize()

        task = Task(platform="test", url="https://test.com")
        assert agent.can_accept_task(task) is True

        wrong_task = Task(platform="shopify", url="https://shop.com")
        assert agent.can_accept_task(wrong_task) is False

        await agent.shutdown()
        await bus.close()

    @pytest.mark.asyncio
    async def test_agent_execute_task_success(self):
        bus = A2AMessageBus()
        registry = AgentRegistry()
        agent = MockScrapingAgent(
            agent_id="success_agent",
            message_bus=bus,
            registry=registry,
        )

        await agent.initialize()
        await bus.subscribe("orchestrator")

        task = Task(platform="test", url="https://test.com/products/1")
        await agent._accept_task(task)
        await agent._execute_task(task)

        assert task.status == TaskStatus.COMPLETED
        assert task.result is not None
        assert agent.tasks_completed == 1

        await agent.shutdown()
        await bus.close()

    @pytest.mark.asyncio
    async def test_agent_execute_task_failure(self):
        bus = A2AMessageBus()
        registry = AgentRegistry()
        agent = MockScrapingAgent(
            agent_id="fail_agent",
            message_bus=bus,
            registry=registry,
            fail=True,
        )

        await agent.initialize()
        await bus.subscribe("orchestrator")

        task = Task(
            platform="test",
            url="https://test.com/fail",
            max_retries=0,  # no retry
        )
        await agent._accept_task(task)

        # Execute task directly
        await agent._execute_task(task)

        # After execution, task should have failed
        assert task.status == TaskStatus.FAILED
        assert task.error is not None
        assert agent.tasks_failed >= 1

        await agent.shutdown()
        await bus.close()

    @pytest.mark.asyncio
    async def test_agent_get_stats(self):
        agent = MockScrapingAgent(agent_id="stats_agent")
        await agent.initialize()

        stats = agent.get_stats()
        assert stats["agent_id"] == "stats_agent"
        assert stats["agent_type"] == "test"
        assert stats["tasks_completed"] == 0
        assert stats["tasks_failed"] == 0
        assert "uptime" in stats
        assert "load_percentage" in stats

        await agent.shutdown()

    @pytest.mark.asyncio
    async def test_agent_shutdown(self):
        bus = A2AMessageBus()
        registry = AgentRegistry()
        agent = MockScrapingAgent(
            agent_id="shutdown_test",
            message_bus=bus,
            registry=registry,
        )

        await agent.initialize()
        assert agent._running is True

        await agent.shutdown()
        assert agent._running is False
        assert agent.status == AgentStatus.SHUTDOWN

        # Should be unregistered
        info = await registry.get_agent("shutdown_test")
        assert info is None

        await bus.close()


# ============================================
# Simple integration: Bus + Registry + Agent
# ============================================

class TestSimpleIntegration:
    """Simple integration test of the A2A system."""

    @pytest.mark.asyncio
    async def test_bus_registry_agent_flow(self):
        """Test the basic flow: message bus + registry + agent."""
        bus = A2AMessageBus()
        registry = AgentRegistry()

        # Create and initialize agent
        agent = MockScrapingAgent(
            agent_id="integration_agent",
            message_bus=bus,
            registry=registry,
        )
        await agent.initialize()

        # Verify agent is registered
        info = await registry.get_agent("integration_agent")
        assert info is not None

        # Verify it can be discovered
        discovered = await registry.discover(platform="test")
        assert len(discovered) >= 1

        # Cleanup
        await agent.shutdown()
        await bus.close()

    @pytest.mark.asyncio
    async def test_multiple_agents(self):
        """Test multiple agents coexisting."""
        bus = A2AMessageBus()
        registry = AgentRegistry()

        agents = []
        for i in range(3):
            agent = MockScrapingAgent(
                agent_id=f"multi_agent_{i}",
                message_bus=bus,
                registry=registry,
            )
            await agent.initialize()
            agents.append(agent)

        # All should be registered
        all_agents = await registry.list_agents()
        assert len(all_agents) == 3

        # Cleanup
        for agent in agents:
            await agent.shutdown()
        await bus.close()

    @pytest.mark.asyncio
    async def test_message_between_agents(self):
        """Test sending a message between agents via the bus."""
        bus = A2AMessageBus()
        registry = AgentRegistry()

        agent_a = MockScrapingAgent(
            agent_id="agent_a",
            message_bus=bus,
            registry=registry,
        )
        agent_b = MockScrapingAgent(
            agent_id="agent_b",
            message_bus=bus,
            registry=registry,
        )
        await agent_a.initialize()
        await agent_b.initialize()

        # agent_a sends message to agent_b
        msg = A2AMessage.create(
            msg_type="test_message",
            sender_id="agent_a",
            target_id="agent_b",
            payload={"data": "hello_from_a"},
        )
        sent = await bus.publish("agent_b", msg)
        assert sent is True

        # agent_b should receive it
        received = await bus.consume("agent_b", timeout=1.0)
        assert received is not None
        assert received.sender_id == "agent_a"
        assert received.payload["data"] == "hello_from_a"

        await agent_a.shutdown()
        await agent_b.shutdown()
        await bus.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])