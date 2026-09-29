import unittest
from benchmarks.audit_failures import failure_kinds


class FailureAuditTest(unittest.TestCase):
    def test_unscored_or_blank_reference_is_not_a_renderer_failure(self):
        for row in [dict(status="rendered", score=None), dict(status="blank", reference_ink=0, iou=1)]:
            self.assertEqual(failure_kinds(row), [])

    def test_independent_failure_categories(self):
        self.assertEqual(failure_kinds(dict(status="error")), ["execution_error"])
        self.assertEqual(failure_kinds(dict(status="blank", reference_ink=1, iou=0)), ["blank_against_ink"])
        self.assertEqual(failure_kinds(dict(status="rendered", reference_ink=1, iou=0)), ["zero_ink_overlap"])
        self.assertEqual(failure_kinds(dict(status="rendered", dimensions_match=False)), ["canvas_mismatch"])


if __name__ == "__main__":
    unittest.main()
