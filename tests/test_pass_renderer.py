import os
import sys
import tempfile
import unittest
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.pass_renderer import build_pass_data, generate_pdf


class TestBuildPassData(unittest.TestCase):
    def test_fields_are_collected_correctly(self):
        check_in = datetime(2026, 8, 20, 9, 30, 0)
        data = build_pass_data(
            visit_id="VMS-20260820-0001",
            check_in_time=check_in,
            first_name="Jane",
            last_name="Doe",
            hp_no="81234567",
            category="Visitor",
            destination="Level 5",
            company="Acme",
            vehicle_number="SGX1234A",
            person_visited="John Smith",
            purpose="Meeting",
        )
        self.assertEqual(data["visit_id"], "VMS-20260820-0001")
        self.assertEqual(data["full_name"], "Jane Doe")
        self.assertEqual(data["hp_no"], "81234567")
        self.assertEqual(data["category"], "Visitor")
        self.assertEqual(data["destination"], "Level 5")
        self.assertEqual(data["check_in_time"], check_in)

    def test_missing_optional_fields_default_to_dash(self):
        data = build_pass_data(visit_id="VMS-1", check_in_time=datetime.now())
        self.assertEqual(data["hp_no"], "-")
        self.assertEqual(data["category"], "-")
        self.assertEqual(data["full_name"], "-")


class TestGeneratePdf(unittest.TestCase):
    def test_generate_pdf_creates_file(self):
        data = build_pass_data(
            visit_id="VMS-TEST-0001",
            check_in_time=datetime.now(),
            first_name="Jane",
            last_name="Doe",
            hp_no="81234567",
            category="Visitor",
            destination="Level 5",
        )
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
            out_path = os.path.join(tmp_dir, "pass.pdf")
            result_path = generate_pdf(data, output_path=out_path)
            self.assertEqual(result_path, out_path)
            self.assertTrue(os.path.exists(out_path))
            self.assertGreater(os.path.getsize(out_path), 0)


if __name__ == "__main__":
    unittest.main()
