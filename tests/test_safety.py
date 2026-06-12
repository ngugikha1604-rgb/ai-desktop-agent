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

    def test_manage_file_folder_safety(self):
        # copy -> CAUTION (không cần confirm)
        a_copy = SafetyChecker.assess(
            "manage_file_folder",
            {"action": "copy", "src_path": r"C:\Users\test.txt", "dest_path": r"C:\Users\backup.txt"},
        )
        self.assertEqual(a_copy.level, RiskLevel.CAUTION)
        self.assertFalse(SafetyChecker.needs_confirmation(a_copy))

        # delete -> DANGEROUS (cần confirm)
        a_delete = SafetyChecker.assess(
            "manage_file_folder",
            {"action": "delete", "src_path": r"C:\Users\test.txt"},
        )
        self.assertEqual(a_delete.level, RiskLevel.DANGEROUS)
        self.assertTrue(SafetyChecker.needs_confirmation(a_delete))

        # system path -> CRITICAL (cần confirm)
        a_critical = SafetyChecker.assess(
            "manage_file_folder",
            {"action": "delete", "src_path": r"C:\Windows\System32\cmd.exe"},
        )
        self.assertEqual(a_critical.level, RiskLevel.CRITICAL)
        self.assertTrue(SafetyChecker.needs_confirmation(a_critical))

    def test_compress_decompress_safety(self):
        # zip -> CAUTION
        a_zip = SafetyChecker.assess(
            "compress_decompress",
            {"action": "zip", "path": r"C:\Users\test"},
        )
        self.assertEqual(a_zip.level, RiskLevel.CAUTION)
        self.assertFalse(SafetyChecker.needs_confirmation(a_zip))

        # unzip -> DANGEROUS
        a_unzip = SafetyChecker.assess(
            "compress_decompress",
            {"action": "unzip", "path": r"C:\Users\archive.zip"},
        )
        self.assertEqual(a_unzip.level, RiskLevel.DANGEROUS)
        self.assertTrue(SafetyChecker.needs_confirmation(a_unzip))


if __name__ == "__main__":
    unittest.main()
