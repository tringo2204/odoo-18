import logging

from odoo import api, fields, models
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)


class HrVnPayrollConfig(models.TransientModel):
    _name = 'hr.vn.payroll.config'
    _description = 'Cấu hình bảng lương VN'

    # --- BHXH rates ---
    vn_bhxh_ee_rate = fields.Float(string='BHXH nhân viên (%)', default=8.0)
    vn_bhyt_ee_rate = fields.Float(string='BHYT nhân viên (%)', default=1.5)
    vn_bhtn_ee_rate = fields.Float(string='BHTN nhân viên (%)', default=1.0)
    vn_bhxh_er_rate = fields.Float(string='BHXH doanh nghiệp (%)', default=17.5)
    vn_bhyt_er_rate = fields.Float(string='BHYT doanh nghiệp (%)', default=3.0)
    vn_bhtn_er_rate = fields.Float(string='BHTN doanh nghiệp (%)', default=1.0)

    # --- Base salary + cap ---
    vn_base_salary = fields.Float(string='Lương cơ sở (VNĐ)', default=2340000)
    vn_bhxh_cap_multiplier = fields.Integer(string='Hệ số trần BHXH', default=20)
    vn_bhxh_cap_computed = fields.Float(
        string='Mức trần BHXH (tự tính)', compute='_compute_bhxh_cap',
    )

    # --- Deductions ---
    vn_self_deduction = fields.Float(string='Giảm trừ bản thân', default=11000000)
    vn_dependent_deduction = fields.Float(string='Giảm trừ mỗi NPT', default=4400000)

    @api.depends('vn_base_salary', 'vn_bhxh_cap_multiplier')
    def _compute_bhxh_cap(self):
        for rec in self:
            rec.vn_bhxh_cap_computed = rec.vn_base_salary * rec.vn_bhxh_cap_multiplier

    def _get_param_value(self, code, default=0):
        param = self.env['hr.rule.parameter'].search([('code', '=', code)], limit=1)
        if param and param.parameter_version_ids:
            latest = param.parameter_version_ids.sorted('date_from', reverse=True)[:1]
            try:
                return safe_eval(latest.parameter_value)
            except Exception:
                return default
        return default

    def _set_param_value(self, code, value):
        param = self.env['hr.rule.parameter'].search([('code', '=', code)], limit=1)
        if not param:
            _logger.warning("Payroll config: parameter '%s' not found, skipping.", code)
            return
        if not param.parameter_version_ids:
            _logger.warning("Payroll config: parameter '%s' has no versions, skipping.", code)
            return
        latest = param.parameter_version_ids.sorted('date_from', reverse=True)[:1]
        latest.parameter_value = str(value)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        res.update({
            'vn_bhxh_ee_rate': self._get_param_value('vn_bhxh_ee_rate', 8.0),
            'vn_bhyt_ee_rate': self._get_param_value('vn_bhyt_ee_rate', 1.5),
            'vn_bhtn_ee_rate': self._get_param_value('vn_bhtn_ee_rate', 1.0),
            'vn_bhxh_er_rate': self._get_param_value('vn_bhxh_er_rate', 17.5),
            'vn_bhyt_er_rate': self._get_param_value('vn_bhyt_er_rate', 3.0),
            'vn_bhtn_er_rate': self._get_param_value('vn_bhtn_er_rate', 1.0),
            'vn_base_salary': self._get_param_value('vn_base_salary', 2340000),
            'vn_bhxh_cap_multiplier': int(self._get_param_value('vn_bhxh_cap_multiplier', 20)),
            'vn_self_deduction': self._get_param_value('vn_self_deduction', 11000000),
            'vn_dependent_deduction': self._get_param_value('vn_dependent_deduction', 4400000),
        })
        return res

    def action_save(self):
        self.ensure_one()
        self._set_param_value('vn_bhxh_ee_rate', self.vn_bhxh_ee_rate)
        self._set_param_value('vn_bhyt_ee_rate', self.vn_bhyt_ee_rate)
        self._set_param_value('vn_bhtn_ee_rate', self.vn_bhtn_ee_rate)
        self._set_param_value('vn_bhxh_er_rate', self.vn_bhxh_er_rate)
        self._set_param_value('vn_bhyt_er_rate', self.vn_bhyt_er_rate)
        self._set_param_value('vn_bhtn_er_rate', self.vn_bhtn_er_rate)
        self._set_param_value('vn_base_salary', self.vn_base_salary)
        self._set_param_value('vn_bhxh_cap_multiplier', self.vn_bhxh_cap_multiplier)
        self._set_param_value('vn_self_deduction', self.vn_self_deduction)
        self._set_param_value('vn_dependent_deduction', self.vn_dependent_deduction)
        # Clear cache so payslip picks up new values
        self.env.registry.clear_cache()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': 'Đã lưu cấu hình lương VN.',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
