"""Unit tests for vn_tax_engine — pure Python, no Odoo dependency."""
import unittest

from odoo.addons.hr_payroll_vietnam.models.vn_tax_engine import (
    calculate_pit_progressive,
    calculate_pit_non_resident,
    calculate_gross_up,
)

# Standard 2024 brackets: (from, to, rate%)
BRACKETS_2024 = [
    (0, 5_000_000, 5),
    (5_000_000, 10_000_000, 10),
    (10_000_000, 18_000_000, 15),
    (18_000_000, 32_000_000, 20),
    (32_000_000, 52_000_000, 25),
    (52_000_000, 80_000_000, 30),
    (80_000_000, 0, 35),
]


class TestPitCalculation(unittest.TestCase):

    def test_zero_income(self):
        self.assertEqual(calculate_pit_progressive(0, BRACKETS_2024), 0)

    def test_negative_income(self):
        self.assertEqual(calculate_pit_progressive(-5_000_000, BRACKETS_2024), 0)

    def test_bracket_1(self):
        # 3,000,000 × 5% = 150,000
        self.assertEqual(calculate_pit_progressive(3_000_000, BRACKETS_2024), 150_000)

    def test_bracket_2(self):
        # 5M×5% + 3M×10% = 250K + 300K = 550K
        self.assertEqual(calculate_pit_progressive(8_000_000, BRACKETS_2024), 550_000)

    def test_bracket_3(self):
        # 5M×5% + 5M×10% + 5M×15% = 250K + 500K + 750K = 1,500K
        self.assertEqual(calculate_pit_progressive(15_000_000, BRACKETS_2024), 1_500_000)

    def test_full_7_brackets(self):
        # 100M taxable: all brackets
        # 5M×5% + 5M×10% + 8M×15% + 14M×20% + 20M×25% + 28M×30% + 20M×35%
        # = 250K + 500K + 1.2M + 2.8M + 5M + 8.4M + 7M = 25,150,000
        self.assertEqual(calculate_pit_progressive(100_000_000, BRACKETS_2024), 25_150_000)

    def test_non_resident(self):
        self.assertEqual(calculate_pit_non_resident(50_000_000), 10_000_000)
        self.assertEqual(calculate_pit_non_resident(0), 0)

    def test_gross_up_no_tax(self):
        # NET = 5M, insurance = 1M, deductions = 11M + 0 NPT = 11M
        # Taxable = 5M + 1M - 1M - 11M = -6M → no tax
        result = calculate_gross_up(
            net_desired=5_000_000,
            insurance_employee=1_000_000,
            self_deduction=11_000_000,
            dependent_count=0,
            dependent_deduction=4_400_000,
            brackets=BRACKETS_2024,
        )
        self.assertEqual(result['pit'], 0)
        self.assertEqual(result['gross'], 6_000_000)  # NET + insurance

    def test_gross_up_with_tax(self):
        # NET = 30M, insurance = 2.1M, deductions = 11M
        result = calculate_gross_up(
            net_desired=30_000_000,
            insurance_employee=2_100_000,
            self_deduction=11_000_000,
            dependent_count=0,
            dependent_deduction=4_400_000,
            brackets=BRACKETS_2024,
        )
        # Verify NET = GROSS - insurance - PIT
        self.assertAlmostEqual(
            result['net'],
            result['gross'] - 2_100_000 - result['pit'],
            delta=1,
        )


if __name__ == '__main__':
    unittest.main()
