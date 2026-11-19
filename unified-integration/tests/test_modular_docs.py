"""Generated status tables preserve the catalog's independent status dimension."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


class ModularDocsTests(unittest.TestCase):
    def test_vendored_source_does_not_replace_implementation_status(self):
        source = Path(__file__).resolve().parents[2] / "scripts/generate_skills_index.py"
        with tempfile.TemporaryDirectory(prefix="ae-modular-docs-") as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            generator = root / "scripts/generate_skills_index.py"
            shutil.copy2(source, generator)
            for category in ("code", "research", "tokens-optimization", "design", "multimedia-writing", "agency"):
                (root / "skills" / category).mkdir(parents=True)
            (root / "plugin-catalog").mkdir()
            (root / "plugin-catalog/catalog.json").write_text(json.dumps({"skills": [{
                "id": "code-example", "slug": "example", "name": "Example",
                "category": "code", "status": "integrated-ready", "vendored": True,
                "source_url": "https://example.test/upstream",
            }]}))
            result = subprocess.run([sys.executable, str(generator)], cwd=root,
                                    env={"PATH": os.environ["PATH"], "HOME": str(root / "home")},
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            lines = (root / "skills/code/README.md").read_text().splitlines()
            statuses = []
            for line in lines:
                if line.strip().startswith("- **Status:** "):
                    statuses.append(line.split("**Status:** ", 1)[1].strip())
                elif line.startswith("|") and "Example" in line:
                    statuses.append(line.split("|")[3].strip())
            self.assertEqual(statuses, ["integrated-ready"])


if __name__ == "__main__":
    unittest.main()
