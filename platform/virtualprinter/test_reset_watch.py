#!/usr/bin/env python3
"""reset_watch.py, without Docker (vt350#224): which klippy log lines restart a board, and following the log.

    python3 platform/virtualprinter/test_reset_watch.py
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reset_watch  # noqa: E402


class Lines(unittest.TestCase):
    def test_each_reset_kind_names_its_board(self):
        for line, want in [
            ("Attempting MCU 'mcu' reset\n", "mcu"),                       # arduino (DTR)
            ("Attempting MCU 'o2s_left' reset command\n", "o2s_left"),     # restart_method: command
            ("Attempting MCU 'o2s_right' config_reset command\n", "o2s_right"),
            ("Attempting MCU 'mcu' Cheetah-style reset\n", "mcu"),
        ]:
            self.assertEqual(reset_watch.board_to_restart(line), want, line)

    def test_other_lines_restart_nothing(self):
        for line in ["Unable to issue reset command on MCU 'mcu'\n", "mcu 'mcu': Starting serial connect\n",
                     "Stats 1.0: mcu: mcu_awake=0.04\n", "Attempting MCU 'mcu' reset via rpi usb power\n", ""]:
            self.assertIsNone(reset_watch.board_to_restart(line), line)


class Follow(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log = os.path.join(self._tmp.name, "klippy.log")

    def tearDown(self):
        self._tmp.cleanup()

    def _append(self, text, path=None):
        with open(path or self.log, "a") as f:
            f.write(text)

    def test_only_new_lines_then_a_rotated_file_from_its_start(self):
        self._append("old line\n")
        lines = reset_watch.follow(self.log, poll=0.01)
        self._append("new 1\n")
        self.assertEqual(next(lines), "new 1\n")
        os.rename(self.log, self.log + ".1")
        self._append("after rotation\n")
        self.assertEqual(next(lines), "after rotation\n")

    def test_a_log_that_appears_later_is_read_from_its_start(self):
        lines = reset_watch.follow(self.log, poll=0.01)
        import threading
        threading.Timer(0.05, self._append, ["first\n"]).start()
        self.assertEqual(next(lines), "first\n")


if __name__ == "__main__":
    unittest.main()
