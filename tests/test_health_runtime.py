from __future__ import annotations

import unittest
from unittest.mock import patch

from infrastructure.health_runtime import HealthRuntime


class _DummySession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def exec(self, _query):
        return None


class HealthRuntimeTests(unittest.TestCase):
    @patch("infrastructure.health_runtime.is_running", return_value=False)
    @patch("infrastructure.health_runtime.list_platforms", return_value=[])
    @patch("infrastructure.health_runtime.Session", return_value=_DummySession())
    def test_readiness_fails_when_registry_is_empty(self, _session_cls, _list_platforms, _is_running):
        runtime = HealthRuntime()

        result = runtime.readiness()

        self.assertFalse(result["ok"])
        self.assertTrue(result["database"]["ok"])
        self.assertFalse(result["registry"]["ok"])
        self.assertEqual(result["registry"]["platform_count"], 0)
        self.assertEqual(result["registry"]["error"], "no platform plugins loaded")


if __name__ == "__main__":
    unittest.main(verbosity=2)
