#!/usr/bin/env python3
"""Regression test suite for the unified-integration layer.

Run:  python3 tests/run-tests.py
Exit code is non-zero when any test fails.
"""
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))

loader = unittest.TestLoader()
suite = unittest.TestSuite()

for mod in [
    "test_compress",
    "test_memory",
    "test_load_skills",
    "test_hooks",
    "test_index",
    "test_sync",
    "test_setup_static",
    "test_ci",
    "test_registry",
    "test_adaptive_preflight",
    "test_link_skills",
    "test_dispatch_anthropic",
    "test_hardening",
    "test_modular_tree",
    "test_mcp_servers",
    "test_native_automation",
    "test_api_config",
    "test_task_observer",
    "test_audit_remediation",
    "test_native_hosts",
    "test_security_regressions",
    "test_context_budget_boundaries",
    "test_discovery_quality",
]:
    suite.addTests(loader.loadTestsFromName(mod))

runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
