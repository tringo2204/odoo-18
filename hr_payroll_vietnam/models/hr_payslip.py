from odoo import fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    # Related fields from contract for display in payslip calculation tab (#172)
    monthly_deduction = fields.Float(
        related='contract_id.monthly_deduction',
        string='Khấu trừ lương hàng tháng',
        readonly=True,
    )
    deduction_note = fields.Char(
        related='contract_id.deduction_note',
        string='Lý do khấu trừ',
        readonly=True,
    )
