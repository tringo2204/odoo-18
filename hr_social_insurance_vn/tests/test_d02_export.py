from datetime import date

from odoo.tests.common import TransactionCase


class TestD02Export(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Trần Thị B',
            'social_insurance_id': '9876543210',
        })
        cls.si_record = cls.env['hr.vn.si.record'].create({
            'employee_id': cls.employee.id,
            'insurance_salary': 15000000,
        })
        cls.history = cls.env['hr.vn.si.history'].create({
            'record_id': cls.si_record.id,
            'change_type': 'increase',
            'effective_date': date(2024, 4, 15),
            'old_salary': 0,
            'new_salary': 15000000,
            'reason': 'Tuyển dụng mới',
        })

    def test_monthly_list_computed_history(self):
        """DS tăng/giảm tháng phải tính đúng biến động."""
        monthly = self.env['hr.vn.si.monthly.list'].create({
            'month': '4',
            'year': 2024,
        })
        self.assertIn(self.history, monthly.increase_ids)
        self.assertEqual(monthly.total_increase, 1)
        self.assertEqual(monthly.total_decrease, 0)

    def test_monthly_list_confirm_confirms_history(self):
        """Xác nhận DS tháng → xác nhận các biến động nháp."""
        monthly = self.env['hr.vn.si.monthly.list'].create({
            'month': '4',
            'year': 2024,
        })
        monthly.action_confirm()
        self.assertEqual(monthly.state, 'confirmed')
        self.assertEqual(self.history.state, 'confirmed')

    def test_d02_report_generate_lines(self):
        """Tạo D02 từ DS tháng → dòng chi tiết đúng."""
        monthly = self.env['hr.vn.si.monthly.list'].create({
            'month': '4',
            'year': 2024,
        })
        monthly.action_confirm()

        report = self.env['hr.vn.si.d02.report'].create({
            'month': '4',
            'year': 2024,
            'monthly_list_id': monthly.id,
        })
        report.action_generate_lines()

        self.assertEqual(len(report.line_ids), 1)
        line = report.line_ids[0]
        self.assertEqual(line.employee_id, self.employee)
        self.assertEqual(line.change_type, 'increase')
        self.assertEqual(line.new_salary, 15000000)

        # History phải đánh dấu reported
        self.assertEqual(self.history.state, 'reported')
        self.assertEqual(self.history.d02_line_id, line)

        # Monthly list phải chuyển sang exported
        self.assertEqual(monthly.state, 'exported')

    def test_d02_report_sequence(self):
        """D02 report phải có mã tự động."""
        report = self.env['hr.vn.si.d02.report'].create({
            'month': '4',
            'year': 2024,
        })
        self.assertNotEqual(report.name, 'Mới')
        self.assertTrue(report.name.startswith('D02-'))
