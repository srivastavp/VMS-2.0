import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.qt_app import get_app  # noqa: F401 — ensures a headless QApplication exists

from utils.printer_manager import PrinterManager, PrinterError


class TestPrinterDiscovery(unittest.TestCase):
    def test_list_printers_returns_list(self):
        printers = PrinterManager.list_printers()
        self.assertIsInstance(printers, list)

    def test_missing_printer_is_not_available(self):
        self.assertFalse(PrinterManager.is_printer_available("Definitely Not Installed XYZ"))

    def test_empty_printer_name_is_not_available(self):
        self.assertFalse(PrinterManager.is_printer_available(""))
        self.assertFalse(PrinterManager.is_printer_available(None))


class TestPrinterConfiguration(unittest.TestCase):
    @patch("utils.printer_manager.app_config.get_configured_printer_name", return_value="Brother QL-800")
    def test_configured_printer_is_used_when_set(self, _mock):
        self.assertEqual(PrinterManager.get_configured_printer(), "Brother QL-800")

    @patch("utils.printer_manager.app_config.get_configured_printer_name", return_value="")
    @patch.object(PrinterManager, "get_default_printer", return_value="Microsoft Print to PDF")
    def test_falls_back_to_windows_default_when_unset(self, _mock_default, _mock_configured):
        self.assertEqual(PrinterManager.get_configured_printer(), "Microsoft Print to PDF")

    @patch("utils.printer_manager.app_config.set_configured_printer_name")
    def test_set_printer_persists_via_app_config(self, mock_set):
        PrinterManager.set_printer("Brother QL-800")
        mock_set.assert_called_once_with("Brother QL-800")


class TestResolvePrinter(unittest.TestCase):
    @patch.object(PrinterManager, "get_configured_printer", return_value="")
    def test_raises_when_nothing_configured_or_default(self, _mock):
        with self.assertRaises(PrinterError):
            PrinterManager._resolve_printer()

    @patch.object(PrinterManager, "is_printer_available", return_value=False)
    def test_raises_when_configured_printer_unavailable(self, _mock):
        with self.assertRaises(PrinterError):
            PrinterManager._resolve_printer("Brother QL-800")

    @patch.object(PrinterManager, "is_printer_available", return_value=True)
    def test_returns_name_when_available(self, _mock):
        self.assertEqual(PrinterManager._resolve_printer("Brother QL-800"), "Brother QL-800")


class TestPrintVisitorPass(unittest.TestCase):
    """
    These tests never touch a real printer: the low-level `_print_data`
    call is mocked out so we can verify the success/failure contract in
    isolation, per the requirement that CI/unit tests must not require a
    physical Brother QL-800.
    """

    def _sample_data(self):
        from datetime import datetime
        from utils.pass_renderer import build_pass_data
        return build_pass_data(visit_id="VMS-TEST-0001", check_in_time=datetime.now(), first_name="Jane")

    @patch.object(PrinterManager, "_print_data")
    @patch.object(PrinterManager, "_resolve_printer", return_value="Brother QL-800")
    def test_print_success(self, _mock_resolve, mock_print_data):
        success, message = PrinterManager.print_visitor_pass(self._sample_data())
        self.assertTrue(success)
        self.assertIn("Brother QL-800", message)
        mock_print_data.assert_called_once()

    @patch.object(PrinterManager, "_resolve_printer", side_effect=PrinterError("Printer not configured."))
    def test_print_failure_returns_false_with_message_not_exception(self, _mock_resolve):
        success, message = PrinterManager.print_visitor_pass(self._sample_data())
        self.assertFalse(success)
        self.assertIn("not configured", message)

    @patch.object(PrinterManager, "_print_data", side_effect=RuntimeError("spooler exploded"))
    @patch.object(PrinterManager, "_resolve_printer", return_value="Brother QL-800")
    def test_unexpected_printer_error_does_not_raise(self, _mock_resolve, _mock_print_data):
        # Must not raise — callers (UI/registration) rely on this never crashing the app.
        success, message = PrinterManager.print_visitor_pass(self._sample_data())
        self.assertFalse(success)
        self.assertIn("unexpected", message.lower())

    @patch.object(PrinterManager, "_print_data")
    @patch.object(PrinterManager, "_resolve_printer", return_value="Brother QL-800")
    def test_test_print_uses_sample_data_not_a_db_record(self, _mock_resolve, mock_print_data):
        success, _ = PrinterManager.test_print(printer_name="Brother QL-800")
        self.assertTrue(success)
        printed_data = mock_print_data.call_args[0][0]
        self.assertEqual(printed_data["visit_id"], "TEST-0000")


if __name__ == "__main__":
    unittest.main()
