from odoo import api, fields, models


class HrVnInsuranceConfig(models.Model):
    _name = 'hr.vn.insurance.config'
    _description = 'Cấu hình BHXH/BHYT/BHTN theo năm'
    _inherit = ['mail.thread']
    _order = 'year desc'

    name = fields.Char(string='Tên', compute='_compute_name', store=True)
    year = fields.Integer(string='Năm', required=True, tracking=True)

    bhxh_employee_rate = fields.Float(string='BHXH NV (%)', default=8.0, tracking=True)
    bhyt_employee_rate = fields.Float(string='BHYT NV (%)', default=1.5, tracking=True)
    bhtn_employee_rate = fields.Float(string='BHTN NV (%)', default=1.0, tracking=True)
    bhxh_employer_rate = fields.Float(string='BHXH DN (%)', default=17.5)
    bhyt_employer_rate = fields.Float(string='BHYT DN (%)', default=3.0)
    bhtn_employer_rate = fields.Float(string='BHTN DN (%)', default=1.0)

    base_salary = fields.Float(
        string='Lương cơ sở', default=2340000, tracking=True,
    )
    bhxh_salary_cap = fields.Float(
        string='Mức trần BHXH', compute='_compute_bhxh_cap', store=True,
    )
    regional_wage_ids = fields.One2many(
        'hr.vn.regional.wage', 'config_id', string='Lương vùng',
    )
    company_id = fields.Many2one(
        'res.company', string='Công ty', default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ('year_company_uniq', 'unique(year, company_id)',
         'Chỉ được có 1 cấu hình BHXH mỗi năm/công ty.'),
    ]

    @api.depends('year')
    def _compute_name(self):
        for rec in self:
            rec.name = f'Cấu hình BHXH {rec.year}' if rec.year else 'Mới'

    @api.depends('base_salary')
    def _compute_bhxh_cap(self):
        for rec in self:
            rec.bhxh_salary_cap = rec.base_salary * 20
