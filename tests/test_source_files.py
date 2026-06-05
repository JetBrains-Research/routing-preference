import unittest
from unittest.mock import Mock, patch

from src.judge.source_files import fetch_source_files


class SourceFilesTest(unittest.TestCase):
    @patch("src.judge.source_files.requests.get")
    def test_skips_directory_like_paths(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.content = b"content"
        mock_get.return_value = response

        source_files = fetch_source_files(
            "owner/repo",
            "abc123",
            [
                "src/app.py",
                "tests/",
                "",
                ".",
                "./",
                "..",
                "/tmp/workspace/src/app.py",
                "/workspace/src/app.py",
                "src/../app.py",
                "src//app.py",
            ],
        )

        self.assertEqual(source_files, {"src/app.py": "content"})
        self.assertEqual(mock_get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
