from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSiIncreaseDecrease(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Nguyễn Văn A',
            'social_insurance_id': '0123456789',
        })
        cls.si_record = cls.env['hr.vn.si.record'].create({
            'employee_id': cls.employee.id,
            'insurance_salary': 10000000,
            'registration_date': date(2024, 1, 1),
        })

    def test_create_si_record_sequence(self):
        """Hồ sơ BH phải có mã tự động."""
        self.assertNotEqual(self.si_record.name, 'Mới')
        self.assertTrue(self.si_record.name.startswith('BHXH-'))

    def test_related_bhxh_number(self):
        """Số sổ BHXH lấy từ nhân viên."""
        self.assertEqual(self.si_record.bhxh_number, '0123456789')

    def test_create_increase_history(self):
        """Tạo biến động tăng."""
        history = self.env['hr.vn.si.history'].create({
            'record_id': self.si_record.id,
            'change_type': 'increase',
            'effective_date': date(2024, 4, 1),
            'old_salary': 0,
            'new_salary': 10000000,
            'reason': 'NV mới vào làm',
        })
        self.assertEqual(history.state, 'draft')
        self.assertEqual(history.employee_id, self.employee)

    def test_confirm_history(self):
        """Xác nhận biến động."""
        history = self.env['hr.vn.si.history'].create({
            'record_id': self.si_record.id,
            'change_type': 'increase',
            'effective_date': date(2024, 4, 1),
            'new_salary': 10000000,
        })
        history.action_confirm()
        self.assertEqual(history.state, 'confirmed')

    def test_cannot_confirm_twice(self):
        """Không cho xác nhận lần 2."""
        history = self.env['hr.vn.si.history'].create({
            'record_id': self.si_record.id,
            'change_type': 'decrease',
            'effective_date': date(2024, 6, 1),
            'old_salary': 10000000,
        })
        history.action_confirm()
        with self.assertRaises(UserError):
            history.action_confirm()

    def test_cannot_draft_reported(self):
        """Không cho chuyển về nháp khi đã báo cáo."""
        history = self.env['hr.vn.si.history'].create({
            'record_id': self.si_record.id,
            'change_type': 'adjust',
            'effective_date': date(2024, 7, 1),
            'old_salary': 10000000,
            'new_salary': 12000000,
        })
        history.action_confirm()
        history.write({'state': 'reported'})
        with self.assertRaises(UserError):
            history.action_draft()

    def test_unique_employee_record(self):
        """Mỗi NV chỉ 1 hồ sơ BH / công ty."""
        with self.assertRaises(Exception):
            self.env['hr.vn.si.record'].create({
                'employee_id': self.employee.id,
                'insurance_salary': 15000000,
            })
