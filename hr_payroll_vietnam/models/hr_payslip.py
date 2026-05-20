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

    def compute_sheet(self):
        """Inject confirmed reward/discipline inputs (#130) before computing lines."""
        self._inject_rd_inputs()
        return super().compute_sheet()

    def _vn_ot_hourly_rate(self):
        """Lương giờ dùng làm gốc tính tiền tăng ca OT (#253).

        lương_giờ = (wage + phụ cấp tính BHXH) / (26 × 8)

        "Phụ cấp tính BHXH" được lấy là tổng phụ cấp chịu thuế (chức vụ,
        trách nhiệm, thâm niên, khác chịu thuế) — đã gộp sẵn trong
        contract.total_taxable_allowance. Số giờ chuẩn/tháng (26×8 = 208)
        có thể cấu hình qua rule parameter ``vn_ot_standard_monthly_hours``.
        """
        self.ensure_one()
        contract = self.contract_id
        if not contract:
            return 0.0
        monthly_base = (contract.wage or 0.0) + (contract.total_taxable_allowance or 0.0)
        std_hours = self._rule_parameter('vn_ot_standard_monthly_hours') or (26 * 8)
        if not std_hours:
            return 0.0
        return monthly_base / std_hours

    def _inject_rd_inputs(self):
        """Create hr.payslip.input records for each confirmed sht.hr.rd in the period."""
        RewardType = self.env['hr.payslip.input.type'].sudo()
        try:
            Rd = self.env['sht.hr.rd'].sudo()
        except KeyError:
            return  # sht_hr_reward_discipline not installed

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
            ])
            _logger.info(
                'payslip %s (%s): found %d RD records in period %s–%s',
                payslip.id, payslip.employee_id.name, len(rd_records),
                payslip.date_from, payslip.date_to,
            )

            for rd in rd_records:
                if not rd.amount:
                    _logger.info('RD %s has amount=0 — skipping', rd.id)
                    continue
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
                _logger.info(
                    'Injected %s input amount=%s into payslip %s',
                    code, rd.amount, payslip.id,
                )
