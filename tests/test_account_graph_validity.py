from __future__ import annotations

import unittest

from core.account_graph import next_lifecycle_status_after_validity_check


class AccountGraphValidityTests(unittest.TestCase):
    def test_invalid_account_recovers_to_registered_when_check_passes(self):
        self.assertEqual(
            next_lifecycle_status_after_validity_check("invalid", valid=True),
            "registered",
        )

    def test_non_invalid_account_keeps_lifecycle_when_check_passes(self):
        self.assertIsNone(
            next_lifecycle_status_after_validity_check("trial", valid=True),
        )

    def test_failed_check_marks_account_invalid(self):
        self.assertEqual(
            next_lifecycle_status_after_validity_check("subscribed", valid=False),
            "invalid",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
