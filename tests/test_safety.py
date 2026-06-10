import unittest

from agent.safety import RiskLevel, SafetyChecker


class TestSafetyChecker(unittest.TestCase):
    def test_read_only_command_is_safe(self):
        assessment = SafetyChecker.assess(
            "run_command",
            {"command": "git status"},
        )
        self.assertEqual(assessment.level, RiskLevel.SAFE)
        self.assertFalse(SafetyChecker.needs_confirmation(assessment))

    def test_overwrite_file_requires_confirmation(self):
        assessment = SafetyChecker.assess(
            "write_file",
            {"path": r"C:\Users\ngugi\notes.txt", "append": False},
        )
        self.assertEqual(assessment.level, RiskLevel.DANGEROUS)
        self.assertTrue(SafetyChecker.needs_confirmation(assessment))

    def test_system_process_is_critical(self):
        assessment = SafetyChecker.assess(
            "kill_process",
            {"name_or_pid": "lsass.exe"},
        )
        self.assertEqual(assessment.level, RiskLevel.CRITICAL)
        self.assertTrue(SafetyChecker.needs_confirmation(assessment))

    def test_unknown_tool_fails_safe(self):
        assessment = SafetyChecker.assess("unknown_tool", {})
        self.assertEqual(assessment.level, RiskLevel.DANGEROUS)
        self.assertTrue(SafetyChecker.needs_confirmation(assessment))


if __name__ == "__main__":
    unittest.main()
