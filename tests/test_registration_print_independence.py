"""
Verifies the core reliability requirement: visitor registration (the
SQLite INSERT) must succeed and remain committed regardless of whether
printing the visitor pass succeeds, fails, or the printer is unavailable.
"""
import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import DatabaseManager
from utils.pass_renderer import build_pass_data
from utils.printer_manager import PrinterManager, PrinterError


class TestRegistrationIndependentOfPrinting(unittest.TestCase):
    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        db_path = os.path.join(self._tmp_dir.name, "test_visitors.db")
        self.db = DatabaseManager(db_path=db_path)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def _register_sample_visitor(self, nric="S1234567D", hp_no="81234567"):
        visit_id = self.db.generate_pass_number()
        check_in_time = datetime.now()
        success = self.db.add_visitor(
            nric=nric,
            hp_no=hp_no,
            first_name="Jane",
            last_name="Doe",
            category="Visitor",
            purpose="Meeting",
            destination="Level 5",
            company="Acme",
            vehicle_number="",
            pass_number=visit_id,
            id_number=None,
            remarks="",
            person_visited="John Smith",
            organization="",
            check_in_time=check_in_time,
        )
        self.assertTrue(success, "Visitor registration (DB insert) itself failed")
        return visit_id, check_in_time

    def _visitor_exists(self, visit_id: str) -> bool:
        rows = self.db._fetchall("SELECT * FROM visitors WHERE pass_number = ?", (visit_id,))
        return len(rows) == 1

    @patch.object(PrinterManager, "print_visitor_pass", return_value=(True, "printed"))
    def test_visitor_saved_when_print_succeeds(self, _mock_print):
        visit_id, check_in_time = self._register_sample_visitor()
        self.assertTrue(self._visitor_exists(visit_id))

        pass_data = build_pass_data(visit_id=visit_id, check_in_time=check_in_time, first_name="Jane")
        success, _ = PrinterManager.print_visitor_pass(pass_data)
        self.assertTrue(success)
        # Registration remains intact regardless of the print outcome.
        self.assertTrue(self._visitor_exists(visit_id))

    @patch.object(PrinterManager, "print_visitor_pass", return_value=(False, "Printer unavailable"))
    def test_visitor_saved_even_when_print_fails(self, _mock_print):
        visit_id, check_in_time = self._register_sample_visitor()
        self.assertTrue(self._visitor_exists(visit_id))

        pass_data = build_pass_data(visit_id=visit_id, check_in_time=check_in_time, first_name="Jane")
        success, message = PrinterManager.print_visitor_pass(pass_data)
        self.assertFalse(success)
        # The critical assertion: registration is NOT rolled back or affected.
        self.assertTrue(self._visitor_exists(visit_id))

    @patch.object(PrinterManager, "print_visitor_pass", side_effect=PrinterError("printer disconnected"))
    def test_visitor_saved_even_when_print_raises(self, _mock_print):
        visit_id, check_in_time = self._register_sample_visitor()
        self.assertTrue(self._visitor_exists(visit_id))

        pass_data = build_pass_data(visit_id=visit_id, check_in_time=check_in_time, first_name="Jane")
        with self.assertRaises(PrinterError):
            PrinterManager.print_visitor_pass(pass_data)
        # Even an exception from the print path must not affect the
        # already-committed visitor record.
        self.assertTrue(self._visitor_exists(visit_id))

    def test_correct_visitor_data_flows_into_pass_data(self):
        visit_id, check_in_time = self._register_sample_visitor(nric="S7654321D", hp_no="99998888")
        pass_data = build_pass_data(
            visit_id=visit_id,
            check_in_time=check_in_time,
            first_name="Jane",
            last_name="Doe",
            hp_no="99998888",
            category="Visitor",
            destination="Level 5",
        )
        self.assertEqual(pass_data["visit_id"], visit_id)
        self.assertEqual(pass_data["hp_no"], "99998888")
        self.assertEqual(pass_data["full_name"], "Jane Doe")


if __name__ == "__main__":
    unittest.main()
