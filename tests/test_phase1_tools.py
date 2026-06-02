import unittest

from tools.open_app import _resolve_candidate
from tools.process_info import get_running_processes
from tools.result import fail, ok
from tools.run_command import run_command
from tools.system_info import get_system_info


class TestResult(unittest.TestCase):
    def test_ok_fail_shape(self):
        success = ok("done", {"x": 1})
        self.assertTrue(success["success"])
        self.assertEqual(success["message"], "done")
        self.assertEqual(success["data"], {"x": 1})

        error = fail("oops")
        self.assertFalse(error["success"])
        self.assertEqual(error["message"], "oops")


class TestSystemInfo(unittest.TestCase):
    def test_returns_success(self):
        result = get_system_info()
        self.assertTrue(result["success"], result["message"])
        self.assertIn("cpu_percent", result["data"])
        self.assertIn("ram", result["data"])


class TestProcessInfo(unittest.TestCase):
    def test_list_processes(self):
        result = get_running_processes(limit=5)
        self.assertTrue(result["success"], result["message"])
        self.assertIsInstance(result["data"], list)
        self.assertLessEqual(len(result["data"]), 5)

    def test_filter_no_match(self):
        result = get_running_processes(name_filter="__no_such_process_xyz__")
        self.assertTrue(result["success"])
        self.assertEqual(result["data"], [])


class TestRunCommand(unittest.TestCase):
    def test_python_echo(self):
        result = run_command(
            f'"{__import__("sys").executable}" -c "print(42)"',
            timeout=30,
        )
        self.assertTrue(result["success"], result["message"])
        self.assertIn("42", result["data"]["stdout"])

    def test_empty_command(self):
        result = run_command("   ")
        self.assertFalse(result["success"])


class TestOpenApp(unittest.TestCase):
    def test_empty_name(self):
        from tools.open_app import open_app

        result = open_app("  ")
        self.assertFalse(result["success"])

    def test_resolve_notepad(self):
        path = _resolve_candidate("notepad")
        self.assertIsNotNone(path)


if __name__ == "__main__":
    unittest.main()
