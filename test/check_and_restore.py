import pathlib
import unittest
from ltarchiver import common


class MyTestCase(unittest.TestCase):
    def test_something(self):
        self.assertEqual(
            "5eb63bbbe01eeed093cb22bb8f5acdc3",
            common.get_file_checksum(pathlib.Path("test/test_source")),
        )


if __name__ == "__main__":
    unittest.main()
