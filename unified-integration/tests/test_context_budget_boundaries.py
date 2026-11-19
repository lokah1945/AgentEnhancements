"""Regression coverage for strict context limits, including unbroken text."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from context_budget import approx_tokens, clamp_to_budget


class ContextBudgetBoundaryTests(unittest.TestCase):
    def test_single_long_line_including_notice_stays_in_budget(self):
        for text in ('capability ' * 2500, '能力pengujian🚀' * 1500):
            with self.subTest(text=text[:20]):
                rendered = clamp_to_budget(text, 400, label='skill cards')
                self.assertLessEqual(approx_tokens(rendered), 400)
                self.assertIn('trimmed', rendered)

    def test_non_positive_or_tiny_limit_never_overflows(self):
        for limit in (0, -1, 1, 4):
            with self.subTest(limit=limit):
                rendered = clamp_to_budget('long text ' * 500, limit)
                self.assertLessEqual(approx_tokens(rendered), max(0, limit))

    def test_multiline_limit_and_short_input(self):
        text = 'first sentence.\nsecond sentence.\n' * 100
        self.assertLessEqual(approx_tokens(clamp_to_budget(text, 75)), 75)
        self.assertEqual(clamp_to_budget('keep this', 400), 'keep this')


if __name__ == '__main__':
    unittest.main()
