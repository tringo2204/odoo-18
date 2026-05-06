import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


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

    def action_compute_sheet(self):
        """Inject confirmed reward/discipline inputs (#130) before computing."""
        self._inject_rd_inputs()
        return super().action_compute_sheet()

    def _inject_rd_inputs(self):
        """Create hr.payslip.input records for each confirmed sht.hr.rd in the period."""
        RewardType = self.env['hr.payslip.input.type'].sudo()
        Rd = self.env['sht.hr.rd'].sudo() if 'sht.hr.rd' in self.env else None
        if Rd is None:
            return

        for payslip in self:
            if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
                continue

            # Remove previously auto-injected RD inputs to prevent duplicates on recompute
            payslip.input_line_ids.filtered(
                lambda x: x.input_type_id.code in ('REWARD', 'DISCIPLINE')
            ).unlink()

            rd_records = Rd.search([
                ('employee_id', '=', payslip.employee_id.id),
                ('state', '=', 'confirmed'),
                ('date', '>=', payslip.date_from),
                ('date', '<=', payslip.date_to),
                ('amount', '>', 0),
            ])

            for rd in rd_records:
                code = 'REWARD' if rd.category == 'reward' else 'DISCIPLINE'
                input_type = RewardType.search([('code', '=', code)], limit=1)
                if not input_type:
                    _logger.warning('hr.payslip.input.type %s not found — skipping', code)
                    continue
                self.env['hr.payslip.input'].sudo().create({
                    'payslip_id': payslip.id,
                    'input_type_id': input_type.id,
                    'amount': rd.amount,
                })
