from odoo import fields, models


class HrVnPersonalDeduction(models.Model):
    _name = 'hr.vn.personal.deduction'
    _description = 'Giảm trừ gia cảnh'
    _order = 'year desc'

    year = fields.Integer(string='Năm', required=True)
    self_deduction = fields.Float(string='Giảm trừ bản thân', default=11000000)
    dependent_deduction = fields.Float(string='Giảm trừ NPT', default=4400000)
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('year_company_uniq', 'unique(year, company_id)',
         'Chỉ được có 1 cấu hình giảm trừ mỗi năm/công ty.'),
    ]
