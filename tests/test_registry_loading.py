from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

from core import registry


class RegistryLoadingTests(unittest.TestCase):
    def test_load_all_ignores_missing_platform_plugin_module(self):
        fake_platforms = types.SimpleNamespace(__path__=["/fake/platforms"], __name__="platforms")

        with patch.dict(sys.modules, {"platforms": fake_platforms}):
            with patch("pkgutil.iter_modules", return_value=[(None, "platforms.fake_no_plugin", True)]):
                with patch("importlib.import_module", side_effect=ModuleNotFoundError("no module", name="platforms.fake_no_plugin.plugin")):
                    registry.load_all()

    def test_load_all_raises_when_plugin_import_fails_inside_dependency(self):
        fake_platforms = types.SimpleNamespace(__path__=["/fake/platforms"], __name__="platforms")

        with patch.dict(sys.modules, {"platforms": fake_platforms}):
            with patch("pkgutil.iter_modules", return_value=[(None, "platforms.fake_with_error", True)]):
                with patch("importlib.import_module", side_effect=ModuleNotFoundError("missing dependency", name="requests")):
                    with self.assertRaises(ModuleNotFoundError) as ctx:
                        registry.load_all()
                    self.assertEqual(getattr(ctx.exception, "name", ""), "requests")


if __name__ == "__main__":
    unittest.main(verbosity=2)
