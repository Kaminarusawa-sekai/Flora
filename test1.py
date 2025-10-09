import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from copy import deepcopy

from agent.agent_actor import AgentActor


class TestAgentActor(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Mock dependencies
        self.registry = Mock()
        self.orchestrator = Mock()
        self.data_resolver = Mock()
        self.topo_sorter = Mock()
        self.neo4j_recorder = Mock()

        # Mock strategy functions
        self.fetch_data_fn = Mock(return_value="mock_data")
        self.acquire_resources_fn = Mock(return_value=100)
        self.execute_capability_fn = Mock(return_value="leaf_result")
        self.execute_self_capability_fn = Mock(return_value="intermediate_result")
        self.evaluator = Mock(return_value=0.95)
        self.improver = Mock()
        self.memory_loader = Mock(return_value={"state": "mock_memory"})
        self.optuna_sampler = Mock(return_value=[{"param": 1}, {"param": 2}])

        # Agent info
        self.agent_info = {
            "agent_id": "test_agent",
            "is_leaf": True,
            "capabilities": ["cap1", "cap2"],
            "data_scope": {"region": "US"}
        }
        self.registry.get_agent_by_id.return_value = self.agent_info

    def _create_actor(self, is_leaf=True, capabilities=None, **kwargs):
        agent_info = deepcopy(self.agent_info)
        agent_info["is_leaf"] = is_leaf
        if capabilities is not None:
            agent_info["capabilities"] = capabilities
        self.registry.get_agent_by_id.return_value = agent_info


        # 构建默认参数字典
        defaults = {
            "agent_id": "test_agent",
            "registry": self.registry,
            "orchestrator": self.orchestrator,
            "data_resolver": self.data_resolver,
            "topo_sorter": self.topo_sorter,
            "memory_loader": self.memory_loader,
            "neo4j_recorder": self.neo4j_recorder,
            "fetch_data_fn": self.fetch_data_fn,
            "acquire_resources_fn": self.acquire_resources_fn,
            "execute_capability_fn": self.execute_capability_fn,
            "execute_self_capability_fn": self.execute_self_capability_fn,
            "evaluator": self.evaluator,
            "improver": self.improver,
            "optuna_sampler": self.optuna_sampler,
        }

        # 用 kwargs 覆盖 defaults
        defaults.update(kwargs)

        return AgentActor(**defaults)

    # def test_init_leaf_agent(self):
    #     actor = self._create_actor(is_leaf=True)
    #     self.assertTrue(actor._is_leaf)
    #     self.assertIsNone(actor._optimization_task)

    # @patch("agent.agent_actor.asyncio.create_task")
    # async def test_init_intermediate_agent_starts_optimization_loop(self, mock_create_task):
    #     actor = self._create_actor(is_leaf=False)
    #     await actor.start()  # ← 显式启动
    #     mock_create_task.assert_called_once()

    # async def test_handle_task_capability_not_supported(self):
    #     actor = self._create_actor()
    #     with self.assertRaises(RuntimeError) as cm:
    #         actor.handle_task("frame1", "unsupported_cap", {})
    #     self.assertIn("does not support capability", str(cm.exception))

    # async def test_handle_task_context_not_match_data_scope(self):
    #     actor = self._create_actor()
    #     with self.assertRaises(RuntimeError) as cm:
    #         actor.handle_task("frame1", "cap1", {"region": "EU"})  # mismatch
    #     self.assertIn("does not satisfy data_scope", str(cm.exception))

    # def test_execute_leaf_success(self):
    #     actor = self._create_actor(is_leaf=True)
    #     actor.handle_task("frame1", "cap1", {"region": "US", "extra": "ctx"})

    #     self.execute_capability_fn.assert_called_once()
    #     call_args = self.execute_capability_fn.call_args[0]
    #     self.assertEqual(call_args[0], "cap1")
    #     self.assertEqual(call_args[1], {"region": "US", "extra": "ctx"})
    #     self.assertEqual(call_args[2], {"state": "mock_memory"})  # memory snapshot

    #     self.orchestrator.report_result.assert_called_with("frame1", "leaf_result")
    #     self.neo4j_recorder.record_execution.assert_called_once()

    async def test_execute_intermediate_success(self):
        # Setup intermediate agent
        self.registry.get_agent_by_id.return_value = {
            "agent_id": "test_agent",
            "is_leaf": False,
            "capabilities": ["main_cap"],
            "data_scope": {}
        }
        self.registry.get_capability_dependencies.return_value = [
            {"from": "main_cap", "to": "sub_cap"}
        ]
        self.topo_sorter.sort.return_value = ["sub_cap", "main_cap"]
        child_mock = {"agent_id": "child1"}
        self.registry.find_direct_child_by_capability.return_value = child_mock
        self.data_resolver.resolve.return_value = {"resolved": True}

        actor = self._create_actor(is_leaf=False)
        print("DEBUG: actor._self_info =", actor._self_info)
        await actor.start()  
        actor.handle_task("frame1", "main_cap", {"input": "test"})

        self.registry.find_direct_child_by_capability.assert_called_with(
            parent_agent_id="test_agent",
            capability="sub_cap",
            context={"input": "test"}
        )
        self.orchestrator.submit_subtask.assert_called()
        self.assertIn("frame1", actor._aggregation_state)
        await actor.stop()  # 清理

    # def test_on_subtask_result_aggregates_and_reports(self):
    #     actor = self._create_actor(is_leaf=False)
    #     actor._aggregation_state["frame1"] = {
    #         "pending": {"frame1_sub1"},
    #         "results": {},
    #         "expected_count": 1
    #     }

    #     actor.on_subtask_result("frame1", "frame1_sub1", "sub_result")

    #     self.orchestrator.report_result.assert_called_with("frame1", "sub_result")
    #     self.assertNotIn("frame1", actor._aggregation_state)

    # def test_fetch_data_sync(self):
    #     actor = self._create_actor()
    #     result = asyncio.run(actor.fetch_data("query1"))
    #     self.assertEqual(result, "mock_data")
    #     self.fetch_data_fn.assert_called_with("query1")

    # def test_fetch_data_async(self):
    #     async def async_fetch(query):
    #         return f"async_{query}"

    #     actor = self._create_actor(fetch_data_fn=async_fetch)
    #     result = asyncio.run(actor.fetch_data("q"))
    #     self.assertEqual(result, "async_q")

    # def test_acquire_resources_async(self):
    #     async def async_acquire(purpose):
    #         return 200

    #     actor = self._create_actor(acquire_resources_fn=async_acquire)
    #     result = asyncio.run(actor.acquire_resources("test"))
    #     self.assertEqual(result, 200)

    # def test_swarm_execute_success(self):
    #     actor = self._create_actor(is_leaf=True)
    #     param_sets = [{"a": 1}, {"a": 2}]
    #     base_context = {"region": "US"}

    #     results = asyncio.run(actor.swarm_execute("cap1", param_sets, base_context))

    #     self.assertEqual(len(results), 2)
    #     for r in results:
    #         self.assertIn("params", r)
    #         self.assertEqual(r["result"], "leaf_result")

    #     self.assertEqual(self.neo4j_recorder.record_optimization_trial.call_count, 2)

    # def test_swarm_execute_intermediate(self):
    #     actor = self._create_actor(is_leaf=False)
    #     param_sets = [{"x": 1}]
    #     results = asyncio.run(actor.swarm_execute("cap1", param_sets, {}))
    #     self.assertEqual(results[0]["result"], "intermediate_result")

    # def test_swarm_execute_no_sampler_raises_error(self):
    #     actor = self._create_actor(optuna_sampler=None)
    #     with self.assertRaises(RuntimeError):
    #         asyncio.run(actor.swarm_execute("cap1", [], {}))

    # def test_run_optimization_task_leaf(self):
    #     actor = self._create_actor(is_leaf=True)
    #     task = {
    #         "task_id": "opt1",
    #         "capability": "cap1",
    #         "test_context": {"test": True}
    #     }

    #     asyncio.run(actor._run_optimization_task(task))

    #     self.execute_capability_fn.assert_called_with("cap1", {"test": True}, {"state": "mock_memory"})
    #     self.evaluator.assert_called_with("opt1", "leaf_result")
    #     self.improver.assert_called_with("opt1", 0.95)
    #     self.neo4j_recorder.record_optimization_trial.assert_called_once()

    # def test_run_optimization_task_intermediate(self):
    #     actor = self._create_actor(is_leaf=False)
    #     task = {
    #         "task_id": "opt2",
    #         "capability": "cap2",
    #         "test_context": {"test": True}
    #     }

    #     asyncio.run(actor._run_optimization_task(task))

    #     self.execute_self_capability_fn.assert_called_with("cap2", {"test": True})
    #     # evaluator/improver still called
    #     self.evaluator.assert_called_with("opt2", "intermediate_result")

    # def test_run_optimization_task_missing_self_fn_raises_error(self):
    #     actor = self._create_actor(is_leaf=False, execute_self_capability_fn=None)
    #     task = {"task_id": "t", "capability": "c", "test_context": {}}
    #     with self.assertRaises(NotImplementedError):
    #         asyncio.run(actor._run_optimization_task(task))

    # def tearDown(self):
    #     # Clean up any running tasks if needed (optional)
    #     pass


if __name__ == "__main__":
    unittest.main()