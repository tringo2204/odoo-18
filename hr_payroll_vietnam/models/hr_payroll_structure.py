import logging

from odoo import api, fields, models
from odoo.addons.hr_payroll_vietnam.models.vn_tax_engine import (
    calculate_pit_progressive,
    calculate_pit_non_resident,
    calculate_insurance,
)

_logger = logging.getLogger(__name__)


class HrPayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    # --- Simulate inputs (transient-like, not stored) ---
    sim_wage = fields.Float(string='Lương cơ bản', default=25000000, store=False)
    sim_insurance_salary = fields.Float(string='Lương đóng BHXH', default=20000000, store=False)
    sim_tax_resident = fields.Boolean(string='Cư trú thuế', default=True, store=False)
    sim_dependent_count = fields.Integer(string='Số NPT', default=0, store=False)
    sim_alw_position = fields.Float(string='PC chức vụ', store=False)
    sim_alw_responsibility = fields.Float(string='PC trách nhiệm', store=False)
    sim_alw_seniority = fields.Float(string='PC thâm niên', store=False)
    sim_alw_phone = fields.Float(string='PC điện thoại', default=92000, store=False)
    sim_alw_meal = fields.Float(string='PC ăn ca', default=730000, store=False)
    sim_alw_transport = fields.Float(string='PC xăng xe', store=False)
    sim_alw_uniform = fields.Float(string='PC đồng phục', default=416667, store=False)

    # --- Simulate results (not stored) ---
    sim_result_html = fields.Html(string='Kết quả', compute='_compute_sim_result', store=False, sanitize=False)

    @api.depends(
        'sim_wage', 'sim_insurance_salary', 'sim_tax_resident', 'sim_dependent_count',
        'sim_alw_position', 'sim_alw_responsibility', 'sim_alw_seniority',
        'sim_alw_phone', 'sim_alw_meal', 'sim_alw_transport', 'sim_alw_uniform',
    )
    def _compute_sim_result(self):
        for rec in self:
            if not rec.sim_wage:
                rec.sim_result_html = '<p class="text-muted">Nhập lương cơ bản để xem kết quả.</p>'
                continue

            year = fields.Date.today().year

            # Load params
            try:
                param = self.env['hr.rule.parameter']._get_parameter_from_code
                bhxh_ee_rate = param('vn_bhxh_ee_rate', raise_if_not_found=False) or 8.0
                bhyt_ee_rate = param('vn_bhyt_ee_rate', raise_if_not_found=False) or 1.5
                bhtn_ee_rate = param('vn_bhtn_ee_rate', raise_if_not_found=False) or 1.0
                bhxh_er_rate = param('vn_bhxh_er_rate', raise_if_not_found=False) or 17.5
                bhyt_er_rate = param('vn_bhyt_er_rate', raise_if_not_found=False) or 3.0
                bhtn_er_rate = param('vn_bhtn_er_rate', raise_if_not_found=False) or 1.0
                base_sal = param('vn_base_salary', raise_if_not_found=False) or 2340000
                cap_mult = param('vn_bhxh_cap_multiplier', raise_if_not_found=False) or 20
                self_ded = param('vn_self_deduction', raise_if_not_found=False) or 11000000
                dep_ded = param('vn_dependent_deduction', raise_if_not_found=False) or 4400000
                pit_brackets = param('vn_pit_brackets', raise_if_not_found=False)
            except (ValueError, KeyError) as e:
                _logger.warning("VN payroll param error: %s", e)
                rec.sim_result_html = '<p class="text-danger">Lỗi: Chưa cấu hình tham số lương VN.</p>'
                continue

            if not pit_brackets:
                pit_brackets = [
                    (0, 5000000, 5), (5000000, 10000000, 10), (10000000, 18000000, 15),
                    (18000000, 32000000, 20), (32000000, 52000000, 25),
                    (52000000, 80000000, 30), (80000000, 0, 35),
                ]

            bhxh_cap = base_sal * cap_mult
            bhtn_cap = 4960000 * cap_mult  # default Vùng I

            ins_salary = rec.sim_insurance_salary or rec.sim_wage
            taxable_alw = rec.sim_alw_position + rec.sim_alw_responsibility + rec.sim_alw_seniority
            nontax_alw = rec.sim_alw_phone + rec.sim_alw_meal + rec.sim_alw_transport + rec.sim_alw_uniform

            gross = rec.sim_wage + taxable_alw

            ins_result = calculate_insurance(
                ins_salary, bhxh_cap, bhtn_cap,
                {'bhxh': bhxh_ee_rate, 'bhyt': bhyt_ee_rate, 'bhtn': bhtn_ee_rate},
            )

            taxable_income = gross - ins_result['total'] - self_ded - (rec.sim_dependent_count * dep_ded)

            if not rec.sim_tax_resident:
                pit = calculate_pit_non_resident(max(taxable_income, 0))
            else:
                pit = calculate_pit_progressive(max(taxable_income, 0), pit_brackets)

            net = gross - ins_result['total'] - pit + nontax_alw

            # Employer cost
            er_bhxh = round(min(ins_salary, bhxh_cap) * bhxh_er_rate / 100)
            er_bhyt = round(min(ins_salary, bhxh_cap) * bhyt_er_rate / 100)
            er_bhtn = round(min(ins_salary, bhtn_cap) * bhtn_er_rate / 100)
            total_cost = gross + er_bhxh + er_bhyt + er_bhtn

            def fmt(v):
                return f"{v:,.0f}"

            html = f"""
            <table class="table table-sm table-bordered" style="max-width: 600px;">
                <thead class="table-light">
                    <tr><th colspan="2" class="text-center">Bảng tính lương mẫu</th></tr>
                </thead>
                <tbody>
                    <tr><td>Lương cơ bản</td><td class="text-end">{fmt(rec.sim_wage)}</td></tr>
                    <tr class="{'d-none' if not taxable_alw else ''}"><td>+ PC chịu thuế</td><td class="text-end">{fmt(taxable_alw)}</td></tr>
                    <tr class="table-primary fw-bold"><td>= GROSS</td><td class="text-end">{fmt(gross)}</td></tr>
                    <tr><td>- BHXH NV ({bhxh_ee_rate}%)</td><td class="text-end text-danger">-{fmt(ins_result['bhxh'])}</td></tr>
                    <tr><td>- BHYT NV ({bhyt_ee_rate}%)</td><td class="text-end text-danger">-{fmt(ins_result['bhyt'])}</td></tr>
                    <tr><td>- BHTN NV ({bhtn_ee_rate}%)</td><td class="text-end text-danger">-{fmt(ins_result['bhtn'])}</td></tr>
                    <tr class="table-secondary"><td>&nbsp;&nbsp;Tổng BH (NV)</td><td class="text-end">-{fmt(ins_result['total'])}</td></tr>
                    <tr><td>&nbsp;&nbsp;Giảm trừ bản thân</td><td class="text-end">-{fmt(self_ded)}</td></tr>
                    <tr><td>&nbsp;&nbsp;Giảm trừ NPT ({rec.sim_dependent_count} người)</td><td class="text-end">-{fmt(rec.sim_dependent_count * dep_ded)}</td></tr>
                    <tr><td>&nbsp;&nbsp;Thu nhập chịu thuế</td><td class="text-end">{fmt(max(taxable_income, 0))}</td></tr>
                    <tr><td>- Thuế TNCN</td><td class="text-end text-danger">-{fmt(pit)}</td></tr>
                    <tr><td>+ PC không chịu thuế</td><td class="text-end text-success">+{fmt(nontax_alw)}</td></tr>
                    <tr class="table-success fw-bold" style="font-size: 1.15em;"><td>= NET (Thực nhận)</td><td class="text-end">{fmt(net)}</td></tr>
                </tbody>
                <thead class="table-light">
                    <tr><th colspan="2" class="text-center">Chi phí doanh nghiệp</th></tr>
                </thead>
                <tbody>
                    <tr><td>BHXH DN ({bhxh_er_rate}%)</td><td class="text-end">{fmt(er_bhxh)}</td></tr>
                    <tr><td>BHYT DN ({bhyt_er_rate}%)</td><td class="text-end">{fmt(er_bhyt)}</td></tr>
                    <tr><td>BHTN DN ({bhtn_er_rate}%)</td><td class="text-end">{fmt(er_bhtn)}</td></tr>
                    <tr class="table-warning fw-bold"><td>= Tổng chi phí DN</td><td class="text-end">{fmt(total_cost)}</td></tr>
                </tbody>
            </table>
            """
            rec.sim_result_html = html
