#!/usr/bin/env python3
"""
AgentEnhancements Feature Flags — Controlled rollout with feature gates.
Per-host enable/disable, A/B test framework, metrics collection.
"""

import json
import os
import sqlite3
import threading
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from enum import Enum
from contextlib import contextmanager


class FeatureFlag(Enum):
    """Feature flags for AgentEnhancements capabilities."""
    PREFETCH_MODE = "preflight_mode"           # 0, 1, 2
    QUALITY_GUIDANCE = "quality_guidance"      # true/false
    STAGE_HINTS = "stage_hints"                # true/false
    SUBAGENT_SUPPORT = "subagent_support"      # true/false
    EFFECTIVENESS_TRACKING = "effectiveness_tracking"  # true/false
    MCP_GATEWAY = "mcp_gateway"                # true/false
    MEMORY_PERSISTENCE = "memory_persistence"  # true/false
    CONTEXT_COMPRESSION = "context_compression" # true/false
    NATIVE_HOOKS = "native_hooks"              # true/false
    SKILL_DISCOVERY = "skill_discovery"        # true/false


@dataclass
class FeatureConfig:
    """Configuration for a feature flag."""
    flag: FeatureFlag
    enabled: bool = False
    host_overrides: Dict[str, bool] = field(default_factory=dict)  # host -> enabled
    rollout_percentage: float = 0.0  # 0-100
    description: str = ""
    min_version: str = ""  # Minimum AE version required


class FeatureFlags:
    """
    Feature flag management with per-host overrides and rollout percentages.

    Features:
    - Per-host enable/disable
    - Gradual rollout percentages
    - Environment variable overrides
    - Configuration file persistence
    """

    DEFAULT_FLAGS = {
        FeatureFlag.PREFETCH_MODE: FeatureConfig(
            flag=FeatureFlag.PREFETCH_MODE,
            enabled=True,
            host_overrides={},
            rollout_percentage=100.0,
            description="Adaptive preflight mode (0=legacy, 1=native, 2=custom)",
        ),
        FeatureFlag.QUALITY_GUIDANCE: FeatureConfig(
            flag=FeatureFlag.QUALITY_GUIDANCE,
            enabled=False,
            host_overrides={},
            rollout_percentage=0.0,
            description="Evidence-based quality guidance and verification checks",
        ),
        FeatureFlag.STAGE_HINTS: FeatureConfig(
            flag=FeatureFlag.STAGE_HINTS,
            enabled=False,
            host_overrides={},
            rollout_percentage=0.0,
            description="Stage/role-aware capability hints",
        ),
        FeatureFlag.SUBAGENT_SUPPORT: FeatureConfig(
            flag=FeatureFlag.SUBAGENT_SUPPORT,
            enabled=False,
            host_overrides={},
            rollout_percentage=0.0,
            description="Subagent-specific capability injection",
        ),
        FeatureFlag.EFFECTIVENESS_TRACKING: FeatureConfig(
            flag=FeatureFlag.EFFECTIVENESS_TRACKING,
            enabled=False,
            host_overrides={},
            rollout_percentage=0.0,
            description="Track capability effectiveness (recommended/used/outcome)",
        ),
        FeatureFlag.MCP_GATEWAY: FeatureConfig(
            flag=FeatureFlag.MCP_GATEWAY,
            enabled=True,
            host_overrides={},
            rollout_percentage=100.0,
            description="MCP server gateway and tool routing",
        ),
        FeatureFlag.MEMORY_PERSISTENCE: FeatureConfig(
            flag=FeatureFlag.MEMORY_PERSISTENCE,
            enabled=True,
            host_overrides={},
            rollout_percentage=100.0,
            description="Cross-session SQLite memory",
        ),
        FeatureFlag.CONTEXT_COMPRESSION: FeatureConfig(
            flag=FeatureFlag.CONTEXT_COMPRESSION,
            enabled=True,
            host_overrides={},
            rollout_percentage=100.0,
            description="Context compression with headroom/Python fallback",
        ),
        FeatureFlag.NATIVE_HOOKS: FeatureConfig(
            flag=FeatureFlag.NATIVE_HOOKS,
            enabled=True,
            host_overrides={},
            rollout_percentage=100.0,
            description="Native lifecycle hooks for supported agents",
        ),
        FeatureFlag.SKILL_DISCOVERY: FeatureConfig(
            flag=FeatureFlag.SKILL_DISCOVERY,
            enabled=True,
            host_overrides={},
            rollout_percentage=100.0,
            description="Skill registry and discovery",
        ),
    }

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._flags: Dict[FeatureFlag, FeatureConfig] = {}
        self._lock = threading.RLock()
        self._load_config()

    def _load_config(self):
        """Load flags from config file."""
        with self._lock:
            # Start with defaults
            self._flags = {k: FeatureConfig(**asdict(v)) for k, v in self.DEFAULT_FLAGS.items()}

            # Load from file
            if self.config_path.exists():
                try:
                    data = json.loads(self.config_path.read_text())
                    for flag_str, config_data in data.get("flags", {}).items():
                        flag = FeatureFlag(flag_str)
                        if flag in self._flags:
                            # Remove 'flag' from config_data if present (it's a string in JSON)
                            config_data.pop("flag", None)
                            # Merge with defaults
                            merged = {**asdict(self._flags[flag]), **config_data}
                            merged["flag"] = flag  # Keep as enum for internal use
                            self._flags[flag] = FeatureConfig(**merged)
                except Exception:
                    pass  # Use defaults

            # Environment overrides
            for flag in FeatureFlag:
                env_var = f"AE_FEATURE_{flag.value.upper()}"
                if os.getenv(env_var) is not None:
                    self._flags[flag].enabled = os.getenv(env_var).lower() == "true"

    def _save_config(self):
        """Save flags to config file."""
        with self._lock:
            data = {
                "version": 1,
                "updated": time.time(),
                "flags": {
                    flag.value: {k: v for k, v in asdict(config).items() if k != "flag"}
                    for flag, config in self._flags.items()
                },
            }
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(json.dumps(data, indent=2))

    def is_enabled(self, flag: FeatureFlag, host: str = "") -> bool:
        """Check if feature is enabled for a host."""
        with self._lock:
            config = self._flags.get(flag)
            if not config:
                return False

            # Check host override first
            if host and host in config.host_overrides:
                return config.host_overrides[host]

            # Check rollout percentage
            if config.rollout_percentage < 100.0:
                # Deterministic rollout based on host hash
                if host:
                    hash_val = int(hashlib.md5(host.encode()).hexdigest(), 16)
                    if (hash_val % 100) >= config.rollout_percentage:
                        return False
                else:
                    # No host context - use random-ish but deterministic
                    return False

            return config.enabled

    def set_enabled(self, flag: FeatureFlag, enabled: bool, host: str = "") -> bool:
        """Set feature enabled state. Global enable also sets 100% rollout."""
        with self._lock:
            if flag not in self._flags:
                return False

            if host:
                self._flags[flag].host_overrides[host] = enabled
            else:
                self._flags[flag].enabled = enabled
                if enabled:
                    # Global enable implies full rollout
                    self._flags[flag].rollout_percentage = 100.0

            self._save_config()
            return True

    def set_rollout(self, flag: FeatureFlag, percentage: float) -> bool:
        """Set rollout percentage (0-100)."""
        with self._lock:
            if flag not in self._flags:
                return False
            if not 0 <= percentage <= 100:
                return False

            self._flags[flag].rollout_percentage = percentage
            self._save_config()
            return True

    def get_host_overrides(self, flag: FeatureFlag) -> Dict[str, bool]:
        """Get host-specific overrides for a flag."""
        with self._lock:
            config = self._flags.get(flag)
            if config:
                return config.host_overrides.copy()
            return {}

    def get_all_flags(self, host: str = "") -> Dict[str, bool]:
        """Get all flag states for a host."""
        with self._lock:
            return {
                flag.value: self.is_enabled(flag, host)
                for flag in FeatureFlag
            }

    def get_config(self, flag: FeatureFlag) -> Optional[FeatureConfig]:
        """Get full config for a flag."""
        with self._lock:
            return self._flags.get(flag)

    def list_flags(self) -> List[Dict]:
        """List all flags with descriptions."""
        with self._lock:
            return [
                {
                    "flag": flag.value,
                    "enabled": config.enabled,
                    "rollout_percentage": config.rollout_percentage,
                    "host_overrides": config.host_overrides,
                    "description": config.description,
                    "min_version": config.min_version,
                }
                for flag, config in self._flags.items()
            ]


class MetricsCollector:
    """Collect structured metrics for A/B testing and monitoring."""

    def __init__(self, memory_dir: Path):
        self.memory_dir = memory_dir
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = memory_dir / "metrics.db"
        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize metrics database."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    task_id TEXT,
                    session_id TEXT,
                    host TEXT,
                    variant TEXT,  -- 'control' or 'treatment'
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    dimensions TEXT  -- JSON
                );

                CREATE INDEX IF NOT EXISTS idx_metrics_task ON metrics(task_id);
                CREATE INDEX IF NOT EXISTS idx_metrics_variant ON metrics(variant);
                CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
            """)

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def record(
        self,
        metric_name: str,
        value: float,
        task_id: str = "",
        session_id: str = "",
        host: str = "",
        variant: str = "treatment",
        dimensions: Optional[Dict] = None
    ):
        """Record a metric value."""
        with self._lock:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO metrics (timestamp, task_id, session_id, host, variant, metric_name, metric_value, dimensions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    time.time(),
                    task_id,
                    session_id,
                    host,
                    variant,
                    metric_name,
                    value,
                    json.dumps(dimensions or {}),
                ))

    def record_batch(self, metrics: List[Dict]):
        """Record multiple metrics at once."""
        with self._lock:
            with self._get_conn() as conn:
                for m in metrics:
                    conn.execute("""
                        INSERT INTO metrics (timestamp, task_id, session_id, host, variant, metric_name, metric_value, dimensions)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        time.time(),
                        m.get("task_id", ""),
                        m.get("session_id", ""),
                        m.get("host", ""),
                        m.get("variant", "treatment"),
                        m["metric_name"],
                        m["metric_value"],
                        json.dumps(m.get("dimensions", {})),
                    ))

    def get_metrics(
        self,
        metric_name: str,
        variant: Optional[str] = None,
        host: str = "",
        start_time: float = 0,
        end_time: float = 0,
        limit: int = 1000
    ) -> List[Dict]:
        """Query metrics."""
        with self._get_conn() as conn:
            query = "SELECT * FROM metrics WHERE metric_name = ?"
            params = [metric_name]

            if variant:
                query += " AND variant = ?"
                params.append(variant)
            if host:
                query += " AND host = ?"
                params.append(host)
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)

            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]

    def get_summary(
        self,
        metric_name: str,
        variant: Optional[str] = None,
        host: str = ""
    ) -> Dict[str, float]:
        """Get statistical summary of a metric."""
        metrics = self.get_metrics(metric_name, variant, host, limit=10000)
        if not metrics:
            return {"count": 0}

        values = [m["metric_value"] for m in metrics]
        values.sort()

        return {
            "count": len(values),
            "mean": sum(values) / len(values),
            "min": values[0],
            "max": values[-1],
            "median": values[len(values) // 2],
            "p95": values[int(len(values) * 0.95)] if len(values) > 1 else values[0],
            "p99": values[int(len(values) * 0.99)] if len(values) > 1 else values[0],
        }

    def compare_variants(self, metric_name: str, control: str = "control", treatment: str = "treatment") -> Dict:
        """Compare metric between variants."""
        control_summary = self.get_summary(metric_name, control)
        treatment_summary = self.get_summary(metric_name, treatment)

        return {
            "control": control_summary,
            "treatment": treatment_summary,
            "difference": treatment_summary.get("mean", 0) - control_summary.get("mean", 0),
            "relative_change": (
                (treatment_summary.get("mean", 0) - control_summary.get("mean", 0))
                / control_summary.get("mean", 1)
                if control_summary.get("mean", 0) != 0 else 0
            ),
        }


class ABTestManager:
    """Manage A/B test assignments and variant selection."""

    def __init__(self, feature_flags: FeatureFlags, metrics: MetricsCollector):
        self.feature_flags = feature_flags
        self.metrics = metrics
        self._assignments: Dict[str, str] = {}  # task_id -> variant
        self._lock = threading.RLock()

    def assign_variant(self, task_id: str, host: str, feature: FeatureFlag) -> str:
        """Assign task to control or treatment variant."""
        with self._lock:
            if task_id in self._assignments:
                return self._assignments[task_id]

            # Check if feature is enabled for treatment
            treatment_enabled = self.feature_flags.is_enabled(feature, host)
            control_enabled = self.feature_flags.is_enabled(feature, "")  # Base config

            # If feature disabled entirely, both get control
            if not control_enabled:
                variant = "control"
            # If treatment enabled for this host, random 50/50
            elif treatment_enabled:
                # Deterministic assignment based on task_id hash
                hash_val = int(hashlib.md5(task_id.encode()).hexdigest(), 16)
                variant = "treatment" if (hash_val % 2 == 0) else "control"
            else:
                variant = "control"

            self._assignments[task_id] = variant
            return variant

    def get_variant(self, task_id: str) -> Optional[str]:
        """Get assigned variant for task."""
        with self._lock:
            return self._assignments.get(task_id)

    def record_metric(self, task_id: str, metric_name: str, value: float, **kwargs):
        """Record metric for assigned variant."""
        variant = self.get_variant(task_id) or "control"
        self.metrics.record(metric_name, value, variant=variant, **kwargs)

    def get_results(self, feature: FeatureFlag) -> Dict:
        """Get A/B test results for a feature."""
        # Get all metrics for this feature
        # This would be expanded with actual metric names
        return {
            "feature": feature.value,
            "note": "Results require metric names to be specified",
        }


# =========================================================================
# CLI INTERFACE
# =========================================================================
def main():
    import argparse

    parser = argparse.ArgumentParser(description="Feature Flags CLI")
    parser.add_argument("command", choices=["list", "enable", "disable", "rollout", "host-override", "metrics", "ab-assign", "ab-results"])
    parser.add_argument("--flag", help="Feature flag")
    parser.add_argument("--host", help="Host name")
    parser.add_argument("--percentage", type=float, help="Rollout percentage")
    parser.add_argument("--enabled", action="store_true", help="Enable flag")
    parser.add_argument("--disabled", action="store_true", help="Disable flag")
    parser.add_argument("--task-id", help="Task ID")
    parser.add_argument("--metric", help="Metric name")
    parser.add_argument("--value", type=float, help="Metric value")
    parser.add_argument("--variant", choices=["control", "treatment"], help="Variant")
    parser.add_argument("--base-dir", help="Base directory")

    args = parser.parse_args()

    if args.base_dir:
        base_dir = Path(args.base_dir)
    else:
        base_dir = Path(__file__).parent.parent.parent

    config_path = base_dir / "unified-integration" / "config" / "feature_flags.json"
    flags = FeatureFlags(config_path)
    memory_dir = base_dir / ".agentenhancements" / "memory"
    metrics = MetricsCollector(memory_dir)
    ab_test = ABTestManager(flags, metrics)

    if args.command == "list":
        for f in flags.list_flags():
            print(f"{f['flag']}: {'ON' if f['enabled'] else 'OFF'} (rollout: {f['rollout_percentage']}%) - {f['description']}")

    elif args.command == "enable":
        if not args.flag:
            parser.error("--flag required")
        flag = FeatureFlag(args.flag)
        host = args.host or ""
        flags.set_enabled(flag, True, host)
        print(f"Enabled {flag.value} for {host or 'all hosts'}")

    elif args.command == "disable":
        if not args.flag:
            parser.error("--flag required")
        flag = FeatureFlag(args.flag)
        host = args.host or ""
        flags.set_enabled(flag, False, host)
        print(f"Disabled {flag.value} for {host or 'all hosts'}")

    elif args.command == "rollout":
        if not args.flag or args.percentage is None:
            parser.error("--flag and --percentage required")
        flag = FeatureFlag(args.flag)
        flags.set_rollout(flag, args.percentage)
        print(f"Set rollout for {flag.value} to {args.percentage}%")

    elif args.command == "host-override":
        if not args.flag:
            parser.error("--flag required")
        flag = FeatureFlag(args.flag)
        if args.host:
            overrides = flags.get_host_overrides(flag)
            print(json.dumps(overrides, indent=2))
        else:
            print(json.dumps(flags.get_all_flags(), indent=2))

    elif args.command == "metrics":
        if not args.metric or args.value is None:
            parser.error("--metric and --value required")
        variant = args.variant or "treatment"
        metrics = MetricsCollector(memory_dir)
        metrics.record(args.metric, args.value, variant=variant)
        print(f"Recorded {args.metric}={args.value} for {variant}")

    elif args.command == "ab-assign":
        if not args.task_id or not args.flag:
            parser.error("--task-id and --flag required")
        feature = FeatureFlag(args.flag)
        variant = ab_test.assign_variant(args.task_id, args.host or "", feature)
        print(f"Assigned {variant}")

    elif args.command == "ab-results":
        if not args.flag:
            parser.error("--flag required")
        feature = FeatureFlag(args.flag)
        print(json.dumps(ab_test.get_results(feature), indent=2))


if __name__ == "__main__":
    import sqlite3
    main()