"""Regression coverage for strict context limits, including unbroken text."""
import sys
import os
import tempfile
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from helpers import UI_DIR, load_module

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'scripts'))
from context_budget import approx_tokens, clamp_to_budget


class ContextBudgetBoundaryTests(unittest.TestCase):
    def test_cold_or_invalid_optional_tokenizer_cache_never_attempts_a_download(self):
        import hashlib
        url = 'https://openaipublic.blob.core.windows.net/encodings/o200k_base.tiktoken'
        with tempfile.TemporaryDirectory(prefix='ae-token-cache-') as directory:
            for invalid in (False, True):
                with self.subTest(invalid_cache=invalid):
                    cache = Path(directory) / str(invalid)
                    cache.mkdir()
                    if invalid:
                        (cache / hashlib.sha1(url.encode()).hexdigest()).write_text('invalid cache')
                    getter = Mock(side_effect=RuntimeError('unexpected download'))
                    with patch.dict(os.environ, {'TIKTOKEN_CACHE_DIR': str(cache)}), \
                         patch.dict(sys.modules, {'tiktoken': SimpleNamespace(get_encoding=getter)}):
                        module = load_module('offline_budget_'+str(invalid), UI_DIR / 'scripts/context_budget.py')
                        self.assertGreater(module.approx_tokens('fixture context'), 0)
                    getter.assert_not_called()

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
