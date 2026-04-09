from odoo import fields, models


class HrVnAllowanceConfig(models.Model):
    _name = 'hr.vn.allowance.config'
    _description = 'Giới hạn phụ cấp không chịu thuế'
    _order = 'year desc, allowance_type'

    year = fields.Integer(string='Năm', required=True)
    allowance_type = fields.Selection([
        ('meal', 'Ăn ca'),
        ('uniform', 'Đồng phục'),
        ('phone', 'Điện thoại'),
        ('transport', 'Xăng xe'),
    ], string='Loại phụ cấp', required=True)
    max_amount = fields.Float(string='Mức trần (VNĐ/tháng)')
    legal_reference = fields.Char(string='Căn cứ pháp lý')
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
    )
