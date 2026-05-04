# -*- coding: utf-8 -*-
"""
#144 — OT giờ từ chấm công → worked days trong bảng lương.

Overrides _get_worked_day_lines() to add an extra OVERTIME line
by summing overtime_hours from hr.attendance within the pay period.
"""
import logging
from datetime import datetime

import pytz

from odoo import fields, models

_logger = logging.getLogger(__name__)

# Work-entry type technical name for overtime (create if missing).
_OT_WE_CODE = 'OVERTIME'


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_worked_day_lines(self, domain=None):
        """Extend base worked-day lines with an OVERTIME line (#144)."""
        res = super()._get_worked_day_lines(domain=domain)

        for payslip in self:
            if not payslip.employee_id or not payslip.date_from or not payslip.date_to:
                continue

            # Fetch overtime hours from attendance records in the pay period.
            ot_hours = payslip._compute_ot_hours()
            if not ot_hours:
                continue

            # Find or create the OVERTIME work-entry type.
            we_type = self.env['hr.work.entry.type'].search(
                [('code', '=', _OT_WE_CODE)], limit=1
            )
            if not we_type:
                we_type = self.env['hr.work.entry.type'].create({
                    'name': 'Tăng ca / OT',
                    'code': _OT_WE_CODE,
                    'color': 4,
                    'is_leave': False,
                })

            # Convert OT hours to "days" using the contract's work-hour denominator.
            contract = payslip.contract_id
            hours_per_day = (
                contract.resource_calendar_id.hours_per_day
                if contract and contract.resource_calendar_id
                else 8.0
            ) or 8.0

            ot_days = ot_hours / hours_per_day

            # Check if an OT line already exists (avoid duplicates on recompute).
            existing = next(
                (l for l in res if l.get('work_entry_type_id') == we_type.id),
                None
            )
            if existing:
                existing['number_of_hours'] += ot_hours
                existing['number_of_days'] += ot_days
            else:
                res.append({
                    'sequence': 99,
                    'work_entry_type_id': we_type.id,
                    'number_of_days': round(ot_days, 4),
                    'number_of_hours': round(ot_hours, 4),
                })

        return res

    def _compute_ot_hours(self):
        """Sum overtime_hours from hr.attendance in the pay period."""
        self.ensure_one()
        # Convert date_from / date_to to UTC datetimes for attendance comparison
        tz_name = (
            self.employee_id.resource_calendar_id.tz
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
            ('overtime_hours', '>', 0),
        ])
        return sum(attendances.mapped('overtime_hours'))
