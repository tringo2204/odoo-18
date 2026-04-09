from odoo import fields, models


class HrVnSiD02Line(models.Model):
    _name = 'hr.vn.si.d02.line'
    _description = 'Dòng chi tiết D02-LT'
    _order = 'change_type, full_name'

    report_id = fields.Many2one(
        'hr.vn.si.d02.report', string='Báo cáo D02',
        required=True, ondelete='cascade',
    )
    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True,
    )
    bhxh_number = fields.Char(string='Số sổ BHXH')
    full_name = fields.Char(string='Họ và tên')
    change_type = fields.Selection([
        ('increase', 'Tăng'),
        ('decrease', 'Giảm'),
        ('adjust', 'Điều chỉnh'),
    ], string='Loại biến động', required=True)
    old_salary = fields.Float(string='Mức lương cũ')
    new_salary = fields.Float(string='Mức lương mới')
    effective_date = fields.Date(string='Ngày hiệu lực')
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        related='report_id.company_id', store=True,
    )
