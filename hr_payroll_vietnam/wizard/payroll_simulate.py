from odoo import api, fields, models
from odoo.addons.hr_payroll_vietnam.models.vn_tax_engine import (
    calculate_pit_progressive,
    calculate_pit_non_resident,
    calculate_insurance,
    calculate_gross_up,
)


class PayrollSimulate(models.TransientModel):
    _name = 'hr.vn.payroll.simulate'
    _description = 'Tính thử lương VN'

    # --- Input ---
    employee_id = fields.Many2one('hr.employee', string='Nhân viên')
    wage = fields.Float(string='Lương cơ bản (Gross)', default=25000000)
    insurance_salary = fields.Float(string='Lương đóng BHXH', default=20000000)
    tax_resident = fields.Boolean(string='Cư trú thuế', default=True)
    dependent_count = fields.Integer(string='Số NPT đã duyệt', default=0)

    # Allowances taxable
    allowance_position = fields.Float(string='PC chức vụ')
    allowance_responsibility = fields.Float(string='PC trách nhiệm')
    allowance_seniority = fields.Float(string='PC thâm niên')

    # Allowances non-taxable
    allowance_phone = fields.Float(string='PC điện thoại', default=92000)
    allowance_meal = fields.Float(string='PC ăn ca', default=730000)
    allowance_transport = fields.Float(string='PC xăng xe')
    allowance_uniform = fields.Float(string='PC đồng phục', default=416667)

    # Tax policy
    tax_policy = fields.Selection([
        ('employee_pays', 'NV chịu thuế'),
        ('gross_up', 'DN chịu thuế (Gross-up)'),
    ], string='Chính sách thuế', default='employee_pays')

    # --- Output ---
    result_gross = fields.Float(string='GROSS', readonly=True)
    result_nontax = fields.Float(string='PC không chịu thuế', readonly=True)
    result_bhxh_ee = fields.Float(string='BHXH NV', readonly=True)
    result_bhyt_ee = fields.Float(string='BHYT NV', readonly=True)
    result_bhtn_ee = fields.Float(string='BHTN NV', readonly=True)
    result_total_ins_ee = fields.Float(string='Tổng BH (NV)', readonly=True)
    result_taxable = fields.Float(string='Thu nhập chịu thuế', readonly=True)
    result_self_deduction = fields.Float(string='Giảm trừ bản thân', readonly=True)
    result_dep_deduction = fields.Float(string='Giảm trừ NPT', readonly=True)
    result_pit = fields.Float(string='Thuế TNCN', readonly=True)
    result_net = fields.Float(string='NET (Thực nhận)', readonly=True)

    # Employer cost
    result_bhxh_er = fields.Float(string='BHXH DN', readonly=True)
    result_bhyt_er = fields.Float(string='BHYT DN', readonly=True)
    result_bhtn_er = fields.Float(string='BHTN DN', readonly=True)
    result_total_cost = fields.Float(string='Tổng chi phí DN', readonly=True)

    computed = fields.Boolean(default=False)

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id:
            emp = self.employee_id
            contract = emp.contract_id
            self.tax_resident = emp.tax_resident
            self.dependent_count = emp.dependent_count or 0
            if contract:
                self.wage = contract.wage
                self.insurance_salary = contract.insurance_salary or contract.wage
                self.allowance_position = contract.allowance_position
                self.allowance_responsibility = contract.allowance_responsibility
                self.allowance_seniority = contract.allowance_seniority
                self.allowance_phone = contract.allowance_phone
                self.allowance_meal = contract.allowance_meal
                self.allowance_transport = contract.allowance_transport
                self.allowance_uniform = contract.allowance_uniform
                self.tax_policy = contract.tax_policy

    def action_compute(self):
        self.ensure_one()

        # Load parameters
        year = fields.Date.today().year
        config = self.env['hr.vn.insurance.config'].search([('year', '=', year)], limit=1)

        bhxh_ee_rate = config.bhxh_employee_rate if config else 8.0
        bhyt_ee_rate = config.bhyt_employee_rate if config else 1.5
        bhtn_ee_rate = config.bhtn_employee_rate if config else 1.0
        bhxh_er_rate = config.bhxh_employer_rate if config else 17.5
        bhyt_er_rate = config.bhyt_employer_rate if config else 3.0
        bhtn_er_rate = config.bhtn_employer_rate if config else 1.0
        bhxh_cap = config.bhxh_salary_cap if config else 46800000
        # BHTN cap = 20 × lương vùng (default Vùng I)
        bhtn_cap = 99200000
        if config and config.regional_wage_ids:
            region_1 = config.regional_wage_ids.filtered(lambda r: r.region == '1')
            if region_1:
                bhtn_cap = region_1[0].wage_amount * 20

        deduction = self.env['hr.vn.personal.deduction'].search([('year', '=', year)], limit=1)
        self_ded = deduction.self_deduction if deduction else 11000000
        dep_ded = deduction.dependent_deduction if deduction else 4400000

        brackets_records = self.env['hr.vn.pit.bracket'].search(
            [('year', '=', year)], order='bracket_no')
        brackets = [(b.income_from, b.income_to, b.tax_rate) for b in brackets_records]
        if not brackets:
            brackets = [
                (0, 5000000, 5), (5000000, 10000000, 10), (10000000, 18000000, 15),
                (18000000, 32000000, 20), (32000000, 52000000, 25),
                (52000000, 80000000, 30), (80000000, 0, 35),
            ]

        # Compute
        ins_salary = self.insurance_salary or self.wage

        # Allowances
        taxable_alw = self.allowance_position + self.allowance_responsibility + self.allowance_seniority
        nontax_alw = self.allowance_phone + self.allowance_meal + self.allowance_transport + self.allowance_uniform

        if self.tax_policy == 'gross_up':
            # Gross-up: NET mong muốn = wage
            ins_result = calculate_insurance(
                ins_salary, bhxh_cap, bhtn_cap,
                {'bhxh': bhxh_ee_rate, 'bhyt': bhyt_ee_rate, 'bhtn': bhtn_ee_rate},
            )
            grossup = calculate_gross_up(
                self.wage, ins_result['total'],
                self_ded, self.dependent_count, dep_ded, brackets,
            )
            gross = grossup['gross'] + taxable_alw
            pit = grossup['pit']
            net = self.wage + nontax_alw  # NET = desired + non-tax
        else:
            # Normal: NV chịu thuế
            gross = self.wage + taxable_alw

            ins_result = calculate_insurance(
                ins_salary, bhxh_cap, bhtn_cap,
                {'bhxh': bhxh_ee_rate, 'bhyt': bhyt_ee_rate, 'bhtn': bhtn_ee_rate},
            )

            taxable_income = gross - ins_result['total'] - self_ded - (self.dependent_count * dep_ded)

            if not self.tax_resident:
                pit = calculate_pit_non_resident(max(taxable_income, 0))
            else:
                pit = calculate_pit_progressive(max(taxable_income, 0), brackets)

            net = gross - ins_result['total'] - pit + nontax_alw

        # Employer insurance
        er_bhxh = round(min(ins_salary, bhxh_cap) * bhxh_er_rate / 100)
        er_bhyt = round(min(ins_salary, bhxh_cap) * bhyt_er_rate / 100)
        er_bhtn = round(min(ins_salary, bhtn_cap) * bhtn_er_rate / 100)

        taxable_income = gross - ins_result['total'] - self_ded - (self.dependent_count * dep_ded)

        # Write results
        self.write({
            'result_gross': gross,
            'result_nontax': nontax_alw,
            'result_bhxh_ee': ins_result['bhxh'],
            'result_bhyt_ee': ins_result['bhyt'],
            'result_bhtn_ee': ins_result['bhtn'],
            'result_total_ins_ee': ins_result['total'],
            'result_taxable': max(taxable_income, 0),
            'result_self_deduction': self_ded,
            'result_dep_deduction': self.dependent_count * dep_ded,
            'result_pit': pit,
            'result_net': net,
            'result_bhxh_er': er_bhxh,
            'result_bhyt_er': er_bhyt,
            'result_bhtn_er': er_bhtn,
            'result_total_cost': gross + er_bhxh + er_bhyt + er_bhtn,
            'computed': True,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.vn.payroll.simulate',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
