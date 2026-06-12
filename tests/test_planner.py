import unittest
from unittest.mock import MagicMock, patch

from agent.planner import Planner, _MAX_HISTORY
from agent.state import AgentState


class TestPlannerBuildMessages(unittest.TestCase):
    """Kiểm tra _build_messages tạo đúng danh sách message cho Ollama."""

    def setUp(self):
        self.planner = Planner()

    def test_first_step_no_history(self):
        state = AgentState(goal="Kiểm tra RAM")
        messages = self.planner._build_messages(state, "System Prompt")
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0], {"role": "system", "content": "System Prompt"})
        self.assertEqual(messages[1], {"role": "user", "content": "Kiểm tra RAM"})

    def test_with_history(self):
        state = AgentState(
            goal="Kiểm tra RAM",
            history=[{
                "action": {"type": "tool", "tool": "get_system_info", "args": {}},
                "observation": "RAM: 8GB/16GB",
            }],
            step_count=1,
        )
        messages = self.planner._build_messages(state, "System Prompt")
        
        # 1 system + 1 user + 1 assistant tool call + 1 tool response = 4 messages
        self.assertEqual(len(messages), 4)
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[2]["tool_calls"][0]["function"]["name"], "get_system_info")
        self.assertEqual(messages[3]["role"], "tool")
        self.assertEqual(messages[3]["content"], "RAM: 8GB/16GB")

    def test_history_capped_at_max(self):
        """Chỉ gửi _MAX_HISTORY bước gần nhất trong history."""
        steps = [
            {
                "action": {"type": "tool", "tool": f"tool_{i}", "args": {}},
                "observation": f"obs_{i}",
            }
            for i in range(10)
        ]
        state = AgentState(goal="test", history=steps, step_count=10)
        messages = self.planner._build_messages(state, "System Prompt")
        
        # Capped at _MAX_HISTORY (5)
        # Mỗi bước lịch sử gồm 2 messages (assistant + tool)
        # 1 system + 1 user + 5 * 2 = 12 messages
        self.assertEqual(len(messages), 12)
        
        # Kiểm tra xem bước cũ nhất trong context là bước thứ 5 (index 5)
        self.assertEqual(messages[2]["tool_calls"][0]["function"]["name"], "tool_5")


class TestPlannerPlanStep(unittest.TestCase):
    """Kiểm tra plan_step() xử lý kết quả trả về từ LLM đúng cách."""

    @patch("agent.planner.get_planner_llm")
    def test_plan_step_returns_tool_action(self, mock_get_llm):
        mock_client = MagicMock()
        mock_client.chat_with_tools.return_value = {
            "content": "",
            "tool_calls": [{
                "function": {
                    "name": "get_system_info",
                    "arguments": {}
                }
            }]
        }
        mock_get_llm.return_value = mock_client

        planner = Planner()
        state = AgentState(goal="RAM còn bao nhiêu?")
        result = planner.plan_step(state)

        self.assertEqual(result["type"], "tool")
        self.assertEqual(result["tool"], "get_system_info")
        self.assertEqual(result["args"], {})

    @patch("agent.planner.get_planner_llm")
    def test_plan_step_returns_finish_action(self, mock_get_llm):
        mock_client = MagicMock()
        mock_client.chat_with_tools.return_value = {
            "content": "RAM của bạn còn 7.2 GB trống.",
            "tool_calls": []
        }
        mock_get_llm.return_value = mock_client

        planner = Planner()
        state = AgentState(goal="RAM còn bao nhiêu?")
        result = planner.plan_step(state)

        self.assertEqual(result["type"], "finish")
        self.assertEqual(result["answer"], "RAM của bạn còn 7.2 GB trống.")

    @patch("agent.planner.get_planner_llm")
    def test_stuck_detection(self, mock_get_llm):
        """Nếu phát hiện lặp lại bước cũ, tự động dừng (stuck)."""
        planner = Planner()
        
        # 2 bước gần nhất gọi cùng tool và cùng args
        state = AgentState(
            goal="test",
            history=[
                {
                    "action": {"type": "tool", "tool": "open_app", "args": {"app_name": "chrome"}},
                    "observation": "FAILED: App not found",
                },
                {
                    "action": {"type": "tool", "tool": "open_app", "args": {"app_name": "chrome"}},
                    "observation": "FAILED: App not found",
                }
            ],
            step_count=2
        )
        
        result = planner.plan_step(state)
        self.assertEqual(result["type"], "finish")
        self.assertIn("xu ly yeu cau", result["answer"])
        # Không được gọi LLM khi bị stuck
        mock_get_llm.assert_not_called()


if __name__ == "__main__":
    unittest.main()
