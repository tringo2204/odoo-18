from odoo import fields, models


class HrVnDependent(models.Model):
    _name = 'hr.vn.dependent'
    _description = 'Người phụ thuộc'
    _order = 'date_from desc'

    employee_id = fields.Many2one(
        'hr.employee', string='Nhân viên', required=True, ondelete='cascade',
    )
    name = fields.Char(string='Họ tên', required=True)
    id_number = fields.Char(string='Số CCCD/CMND')
    relationship = fields.Selection([
        ('child', 'Con'),
        ('spouse', 'Vợ/Chồng'),
        ('parent', 'Bố/Mẹ'),
        ('other', 'Khác'),
    ], string='Quan hệ', required=True)
    date_of_birth = fields.Date(string='Ngày sinh')
    date_from = fields.Date(string='Giảm trừ từ ngày')
    date_to = fields.Date(string='Giảm trừ đến ngày')
    tax_office_confirmed = fields.Boolean(string='CQ thuế xác nhận', default=False)
    status = fields.Selection([
        ('pending', 'Chờ duyệt'),
        ('approved', 'Đã duyệt'),
        ('expired', 'Hết hạn'),
    ], string='Trạng thái', default='pending', tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Công ty',
        related='employee_id.company_id', store=True,
    )

    def action_approve(self):
        self.write({'status': 'approved', 'tax_office_confirmed': True})

    def action_expire(self):
        self.write({'status': 'expired'})

    def action_reset_pending(self):
        self.write({'status': 'pending', 'tax_office_confirmed': False})
