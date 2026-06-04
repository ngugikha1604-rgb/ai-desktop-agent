import unittest


class TestImports(unittest.TestCase):
    def test_agent_import(self):
        from agent import Agent
        self.assertIsNotNone(Agent)

    def test_tool_registry(self):
        from tools import TOOL_REGISTRY
        self.assertIn("open_app", TOOL_REGISTRY)
        self.assertEqual(len(TOOL_REGISTRY), 16)

