import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import app_config


class TestAppConfigPrinterSettings(unittest.TestCase):
    def setUp(self):
        # Redirect config path to a throwaway temp file so tests never
        # touch the real application config.
        self._tmp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self._orig_config_path = app_config.CONFIG_PATH
        self._orig_data_dir = app_config.DATA_DIR
        app_config.DATA_DIR = self._tmp_dir.name
        app_config.CONFIG_PATH = os.path.join(self._tmp_dir.name, "config.json")
        # CONFIG_PATH is a Path object normally; wrap for consistency.
        from pathlib import Path
        app_config.DATA_DIR = Path(self._tmp_dir.name)
        app_config.CONFIG_PATH = Path(self._tmp_dir.name) / "config.json"

    def tearDown(self):
        app_config.CONFIG_PATH = self._orig_config_path
        app_config.DATA_DIR = self._orig_data_dir
        self._tmp_dir.cleanup()

    def test_printer_name_persists(self):
        self.assertEqual(app_config.get_configured_printer_name(), "")
        app_config.set_configured_printer_name("Brother QL-800")
        self.assertEqual(app_config.get_configured_printer_name(), "Brother QL-800")

    def test_label_size_defaults_when_unset(self):
        width, height = app_config.get_label_size_mm()
        self.assertEqual(width, app_config.DEFAULT_LABEL_WIDTH_MM)
        self.assertEqual(height, app_config.DEFAULT_LABEL_HEIGHT_MM)

    def test_label_size_persists_after_set(self):
        app_config.set_config_value(app_config.KEY_LABEL_WIDTH_MM, 62.0)
        app_config.set_config_value(app_config.KEY_LABEL_HEIGHT_MM, 100.0)
        width, height = app_config.get_label_size_mm()
        self.assertEqual(width, 62.0)
        self.assertEqual(height, 100.0)

    def test_invalid_label_size_falls_back_to_default(self):
        app_config.set_config_value(app_config.KEY_LABEL_WIDTH_MM, "not-a-number")
        width, height = app_config.get_label_size_mm()
        self.assertEqual(width, app_config.DEFAULT_LABEL_WIDTH_MM)
        self.assertEqual(height, app_config.DEFAULT_LABEL_HEIGHT_MM)


if __name__ == "__main__":
    unittest.main()
