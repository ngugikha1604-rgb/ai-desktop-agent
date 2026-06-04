import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from agent.planner import Planner, ActionSchema
from agent.state import AgentState


class TestActionSchema(unittest.TestCase):
    """Kiểm tra validation schema cho action."""

    def test_tool_action_valid(self):
        data = {"type": "tool", "tool": "get_system_info", "args": {}}
        action = ActionSchema.model_validate(data)
        self.assertEqual(action.type, "tool")
        self.assertEqual(action.tool, "get_system_info")

    def test_finish_action_valid(self):
        data = {"type": "finish", "answer": "RAM còn 7GB."}
        action = ActionSchema.model_validate(data)
        self.assertEqual(action.type, "finish")
        self.assertEqual(action.answer, "RAM còn 7GB.")

    def test_tool_missing_name_raises(self):
        with self.assertRaises(ValidationError):
            ActionSchema.model_validate({"type": "tool", "args": {}})

    def test_finish_missing_answer_raises(self):
        with self.assertRaises(ValidationError):
            ActionSchema.model_validate({"type": "finish"})

    def test_invalid_type_raises(self):
        with self.assertRaises(ValidationError):
            ActionSchema.model_validate({"type": "unknown"})


class TestPlannerParse(unittest.TestCase):
    """Kiểm tra _parse() với nhiều dạng LLM output."""

    def setUp(self):
        self.planner = Planner()

    def test_parse_tool_action(self):
        raw = '{"type": "tool", "tool": "get_system_info", "args": {}}'
        result = self.planner._parse(raw)
        self.assertEqual(result["type"], "tool")
        self.assertEqual(result["tool"], "get_system_info")

    def test_parse_finish_action(self):
        raw = '{"type": "finish", "answer": "Xong rồi!"}'
        result = self.planner._parse(raw)
        self.assertEqual(result["type"], "finish")
        self.assertEqual(result["answer"], "Xong rồi!")

    def test_parse_strips_markdown_fence(self):
        raw = '```json\n{"type": "finish", "answer": "OK"}\n```'
        result = self.planner._parse(raw)
        self.assertEqual(result["type"], "finish")

    def test_parse_invalid_raises(self):
        with self.assertRaises(ValidationError):
            self.planner._parse('{"type": "tool"}')  # thiếu "tool" field


class TestPlannerBuildMessage(unittest.TestCase):
    """Kiểm tra _build_message tạo context đúng."""

    def setUp(self):
        self.planner = Planner()

    def test_first_step_no_history(self):
        state = AgentState(goal="Kiểm tra RAM")
        msg = self.planner._build_message(state)
        self.assertIn("Goal: Kiểm tra RAM", msg)
        self.assertNotIn("History:", msg)
        self.assertNotIn("Observation:", msg)

    def test_with_history_and_observation(self):
        state = AgentState(
            goal="Kiểm tra RAM",
            history=[{
                "action": {"type": "tool", "tool": "get_system_info", "args": {}},
                "observation": "RAM: 8GB/16GB",
            }],
            observation="RAM: 8GB/16GB",
            step_count=1,
        )
        msg = self.planner._build_message(state)
        self.assertIn("History:", msg)
        self.assertIn("Observation:", msg)
        self.assertIn("get_system_info", msg)

    def test_history_capped_at_max(self):
        """Chỉ gửi _MAX_HISTORY bước gần nhất."""
        steps = [
            {
                "action": {"type": "tool", "tool": f"tool_{i}", "args": {}},
                "observation": f"obs_{i}",
            }
            for i in range(10)
        ]
        state = AgentState(goal="test", history=steps, step_count=10)
        msg = self.planner._build_message(state)
        # Chỉ 3 bước cuối xuất hiện
        self.assertIn("tool_9", msg)
        self.assertIn("tool_8", msg)
        self.assertIn("tool_7", msg)
        self.assertNotIn("tool_6", msg)


class TestPlannerPlanStep(unittest.TestCase):
    """Kiểm tra plan_step() gọi LLM đúng cách."""

    @patch("agent.planner.get_planner_llm")
    def test_plan_step_returns_tool_action(self, mock_get_llm):
        mock_client = MagicMock()
        mock_client.generate.return_value = (
            '{"type": "tool", "tool": "get_system_info", "args": {}}'
        )
        mock_get_llm.return_value = mock_client

        planner = Planner()
        state = AgentState(goal="RAM còn bao nhiêu?")
        result = planner.plan_step(state)

        self.assertEqual(result["type"], "tool")
        self.assertEqual(result["tool"], "get_system_info")
        mock_client.generate.assert_called_once()
        kwargs = mock_client.generate.call_args.kwargs
        self.assertTrue(kwargs.get("json_mode"))

    @patch("agent.planner.get_planner_llm")
    def test_plan_step_returns_finish_on_parse_error(self, mock_get_llm):
        """Nếu LLM trả JSON sai, plan_step() trả finish fallback."""
        mock_client = MagicMock()
        mock_client.generate.return_value = "this is not json"
        mock_get_llm.return_value = mock_client

        planner = Planner()
        state = AgentState(goal="test")
        result = planner.plan_step(state)

        self.assertEqual(result["type"], "finish")

    @patch("agent.planner.get_planner_llm")
    def test_plan_step_uses_json_mode(self, mock_get_llm):
        mock_client = MagicMock()
        mock_client.generate.return_value = (
            '{"type": "finish", "answer": "Xin chào!"}'
        )
        mock_get_llm.return_value = mock_client

        planner = Planner()
        state = AgentState(goal="Xin chào")
        planner.plan_step(state)

        kwargs = mock_client.generate.call_args.kwargs
        self.assertTrue(kwargs.get("json_mode"))


if __name__ == "__main__":
    unittest.main()
