import os
import tempfile
import unittest

from py_symlink import SymlinkStatus, SymlinkResult, validate_symlink


class SymlinkValidatorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = os.path.realpath(self._tmp.name)

    def _link(self, name, target):
        path = os.path.join(self.root, name)
        os.symlink(target, path)
        return path

    def _file(self, name, content=""):
        path = os.path.join(self.root, name)
        with open(path, "w") as handle:
            handle.write(content)
        return path

    def test_plain_file_is_ok_with_zero_depth(self):
        path = self._file("plain.txt")
        result = validate_symlink(path)
        self.assertEqual(result.status, SymlinkStatus.OK)
        self.assertEqual(result.depth, 0)
        self.assertEqual(result.resolved, os.path.abspath(path))
        self.assertEqual(result.path, path)

    def test_single_link_to_file(self):
        target = self._file("target.txt")
        link = self._link("link", "target.txt")
        result = validate_symlink(link)
        self.assertEqual(result.status, SymlinkStatus.OK)
        self.assertEqual(result.depth, 1)
        self.assertEqual(result.resolved, os.path.abspath(target))

    def test_chain_of_three_links(self):
        target = self._file("target.txt")
        self._link("c", "target.txt")
        self._link("b", "c")
        link = self._link("a", "b")
        result = validate_symlink(link)
        self.assertEqual(result.status, SymlinkStatus.OK)
        self.assertEqual(result.depth, 3)
        self.assertEqual(result.resolved, os.path.abspath(target))

    def test_missing_target(self):
        link = self._link("dangling", "nowhere.txt")
        result = validate_symlink(link)
        self.assertEqual(result.status, SymlinkStatus.MISSING)
        self.assertEqual(result.depth, 1)
        self.assertEqual(
            result.resolved, os.path.join(self.root, "nowhere.txt")
        )

    def test_chain_ending_in_missing_target(self):
        self._link("b", "nowhere.txt")
        link = self._link("a", "b")
        result = validate_symlink(link)
        self.assertEqual(result.status, SymlinkStatus.MISSING)
        self.assertEqual(result.depth, 2)
        self.assertEqual(
            result.resolved, os.path.join(self.root, "nowhere.txt")
        )

    def test_direct_cycle(self):
        link = self._link("loop", "loop")
        result = validate_symlink(link)
        self.assertEqual(result.status, SymlinkStatus.CIRCULAR)
        self.assertEqual(result.depth, 1)
        self.assertEqual(result.resolved, link)

    def test_two_link_cycle(self):
        self._link("b", "a")
        link = self._link("a", "b")
        result = validate_symlink(link)
        self.assertEqual(result.status, SymlinkStatus.CIRCULAR)
        self.assertEqual(result.depth, 2)
        self.assertEqual(result.resolved, link)

    def test_max_depth_zero_on_symlink(self):
        link = self._link("link", "target.txt")
        result = validate_symlink(link, max_depth=0)
        self.assertEqual(result.status, SymlinkStatus.TOO_DEEP)
        self.assertEqual(result.depth, 0)
        self.assertEqual(result.resolved, link)

    def test_max_depth_exceeded(self):
        self._file("target.txt")
        self._link("c", "target.txt")
        self._link("b", "c")
        link = self._link("a", "b")
        result = validate_symlink(link, max_depth=2)
        self.assertEqual(result.status, SymlinkStatus.TOO_DEEP)
        self.assertEqual(result.depth, 2)
        self.assertEqual(result.resolved, os.path.join(self.root, "c"))

    def test_negative_max_depth_raises(self):
        with self.assertRaises(ValueError):
            validate_symlink("whatever", max_depth=-1)

    def test_relative_path_is_accepted(self):
        target = self._file("target.txt")
        link = self._link("link", "target.txt")
        cwd = os.getcwd()
        try:
            os.chdir(self.root)
            result = validate_symlink("link")
        finally:
            os.chdir(cwd)
        self.assertEqual(result.status, SymlinkStatus.OK)
        self.assertEqual(result.resolved, os.path.abspath(target))
        self.assertEqual(result.path, "link")

    def test_result_equality_and_hash(self):
        a = SymlinkResult("x", SymlinkStatus.OK, "/x", 0)
        b = SymlinkResult("x", SymlinkStatus.OK, "/x", 0)
        c = SymlinkResult("x", SymlinkStatus.MISSING, "/x", 0)
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, a)
        self.assertNotEqual(a, "not a result")


if __name__ == "__main__":
    unittest.main()
