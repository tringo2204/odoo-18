# -*- coding: utf-8 -*-
"""
#144 — OT giờ từ chấm công → worked days trong bảng lương.

Overrides _get_worked_day_lines() to add an OVERTIME worked-day line
by summing overtime_hours from hr.attendance within the pay period.
The override matches Odoo 18 enterprise signature exactly.
"""
import logging
from datetime import datetime

import pytz

from odoo import fields, models

_logger = logging.getLogger(__name__)

_OT_WE_CODE = 'OVERTIME'


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _compute_worked_days_line_ids(self):
        """After base computation, append OVERTIME lines from hr.attendance."""
        super()._compute_worked_days_line_ids()
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                continue
            ot_hours = slip._compute_ot_hours()
            if not ot_hours:
                continue
            we_type = self.env['hr.work.entry.type'].search(
                [('code', '=', _OT_WE_CODE)], limit=1
            )
            if not we_type:
                we_type = self.env['hr.work.entry.type'].sudo().create({
                    'name': 'Tăng ca / OT',
                    'code': _OT_WE_CODE,
                    'color': 4,
                    'is_leave': False,
                })
            if _OT_WE_CODE in slip.worked_days_line_ids.mapped('work_entry_type_id.code'):
                continue
            contract = slip.contract_id
            hours_per_day = (
                contract.resource_calendar_id.hours_per_day
                if contract and contract.resource_calendar_id
                else 8.0
            ) or 8.0
            slip.worked_days_line_ids = [(0, 0, {
                'sequence': 99,
                'work_entry_type_id': we_type.id,
                'number_of_days': round(ot_hours / hours_per_day, 4),
                'number_of_hours': round(ot_hours, 4),
            })]

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """Extend base worked-day lines with an OVERTIME line (#144)."""
        res = super()._get_worked_day_lines(domain=domain, check_out_of_contract=check_out_of_contract)

        # Only add OT when computing regular (non-credit) lines
        if domain and any('is_credit_time' in str(d) for d in domain):
            return res

        ot_hours = self._compute_ot_hours()
        if not ot_hours:
            return res

        we_type = self.env['hr.work.entry.type'].search(
            [('code', '=', _OT_WE_CODE)], limit=1
        )
        if not we_type:
            we_type = self.env['hr.work.entry.type'].sudo().create({
                'name': 'Tăng ca / OT',
                'code': _OT_WE_CODE,
                'color': 4,
                'is_leave': False,
            })

        contract = self.contract_id
        hours_per_day = (
            contract.resource_calendar_id.hours_per_day
            if contract and contract.resource_calendar_id
            else 8.0
        ) or 8.0
        ot_days = round(ot_hours / hours_per_day, 4)

        # Skip if an OT line already exists
        if any(l.get('work_entry_type_id') == we_type.id for l in res):
            return res

        res.append({
            'sequence': 99,
            'work_entry_type_id': we_type.id,
            'number_of_days': ot_days,
            'number_of_hours': round(ot_hours, 4),
        })
        return res

    def _compute_ot_hours(self):
        """Sum overtime_hours from hr.attendance records in the pay period."""
        self.ensure_one()
        if not self.employee_id or not self.date_from or not self.date_to:
            return 0.0

        tz_name = (
            (self.contract_id.resource_calendar_id.tz if self.contract_id else None)
            or self.employee_id.resource_calendar_id.tz
            or self.env.user.tz
            or 'UTC'
        )
        local_tz = pytz.timezone(tz_name)

        dt_from = datetime.combine(self.date_from, datetime.min.time())
        dt_to = datetime.combine(self.date_to, datetime.max.time().replace(microsecond=0))
        dt_from_utc = local_tz.localize(dt_from).astimezone(pytz.utc).replace(tzinfo=None)
        dt_to_utc = local_tz.localize(dt_to).astimezone(pytz.utc).replace(tzinfo=None)

        attendances = self.env['hr.attendance'].search([
            ('employee_id', '=', self.employee_id.id),
            ('check_in', '>=', dt_from_utc),
            ('check_in', '<=', dt_to_utc),
            ('check_out', '!=', False),
        ])
        if not attendances:
            return 0.0

        # Flush computed fields to ensure overtime_hours is up-to-date
        attendances.flush_recordset(['overtime_hours'])
        ot = sum(att.overtime_hours for att in attendances if att.overtime_hours > 0)
        return ot
