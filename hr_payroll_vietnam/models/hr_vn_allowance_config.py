from odoo import api, fields, models


class HrVnAllowanceConfig(models.Model):
    _name = 'hr.vn.allowance.config'
    _description = 'Cấu hình phụ cấp (chịu thuế và không chịu thuế)'
    _order = 'year desc, allowance_type'

    year = fields.Integer(string='Năm', required=True)
    allowance_type = fields.Selection([
        # Non-taxable allowances (KCT)
        ('meal', 'Ăn ca (KCT)'),
        ('uniform', 'Đồng phục (KCT)'),
        ('phone', 'Điện thoại (KCT)'),
        ('transport', 'Xăng xe (KCT)'),
        # Taxable allowances (CT)
        ('position', 'Phụ cấp chức vụ (CT)'),
        ('responsibility', 'Phụ cấp trách nhiệm (CT)'),
        ('seniority', 'Phụ cấp thâm niên (CT)'),
        ('other_taxable', 'Phụ cấp khác (CT)'),
    ], string='Loại phụ cấp', required=True)
    is_taxable = fields.Boolean(
        string='Chịu thuế',
        compute='_compute_is_taxable', store=True,
    )
    default_amount = fields.Float(string='Mức mặc định (VNĐ/tháng)')
    max_amount = fields.Float(string='Mức trần (VNĐ/tháng)')
    legal_reference = fields.Char(string='Căn cứ pháp lý')
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('type_year_company_uniq',
         'unique(allowance_type, year, company_id)',
         'Mỗi loại phụ cấp chỉ có 1 cấu hình mỗi năm/công ty.'),
    ]

    @api.depends('allowance_type')
    def _compute_is_taxable(self):
        taxable_types = {'position', 'responsibility', 'seniority', 'other_taxable'}
        for rec in self:
            rec.is_taxable = rec.allowance_type in taxable_types
