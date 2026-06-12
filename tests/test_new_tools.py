import os
import shutil
import unittest
from pathlib import Path

from tools.manage_file_folder import manage_file_folder
from tools.compress_decompress import compress_decompress


class TestNewTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Tạo thư mục test tạm thời bên trong workspace
        cls.test_root = Path(__file__).parent / "temp_test_dir"
        cls.test_root.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        # Dọn dẹp thư mục test tạm thời sau khi kết thúc các test
        if cls.test_root.exists():
            shutil.rmtree(cls.test_root)

    def setUp(self):
        # Tạo cấu trúc file/thư mục cơ bản trước mỗi test case
        self.src_dir = self.test_root / "src"
        self.dest_dir = self.test_root / "dest"
        
        self.src_dir.mkdir(parents=True, exist_ok=True)
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        
        self.test_file = self.src_dir / "test.txt"
        self.test_file.write_text("Hello World", encoding="utf-8")

    def tearDown(self):
        # Xóa các thư mục con sau mỗi test case
        if self.src_dir.exists():
            shutil.rmtree(self.src_dir)
        if self.dest_dir.exists():
            shutil.rmtree(self.dest_dir)

    # ── Tests cho manage_file_folder ──────────────────────────────────────────

    def test_create_folder(self):
        new_folder = self.src_dir / "subfolder"
        res = manage_file_folder("create_folder", src_path=str(new_folder))
        self.assertTrue(res["success"])
        self.assertTrue(new_folder.exists() and new_folder.is_dir())

    def test_copy_file(self):
        dest_file = self.dest_dir / "copied.txt"
        res = manage_file_folder("copy", src_path=str(self.test_file), dest_path=str(dest_file))
        self.assertTrue(res["success"])
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.read_text(encoding="utf-8"), "Hello World")

    def test_move_file(self):
        dest_file = self.dest_dir / "moved.txt"
        res = manage_file_folder("move", src_path=str(self.test_file), dest_path=str(dest_file))
        self.assertTrue(res["success"])
        self.assertFalse(self.test_file.exists())
        self.assertTrue(dest_file.exists())
        self.assertEqual(dest_file.read_text(encoding="utf-8"), "Hello World")

    def test_rename_file(self):
        renamed_file = self.src_dir / "renamed.txt"
        res = manage_file_folder("rename", src_path=str(self.test_file), dest_path=str(renamed_file))
        self.assertTrue(res["success"])
        self.assertFalse(self.test_file.exists())
        self.assertTrue(renamed_file.exists())

    def test_delete_file(self):
        res = manage_file_folder("delete", src_path=str(self.test_file))
        self.assertTrue(res["success"])
        self.assertFalse(self.test_file.exists())

    def test_delete_dir(self):
        res = manage_file_folder("delete", src_path=str(self.src_dir))
        self.assertTrue(res["success"])
        self.assertFalse(self.src_dir.exists())

    # ── Tests cho compress_decompress ─────────────────────────────────────────

    def test_zip_unzip_file(self):
        zip_path = self.test_root / "test_archive.zip"
        unzip_dir = self.test_root / "unzipped_test"
        
        # 1. Nén file
        res_zip = compress_decompress("zip", path=str(self.test_file), dest_path=str(zip_path))
        self.assertTrue(res_zip["success"])
        self.assertTrue(zip_path.exists())
        
        # 2. Giải nén file
        res_unzip = compress_decompress("unzip", path=str(zip_path), dest_path=str(unzip_dir))
        self.assertTrue(res_unzip["success"])
        self.assertTrue(unzip_dir.exists())
        
        extracted_file = unzip_dir / "test.txt"
        self.assertTrue(extracted_file.exists())
        self.assertEqual(extracted_file.read_text(encoding="utf-8"), "Hello World")
        
        # Cleanup zip và thư mục giải nén
        if zip_path.exists():
            zip_path.unlink()
        if unzip_dir.exists():
            shutil.rmtree(unzip_dir)


if __name__ == "__main__":
    unittest.main()
