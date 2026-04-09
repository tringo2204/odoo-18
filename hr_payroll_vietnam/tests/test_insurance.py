"""Unit tests for insurance calculation."""
import unittest

from odoo.addons.hr_payroll_vietnam.models.vn_tax_engine import calculate_insurance


class TestInsurance(unittest.TestCase):

    def test_below_cap(self):
        result = calculate_insurance(
            salary=15_000_000,
            bhxh_cap=46_800_000,  # 20 × 2.34M
            bhtn_cap=99_200_000,  # 20 × 4.96M
            employee_rates={'bhxh': 8.0, 'bhyt': 1.5, 'bhtn': 1.0},
        )
        self.assertEqual(result['bhxh'], 1_200_000)  # 15M × 8%
        self.assertEqual(result['bhyt'], 225_000)     # 15M × 1.5%
        self.assertEqual(result['bhtn'], 150_000)     # 15M × 1%
        self.assertEqual(result['total'], 1_575_000)

    def test_above_bhxh_cap(self):
        # Salary 50M but BHXH cap is 46.8M
        result = calculate_insurance(
            salary=50_000_000,
            bhxh_cap=46_800_000,
            bhtn_cap=99_200_000,
            employee_rates={'bhxh': 8.0, 'bhyt': 1.5, 'bhtn': 1.0},
        )
        self.assertEqual(result['bhxh'], 3_744_000)   # 46.8M × 8%
        self.assertEqual(result['bhyt'], 702_000)      # 46.8M × 1.5%
        self.assertEqual(result['bhtn'], 500_000)      # 50M × 1% (below BHTN cap)

    def test_above_both_caps(self):
        result = calculate_insurance(
            salary=120_000_000,
            bhxh_cap=46_800_000,
            bhtn_cap=99_200_000,
            employee_rates={'bhxh': 8.0, 'bhyt': 1.5, 'bhtn': 1.0},
        )
        self.assertEqual(result['bhxh'], 3_744_000)   # capped at 46.8M
        self.assertEqual(result['bhtn'], 992_000)      # capped at 99.2M


if __name__ == '__main__':
    unittest.main()
