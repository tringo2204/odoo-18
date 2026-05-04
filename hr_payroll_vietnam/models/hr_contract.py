import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


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

    # --- Totals (computed, Row 29) ---
    total_taxable_allowance = fields.Float(
        string='Tổng PC chịu thuế',
        compute='_compute_allowance_totals',
        store=True,
    )
    total_nontax_allowance = fields.Float(
        string='Tổng PC không chịu thuế',
        compute='_compute_allowance_totals',
        store=True,
    )

    @api.depends(
        'allowance_position', 'allowance_responsibility',
        'allowance_seniority', 'allowance_other_taxable',
        'allowance_phone', 'allowance_meal',
        'allowance_transport', 'allowance_uniform', 'allowance_other_nontax',
    )
    def _compute_allowance_totals(self):
        for rec in self:
            rec.total_taxable_allowance = (
                rec.allowance_position
                + rec.allowance_responsibility
                + rec.allowance_seniority
                + rec.allowance_other_taxable
            )
            rec.total_nontax_allowance = (
                rec.allowance_phone
                + rec.allowance_meal
                + rec.allowance_transport
                + rec.allowance_uniform
                + rec.allowance_other_nontax
            )

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

    # --- Monthly salary deductions ---
    monthly_deduction = fields.Float(
        string='Khấu trừ lương hàng tháng',
        help='Khoản khấu trừ cố định hàng tháng (trả nợ, ứng lương,...)',
    )
    deduction_note = fields.Char(string='Lý do khấu trừ')

    def write(self, vals):
        """Auto-create SI history when insurance_salary changes."""
        if 'insurance_salary' in vals and 'hr.vn.si.record' in self.env:
            for contract in self:
                old_salary = contract.insurance_salary
                new_salary = vals['insurance_salary']
                if old_salary and new_salary and old_salary != new_salary:
                    si_rec = self.env['hr.vn.si.record'].search([
                        ('employee_id', '=', contract.employee_id.id),
                        ('current_status', '=', 'active'),
                    ], limit=1)
                    if si_rec:
                        self.env['hr.vn.si.history'].create({
                            'record_id': si_rec.id,
                            'change_type': 'adjust',
                            'effective_date': fields.Date.today(),
                            'old_salary': old_salary,
                            'new_salary': new_salary,
                            'reason': 'Điều chỉnh lương đóng BH từ HĐ',
                        })
                        si_rec.write({'insurance_salary': new_salary})
                        _logger.info("SI adjust: %s %s → %s",
                                     contract.employee_id.name, old_salary, new_salary)
        return super().write(vals)
