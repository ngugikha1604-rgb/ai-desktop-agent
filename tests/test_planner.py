import unittest
from unittest.mock import MagicMock, patch
from pydantic import ValidationError

from agent.planner import Planner, PlanSchema, StepSchema


class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.planner = Planner()

    def test_parse_plan_valid_object(self):
        # JSON object containing "steps"
        raw_json = """
        {
            "steps": [
                {"task": "search_google", "tool": "search_web", "args": {"query": "github"}},
                {"task": "open_chrome", "tool": "open_app", "args": {"app_name": "chrome"}}
            ]
        }
        """
        parsed = self.planner._parse_plan(raw_json)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["task"], "search_google")
        self.assertEqual(parsed[0]["tool"], "search_web")
        self.assertEqual(parsed[0]["args"], {"query": "github"})

    def test_parse_plan_valid_object_with_markdown_fences(self):
        # JSON object in markdown code block
        raw_json = """
        ```json
        {
            "steps": [
                {"task": "search_google", "tool": "search_web", "args": {"query": "github"}}
            ]
        }
        ```
        """
        parsed = self.planner._parse_plan(raw_json)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["args"]["query"], "github")

    def test_parse_plan_fallback_raw_list(self):
        # Legacy list-based fallback support
        raw_json = """
        [
            {"task": "search_google", "tool": "search_web", "args": {"query": "github"}}
        ]
        """
        parsed = self.planner._parse_plan(raw_json)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["args"]["query"], "github")

    def test_parse_plan_invalid_structure_raises(self):
        # Incomplete structure missing required fields (like "tool") should raise ValidationError
        raw_json_invalid = """
        {
            "steps": [
                {"task": "search_google"}
            ]
        }
        """
        with self.assertRaises(ValidationError):
            self.planner._parse_plan(raw_json_invalid)

    @patch("agent.planner.get_planner_llm")
    def test_plan_calls_llm_with_json_mode(self, mock_get_llm):
        mock_client = MagicMock()
        mock_client.generate.return_value = '{"steps": []}'
        mock_get_llm.return_value = mock_client

        self.planner.plan("test input")

        mock_client.generate.assert_called_once()
        # Verify json_mode=True is passed to generate
        kwargs = mock_client.generate.call_args.kwargs
        self.assertTrue(kwargs.get("json_mode"))


if __name__ == "__main__":
    unittest.main()
