from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # --- Insurance ---
    insurance_salary = fields.Float(
        string='Lương đóng BHXH',
        help='Mức lương dùng để tính BHXH (có thể khác wage)',
    )

    # --- Taxable allowances ---
    allowance_position = fields.Float(string='PC chức vụ')
    allowance_responsibility = fields.Float(string='PC trách nhiệm')
    allowance_seniority = fields.Float(string='PC thâm niên')
    allowance_other_taxable = fields.Float(string='PC khác (chịu thuế)')

    # --- Non-taxable allowances ---
    allowance_phone = fields.Float(string='PC điện thoại')
    allowance_meal = fields.Float(string='PC ăn ca')
    allowance_transport = fields.Float(string='PC xăng xe')
    allowance_uniform = fields.Float(string='PC đồng phục')
    allowance_other_nontax = fields.Float(string='PC khác (KCT)')

    # --- OT rates ---
    ot_rate_weekday = fields.Float(string='OT ngày thường (%)', default=150)
    ot_rate_weekend = fields.Float(string='OT cuối tuần (%)', default=200)
    ot_rate_holiday = fields.Float(string='OT ngày lễ (%)', default=300)
    ot_rate_night_extra = fields.Float(string='Phụ trội ca đêm (%)', default=30)

    # --- Tax policy ---
    tax_policy = fields.Selection([
        ('employee_pays', 'NV chịu thuế'),
        ('gross_up', 'DN chịu thuế (Gross-up)'),
    ], string='Chính sách thuế', default='employee_pays')
