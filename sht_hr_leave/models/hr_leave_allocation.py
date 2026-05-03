# -*- coding: utf-8 -*-
import math

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    sht_seniority_bonus_days = fields.Float(
        string='Seniority Bonus Days',
        compute='_compute_sht_seniority_bonus_days',
    )

    def _sht_employee_seniority_start_date(self, employee):
        if not employee:
            return False
        if 'seniority_start_date' in employee._fields:
            d = employee.seniority_start_date
            if d:
                return d
        if 'first_contract_date' in employee._fields:
            d = employee.first_contract_date
            if d:
                return d
        return False

    @api.depends(
        'employee_id',
        'holiday_status_id',
        'holiday_status_id.sht_seniority_bonus',
    )
    def _compute_sht_seniority_bonus_days(self):
        today = fields.Date.today()
        for allocation in self:
            bonus = 0.0
            leave_type = allocation.holiday_status_id
            employee = allocation.employee_id
            if leave_type and leave_type.sht_seniority_bonus and employee:
                start = allocation._sht_employee_seniority_start_date(employee)
                if start:
                    years = relativedelta(today, start).years
                    bonus = float((years // 5) * 1)
            allocation.sht_seniority_bonus_days = bonus

    def _process_accrual_plan_level(self, level, start_period, start_date, end_period, end_date):
        """Override: round up accrued days to nearest integer for day-type plans."""
        added_value = super()._process_accrual_plan_level(
            level, start_period, start_date, end_period, end_date,
        )
        if level.added_value_type == 'day' and added_value > 0:
            added_value = math.ceil(added_value)
        return added_value
