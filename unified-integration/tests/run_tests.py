#!/usr/bin/env python3
"""
AgentEnhancements Test Runner — Runs all integration tests.
"""

import sys
import subprocess
import time
from pathlib import Path


TEST_MODULES = [
    "test_registry",
    "test_memory",
    "test_adaptive_preflight",
    "test_gateway",
    "test_compression",
    "test_native_integration",
    "test_runtime",
    "test_setup",
    "test_load_skills",
    "test_stage_detector",
    "test_subagent_handler",
    "test_host_adapters",
]


def run_test_module(module_name: str) -> bool:
    """Run a single test module."""
    test_file = Path(__file__).parent / f"{module_name}.py"
    if not test_file.exists():
        print(f"⚠️  Test file not found: {test_file}")
        return False

    print(f"\n{'='*60}")
    print(f"Running {module_name}...")
    print(f"{'='*60}")

    start = time.time()
    result = subprocess.run(
        [sys.executable, str(test_file)],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent
    )
    elapsed = time.time() - start

    if result.returncode == 0:
        print(result.stdout)
        print(f"✅ {module_name} passed ({elapsed:.2f}s)")
        return True
    else:
        print(result.stdout)
        print(result.stderr)
        print(f"❌ {module_name} failed ({elapsed:.2f}s)")
        return False


def main():
    """Run all tests."""
    print("🧪 AgentEnhancements Integration Test Suite")
    print("=" * 60)

    passed = 0
    failed = 0
    total_start = time.time()

    for module in TEST_MODULES:
        if run_test_module(module):
            passed += 1
        else:
            failed += 1

    total_elapsed = time.time() - total_start

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Total:  {len(TEST_MODULES)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Time:   {total_elapsed:.2f}s")

    if failed == 0:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n💥 {failed} TEST MODULE(S) FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())