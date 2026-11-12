"""Drift guard: setup.sh heredoc generators must match committed artifacts.

Regression coverage for the multi-generational drift found in the audit
(committed launch-agent.sh, compress.sh, load-skills.py etc. were stale
copies of older generator versions).
"""
import re
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import UI_DIR

SETUP = UI_DIR / "setup.sh"

TARGETS = {
    "$UNIFIED_DIR/scripts/load-skills.py": "scripts/load-skills.py",
    "$UNIFIED_DIR/scripts/memory.py": "scripts/memory.py",
    "$UNIFIED_DIR/scripts/compress.py": "scripts/compress.py",
    "$UNIFIED_DIR/launch-agent.sh": "launch-agent.sh",
    "$COMPRESSION_DIR/compress.sh": "compression/compress.sh",
    "$MEMORY_DIR/config.yaml": "memory/config.yaml",
    "$MEMORY_DIR/init-memory.sh": "memory/init-memory.sh",
    "$SKILLS_DIR/README.md": "skills/README.md",
    "$UNIFIED_DIR/prompts/universal-system-prompt.txt": "prompts/universal-system-prompt.txt",
}

# memory hook templates carry an AGENT_PLACEHOLDER substituted at generation
HOOK_PY = ("$MEMORY_DIR/hooks/${agent}-memory-hook.py", "memory/hooks/claude-code-memory-hook.py", "claude-code")
HOOK_SH = ("$MEMORY_DIR/hooks/${agent}-memory-hook.sh", "memory/hooks/claude-code-memory-hook.sh", "claude-code")


def extract_heredoc(setup_src, target_expr):
    pattern = re.compile(
        r'cat > "' + re.escape(target_expr) + r'" << \'([A-Z_]+)\'\n(.*?)\n\1\n',
        re.DOTALL,
    )
    m = pattern.search(setup_src)
    return m.group(2) if m else None


class SyncTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = SETUP.read_text()

    def _assert_sync(self, target_expr, rel, substitute=None):
        generated = extract_heredoc(self.src, target_expr)
        self.assertIsNotNone(generated, f"heredoc for {target_expr} not found in setup.sh")
        if substitute:
            generated = generated.replace("AGENT_PLACEHOLDER", substitute)
        committed = (UI_DIR / rel).read_text()
        self.assertEqual(
            generated.strip(), committed.strip(),
            f"DRIFT: {rel} differs from the setup.sh generator",
        )

    def test_all_artifacts_in_sync(self):
        for target_expr, rel in TARGETS.items():
            with self.subTest(artifact=rel):
                self._assert_sync(target_expr, rel)

    def test_memory_hook_templates_in_sync(self):
        for target_expr, rel, sub in (HOOK_PY, HOOK_SH):
            with self.subTest(artifact=rel):
                self._assert_sync(target_expr, rel, substitute=sub)

    def test_heredocs_have_no_mojibake(self):
        """The skills README heredoc once contained a corrupted glyph."""
        generated = extract_heredoc(self.src, "$SKILLS_DIR/README.md")
        self.assertIsNotNone(generated)
        self.assertNotIn("\ufffd", generated)


if __name__ == "__main__":
    unittest.main()
