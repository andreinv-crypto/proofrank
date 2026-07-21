#!/usr/bin/env python3
"""Regression tests for the local competition-video assembler."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("build_video.py")
SPEC = importlib.util.spec_from_file_location("proofrank_build_video", MODULE_PATH)
assert SPEC and SPEC.loader
BUILD_VIDEO = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD_VIDEO)


class SplitCuesTests(unittest.TestCase):
    def test_short_sentence_is_unchanged(self) -> None:
        self.assertEqual(BUILD_VIDEO.split_cues("Short sentence."), ["Short sentence."])

    def test_long_unbroken_token_is_split_without_looping(self) -> None:
        token = "x" * 200
        cues = BUILD_VIDEO.split_cues(token)
        self.assertEqual("".join(cues), token)
        self.assertTrue(all(1 <= len(cue) <= 78 for cue in cues))


if __name__ == "__main__":
    unittest.main()
